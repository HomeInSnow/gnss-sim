# -*- coding: utf-8 -*-
"""高级图谱页 GUI 验收驱动：回放 → 锁定 → 进入高级页 → 截 IQ/I 两模式图。

用法: python .workbuddy/pocket_adv_drive.py <iq_abs_path> <shots_dir>
判据: 进入高级页后 psd/corr/corr_hist 均有帧且 corr cn0>30 → ADV-DRIVE-OK
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
        win.foot_l.setText(f"adv-drive: fix={nfix} lock={lock} t={st['t']}")
        if nfix >= 12 and lock >= 4:
            enter_adv()
            return
        if st["t"] > 170:
            win.grab().save(f"{SHOTS}/p5_timeout.png")
            print(f"ADV-DRIVE-TIMEOUT fix={nfix} lock={lock}", flush=True)
            app.quit()
            return
        QTimer.singleShot(2000, poll)

    def enter_adv():
        win.goto("advanced")
        QTimer.singleShot(500, lambda: wait_ch(0.0))

    def wait_ch(elapsed):
        # 等 ch_stat 首帧到达（页面内自动锁定首个在用通道）
        adv = win.page_advanced
        if (adv.lock_chs and adv.ch in adv.lock_chs) or elapsed > 8.0:
            QTimer.singleShot(3500, shoot_iq)
        else:
            QTimer.singleShot(500, lambda: wait_ch(elapsed + 0.5))

    def shoot_iq():
        adv = win.page_advanced
        win.grab().save(f"{SHOTS}/p5_advanced_iq.png")
        adv.cb_mode.setCurrentText("I")   # 切换显示量 → 等下一帧重绘
        QTimer.singleShot(1500, shoot_i)

    def shoot_i():
        win.grab().save(f"{SHOTS}/p5_advanced_i.png")
        adv = win.page_advanced
        cmax = 0.0
        if adv.corr is not None and adv.corr["n"]:
            cmax = float(np.max(np.abs(adv.corr["C"])))
        cn0_stat = 0.0
        if adv.stat_row:
            try:
                cn0_stat = float(adv.stat_row[6])
            except (ValueError, IndexError):
                pass
        ok = (adv.psd_msg is not None and adv.corr is not None and cmax > 0
              and adv.hist is not None and adv.hist["n"] > 0
              and cn0_stat > 35.0)
        info = dict(ch=adv.ch, lock_chs=len(adv.lock_chs),
                    corr_n=adv.corr["n"] if adv.corr else 0,
                    npos=adv.corr["npos"] if adv.corr else 0,
                    Cmax=round(cmax, 2), cn0_chstat=round(cn0_stat, 1),
                    hist_n=adv.hist["n"] if adv.hist else 0,
                    psd_n=adv.psd_msg["psd"].size if adv.psd_msg else 0)
        print(("ADV-DRIVE-OK " if ok else "ADV-DRIVE-BAD ") + str(info),
              flush=True)
        app.quit()

    QTimer.singleShot(3000, poll)
    rc = app.exec()
    sys.exit(rc)


main()
