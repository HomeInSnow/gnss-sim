# -*- coding: utf-8 -*-
"""上篇新口径：验证页只用跟踪解（coh）跑主场景并截图 04/05 → img2/。

用法：.venv/Scripts/python.exe .workbuddy/art_desk_verify_trk.py <runid>
判据: SHOT 04/05 + TRK-RESHOT-OK + VERIFY 行（含 tracking error_m）。
"""
import sys

sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

IMG = "output/wechat_l1ca_article/img2/"
runid = sys.argv[1]

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
v = win.pages["verify"]
win.goto("verify")
win.show()
v.ed_outdir.setText(runid)
v.cb_track.setChecked(True)
v.cb_dll.setCurrentIndex(0)              # coh 相干E/L+PLL
v.ed_tracks.setText("15")                # 跟踪窗 15 s，控成本取稳态
v.ck_dll.setChecked(True)                # 叠加跟踪 chi 曲线
v.cb_trace.setChecked(True)
v.ed_mindb.setText("12")                 # 本场景 metric 10.4~15.9 dB，15 会误杀边际星
v.ed_mlat.setText("60.182537")           # 基准点 = 场景真值
v.ed_mlon.setText("24.82826")
v.ed_malt.setText("47.248")
v.run_verify()

state = {"t": 0, "done": False}


def shot_log():
    win.grab().save(IMG + "05_desk_log.png")
    print("SHOT 05", flush=True)
    print("TRK-RESHOT-OK", runid, flush=True)
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
        tf = res.get("tracking_fix") or {}
        print("VERIFY", txt, "| snap err", res.get("error_m"),
              "| pdop", res.get("pdop"), "| rms", res.get("residual_rms_m"),
              "| trk err", tf.get("error_m"),
              "| trk n", len(tf.get("prns_used") or tf.get("per_sv") or []),
              flush=True)
        if "失败" in txt:
            app.quit()
            return
        QTimer.singleShot(500, shot_verify)
        return
    if state["t"] > 2400:
        print("TIMEOUT", txt, flush=True)
        app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: tm.start(3000))
sys.exit(app.exec())
