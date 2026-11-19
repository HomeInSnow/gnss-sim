# -*- coding: utf-8 -*-
"""下篇新口径实测：PocketSDR Desktop 原版(BRDC/SAAS) 回放大气+钟差全开 run。

IQ = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("out/20261119T091827202957/gpssim.bin")
Klobuchar+Saastamoinen+sv_clock+AWGN seed 2281271，12 星）。
nmea 由预写 out/_pocket_runlog/desktop_original.ini 的 paths 落盘。
截图输出 output/wechat_l1ca_article/img4/：20 控制台 21 监控 22 高级 23 数据 24 定位。
判据: SHOT 20~24 齐 + STD-SHOT-OK + 末尾 KPI/CN0 dump。
"""
import os
import sys
import json

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")

from PySide6.QtCore import QTimer                                # noqa: E402
from pocket_desktop.app import _make_app                         # noqa: E402
from pocket_desktop.ui.main_window import MainWindow             # noqa: E402

IQ = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("out/20261119T091827202957/gpssim.bin")
SHOT = "output/wechat_l1ca_article/img4/"
os.makedirs(SHOT, exist_ok=True)
SIGS = "L1CA:4,5,9,11,12,18,20,25,26,28,29,31"
st = {"t": 0}


def dump_monitor(win):
    m = win.page_monitor
    rows = []
    for r in range(m.tbl.rowCount()):
        row = [m.tbl.item(r, c) for c in range(m.tbl.columnCount())]
        rows.append([it.text() if it else "" for it in row])
    print("MONITOR-ROWS", json.dumps(rows, ensure_ascii=False), flush=True)


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
    cp.ed_sigs.setText(SIGS)
    cp.chip.set_selected(["原版 BRDC/SAAS"])   # 标准版
    cp.sp_lat.setValue(60.182537)
    cp.sp_lon.setValue(24.82826)
    cp.sp_alt.setValue(47.248)
    win.session.truth = {"lat": 60.182537, "lon": 24.82826, "h": 47.248}
    win.show()

    def shot_console():
        win.grab().save(SHOT + "20_pocket_console.png")
        print("SHOT 20", flush=True)
        cp._start()
        QTimer.singleShot(3000, poll)

    def poll():
        st["t"] += 2
        lock = win.page_monitor.tbl.rowCount()
        win.foot_l.setText(f"art-std: lock={lock} t={st['t']}")
        # monitor 截图推迟到回放后半段：lock 时长/#NAV/az/el 均已填充
        if (lock >= 6 and st["t"] >= 45) or st["t"] > 220:
            print("POLL lock", lock, "t", st["t"], flush=True)
            win.goto("monitor")
            dump_monitor(win)
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
            QTimer.singleShot(2000, shot_adv)
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
        # 等回放（60 s 场景）+ KPI 铺满后去定位页
        QTimer.singleShot(60000, goto_sol)

    def goto_sol():
        win.goto("solution")
        QTimer.singleShot(4000, shot_sol)

    def shot_sol():
        sol = win.page_solution
        try:
            dump_monitor(win)
        except Exception:
            pass
        print("KPI-H", sol.k_h.v.text(), "KPI-V", sol.k_v.v.text(), flush=True)
        texts = []
        for kid in dir(sol):
            o = getattr(sol, kid, None)
            if isinstance(o, type(sol.k_h)) and kid.startswith("k"):
                texts.append(f"{kid}={o.v.text()}|{o.s.text()}")
        print("KPI-ALL", " | ".join(texts), flush=True)
        win.grab().save(SHOT + "24_pocket_sol.png")
        print("SHOT 24", flush=True)
        print("STD-SHOT-OK", flush=True)
        try:
            cp._stop()
        except Exception:
            pass
        app.quit()

    QTimer.singleShot(900, shot_console)
    rc = app.exec()
    sys.exit(rc)


main()
