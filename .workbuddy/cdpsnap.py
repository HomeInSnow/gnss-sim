# -*- coding: utf-8 -*-
"""纯 stdlib 的 CDP 浏览器控制/截图工具（控制 headless Edge）。

用法（作为库）:
    from cdpsnap import CDP
    c = CDP(port=9223)
    c.navigate("http://127.0.0.1:8010/")
    v = c.eval("1+1")
    c.wait_js("typeof addChannel==='function'", timeout=20)
    c.shot("out.png", clip=c.rect_of("#ch1 .card"))
前置：headless Edge 已以 --remote-debugging-port=9223 启动（见 start_edge 注释）。
"""
import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.parse
import urllib.request

CDP_PORT = int(os.environ.get("CDP_PORT", "9223"))


class ConnectionLost(Exception):
    pass


def _ws_connect(sock, path="/"):
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n" % (path, key))
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)
    assert b"101" in buf.split(b"\r\n")[0], buf[:120]


def _send_op(sock, op, payload=b""):
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    n = len(payload)
    hdr = bytes([0x80 | op])
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0xFE]) + struct.pack(">H", n)
    else:
        hdr += bytes([0xFF]) + struct.pack(">Q", n)
    sock.sendall(hdr + mask + masked)


def _read_frame(sock):
    """返回 (opcode, payload)；None=超时；自动应答 ping。"""
    def rd(n):
        buf = b""
        while len(buf) < n:
            try:
                b = sock.recv(min(n - len(buf), 1 << 16))
            except socket.timeout:
                return None
            except OSError:
                raise ConnectionLost()
            if not b:
                raise ConnectionLost()
            buf += b
        return buf
    h = rd(2)
    if h is None:
        return None
    op = h[0] & 0x0F
    n = h[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", rd(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", rd(8))[0]
    pl = rd(n) if n else b""
    if pl is None:
        return None
    if op == 0x9:
        _send_op(sock, 0xA, pl)
        return None
    return op, pl


class CDP:
    def __init__(self, port=CDP_PORT, url_sub="", create=False):
        """url_sub: 用 URL 子串挑选 page target；create=True 时新建一个后台页。"""
        self._id = 0
        self._evq = []           # 缓存事件
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}))   # 绕开沙箱 http_proxy
        if create:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/json/new?url=%s" % (
                    port, urllib.parse.quote(url_sub or "about:blank")),
                method="PUT")
            t = opener.open(req, timeout=5)
            pages = [json.load(t)]
        else:
            j = json.load(opener.open(
                "http://127.0.0.1:%d/json" % port, timeout=5))
            pages = [t for t in j if t.get("type") == "page"]
            if url_sub:
                pages = [t for t in pages if url_sub in t.get("url", "")]
        if not pages:
            raise RuntimeError("no page target; start Edge first")
        url = pages[0]["webSocketDebuggerUrl"]
        path = url.split(str(port), 1)[1]
        self.s = socket.create_connection(("127.0.0.1", port), timeout=10)
        _ws_connect(self.s, path)
        self.s.settimeout(2.0)
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")

    # ---- 底层 ----
    def cmd(self, method, params=None, timeout=60):
        self._id += 1
        mid = self._id
        _send_op(self.s, 0x1, json.dumps(
            {"id": mid, "method": method, "params": params or {}}).encode())
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                f = _read_frame(self.s)
            except socket.timeout:
                continue
            if f is None:
                continue
            op, pl = f
            if op != 0x1:
                continue
            m = json.loads(pl.decode("utf-8", "ignore"))
            if m.get("id") == mid:
                if "error" in m:
                    raise RuntimeError("%s -> %s" % (method, m["error"]))
                return m.get("result", {})
            else:
                self._evq.append(m)
        raise TimeoutError(method)

    def wait_event(self, name, timeout=30):
        for i, m in enumerate(self._evq):
            if m.get("method") == name:
                self._evq.pop(i)
                return m
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                f = _read_frame(self.s)
            except socket.timeout:
                continue
            if f is None:
                continue
            op, pl = f
            if op != 0x1:
                continue
            m = json.loads(pl.decode("utf-8", "ignore"))
            if m.get("method") == name:
                return m
        raise TimeoutError(name)

    # ---- 高层 ----
    def navigate(self, url, timeout=30):
        self.cmd("Page.navigate", {"url": url})
        self.wait_event("Page.loadEventFired", timeout)
        time.sleep(0.5)

    def eval(self, expr, await_promise=False, timeout=120):
        r = self.cmd("Runtime.evaluate", {
            "expression": expr, "returnByValue": True,
            "awaitPromise": await_promise}, timeout=timeout)
        res = r.get("result", {})
        if r.get("exceptionDetails"):
            raise RuntimeError("JS exception: " + json.dumps(
                r["exceptionDetails"].get("exception", {}))[:300])
        return res.get("value")

    def wait_js(self, expr, timeout=30, step=0.4):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.eval(expr):
                    return True
            except Exception:
                pass
            time.sleep(step)
        raise TimeoutError("wait_js: " + expr[:80])

    def set_viewport(self, w=1440, h=950, dsf=2):
        self.cmd("Emulation.setDeviceMetricsOverride",
                 {"width": w, "height": h, "deviceScaleFactor": dsf,
                  "mobile": False})

    def shot(self, path, clip=None, dsf=2):
        params = {"format": "png", "captureBeyondViewport": True}
        if clip:
            params["clip"] = dict(clip, scale=dsf)
        r = self.cmd("Page.captureScreenshot", params, timeout=120)
        data = base64.b64decode(r["data"])
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        print("shot ->", path, len(data), "bytes", flush=True)

    def rect_of(self, selector, pad=8, scroll=True):
        js = """(() => {
            const el = document.querySelector(%r);
            if (!el) return null;
            %s
            const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, width: r.width, height: r.height};
        })()""" % (selector, "el.scrollIntoView({block:'start'});" if scroll else "")
        r = self.eval(js)
        if r is None:
            raise RuntimeError("no element: " + selector)
        time.sleep(0.2)
        return {"x": max(0, r["x"] - pad), "y": max(0, r["y"] - pad),
                "width": r["width"] + 2 * pad, "height": r["height"] + 2 * pad}

    def click(self, selector):
        js = "(() => {const el=document.querySelector(%r);" \
             "if(!el) return 'NOEL'; el.click(); return 'OK';})()" % selector
        v = self.eval(js)
        if v != "OK":
            raise RuntimeError("click failed: " + selector)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass
