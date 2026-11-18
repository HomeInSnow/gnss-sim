# -*- coding: utf-8 -*-
"""高级页增强 + 数据页 GUI 验收驱动 v2。

用法: python .workbuddy/pocket_adv_drive.py <iq_abs_path> <shots_dir>
判据: 高级页 psd/corr/hist 齐 + 频段刻度 sigs 非空 +
      数据页观测表 >=4 行 + 卫星表 >=4 行 → ADV2-DRIVE-OK
"""
import os
import sys

import numpy as np

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")

from PySide6.QtCore import QTimer                                # noqa: E402
from pocket_desktop.app import _make_app                         # noqa: E402
from pocket_desktop.ui.main_window import MainWindow             # noqa: E402

IQ, SHOTS = sys.argv[1], sys.argv[2]
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
    QTimer.singleShot(600, cp._start)

    def poll():
        st["t"] += 2
        nfix = len(win.page_solution.pts)
        lock = win.page_monitor.tbl.rowCount()
        win.foot_l.setText(f"adv2-drive: fix={nfix} lock={lock} t={st['t']}")
        if nfix >= 12 and lock >= 4:
            win.goto("advanced")
            QTimer.singleShot(500, lambda: wait_adv(0.0))
            return
        if st["t"] > 170:
            win.grab().save(f"{SHOTS}/p6_timeout.png")
            print(f"ADV2-DRIVE-TIMEOUT fix={nfix} lock={lock}", flush=True)
            app.quit()
            return
        QTimer.singleShot(2000, poll)

    def wait_adv(elapsed):
        adv = win.page_advanced
        if (adv.lock_chs and adv.ch in adv.lock_chs
                and adv.psd_msg and adv.corr) or elapsed > 10:
            QTimer.singleShot(3000, shoot_adv)
        else:
            QTimer.singleShot(500, lambda: wait_adv(elapsed + 0.5))

    def shoot_adv():
        adv = win.page_advanced
        win.grab().save(f"{SHOTS}/p6_advanced_enh.png")
        win.goto("data")
        QTimer.singleShot(500, lambda: wait_data(0.0))

    def wait_data(elapsed):
        dp = win.page_data
        if ((dp.tbl_ch.rowCount() >= 4 and dp.tbl_sat.rowCount() >= 4)
                or elapsed > 12):
            QTimer.singleShot(1200, shoot_data)
        else:
            QTimer.singleShot(500, lambda: wait_data(elapsed + 0.5))

    def shoot_data():
        adv, dp = win.page_advanced, win.page_data
        sigs_n = sum(len(v) for v in adv._sigs.values())
        cmax = 0.0
        if adv.corr is not None and adv.corr["n"]:
            cmax = float(np.max(np.abs(adv.corr["C"])))
        ok = (adv.psd_msg and adv.corr and cmax > 0 and adv.hist
              and adv.hist["n"] > 0 and sigs_n > 0
              and dp.tbl_ch.rowCount() >= 4 and dp.tbl_sat.rowCount() >= 4)
        win.grab().save(f"{SHOTS}/p6_data.png")
        info = dict(ch=adv.ch, sigs=sigs_n, Cmax=round(cmax, 2),
                    ch_rows=dp.tbl_ch.rowCount(),
                    ch_cols=dp.tbl_ch.columnCount(),
                    sat_rows=dp.tbl_sat.rowCount())
        print(("ADV2-DRIVE-OK " if ok else "ADV2-DRIVE-BAD ") + str(info),
              flush=True)
        app.quit()

    QTimer.singleShot(3000, poll)
    rc = app.exec()
    sys.exit(rc)


main()
