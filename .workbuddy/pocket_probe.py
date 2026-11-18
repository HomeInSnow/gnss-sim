# -*- coding: utf-8 -*-
"""CLI 探针：引擎+WS 全帧打印，定位链路卡点。

用法: python .workbuddy/pocket_probe.py <iq_abs> [seconds=90]
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from PySide6.QtCore import QTimer                                # noqa: E402
from pocket_desktop.app import _make_app                         # noqa: E402
from pocket_desktop.core.engine_mgr import EngineMgr, ensure_tag # noqa: E402
from pocket_desktop.core.wslink import WsLink                    # noqa: E402

IQ = sys.argv[1]
SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 90
seen = {}


def main():
    app = _make_app()
    mgr = EngineMgr(log_fn=lambda m, lv="info": print(f"[eng:{lv}] {m}", flush=True))
    ws = WsLink()
    ensure_tag(IQ, 8, 25.0, "1575.42", "2", "16")

    def on_status(s):
        print(f"[ws] {s}", flush=True)
        if s == "connected":
            for c in ([{"cmd": "set_inp", "inp": 1, "fmt": 8, "fs": 25.0,
                        "file": IQ, "fo": "1575.42", "IQ": "2", "bits": "16",
                        "tscale": 1.0, "toff": 0.0},
                       {"cmd": "sub", "topic": "rcv_stat", "cyc": 500},
                       {"cmd": "sub", "topic": "ch_stat", "cyc": 1000,
                        "sys": "GPS", "chno": 0, "min_lock": 0.0, "rfch": 0,
                        "opt": 0},
                       {"cmd": "sub", "topic": "pvt_sol", "cyc": 500},
                       {"cmd": "sub", "topic": "log", "cyc": 300},
                       {"cmd": "start"}]):
                ws.cmd(c)

    def on_msg(m):
        t = m.get("type")
        seen[t] = seen.get(t, 0) + 1
        if t == "ack" or seen[t] <= 2 or (t == "pvt_sol" and seen[t] % 10 == 0):
            s = str(m)
            print(f"[{t}] {s[:300]}", flush=True)

    ws.status.connect(on_status)
    ws.msg.connect(on_msg)
    mgr.start("bothoff", __import__("pathlib").Path("out/_pocket_runlog"))
    ws.connect_to(mgr.port, retry_s=20)

    def stop():
        print("SEEN:", seen, flush=True)
        ws.cmd({"cmd": "stop"})
        QTimer.singleShot(600, lambda: (ws.close(), mgr.stop(), app.quit()))
    QTimer.singleShot(SECS * 1000, stop)
    app.exec()


main()
