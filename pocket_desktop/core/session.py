# -*- coding: utf-8 -*-
"""会话：日志总线 + 控制台参数/真值持久化（~/.pocket-desktop.json）。"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class LogBus(QObject):
    line = Signal(str, str, str)     # ts, level, msg


class Session:
    def __init__(self):
        self.bus = LogBus()
        self.file = Path.home() / ".pocket-desktop.json"
        self.params: dict = {}
        self.truth: dict | None = None      # {lat, lon, alt}
        self.load()

    def log(self, msg: str, level: str = "info"):
        self.bus.line.emit(dt.datetime.now().strftime("%H:%M:%S"), level, msg)

    def load(self):
        try:
            self.params = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.params = {}

    def save(self):
        try:
            self.file.write_text(json.dumps(self.params, ensure_ascii=False,
                                            indent=1), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def runlog_dir() -> Path:
        import sys
        if getattr(sys, "frozen", False):
            d = Path(sys.executable).parent / "runlog"
        else:
            d = Path(__file__).resolve().parents[2] / "out" / "_pocket_runlog"
        d.mkdir(parents=True, exist_ok=True)
        return d
