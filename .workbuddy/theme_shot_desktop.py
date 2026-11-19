# -*- coding: utf-8 -*-
"""配色 v2 验收截图：gnss-sim Desktop（仿真配置/星空预览/验证解算/日志）。

复用文章 run 20261118T152018562283 做快照解，不重新生成。
用法: .venv/Scripts/python.exe .workbuddy/theme_shot_desktop.py
判据: SHOT 10/11/12/13 齐 + THEME-SHOT-DESKTOP-OK
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer, QDateTime, QDate, QTime
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

SHOT = "output/theme_v2/"
os.makedirs(SHOT, exist_ok=True)
RUNID = "20261118T152018562283"

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
sim = win.pages["sim"]
v = win.pages["verify"]

win.goto("sim")
win.show()
sim.dt_start.setDateTime(QDateTime(QDate(2023, 9, 28), QTime(23, 20, 0)))
sim.ed_dur.setText("60")
sim.cb_sr.setCurrentText("25000000")
sim.cb_fmt.setCurrentText("int16")
sim.ed_rinex.setText("AUTO")
sim.cb_iono.setCurrentText("klobuchar")
sim.cb_tropo.setCurrentText("saastamoinen")
sim.ck_models_iq.setChecked(True)
sim.ck_imp.setChecked(True)
sim.ed_impsnr.setText("-18.33")
sim.ed_impseed.setText("2281271")
sim.ed_lat.setText("60.182537")
sim.ed_lon.setText("24.82826")
sim.ed_alt.setText("47.248")
sim._cfg_scroll.verticalScrollBar().setValue(0)
sim.store_task()
QTimer.singleShot(1200, lambda: (
    win.grab().save(SHOT + "10_desk_sim.png"),
    print("SHOT 10", flush=True),
    sim.btn_preview.click()))

state = {"phase": "preview", "t": 0}


def poll():
    state["t"] += 2
    if state["phase"] == "preview":
        if sim.tbl.rowCount() > 0:
            print("PREVIEW rows", sim.tbl.rowCount(), flush=True)
            sim._cfg_scroll.verticalScrollBar().setValue(0)
            win.grab().save(SHOT + "11_desk_preview.png")
            print("SHOT 11", flush=True)
            state["phase"] = "verify"
            state["t"] = 0
            win.goto("verify")
            v.ed_outdir.setText(RUNID)
            v.cb_track.setChecked(False)   # 快照解：配色验收只需 KPI/表/图
            from backend import inspector
            real = {4, 5, 9, 11, 12, 18, 20, 25, 26, 28, 29, 31}
            iq = inspector.read_iq(f"out/{RUNID}/gpssim.bin",
                                   "int16", int(25e6 * 0.020))
            met = {p: float(inspector.acquire(iq, 25e6, p)["metric_db"])
                   for p in range(1, 33)}
            fmax = max(x for p, x in met.items() if p not in real)
            tmin = min(x for p, x in met.items() if p in real)
            print("GATE false_max", round(fmax, 2), "true_min",
                  round(tmin, 2), flush=True)
            if tmin > fmax + 1.0:
                gate = round((fmax + tmin) / 2.0, 1)
                if gate > 9.0:
                    v.ed_mindb.setText(str(gate))
                    print("GATE set min_db", gate, flush=True)
            v.run_verify()
            return
    elif state["phase"] == "verify":
        txt = v.status_lbl.text()
        if "完成" in txt or "失败" in txt:
            print("VERIFY", txt, flush=True)
            win.pages["verify"].grab().save(SHOT + "12_desk_verify.png")
            print("SHOT 12", flush=True)
            state["phase"] = "log"
            win.goto("log")
            QTimer.singleShot(800, shoot_log)
            return
    if state["t"] > 900:
        print("TIMEOUT at", state["phase"], flush=True)
        win.grab().save(SHOT + "19_timeout.png")
        app.quit()


def shoot_log():
    win.grab().save(SHOT + "13_desk_log.png")
    print("SHOT 13", flush=True)
    print("THEME-SHOT-DESKTOP-OK", flush=True)
    app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: tm.start(2000))
sys.exit(app.exec())
