# -*- coding: utf-8 -*-
"""配色 v2 验收截图：PocketSDR Desktop（控制台/监控/高级/数据/日志）。

回放 afzero 干净 run 20261118T104257507553（CS16 25Msps 1575.42，带 .tag）。
用法: .venv/Scripts/python.exe .workbuddy/theme_shot_pocket.py
判据: SHOT 20~24 齐 + THEME-SHOT-POCKET-OK
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")

from PySide6.QtCore import QTimer                                # noqa: E402
from pocket_desktop.app import _make_app                         # noqa: E402
from pocket_desktop.ui.main_window import MainWindow             # noqa: E402

IQ = os.path.abspath("out/20261118T104257507553/gpssim.bin")
SHOT = "output/theme_v2/"
os.makedirs(SHOT, exist_ok=True)
st = {"t": 0}


def main():
    app = _make_app()
    win = MainWindow()
    cp = win.page_console
    cp.ed_file.setText(IQ)
    cp.cb_fmt.setCurrentIndex(0)          # CS16
    cp.sp_fs.setValue(25.0)
    cp.ed_fo.setText("1575.42")
    cp.ed_iq.setText("2")
    cp.ed_bits.setText("16")
    cp.sp_lat.setValue(60.182537)
    cp.sp_lon.setValue(24.82826)
    cp.sp_alt.setValue(47.248)
    win.show()

    def shot_console():
        win.grab().save(SHOT + "20_pocket_console.png")
        print("SHOT 20", flush=True)
        cp._start()
        QTimer.singleShot(3000, poll)

    def poll():
        st["t"] += 2
        lock = win.page_monitor.tbl.rowCount()
        win.foot_l.setText(f"theme-shot: lock={lock} t={st['t']}")
        if lock >= 6 or st["t"] > 160:
            print("POLL lock", lock, "t", st["t"], flush=True)
            win.goto("monitor")
            QTimer.singleShot(1500, shot_monitor)
            return
        QTimer.singleShot(2000, poll)

    def shot_monitor():
        win.grab().save(SHOT + "21_pocket_monitor.png")
        print("SHOT 21", flush=True)
        win.goto("advanced")
        QTimer.singleShot(500, lambda: wait_adv(0.0))

    def wait_adv(elapsed):
        adv = win.page_advanced
        if (adv.lock_chs and adv.ch in adv.lock_chs
                and adv.psd_msg and adv.corr) or elapsed > 12:
            QTimer.singleShot(3000, shot_adv)
        else:
            QTimer.singleShot(500, lambda: wait_adv(elapsed + 0.5))

    def shot_adv():
        win.grab().save(SHOT + "22_pocket_advanced.png")
        print("SHOT 22", flush=True)
        win.goto("data")
        QTimer.singleShot(500, lambda: wait_data(0.0))

    def wait_data(elapsed):
        dp = win.page_data
        if (dp.tbl_ch.rowCount() >= 4 or dp.tbl_sat.rowCount() >= 4
                or elapsed > 15):
            QTimer.singleShot(1200, shoot_data)
        else:
            QTimer.singleShot(500, lambda: wait_data(elapsed + 0.5))

    def shoot_data():
        win.grab().save(SHOT + "23_pocket_data.png")
        print("SHOT 23", flush=True)
        win.goto("log")
        QTimer.singleShot(800, shoot_log)

    def shoot_log():
        # 引擎仍在跑，日志页此时应有通道/捕获流水
        win.grab().save(SHOT + "24_pocket_log.png")
        print("SHOT 24", flush=True)
        print("THEME-SHOT-POCKET-OK", flush=True)
        try:
            cp._stop()
        except Exception:
            pass
        app.quit()

    # poll 链只允许从 shot_console 内部启动一次，防双链互踩截图
    QTimer.singleShot(900, shot_console)
    rc = app.exec()
    sys.exit(rc)


main()
