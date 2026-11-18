# -*- coding: utf-8 -*-
"""日志页：引擎 log topic + UI 事件统一留痕，可导出。"""
from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from ..widgets import Card

LEVEL_COLOR = {"info": "#dbe6f7", "ok": "#39e6b4", "warn": "#ffb454",
               "bad": "#ff6b81"}


class LogPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._lines: list[tuple[str, str, str]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        c = Card("运行日志", "引擎 log topic + 操作事件")
        self.view = QPlainTextEdit()
        self.view.setObjectName("LogView")
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(8000)
        c.body.addWidget(self.view, 1)
        row = QHBoxLayout()
        b_clear = QPushButton("清空")
        b_clear.setObjectName("FileBtn")
        b_clear.clicked.connect(self._clear)
        b_exp = QPushButton("导出 txt")
        b_exp.setObjectName("FileBtn")
        b_exp.clicked.connect(self._export)
        row.addWidget(b_clear)
        row.addWidget(b_exp)
        row.addStretch(1)
        c.body.addLayout(row)
        lay.addWidget(c, 1)
        win.session.bus.line.connect(self._append)

    def _append(self, ts: str, level: str, msg: str):
        self._lines.append((ts, level, msg))
        color = LEVEL_COLOR.get(level, "#dbe6f7")
        self.view.appendHtml(
            f"<span style='color:#55648a'>{ts}</span> "
            f"<span style='color:{color}'>{msg.replace('<', '&lt;')}</span>")

    def _clear(self):
        self.view.clear()
        self._lines.clear()

    def _export(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "导出日志",
            f"pocket-desktop-log-{dt.datetime.now():%Y%m%d-%H%M%S}.txt",
            "文本 (*.txt)")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                for ts, level, msg in self._lines:
                    f.write(f"[{ts}] {level:5s} {msg}\n")
            self.win.log(f"日志已导出：{p}", "ok")
        except OSError as e:
            self.win.log(f"导出失败：{e}", "bad")
