# -*- coding: utf-8 -*-
"""数据页：通道观测表（ch_stat opt=1 全列）+ 卫星状态表（sat_stat 标志）。

数据源（src/sdr_web.c 实证）：
  ch_stat(opt=1) → 26 列通道级观测/质量（表头行直接作列名，TRUTH 不猜）：
    CH/RFCH/SAT/SIG/PRN/LOCK/C-N0/…/COFF/DOP/ADR/SYNC/#NAV/#ERR…/ERR_P/
    ERR_C/PLI/NAV/WEEK/TOW
  sat_stat       → 每星 {sat,az,el,pvt,obs,eph,svh,fcn}（int 标志位）
    PVT/OBS/EPH 解出、SVH 健康位（官方 sats.js 同款 OK/十六进制显示）
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel,
                               QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .. import theme
from ..widgets import Card

GREEN = Qt.GlobalColor.darkGreen


def _item(text: str, color: str | None = None, mono: bool = True) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if color:
        it.setForeground(Qt.GlobalColor.green if color == "OK"
                         else _qcolor(color))
    if mono:
        f = it.font()
        f.setFamily("Consolas")
        f.setPointSize(10)
        it.setFont(f)
    return it


def _qcolor(hex_str: str):
    from PySide6.QtGui import QColor
    return QColor(hex_str)


class DataPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._sats_key = ""
        self._ch_cols: list[str] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        top = QHBoxLayout()
        self.lbl_stat = QLabel("等待引擎数据 …（进入本页自动订阅 ch_stat/sat_stat）")
        self.lbl_stat.setObjectName("MonoVal")
        top.addWidget(self.lbl_stat)
        top.addStretch(1)
        lay.addLayout(top)

        sp = QSplitter(Qt.Horizontal)
        c1 = Card("通道观测", "ch_stat(opt=1) · 观测/质量全列")
        self.tbl_ch = QTableWidget()
        self.tbl_ch.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_ch.setAlternatingRowColors(True)
        self.tbl_ch.verticalHeader().setVisible(False)
        self.tbl_ch.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        c1.body.addWidget(self.tbl_ch)
        sp.addWidget(c1)

        c2 = Card("卫星状态 / 导航", "sat_stat · PVT/观测/导航电文/健康")
        self.tbl_sat = QTableWidget()
        self.tbl_sat.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_sat.setAlternatingRowColors(True)
        self.tbl_sat.verticalHeader().setVisible(False)
        self.tbl_sat.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        c2.body.addWidget(self.tbl_sat)
        sp.addWidget(c2)
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 2)
        lay.addWidget(sp, 1)

    # ── 订阅 ──────────────────────────────────────────────────
    def on_show(self):
        # 与已验证探针同款参数（opt=1 出 26 列）
        self.win.ws_cmd({"cmd": "sub", "topic": "ch_stat", "chno": 0,
                         "opt": 1, "cyc": 200, "min_lock": 2.0})
        if self._sats_key:
            self._resub_sat(self._sats_key.split(","))

    def on_hide(self):
        for t in ("ch_stat", "sat_stat"):
            self.win.ws_cmd({"cmd": "unsub", "topic": t})

    def _resub_sat(self, sats: list[str]):
        if self.isVisible() and sats:
            # 引擎 jsn_str 要求逗号分隔字符串（monitor 页同款）
            self.win.ws_cmd({"cmd": "sub", "topic": "sat_stat",
                             "sats": ",".join(sats), "cyc": 1000})

    # ── 通道观测表 ────────────────────────────────────────────
    # 引擎 print_head 表头固定 16 列名；opt=1 数据行为 26 列，
    # 17~26 列名按官方 corr.js 字段语义补全（19/26 列语义未公开 → "-"）
    EXTRA_COLS = ["ERR_P", "ERR_C", "PLI", "-",
                  "NAV1", "NAV2", "NAV3", "WEEK", "TOW", "-"]

    def update_ch_stat(self, text: str):
        lines = text.split("\n")
        if len(lines) < 3:
            return
        cols = lines[1].strip().split()
        rows = [ln.strip().split() for ln in lines[2:]
                if ln.strip() and ln.split()[0].isdigit()]
        # 空帧（引擎瞬态全过滤）不更新
        if not rows:
            return
        data_max = max(len(f) for f in rows)
        if data_max > len(cols):
            cols = cols + (self.EXTRA_COLS[:data_max - len(cols)]
                           if data_max - len(cols) <= len(self.EXTRA_COLS)
                           else [f"c{i+1}"
                                 for i in range(len(cols), data_max)])
        self._ch_cols = cols
        self.tbl_ch.clear()
        self.tbl_ch.setColumnCount(len(cols))
        self.tbl_ch.setHorizontalHeaderLabels(cols)
        self.tbl_ch.setRowCount(len(rows))
        sats = []
        for r, f in enumerate(rows):
            for c in range(len(cols)):
                v = f[c] if c < len(f) else ""
                color = None
                if c < len(f):
                    if c == 2 and v:                       # SAT 按系统着色
                        color = theme.SYS_COLOR.get(v[0])
                    elif c == 5:                           # LOCK
                        try:
                            lv = float(v)
                            color = (theme.ACC2 if lv >= 4 else
                                     theme.WARN if lv >= 2 else theme.BAD)
                        except ValueError:
                            pass
                    elif c == 6:                           # C/N0
                        try:
                            cv = float(v)
                            color = (theme.ACC2 if cv >= 40 else
                                     theme.WARN if cv >= 35 else
                                     theme.BAD if cv > 0 else theme.DIM)
                        except ValueError:
                            pass
                self.tbl_ch.setItem(r, c, _item(v, color))
            if len(f) > 2 and f[2]:
                sats.append(f[2])
        # 星集变化 → 重订阅 sat_stat（monitor 页同款配方）
        key = ",".join(sorted(set(sats)))
        if key != self._sats_key:
            self._sats_key = key
            self._resub_sat(sorted(set(sats)))
        self.lbl_stat.setText(
            f"通道观测 {len(rows)} 行 · 卫星 {len(set(sats))} 颗 · "
            f"列名取引擎 ch_stat 表头（opt=1）")

    # ── 卫星状态表 ────────────────────────────────────────────
    def update_sat_stat(self, sats: list):
        heads = ["SAT", "AZ", "EL", "PVT", "OBS", "EPH", "SVH", "FCN"]
        if self.tbl_sat.columnCount() != len(heads):
            self.tbl_sat.clear()
            self.tbl_sat.setColumnCount(len(heads))
            self.tbl_sat.setHorizontalHeaderLabels(heads)
        self.tbl_sat.setRowCount(len(sats))
        for r, s in enumerate(sats):
            svh = s.get("svh", 0)
            row = [
                _item(str(s.get("sat", "")),
                      theme.SYS_COLOR.get(str(s.get("sat", "?"))[:1])),
                _item(f"{s.get('az', 0):.1f}"),
                _item(f"{s.get('el', 0):.1f}"),
                _item("OK" if s.get("pvt") else "-", "OK" if s.get("pvt")
                      else theme.DIM),
                _item("OK" if s.get("obs") else "-", "OK" if s.get("obs")
                      else theme.DIM),
                _item("OK" if s.get("eph") else "-", "OK" if s.get("eph")
                      else theme.DIM),
                _item(f"0x{svh:02x}" if svh else "0x00",
                      theme.BAD if svh else theme.ACC2),
                _item(str(s.get("fcn", "")) if s.get("fcn") else "-"),
            ]
            for c, it in enumerate(row):
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_sat.setItem(r, c, it)
