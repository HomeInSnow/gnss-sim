# -*- coding: utf-8 -*-
"""图谱页（M2）：捕获曲面 / 波形 scrubber / 星座图 / 频谱 / C-N0 趋势。

M1 先占位：展示说明卡与 pyqtgraph 画布框架，M2 接入 bridge.iqplot /
bridge.correlation 数据。
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout

from ..widgets import Card


class IqPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        info = Card("IQ 图谱", "M2 里程碑接入")
        tip = QLabel(
            "此页将展示：捕获度量曲面（/api/correlation 同源内核）、"
            "波形 scrubber、I/Q 星座图、分频带频谱与 C/N₀ 趋势。"
            "当前为占位框架，M2 完成后自动填充最近一次生成场景。")
        tip.setObjectName("Mut")
        tip.setWordWrap(True)
        info.body.addWidget(tip)
        lay.addWidget(info)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.cells: list[Card] = []
        for i, title in enumerate(("捕获度量曲面", "IQ 波形", "星座图", "频谱")):
            c = Card(title)
            ph = QLabel("待 M2 填充")
            ph.setObjectName("DimTxt")
            c.body.addWidget(ph)
            c.setMinimumHeight(220)
            grid.addWidget(c, i // 2, i % 2)
            self.cells.append(c)
        lay.addLayout(grid, 1)
