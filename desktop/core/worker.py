# -*- coding: utf-8 -*-
"""QThread 工作器：预览/验证等短任务用 FnWorker，生成长任务用 GenerateWorker。"""
from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal


class FnWorker(QThread):
    """在后台线程执行任意可调用（bridge 函数），结果经信号回 UI。"""
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


class GenerateWorker(QThread):
    """生成任务：桥接层在同一条代码路径上跑 SSE 进度，这里只做信号搬运。"""
    progress = Signal(float)
    ok = Signal(dict)
    fail = Signal(str)

    def __init__(self, body: dict, parent=None):
        super().__init__(parent)
        self._body = body
        self._stop = False

    def request_stop(self):
        """UI 侧点『停止』：置标志 + 调与 Web /api/generate/stop 同一入口。"""
        self._stop = True
        try:
            from desktop.core import bridge
            bridge.stop()
        except Exception:                      # noqa: BLE001 - 未开跑时忽略
            pass

    def run(self):                             # noqa: D102
        from desktop.core import bridge
        try:
            done = bridge.generate(self._body,
                                   progress_cb=self.progress.emit,
                                   stop_flag=lambda: self._stop)
            self.ok.emit(done)
        except Exception as e:                 # noqa: BLE001
            tb = traceback.format_exc(limit=8)
            self.fail.emit(f"{type(e).__name__}: {e}\n{tb}")
