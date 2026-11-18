# -*- coding: utf-8 -*-
"""M2 驱动：真实跑一次 Verify Fix（跟踪解+trace），完成后截图验证页。

用法：.venv/Scripts/python.exe .workbuddy/desktop_m2_drive.py <runid> <out_png>
"""
import sys
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication
from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

runid = sys.argv[1]
png = sys.argv[2]

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
s.last_outdir = runid
win = MainWindow(s)
v = win.pages["verify"]
v.ed_outdir.setText(runid)
v.cb_track.setChecked(True)
win.goto("verify")
win.show()
v.run_verify(auto=True)

state = {"t": 0}


def poll():
    state["t"] += 2
    txt = v.status_lbl.text()
    if "完成" in txt or "失败" in txt:
        QTimer.singleShot(800, snap)
        return
    if state["t"] > 600:
        print("TIMEOUT", txt)
        app.quit()


def snap():
    res = v._result or {}
    tf = res.get("tracking_fix") or {}
    print("RESULT err", res.get("error_m"), "| track", tf.get("error_m"),
          "| svs", len((tf.get("per_sv") or {})))
    win.grab().save(png)
    print("SHOT", png)
    app.quit()


QTimer.singleShot(1500, poll)
tm = QTimer()
tm.timeout.connect(poll)
tm.start(2000)
sys.exit(app.exec())
