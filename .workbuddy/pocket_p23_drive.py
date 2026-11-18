# -*- coding: utf-8 -*-
"""P2/P3 联合验收驱动：程序化开始回放 → 锁定后截监控/定位页。

用法: python .workbuddy/pocket_p23_drive.py <iq_abs_path> <shots_dir>
判据: solution 页累计解 >=12 → 截 monitor/solution 两图。
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")

from PySide6.QtCore import QTimer                                # noqa: E402
from pocket_desktop.app import _make_app                         # noqa: E402
from pocket_desktop.ui.main_window import MainWindow             # noqa: E402

IQ, SHOTS = sys.argv[1], sys.argv[2]
st = {"phase": "run", "t": 0}


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
    QTimer.singleShot(600, cp._start)

    def poll():
        st["t"] += 2
        nfix = len(win.page_solution.pts)
        lock = win.page_monitor.tbl.rowCount()
        win.foot_l.setText(f"drive: fix={nfix} lock={lock} t={st['t']}")
        if nfix >= 12 and lock >= 4:
            win.goto("monitor")
            QTimer.singleShot(1500, lambda: (
                win.grab().save(f"{SHOTS}/p2_monitor_live.png"),
                win.goto("solution"),
                QTimer.singleShot(1500, lambda: (
                    win.grab().save(f"{SHOTS}/p3_solution_live.png"),
                    print(f"DRIVE-OK fix={nfix} lock={lock}", flush=True),
                    app.quit()))))
            return
        if st["t"] > 170:
            win.grab().save(f"{SHOTS}/p2_timeout.png")
            print(f"DRIVE-TIMEOUT fix={nfix} lock={lock}", flush=True)
            app.quit()
            return
        QTimer.singleShot(2000, poll)

    QTimer.singleShot(3000, poll)
    rc = app.exec()
    sys.exit(rc)


main()
