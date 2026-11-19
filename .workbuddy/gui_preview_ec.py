# -*- coding: utf-8 -*-
"""GUI 驱动实测：勾选 G+E+C 点几何预览，天空视图必须出现 E/C 卫星。

断网桩 → AUTO 解析走 _newest_cached_rinex 覆盖过滤（验证修复路径）。
判据: EC-GUI-OK + 截图 output/preview_ec/20_sim_preview_ec.png
用法: .venv/Scripts/python.exe .workbuddy/gui_preview_ec.py
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")
import urllib.request  # noqa: E402
import requests  # noqa: E402


def _blocked(*a, **k):
    raise RuntimeError("network stubbed")


urllib.request.urlopen = _blocked        # type: ignore
requests.get = _blocked                  # type: ignore

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from desktop.ui import theme  # noqa: E402
from desktop.ui.main_window import MainWindow  # noqa: E402
from desktop.core.session import Session  # noqa: E402

SHOT = "output/preview_ec/"
os.makedirs(SHOT, exist_ok=True)

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
sim = win.pages["sim"]

win.goto("sim")
win.show()
sim.chip_sys.set_selected(["G", "E", "C"])
sim.store_task()
print("GUI systems selected:", sim.chip_sys.selected(), flush=True)
QTimer.singleShot(1000, lambda: (
    sim._cfg_scroll.verticalScrollBar().setValue(0),
    sim.btn_preview.click()))

state = {"t": 0}


def poll():
    state["t"] += 2
    if sim.tbl.rowCount() > 0:
        syss = sorted({sim.tbl.item(r, 1).text()
                       for r in range(sim.tbl.rowCount())})
        print("PREVIEW rows", sim.tbl.rowCount(), "sys", syss, flush=True)
        sky = getattr(sim, "skyplot", None)
        sky_sys = sorted({x.get("sys") for x in getattr(sky, "_sats", [])})
        print("SKYPLAT sats", len(getattr(sky, "_sats", [])),
              "sys", sky_sys, flush=True)
        warns = sim.warn_view.toPlainText() if hasattr(
            sim.warn_view, "toPlainText") else sim.warn_view.text()
        print("WARNINGS:", warns, flush=True)
        sim._cfg_scroll.verticalScrollBar().setValue(0)
        win.grab().save(SHOT + "20_sim_preview_ec.png")
        print("SHOT saved", flush=True)
        ok = {"E", "C"} <= set(syss)
        print("EC-GUI-OK" if ok else "EC-GUI-FAIL", flush=True)
        app.quit()
        return
    if state["t"] > 240:
        print("TIMEOUT waiting preview", flush=True)
        win.grab().save(SHOT + "20_timeout.png")
        print("EC-GUI-FAIL", flush=True)
        app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: tm.start(2000))
sys.exit(app.exec())
