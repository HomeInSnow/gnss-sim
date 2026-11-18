# -*- coding: utf-8 -*-
"""桌面版通用控件：卡片、表单行、Chip 组、KPI 卡、Skyplot 极坐标。"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import (QColor, QFont, QPainter, QPen, QBrush,
                           QFontMetrics)
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                               QWidget, QPushButton, QSizePolicy)

from . import theme


# ── 卡片 ────────────────────────────────────────────────────────────
class Card(QFrame):
    """QFrame#Card + 标题栏 + 内容布局。子控件加到 .body。"""

    def __init__(self, title: str = "", tag: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setObjectName("CardTitle")
        head.addWidget(self.title_lbl)
        if tag:
            t = QLabel(tag)
            t.setObjectName("CardTag")
            head.addWidget(t)
        head.addStretch(1)
        outer.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(7)
        outer.addLayout(self.body)

    def set_title(self, text: str):
        self.title_lbl.setText(text.upper())


# ── 表单行 ──────────────────────────────────────────────────────────
def form_row(label: str, widget: QWidget, hint: str = "") -> QHBoxLayout:
    """左标签右控件的一行；返回行布局由调用方 addLayout。"""
    row = QHBoxLayout()
    row.setSpacing(8)
    lab = QLabel(label)
    lab.setObjectName("Mut")
    lab.setMinimumWidth(96)
    row.addWidget(lab)
    row.addWidget(widget, 1)
    if hint:
        h = QLabel(hint)
        h.setObjectName("DimTxt")
        row.addWidget(h)
    return row


# ── Chip 多选组 ─────────────────────────────────────────────────────
class ChipGroup(QWidget):
    """一排可多选 chip 按钮（G/R/E/C…、L1/L2/L5）。"""
    changed = Signal()

    def __init__(self, items: list[str], selected: list[str] | None = None,
                 multi: bool = True, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._btns: dict[str, QPushButton] = {}
        for it in items:
            b = QPushButton(it)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(bool(selected and it in selected))
            b.toggled.connect(self._on_toggle)
            lay.addWidget(b)
            self._btns[it] = b
        lay.addStretch(1)
        self._multi = multi

    def _on_toggle(self, _):
        if not self._multi:                      # 单选语义
            sender = self.sender()
            for b in self._btns.values():
                if b is not sender and b.isChecked():
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)
        self.changed.emit()

    def selected(self) -> list[str]:
        return [k for k, b in self._btns.items() if b.isChecked()]

    def set_selected(self, items: list[str]):
        for k, b in self._btns.items():
            b.blockSignals(True)
            b.setChecked(k in (items or []))
            b.blockSignals(False)


# ── KPI 统计卡 ──────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, key: str, color: str = "green", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(1)
        self.v = QLabel("—")
        self.v.setObjectName("StatV" if color == "green" else "StatVB")
        self.k = QLabel(key)
        self.k.setObjectName("StatK")
        self.s = QLabel("")
        self.s.setObjectName("StatS")
        lay.addWidget(self.v)
        lay.addWidget(self.k)
        lay.addWidget(self.s)

    def set(self, val, sub: str = ""):
        self.v.setText(str(val))
        self.s.setText(sub)


# ── Skyplot 极坐标 ──────────────────────────────────────────────────
class Skyplot(QWidget):
    """方位-仰角极坐标：中心=天顶(90°)，外圈=地平(0°)。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._sats: list[dict] = []

    def set_satellites(self, sats: list[dict]):
        self._sats = list(sats or [])
        self.update()

    def paintEvent(self, _ev):                    # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h) - 28
        cx, cy = w / 2.0, h / 2.0 + 4
        r = side / 2.0
        line = QPen(QColor(theme.LINE))
        line.setWidth(1)
        mut = QColor(theme.MUT)
        dim = QColor(theme.DIM)

        # 同心圈 0/30/60 + 十字（刻度标注放 45° 方向避免与 N 标注重叠）
        p.setPen(line)
        p.setBrush(Qt.NoBrush)
        for frac, lab in ((1.0, "0°"), (2 / 3, "30°"), (1 / 3, "60°")):
            p.drawEllipse(QPointF(cx, cy), r * frac, r * frac)
            p.setPen(QPen(dim))
            lx = cx + (r * frac) * math.sin(math.radians(45)) + 3
            ly = cy - (r * frac) * math.cos(math.radians(45)) - 3
            p.drawText(QPointF(lx, ly), lab)
            p.setPen(line)
        p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        # 方位标注 N/E/S/W
        p.setPen(QPen(mut))
        f = QFont(theme.FONT_UI, 9, QFont.Bold)
        p.setFont(f)
        p.drawText(QPointF(cx - 5, cy - r - 6), "N")
        p.drawText(QPointF(cx + r + 5, cy + 4), "E")
        p.drawText(QPointF(cx - 5, cy + r + 14), "S")
        p.drawText(QPointF(cx - r - 16, cy + 4), "W")

        # 卫星点：az 顺时针自北，el=90 在圆心
        fs = QFont(theme.FONT_MONO, 7)
        p.setFont(fs)
        fm = QFontMetrics(fs)
        for s in self._sats:
            el = float(s.get("el_deg", 0.0))
            az = float(s.get("az_deg", 0.0))
            if el < 0:
                continue
            rr = r * (1.0 - el / 90.0)
            x = cx + rr * math.sin(math.radians(az))
            y = cy - rr * math.cos(math.radians(az))
            color = QColor(theme.SYS_COLOR.get(s.get("sys", "G"), theme.MUT))
            p.setPen(QPen(color, 1))
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(x, y), 5, 5)
            p.setPen(QPen(QColor(theme.TXT)))
            lbl = str(s.get("prn", ""))
            p.drawText(QPointF(x + 7, y - 4), lbl)


# ── 仰角迷你条（表格单元格用）──────────────────────────────────────
class ElBar(QWidget):
    def __init__(self, el: float, parent=None):
        super().__init__(parent)
        self.el = max(0.0, min(90.0, float(el)))
        self.setFixedHeight(14)
        self.setMinimumWidth(64)

    def paintEvent(self, _ev):                    # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width() - 2, 6
        y = (self.height() - h) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.LINE2))
        p.drawRoundedRect(1, y, w, h, 3, 3)
        frac = self.el / 90.0
        col = theme.BAD if self.el < 15 else (theme.WARN if self.el < 30 else theme.ACC2)
        p.setBrush(QColor(col))
        p.drawRoundedRect(1, y, max(2, int(w * frac)), h, 3, 3)


def fmt_bytes(n: int | float) -> str:
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024:
            return f"{x:.1f} {u}" if u != "B" else f"{int(x)} B"
        x /= 1024.0
    return f"{x:.1f} PB"
