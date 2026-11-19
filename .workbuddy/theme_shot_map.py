# -*- coding: utf-8 -*-
"""补拍：仿真页配置区滚动到底，拍"接收机位置"世界地图卡片。
用法: .venv/Scripts/python.exe .workbuddy/theme_shot_map.py [outdir]
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

SHOT = (sys.argv[1] if len(sys.argv) > 1 else "output/theme_v3_light/")
os.makedirs(SHOT, exist_ok=True)

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
win = MainWindow(Session())
sim = win.pages["sim"]
win.goto("sim")
win.show()


def shoot():
    sb = sim._cfg_scroll.verticalScrollBar()
    sb.setValue(sb.maximum())
    QTimer.singleShot(700, finish)


def finish():
    win.grab().save(SHOT + "14_desk_sim_map.png")
    print("MAP-SHOT-OK", flush=True)
    app.quit()


QTimer.singleShot(1200, shoot)
sys.exit(app.exec())
