# -*- coding: utf-8 -*-
"""公众号 v3 重拍：浅色主题下重截文章场景 01/02/03（配置/预览/生成完成）。

克隆自 article_desk_drive.py，改动：
  - 输出目录 argv[1]（默认 output/wechat_l1ca_article/img3/）
  - SHOT 03 之后直接收尾退出（04/05 沿用 img2/ 的跟踪解版）
场景与 v2 完全同参（同种子 2281271），生成产物与主 run 逐字节一致。

用法：.venv/Scripts/python.exe .workbuddy/article_desk_drive_v3.py [imgdir]
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"   # offscreen 下无中文字体→豆腐块（theme_shot 同款配方）
os.environ["PYTHONWARNINGS"] = "ignore::FutureWarning"
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer, QDateTime, QDate, QTime
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

IMG = sys.argv[1] if len(sys.argv) > 1 else \
    "output/wechat_l1ca_article/img3/"
os.makedirs(IMG, exist_ok=True)

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
sim = win.pages["sim"]

win.goto("sim")
win.show()
sim.chip_sys.set_selected(["G"])          # 文章场景=GPS L1 C/A 单系统
sim.chip_band.set_selected([])            # 空=本征频段 L1CA
sim.dt_start.setDateTime(QDateTime(QDate(2023, 9, 28), QTime(23, 20, 0)))
sim.ed_dur.setText("60")
sim.cb_sr.setCurrentText("25000000")
sim.cb_fmt.setCurrentText("int16")
sim.ed_rinex.setText("AUTO")
sim.cb_iono.setCurrentText("klobuchar")
sim.cb_tropo.setCurrentText("saastamoinen")
sim.ck_models_iq.setChecked(True)
sim.ck_imp.setChecked(True)
sim.cb_imppreset.setCurrentIndex(max(0, sim.cb_imppreset.findData("manual")))
sim.ed_impsnr.setText("-18.33")
sim.ed_impseed.setText("2281271")
# 文章场景=纯 AWGN：其余损伤参数显式清零（防持久化任务夹带）
for w in (sim.ed_impcfo, sim.ed_impppm, sim.ed_impphn, sim.ed_impgain,
          sim.ed_impiqph, sim.ed_impdci, sim.ed_impdq, sim.ed_impclip,
          sim.ed_impbits):
    w.setText("0")
sim.ed_lat.setText("60.182537")
sim.ed_lon.setText("24.82826")
sim.ed_alt.setText("47.248")
sim._cfg_scroll.verticalScrollBar().setValue(0)
sim.store_task()
QTimer.singleShot(1200, lambda: (win.grab().save(IMG + "01_desk_config.png"),
                                 print("SHOT 01"), sim.btn_preview.click()))

state = {"phase": "preview", "t": 0}


def poll():
    state["t"] += 2
    if state["phase"] == "preview":
        if sim.tbl.rowCount() > 0:
            dop = (s.current().last_preview or {}).get("dop", {})
            print("PREVIEW sats", sim.tbl.rowCount(),
                  "pdop", dop.get("pdop"), "gdop", dop.get("gdop"))
            sim._cfg_scroll.verticalScrollBar().setValue(0)
            win.grab().save(IMG + "02_desk_preview.png")
            print("SHOT 02")
            state["phase"] = "gen"
            state["t"] = 0
            sim.btn_gen.click()
            return
    elif state["phase"] == "gen":
        if "生成完成" in sim.hint.text():
            print("GEN", sim.hint.text())
            win.grab().save(IMG + "03_desk_generate.png")
            print("SHOT 03 runid", s.last_outdir)
            print("ARTICLE-DRIVE-V3-OK")
            app.quit()
            return
    if state["t"] > 900:
        print("TIMEOUT at", state["phase"], sim.hint.text())
        app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: (tm.start(2000)))
sys.exit(app.exec())
