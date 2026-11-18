# -*- coding: utf-8 -*-
"""复用已生成 run，仅重跑验证（勾逐历元 trace，关跟踪解）并截图 04/05。

用法：.venv/Scripts/python.exe .workbuddy/article_verify_reshot.py <runid>
"""
import sys

sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

IMG = "output/wechat_l1ca_article/img/"
runid = sys.argv[1]

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
v = win.pages["verify"]
win.goto("verify")
win.show()
v.ed_outdir.setText(runid)
v.cb_track.setChecked(False)
v.cb_trace.setChecked(True)          # 逐历元 trace：填码相位误差图
v.run_verify()

state = {"t": 0, "done": False}


def shot_log():
    win.grab().save(IMG + "05_desk_log.png")
    print("SHOT 05", flush=True)
    print("RESHOT-OK", runid, flush=True)
    app.quit()


def shot_verify():
    win.grab().save(IMG + "04_desk_verify.png")
    print("SHOT 04", flush=True)
    win.goto("log")
    QTimer.singleShot(800, shot_log)


def poll():
    if state["done"]:
        return
    state["t"] += 3
    txt = v.status_lbl.text()
    if "完成" in txt or "失败" in txt:
        state["done"] = True
        res = v._result or {}
        print("VERIFY", txt, "| err", res.get("error_m"),
              "| pdop", res.get("pdop"), "| rms", res.get("residual_rms_m"),
              "| svs", res.get("prns_used"), flush=True)
        QTimer.singleShot(500, shot_verify)
        return
    if state["t"] > 1200:
        print("TIMEOUT", txt, flush=True)
        app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: tm.start(3000))
sys.exit(app.exec())
