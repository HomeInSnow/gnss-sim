# -*- coding: utf-8 -*-
"""PocketSDR Desktop 入口。

自检：
  python -m pocket_desktop.app --shot x.png --page console   （windows 平台截图）
  python -m pocket_desktop.app --selftest [iq_path]          （回放验收）
"""
from __future__ import annotations

import argparse
import sys


def _make_app():
    from PySide6.QtWidgets import QApplication
    from .ui import theme
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.QSS)
    _set_window_icon(app)
    return app


def _set_window_icon(app) -> None:
    """任务栏/窗口图标：frozen=_MEIPASS 随包，源码态=仓库目录。"""
    import pathlib
    from PySide6.QtGui import QIcon
    mp = getattr(sys, "_MEIPASS", None)
    base = (pathlib.Path(mp) if mp
            else pathlib.Path(__file__).resolve().parents[1])
    ico = base / "pocket_desktop" / "assets" / "app.ico"
    if ico.is_file():
        app.setWindowIcon(QIcon(str(ico)))


def run_selftest(iq: str | None) -> int:
    """拉起 both-off 引擎回放 60s 场景，收到 ≥1 个 FIX 解算即 PASS。"""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = _make_app()
    from PySide6.QtCore import QTimer
    from .ui.main_window import MainWindow
    from pathlib import Path

    if not iq:
        import sys as _s
        if getattr(_s, "frozen", False):
            root = Path(_s.executable).resolve().parent
        else:
            root = Path(__file__).resolve().parents[1]
        cands = sorted((root / "out").glob("*/gpssim.bin"))
        if not cands:
            print("SELFTEST-FAIL no iq candidate")
            return 2
        iq = str(cands[-1].resolve())
    else:
        iq = str(Path(iq).resolve())   # 引擎子进程 cwd 在别处，必须绝对路径
    from .core.engine_mgr import ensure_tag
    ensure_tag(iq, 8, 25.0, "1575.42", "2", "3")
    win = MainWindow()
    win.show()
    state = {"fix": 0, "t0": 0}

    from .ui.pages import solution as solmod
    orig = win.page_solution.update_pvt

    def spy(s: str):
        orig(s)
        if solmod.parse_pvt(s) is not None:
            state["fix"] += 1
    win.page_solution.update_pvt = spy

    def kick():
        cmds = [{"cmd": "set_inp", "inp": 1, "fmt": 8, "fs": 25.0,
                 "file": iq, "fo": "1575.42", "IQ": "2", "bits": "3",
                 "tscale": 1.0, "toff": 0.0},
                {"cmd": "set_sig", "sigs": "L1CA:1-32"},
                {"cmd": "sub", "topic": "pvt_sol", "cyc": 200},
                {"cmd": "sub", "topic": "log", "cyc": 300}]
        win.start_replay("bothoff", cmds)

    def poll():
        if state["fix"] >= 1:
            print(f"SELFTEST-PASS fixes={state['fix']} iq={iq}")
            win.close(); app.quit(); return
        state["t0"] += 2
        if state["t0"] > 150:
            print(f"SELFTEST-FAIL fixes=0 iq={iq}")
            win.close(); app.quit(); return
        QTimer.singleShot(2000, poll)

    QTimer.singleShot(300, kick)
    QTimer.singleShot(3000, poll)
    app.exec()
    return 0 if state["fix"] >= 1 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pocket-desktop")
    ap.add_argument("--shot", metavar="PNG", help="截图后退出")
    ap.add_argument("--page", default="console")
    ap.add_argument("--exit-after", type=float, default=None)  # 无参 GUI 常驻
    ap.add_argument("--show-delay", type=float, default=0.8)
    ap.add_argument("--selftest", nargs="?", const="", metavar="IQ")
    args = ap.parse_args(argv)

    if args.selftest is not None:
        return run_selftest(args.selftest or None)

    app = _make_app()
    from .ui.main_window import MainWindow
    from PySide6.QtCore import QTimer
    win = MainWindow()
    win.goto(args.page)
    win.page_console.restore()
    win.show()

    if args.shot:
        def snap():
            win.grab().save(args.shot)
            app.quit()
        QTimer.singleShot(int(args.show_delay * 1000), snap)
    elif args.exit_after:
        QTimer.singleShot(int(args.exit_after * 1000), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
