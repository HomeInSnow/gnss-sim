# -*- coding: utf-8 -*-
"""高级图谱探针：起引擎回放 60s 场景，订阅 psd/corr/corr_hist，
统计二进制帧到达与字段有效性。PROBE-OK 判据：三类帧均 ≥5 且字段合理。"""
import os
import sys
import time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, ".")

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402
from pocket_desktop.core.engine_mgr import EngineMgr, ensure_tag  # noqa: E402
from pocket_desktop.core.wslink import WsLink  # noqa: E402

IQ = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\out\20261118T104257507553\gpssim.bin"
IQ = os.path.abspath(IQ)
ensure_tag(IQ, 8, 25.0, "1575.42", "2", "16")

app = QCoreApplication(sys.argv)
cnt = {"psd": 0, "corr": 0, "corr_hist": 0, "ch_stat": 0, "ack_bad": 0}
sample = {}
st = {"t0": 0}


def on_msg(m):
    t = m.get("type")
    if t == "bin":
        f = m.get("frm")
        cnt[f] = cnt.get(f, 0) + 1
        if f not in sample:
            if f == "psd":
                sample[f] = (m["rfch"], m["iq"], round(m["fo"] / 1e6, 3),
                             round(m["fs"] / 1e6, 2), m["psd"].size,
                             round(float(m["psd"].min()), 1),
                             round(float(m["psd"].max()), 1))
            elif f == "corr":
                sample[f] = (m["ch"], m["n"], m["npos"], round(m["cn0"], 1),
                             round(m["fd"], 1), round(m["coff"], 5),
                             round(float(abs(m["C"][0::2]).max()), 2))
            else:
                sample[f] = (m["ch"], m["n"], round(m["T"], 4),
                             round(m["time"], 3))
    elif t == "ch_stat":
        cnt["ch_stat"] += 1
    elif t == "ack" and not m.get("ok", True):
        cnt["ack_bad"] += 1
        print("ACK-REJ", m)


def on_status(s):
    if s == "connected":
        for c in cmds:
            ws.cmd(c)


mgr = EngineMgr(log_fn=lambda *a: None)
ws = WsLink()
ws.msg.connect(on_msg)


def kick():
    mgr.start("bothoff", __import__("pathlib").Path(".workbuddy/probe_runlog"))


mgr.started.connect(lambda p: (ws.connect_to(p), on_start(p)))
ws.status.connect(on_status)


def on_start(p):
    pass


cmds = [
    {"cmd": "set_inp", "inp": 1, "fmt": 8, "fs": 25.0, "file": IQ,
     "fo": "1575.42", "IQ": "2", "bits": "16", "tscale": 1, "toff": 0},
    {"cmd": "set_sig", "sigs": "L1CA:1-32"},
    {"cmd": "start"},
    {"cmd": "sub", "topic": "psd", "rfch": 1, "cyc": 200, "nfft": 2048,
     "tave": 0.01},
    {"cmd": "sub", "topic": "corr", "ch": 1, "cyc": 100, "width": 5e-6},
    {"cmd": "sub", "topic": "corr_hist", "ch": 1, "cyc": 100, "tspan": 1.0},
    {"cmd": "sub", "topic": "ch_stat", "chno": 0, "opt": 1, "cyc": 200,
     "min_lock": 2.0},
]


def poll():
    st["t0"] += 2
    if st["t0"] % 10 == 0:
        print(f"t={st['t0']}s", cnt)
    if cnt["psd"] >= 5 and cnt["corr"] >= 5 and cnt["corr_hist"] >= 5 \
            and cnt["ch_stat"] >= 2:
        print("PROBE-OK", cnt)
        for k, v in sample.items():
            print(" sample", k, v)
        done(0)
    elif st["t0"] > 90:
        print("PROBE-FAIL", cnt)
        for k, v in sample.items():
            print(" sample", k, v)
        done(1)
    else:
        QTimer.singleShot(2000, poll)


def done(rc):
    ws.close()
    mgr.stop()
    app.exit(rc)


QTimer.singleShot(300, kick)
QTimer.singleShot(3000, poll)
sys.exit(app.exec())
