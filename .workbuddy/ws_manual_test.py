# -*- coding: utf-8 -*-
"""最小 WebSocket 客户端：模拟浏览器手动在 WebUI 填表并点 Start 的路径。
发送与页面 JS 完全相同的 set_inp/set_sig/set_out + start 命令，
验证"手动使用 WebUI"路线（不经 -ini/-start 快捷方式）可用。
用法: python ws_manual_test.py <port> <run_s>
"""
import base64
import json
import os
import socket
import struct
import sys
import time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8084
RUN_S = float(sys.argv[2]) if len(sys.argv) > 2 else 75
OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/pocket_web_verify/"
SAT = "2,7,8,10,11,12,14,22,23,24,33"

def ws_connect(sock):
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n" % key)
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)
    assert b"101" in buf.split(b"\r\n")[0], buf[:80]

def ws_send(sock, text):
    payload = text.encode()
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    n = len(payload)
    hdr = b"\x81"
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0xFE]) + struct.pack(">H", n)
    else:
        hdr += bytes([0xFF]) + struct.pack(">Q", n)
    sock.sendall(hdr + mask + masked)

def ws_send_op(sock, op, payload=b""):
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

def ws_read_frame(sock):
    """读一个服务端帧（无掩码），返回 text 或 None（超时）/ 抛 ConnectionLost；自动回 pong"""
    def rd(n):
        buf = b""
        while len(buf) < n:
            try:
                b = sock.recv(n - len(buf))
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
    if op == 0x9:                # ping -> pong（浏览器自动做，裸客户端必须自己回）
        ws_send_op(sock, 0xA, pl or b"")
        return None
    if op == 0x8:
        ws_send_op(sock, 0x8, pl[:2] if len(pl) >= 2 else b"")
        raise ConnectionLost("close frame: " + (pl[:60].decode("utf-8", "ignore") if pl else ""))
    if op == 0x1 and pl:
        return pl.decode("utf-8", "ignore")
    return None

class ConnectionLost(Exception):
    pass

def ws_recv_avail(sock, deadline, echo=False):
    """尽力读取到 deadline；echo=True 时打印收到的文本帧"""
    sock.settimeout(0.5)
    while time.time() < deadline:
        try:
            t = ws_read_frame(sock)
        except socket.timeout:
            continue
        except ConnectionLost as e:
            print("CONN-CLOSED:", e, flush=True)
            return False
        if t and echo:
            print("  <<", t[:220], flush=True)
    return True

def main():
    s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
    ws_connect(s)
    now = time.time
    cmds = [
        {"cmd": "set_inp", "inp": 1, "fmt": 8, "fs": 25.0, "toff": 0.0,
         "tscale": 1.0,
         "file": "D:/workbuddy/GNSSSignal/gnss-sim-desktop/out/"
                 "20261117T123629105786/pocket_e1e5a.bin",
         "fo": "1575.42,1176.45,0,0,0,0,0,0",
         "IQ": "2,2,2,2,2,2,2,2", "bits": "2,2,2,2,2,2,2,2",
         "lpf": "0,0,0,0,0,0,0,0"},
        {"cmd": "set_sig",
         "sigs": "E1B:%s E5AI:%s" % (SAT, SAT),
         "satno": "1-32|-7-6/1-27|1-36|1-9|1-63|1-14|120-158",
         "satasgn": "", "rfch": ""},
        {"cmd": "set_out", "types": "1,3,0,0,0,0,0,0",
         "log_mask": "1,1,1,1,1,1,1,1,1,1,1",
         "paths": OUT + "web4.nmea|" + OUT + "web4.log| | | | | |"},
        {"cmd": "start"},
    ]
    for c in cmds:
        ws_send(s, json.dumps(c))
        ws_recv_avail(s, now() + 1.0)
        print("sent:", c["cmd"], flush=True)
    ws_recv_avail(s, now() + RUN_S)  # 实时回放期间保持连接
    ws_send(s, json.dumps({"cmd": "stop"}))
    ws_recv_avail(s, now() + 2)
    s.close()
    print("manual-path session done")

if __name__ == "__main__":
    main()
