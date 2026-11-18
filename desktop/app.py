# -*- coding: utf-8 -*-
"""桌面版入口。

开发运行（仓库根目录）：
    .venv/Scripts/python.exe -m desktop.app
自检模式（无头截图，供回归/审阅）：
    .venv/Scripts/python.exe -m desktop.app --shot C:/Temp/sim.png --page sim
    --exit-after <秒> 定时退出；--page 定位初始页。
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

# 允许 python desktop/app.py 直跑
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _apply_frozen_dirs() -> None:
    """打包环境：out/data/logs 落 exe 旁（可写、用户可见），须在导入 backend 前。"""
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys.executable).resolve().parent
        os.environ.setdefault("OUT_DIR", str(base / "out"))
        os.environ.setdefault("DATA_DIR", str(base / "data"))
        os.environ.setdefault("LOG_DIR", str(base / "logs"))
        os.environ.setdefault("ALLOW_TX", "0")


def main() -> int:
    _apply_frozen_dirs()
    ap = argparse.ArgumentParser(prog="gnss-sim-desktop")
    ap.add_argument("--shot", help="窗口截图输出 png（自检用）")
    ap.add_argument("--page", default="sim",
                    choices=["sim", "verify", "iq", "traj", "log", "hist"])
    ap.add_argument("--outdir", default="",
                    help="预载场景 runid（图谱/验证页直接可用）")
    ap.add_argument("--exit-after", type=float, default=0.0,
                    help="N 秒后自动退出")
    ap.add_argument("--show-delay", type=float, default=0.6,
                    help="截图前等待渲染的秒数")
    ap.add_argument("--selftest", action="store_true",
                    help="打包冒烟：桥接全链路（preview→generate→receiver）后退出")
    args = ap.parse_args()

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from desktop.ui import theme
    from desktop.ui.main_window import MainWindow
    from desktop.core.session import Session

    app = QApplication(sys.argv)
    app.setApplicationName("gnss-sim")
    app.setStyleSheet(theme.QSS)

    if args.selftest:
        from desktop.core import bridge
        from desktop.core.model import SimTask
        t = SimTask(name="selftest", duration_s=2,
                    sample_rate=1000000.0, sample_format="int8",
                    systems=["G"])
        pv = bridge.preview(t.preview_body())
        nsats = len(pv.get("satellites", []) or [])
        done = bridge.generate(t.generate_body())
        od = done.get("outdir", "")
        res = bridge.receiver(od, marker={"lat": t.lat, "lon": t.lon,
                                          "alt": t.alt}, trace=False)
        err = res.get("error_m")
        print(f"SELFTEST outdir={od} sats={nsats} err_m={err}")
        ok = (nsats >= 4 and "error" not in res
              and isinstance(err, (int, float)) and err < 200)
        print("SELFTEST-PASS" if ok else "SELFTEST-FAIL")
        return 0 if ok else 2

    session = Session()
    win = MainWindow(session)
    if args.outdir:
        session.last_outdir = args.outdir
        win.pages["iq"].ed_outdir.setText(args.outdir)
        win.pages["verify"].ed_outdir.setText(args.outdir)
    win.goto(args.page)
    win.show()
    if args.outdir and args.page == "iq":
        win.pages["iq"]._load_iq()
        win.pages["iq"]._load_corr()
    if args.outdir and args.page == "verify":
        win.pages["verify"]._load_traces()

    if args.exit_after > 0:
        QTimer.singleShot(int(args.exit_after * 1000), app.quit)
    if args.shot:
        def _snap():
            ok = win.grab().save(args.shot)
            print(f"SHOT {'OK' if ok else 'FAIL'} {args.shot}")
            app.quit()
        QTimer.singleShot(int(args.show_delay * 1000), _snap)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
