# -*- coding: utf-8 -*-
"""QThread 工作器：短任务（文件探测/run meta 读取）用 FnWorker。"""
from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal


class FnWorker(QThread):
    """在后台线程执行任意可调用，结果经信号回 UI。"""
    ok = Signal(object)
    fail = Signal(str)

    def __init__(self, fn, *a, kw: dict | None = None,
                 busy_msg: str = "", parent=None):
        super().__init__(parent)
        self._fn, self._a, self._kw = fn, a, dict(kw or {})
        self.busy_msg = busy_msg

    def run(self):                             # noqa: D102
        try:
            self.ok.emit(self._fn(*self._a, **self._kw))
        except Exception as e:                 # noqa: BLE001
            tb = traceback.format_exc(limit=6)
            self.fail.emit(f"{type(e).__name__}: {e}\n{tb}")
