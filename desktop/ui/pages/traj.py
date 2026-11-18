# -*- coding: utf-8 -*-
"""轨迹页（M3）：航点表 + 平面轨迹线 + 应用到任务。M1 占位。"""
from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QPushButton,
                               QHeaderView, QAbstractItemView)

from ..widgets import Card


class TrajPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        c = Card("航点编辑", "Trajectory · M3 完整交互")
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(
            ["点名", "纬度 °", "经度 °", "高程 m"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        c.body.addWidget(self.tbl, 1)
        row = QHBoxLayout()
        for text in ("添加航点", "删除选行", "应用到当前任务", "清空"):
            b = QPushButton(text)
            b.setObjectName("Ghost" if text == "应用到当前任务" else "FileBtn")
            b.clicked.connect(self._placeholder)
            row.addWidget(b)
        row.addStretch(1)
        c.body.addLayout(row)
        lay.addWidget(c, 1)

        c2 = Card("平面轨迹预览")
        ph = QLabel("M3：接入 pyqtgraph 平面轨迹线 + 离线地图底图")
        ph.setObjectName("DimTxt")
        c2.body.addWidget(ph)
        c2.setMinimumHeight(180)
        lay.addWidget(c2, 1)

    def _placeholder(self):
        self.win.log("轨迹编辑将在 M3 里程碑启用", "warn")

    def load_route(self, route: list):
        """M3：从任务 route 回填。"""
        if not route:
            return
        self.tbl.setRowCount(len(route))
        for r, wp in enumerate(route):
            vals = [f"P{r+1}", f"{wp[0]:.6f}", f"{wp[1]:.6f}", f"{wp[2]:.2f}"]
            for c, v in enumerate(vals):
                self.tbl.setItem(r, c, QTableWidgetItem(v))
