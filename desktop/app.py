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
import pathlib
import sys

# 允许 python desktop/app.py 直跑
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(prog="gnss-sim-desktop")
    ap.add_argument("--shot", help="窗口截图输出 png（自检用）")
    ap.add_argument("--page", default="sim",
                    choices=["sim", "verify", "iq", "traj", "log", "hist"])
    ap.add_argument("--exit-after", type=float, default=0.0,
                    help="N 秒后自动退出")
    ap.add_argument("--show-delay", type=float, default=0.6,
                    help="截图前等待渲染的秒数")
    args = ap.parse_args()

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from desktop.ui import theme
    from desktop.ui.main_window import MainWindow
    from desktop.core.session import Session

    app = QApplication(sys.argv)
    app.setApplicationName("gnss-sim")
    app.setStyleSheet(theme.QSS)

    session = Session()
    win = MainWindow(session)
    win.goto(args.page)
    win.show()

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
