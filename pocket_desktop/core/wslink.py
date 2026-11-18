# -*- coding: utf-8 -*-
"""WebSocket 链路：连接引擎 /ws，收 JSON topic 帧 → Qt 信号；命令队列下发。

协议（src/sdr_web.c 实证）：
  发 {"cmd":"sub","topic":"ch_stat","cyc":200,...} / {"cmd":"start"} 等
  收 {"type":"rcv_stat"|"ch_stat"|"pvt_sol","str":...} /
     {"type":"sat_stat","sats":[{sat,az,el,pvt,obs,eph,svh,fcn}]} /
     {"type":"log","lines":[...]} / {"type":"ack","cmd":...,"ok":bool,...}
  二进制帧（psd/corr/corr_hist）经 core/binframe.py 解码后以
     {"type":"bin","frm":"psd"|"corr"|"corr_hist",...} 发出
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading

import websockets
from PySide6.QtCore import QThread, Signal


class WsLink(QThread):
    status = Signal(str)            # connecting / connected / closed / error:<..>
    msg = Signal(dict)              # 全部解好码的帧

    def __init__(self, parent=None):
        super().__init__(parent)
        self._q: "queue.Queue[dict | None]" = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._host, self._port = "127.0.0.1", 0
        self._deadline = 0.0

    # ── 对外接口（UI 线程调用）───────────────────────────────────
    def connect_to(self, port: int, retry_s: float = 15.0):
        """引擎 web 服务需启动时间：retry_s 秒内反复尝试连接。"""
        import time as _t
        self._host, self._port = "127.0.0.1", port
        self._deadline = _t.monotonic() + retry_s
        if not self.isRunning():
            self.start()

    def cmd(self, d: dict):
        self._q.put(d)

    def close(self):
        self._q.put(None)
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(loop.stop)

    # ── 线程体 ──────────────────────────────────────────────────
    def run(self):
        try:
            asyncio.run(self._main())
        except Exception as e:                       # noqa: BLE001
            self.status.emit(f"error:{type(e).__name__}: {e}")

    async def _main(self):
        import time as _t
        self.status.emit("connecting")
        ws = None
        while True:
            if ws is None:
                try:
                    ws = await websockets.connect(
                        f"ws://{self._host}:{self._port}/ws",
                        max_size=4 << 20,
                        open_timeout=2.0, ping_interval=None)
                    self.status.emit("connected")
                except OSError:
                    ws = None
                    if _t.monotonic() > self._deadline:
                        self.status.emit("closed")
                        return
                    await asyncio.sleep(0.3)
                    continue
            # 冲刷待发命令
            try:
                while True:
                    item = self._q.get_nowait()
                    if item is None:
                        await ws.close()
                        self.status.emit("closed")
                        return
                    await ws.send(json.dumps(item))
            except queue.Empty:
                pass
            # 收帧（超时回主循环查命令队列）
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.15)
            except asyncio.TimeoutError:
                continue
            except Exception:                        # noqa: BLE001
                await ws.close()
                ws = None                            # 断线 → 重连窗口内自动重连
                if _t.monotonic() > self._deadline:
                    self.status.emit("closed")
                    return
                continue
            if not isinstance(raw, str):
                from .binframe import decode_frame
                d = decode_frame(bytes(raw))
                if d is not None:
                    self.msg.emit(d)
                continue
            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self.msg.emit(frame)
