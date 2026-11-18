# -*- coding: utf-8 -*-
"""监控页：ch_stat 通道表 + C/N₀ 着色 + sat_stat → Skyplot。"""
from __future__ import annotations

import re

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from .. import theme
from ..widgets import Card, Skyplot

pg.setConfigOptions(background=theme.BG, foreground=theme.MUT, antialias=True)

SAT_RE = re.compile(r"^[GRCEJIS]\d")
COLS = ["SAT", "SIG", "PRN", "LOCK(s)", "C/N0", "az", "el", "#NAV", "#ERR"]


class MonitorPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._sats_key = ""
        self._az_el: dict[str, tuple[float, float]] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(10)

        c1 = Card("卫星天空视图", "az/el 来自 sat_stat（锁定≥2 s）")
        self.sky = Skyplot()
        c1.body.addWidget(self.sky, 1)
        self.lbl_cnt = QLabel("无锁定卫星")
        self.lbl_cnt.setObjectName("DimTxt")
        c1.body.addWidget(self.lbl_cnt)
        row.addWidget(c1, 0)

        c2 = Card("通道状态", "ch_stat 表（引擎文本表解析）")
        self.tbl = QTableWidget(0, len(COLS))
        self.tbl.setHorizontalHeaderLabels(COLS)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        c2.body.addWidget(self.tbl, 1)
        row.addWidget(c2, 1)
        lay.addLayout(row, 1)

    # ── ch_stat 帧 ──────────────────────────────────────────────
    def update_ch_stat(self, s: str):
        lines = [ln for ln in s.split("\n")][2:]
        rows = []
        for ln in lines:
            f = ln.strip().split()
            if len(f) < 16 or not SAT_RE.match(f[2]):
                continue
            try:
                lock = float(f[5]); cn0 = float(f[6])
            except ValueError:
                continue
            rows.append({"sat": f[2], "sig": f[3], "prn": f[4],
                         "lock": lock, "cn0": cn0,
                         "nav": f[12], "err": f[13]})
        self.tbl.setRowCount(len(rows))
        sats = []
        for i, r in enumerate(rows):
            az, el = self._az_el.get(r["sat"], (None, None))
            vals = [r["sat"], r["sig"], r["prn"], f"{r['lock']:.1f}",
                    f"{r['cn0']:.1f}",
                    "-" if az is None else f"{az:.0f}",
                    "-" if el is None else f"{el:.0f}",
                    r["nav"], r["err"]]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 4:
                    col = (theme.BAD if r["cn0"] < 35 else
                           theme.WARN if r["cn0"] < 40 else theme.ACC2)
                    it.setForeground(_qcolor(col))
                self.tbl.setItem(i, j, it)
            sats.append(r["sat"])
        self.lbl_cnt.setText(f"锁定 {len(sats)} 通道")
        key = ",".join(sorted(set(sats)))
        if key != self._sats_key:            # 星集变化 → 重订阅 sat_stat
            self._sats_key = key
            if key:
                self.win.ws_cmd({"cmd": "sub", "topic": "sat_stat",
                                 "sats": key, "cyc": 500})

    # ── sat_stat 帧 ─────────────────────────────────────────────
    def update_sat_stat(self, sats: list):
        pts, n_pvt = [], 0
        for s in sats:
            sat = s.get("sat", "")
            if not sat:
                continue
            self._az_el[sat] = (s.get("az", 0), s.get("el", 0))
            pts.append({"prn": sat[1:] if SAT_RE.match(sat) else sat,
                        "sys": sat[0], "az_deg": s.get("az", 0),
                        "el_deg": s.get("el", 0)})
            n_pvt += int(s.get("pvt", 0) or 0)
        self.sky.set_satellites(pts)
        # 刷新表中 az/el 两列
        for i in range(self.tbl.rowCount()):
            sat = self.tbl.item(i, 0)
            if sat and sat.text() in self._az_el:
                az, el = self._az_el[sat.text()]
                self.tbl.item(i, 5).setText(f"{az:.0f}")
                self.tbl.item(i, 6).setText(f"{el:.0f}")

    def on_show(self):
        # 进入本页时按当前系统过滤重订阅 ch_stat
        sysv = self.win.page_console.cb_sys.currentText()
        self.win.ws_cmd({"cmd": "sub", "topic": "ch_stat", "cyc": 500,
                         "sys": sysv, "chno": 0, "min_lock": 2.0,
                         "rfch": 0, "opt": 0})


def _qcolor(hex_str: str):
    from PySide6.QtGui import QColor
    return QColor(hex_str)
