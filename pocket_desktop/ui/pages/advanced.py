# -*- coding: utf-8 -*-
"""高级图谱页：RF 频谱 PSD + 相关器四联图（对齐官方 Web UI rfch/corr 页语义）。

数据源（引擎二进制 topic，src/sdr_web.c 实证）：
  psd        rfch 选定，nfft/tave 可调      → 频谱曲线（dB，fo 处竖线）
  corr       ch 选定，width(μs) 扫查窗      → 相关峰：x=coff+pos/fs(ms)
  corr_hist  ch 选定，tspan(s) 历史窗       → IP-QP 星座 + IP/QP 时间线
  ch_stat(opt=1)                            → 锁定 CH 下拉 + C/N0/COFF/DOP KPI
"""
from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from .. import theme
from ..widgets import Card

pg.setConfigOptions(background=theme.BG, foreground=theme.MUT, antialias=True)

MODES = ["IQ", "I", "Q", "AveI", "AveIQ"]          # 相关曲线显示量（官方 TITLES）
W_OPTS = ["0.2", "0.3", "0.5", "1", "1.5", "2", "3", "5", "10", "20"]   # μs
T_OPTS = ["0.1", "0.2", "0.5", "1", "2", "5", "10"]                     # s
R_OPTS = ["0.1", "0.15", "0.2", "0.3", "0.4", "0.6", "0.8", "1.0", "1.5", "2"]
NFFT_OPTS = ["256", "1024", "2048", "4096"]
TAVE_OPTS = {"1": 0.001, "10": 0.01, "20": 0.02, "50": 0.05}            # ms


class AdvancedPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.ch = 1
        self._ch_manual = False             # 用户手动选过 CH 后不再自动切换
        self.lock_chs: list[int] = []
        self._ch_key = ""
        self.stat_row: list[str] | None = None
        self.corr = None          # 最近 corr 快照
        self.hist = None          # 最近 corr_hist
        self.psd_msg = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        # ── 工具条 ─────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(6)

        def combo(opts, default=None, w=72):
            c = QComboBox()
            c.addItems([str(o) for o in opts])
            if default is not None:
                c.setCurrentText(str(default))
            c.setFixedWidth(w)
            return c

        def label(t):
            lb = QLabel(t)
            lb.setStyleSheet(f"color:{theme.MUT};")
            return lb

        bar.addWidget(label("相关 CH"))
        from PySide6.QtWidgets import QPushButton
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(28)
        self.btn_prev.clicked.connect(lambda: self._nav_ch(-1))
        bar.addWidget(self.btn_prev)
        self.cb_ch = QComboBox()
        self.cb_ch.setFixedWidth(64)
        self.cb_ch.currentIndexChanged.connect(self._ch_changed)
        bar.addWidget(self.cb_ch)
        btn_next = QPushButton("▶")
        btn_next.setFixedWidth(28)
        btn_next.clicked.connect(lambda: self._nav_ch(1))
        bar.addWidget(btn_next)
        bar.addWidget(label("量"))
        self.cb_mode = combo(MODES, "IQ", 64)
        self.cb_mode.currentIndexChanged.connect(self._draw_corr)
        bar.addWidget(self.cb_mode)
        bar.addWidget(label("W(μs)"))
        self.cb_w = combo(W_OPTS, "5", 58)
        self.cb_w.currentIndexChanged.connect(self._resub_corr)
        bar.addWidget(self.cb_w)
        bar.addWidget(label("T(s)"))
        self.cb_t = combo(T_OPTS, "1", 58)
        self.cb_t.currentIndexChanged.connect(self._resub_hist)
        bar.addWidget(self.cb_t)
        bar.addWidget(label("Range"))
        self.cb_r = combo(R_OPTS, "0.4", 58)
        self.cb_r.currentIndexChanged.connect(self._draw_all)
        bar.addWidget(self.cb_r)
        bar.addSpacing(14)
        bar.addWidget(label("PSD RFCH"))
        self.cb_rfch = combo([1, 2, 3, 4], 1, 52)
        self.cb_rfch.currentIndexChanged.connect(self._resub_psd)
        bar.addWidget(self.cb_rfch)
        bar.addWidget(label("NFFT"))
        self.cb_nfft = combo(NFFT_OPTS, "2048", 70)
        self.cb_nfft.currentIndexChanged.connect(self._resub_psd)
        bar.addWidget(self.cb_nfft)
        bar.addWidget(label("TAVE(ms)"))
        self.cb_tave = combo(list(TAVE_OPTS), "10", 58)
        self.cb_tave.currentIndexChanged.connect(self._resub_psd)
        bar.addWidget(self.cb_tave)
        bar.addStretch(1)
        lay.addLayout(bar)

        # ── KPI 通道信息 ───────────────────────────────────────
        c0 = Card("通道信息", "ch_stat(opt=1) + 帧头")
        self.lbl_kpi = QLabel("等待引擎数据 …进入本页并回放后显示")
        self.lbl_kpi.setObjectName("MonoVal")
        c0.body.addWidget(self.lbl_kpi)
        lay.addWidget(c0)

        # ── 2x2 图区 ───────────────────────────────────────────
        g = QGridLayout()
        g.setSpacing(10)
        self.pg_psd = pg.PlotWidget()
        self.pg_psd.setLabel("bottom", "频率 (MHz)")
        self.pg_psd.setLabel("left", "dB")
        self.pg_psd.showGrid(x=True, y=True, alpha=0.15)
        self._fo_line = pg.InfiniteLine(pen=pg.mkPen(theme.WARN, width=1,
                                                      style=Qt.DashLine))
        self.pg_psd.addItem(self._fo_line)
        c1 = Card("频谱 PSD", "psd · 噪声基底/信号带宽")
        c1.body.addWidget(self.pg_psd)

        self.pg_corr = pg.PlotWidget()
        self.pg_corr.setLabel("bottom", "COFF (ms)")
        self.pg_corr.showGrid(x=True, y=True, alpha=0.15)
        self._coff_line = pg.InfiniteLine(pen=pg.mkPen(theme.MUT, width=1))
        self.pg_corr.addItem(self._coff_line)
        c2 = Card("相关峰", "corr · 主相关器大点/扫查相关器连线")
        c2.body.addWidget(self.pg_corr)

        self.pg_iq = pg.PlotWidget()
        self.pg_iq.setAspectLocked(True)
        self.pg_iq.showGrid(x=True, y=True, alpha=0.15)
        c3 = Card("IP-QP 星座", "corr_hist 散点 + 当前 prompt")
        c3.body.addWidget(self.pg_iq)

        self.pg_hist = pg.PlotWidget()
        self.pg_hist.setLabel("bottom", "时间 (s)")
        self.pg_hist.showGrid(x=True, y=True, alpha=0.15)
        c4 = Card("IP/QP 历史", "corr_hist · 载波环跟踪质量")
        c4.body.addWidget(self.pg_hist)

        g.addWidget(c1, 0, 0)
        g.addWidget(c2, 0, 1)
        g.addWidget(c3, 1, 0)
        g.addWidget(c4, 1, 1)
        for p in (self.pg_psd, self.pg_corr, self.pg_iq, self.pg_hist):
            p.setMinimumHeight(200)
        g.setRowStretch(0, 1)
        g.setRowStretch(1, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        lay.addLayout(g, 1)

    # ── 订阅管理 ──────────────────────────────────────────────
    def on_show(self):
        self._resub_psd()
        self._resub_corr()
        self._resub_hist()
        self.win.ws_cmd({"cmd": "sub", "topic": "ch_stat", "chno": 0,
                         "opt": 1, "cyc": 200, "min_lock": 2.0})
        self._draw_all()

    def on_hide(self):
        for t in ("psd", "corr", "corr_hist", "ch_stat"):
            self.win.ws_cmd({"cmd": "unsub", "topic": t})

    def _resub_psd(self):
        if not self.isVisible():
            return
        self.win.ws_cmd({"cmd": "sub", "topic": "psd",
                         "rfch": int(self.cb_rfch.currentText()),
                         "cyc": 200, "nfft": int(self.cb_nfft.currentText()),
                         "tave": TAVE_OPTS[self.cb_tave.currentText()]})

    def _resub_corr(self):
        if not self.isVisible():
            return
        w = float(self.cb_w.currentText())
        self.win.ws_cmd({"cmd": "sub", "topic": "corr", "ch": self.ch,
                         "cyc": 100, "width": w * 1e-6})

    def _resub_hist(self):
        if not self.isVisible():
            return
        t = float(self.cb_t.currentText())
        self.win.ws_cmd({"cmd": "sub", "topic": "corr_hist", "ch": self.ch,
                         "cyc": 100, "tspan": t})

    # ── CH 选择 ───────────────────────────────────────────────
    def _nav_ch(self, d: int):
        if not self.lock_chs:
            return
        self._ch_manual = True
        i = self.lock_chs.index(self.ch) if self.ch in self.lock_chs else 0
        self._set_ch(self.lock_chs[min(max(i + d, 0), len(self.lock_chs) - 1)])

    def _ch_changed(self):
        v = self.cb_ch.currentText()
        if v.isdigit() and int(v) != self.ch:
            self._ch_manual = True           # 用户选定后不再自动切换
            self._set_ch(int(v))

    def _set_ch(self, ch: int):
        self.ch = max(ch, 1)
        self.corr = self.hist = None
        self._sync_ch_combo()
        self._resub_corr()
        self._resub_hist()
        self._draw_all()

    def _sync_ch_combo(self):
        key = ",".join(map(str, self.lock_chs)) + f";{self.ch}"
        if key == self._ch_key:
            return
        self._ch_key = key
        self.cb_ch.blockSignals(True)
        self.cb_ch.clear()
        opts = list(self.lock_chs)
        if self.ch not in opts:
            opts.insert(0, self.ch)
        self.cb_ch.addItems([str(c) for c in opts])
        self.cb_ch.setCurrentText(str(self.ch))
        self.cb_ch.blockSignals(False)

    # ── 帧入口（main_window._dispatch 路由）───────────────────
    def on_bin(self, m: dict):
        f = m.get("frm")
        if f == "psd":
            self.psd_msg = m
            self._draw_psd()
        elif f == "corr":
            if m.get("ch") != self.ch:
                return
            self.corr = m
            self._draw_corr()
        elif f == "corr_hist":
            if m.get("ch") != self.ch:
                return
            self.hist = m
            self._draw_iq()
            self._draw_hist()

    def update_ch_stat_opt(self, text: str):
        """ch_stat(opt=1) 文本表：26+ 列，f[0]=CH。填 CH 下拉 + KPI。"""
        rows = []
        stat = None
        for line in text.split("\n")[2:]:
            f = line.strip().split()
            if len(f) < 26 or not f[0].isdigit():
                continue
            rows.append(int(f[0]))
            if int(f[0]) == self.ch:
                stat = f
        self.stat_row = stat
        if rows != self.lock_chs:
            self.lock_chs = rows
            self._sync_ch_combo()
            if rows and not self._ch_manual and self.ch not in rows:
                self._set_ch(rows[0])        # 自动锁定到首个在用通道
        self._update_kpi()

    # ── KPI ───────────────────────────────────────────────────
    def _update_kpi(self):
        parts = []
        s = self.stat_row
        if s:
            parts.append(f"CH{self.ch} RF:{s[1]} SAT:{s[2]} SIG:{s[3]} "
                         f"PRN:{s[4]} C/N0:{s[6]} COFF:{s[8]}ms "
                         f"DOP:{s[9]}Hz #NAV:{s[12]}")
        if self.corr:
            m = self.corr
            parts.append(f"corr: state={m['state']} lock={m['lock']:.2f} "
                         f"n={m['n']}(主{m['npos']}) fd={m['fd']:.1f}Hz "
                         f"fs={m['fs']/1e6:.2f}MHz")
        if self.psd_msg:
            p = self.psd_msg
            parts.append(f"psd: fo={p['fo']/1e6:.3f}MHz fs={p['fs']/1e6:.2f}MHz "
                         f"nfft={p['psd'].size}")
        self.lbl_kpi.setText("   |   ".join(parts) if parts
                             else "等待引擎数据 …（需先开始回放）")

    # ── 画图 ──────────────────────────────────────────────────
    def _draw_all(self):
        self._draw_psd()
        self._draw_corr()
        self._draw_iq()
        self._draw_hist()

    def _draw_psd(self):
        p, m = self.pg_psd, self.psd_msg
        p.clear()
        if not m:
            return
        n = m["psd"].size
        fo, fs = m["fo"] * 1e-6, m["fs"] * 1e-6           # Hz→MHz
        x0 = fo if m["iq"] == 1 else fo - fs / 2
        w = fs / 2
        x = x0 + (np.arange(n) + 0.5) * (w / n)
        p.plot(x, m["psd"], pen=pg.mkPen(theme.ACC, width=1),
               connect="all")
        self._fo_line.setValue(fo)
        self._fo_line.setVisible(True)
        p.setXRange(x0, x0 + w, padding=0)

    def _draw_corr(self):
        p, m = self.pg_corr, self.corr
        p.clear()
        self._coff_line.setVisible(False)
        if not m or m["n"] == 0:
            return
        w = float(self.cb_w.currentText())
        R = float(self.cb_r.currentText())
        mode = self.cb_mode.currentText()
        sign = 1.0 if m["C"][0] >= 0.0 else -1.0
        C, pos = m["C"], m["pos"]
        x = m["coff"] + pos / m["fs"] * 1e3               # ms
        if mode == "I":
            y = C[0::2] * sign
        elif mode == "Q":
            y = C[1::2] * sign
        elif mode == "IQ":
            y = np.sqrt(C[0::2] ** 2 + C[1::2] ** 2)
        elif mode == "AveI":
            y = m["ave_i"]
        else:                                             # AveIQ
            y = np.sqrt(np.maximum(m["ave_p"], 0.0))
        half = w * 5e-4                                    # W(μs)/2 → ms
        npos = min(int(m["npos"]), m["n"])
        if m["n"] > npos:                                  # 附加扫查相关器
            p.plot(x[npos:], y[npos:], pen=pg.mkPen(theme.ACC2, width=1))
            p.addItem(pg.ScatterPlotItem(x=x[npos:], y=y[npos:],
                                         brush=pg.mkBrush(theme.ACC2),
                                         size=3))
        p.addItem(pg.ScatterPlotItem(x=x[:npos], y=y[:npos],
                                     brush=pg.mkBrush(theme.ACC), size=9))
        self._coff_line.setValue(m["coff"])
        self._coff_line.setVisible(True)
        p.addItem(pg.InfiniteLine(pos=0, angle=0,
                                  pen=pg.mkPen(theme.LINE, width=1)))
        p.setXRange(m["coff"] - half, m["coff"] + half, padding=0)
        if mode in ("Q",):
            p.setYRange(-R, R, padding=0)
        elif mode in ("IQ", "AveIQ"):
            p.setYRange(0, R, padding=0)
        else:
            p.setYRange(-R * 0.3, R, padding=0)

    def _draw_iq(self):
        p = self.pg_iq
        p.clear()
        R = float(self.cb_r.currentText())
        p.addItem(pg.InfiniteLine(pos=0, pen=pg.mkPen(theme.LINE, width=1)))
        p.addItem(pg.InfiniteLine(pos=0, angle=0,
                                  pen=pg.mkPen(theme.LINE, width=1)))
        h, m = self.hist, self.corr
        if h and h["n"]:
            P = h["P"]
            p.addItem(pg.ScatterPlotItem(x=P[0::2], y=P[1::2],
                                         brush=pg.mkBrush(theme.ACC2),
                                         size=2))
        if m and m["n"]:
            p.addItem(pg.ScatterPlotItem(x=[m["C"][0]], y=[m["C"][1]],
                                         brush=pg.mkBrush(theme.ACC),
                                         size=10))
        p.setXRange(-R, R, padding=0)
        p.setYRange(-R, R, padding=0)

    def _draw_hist(self):
        p = self.pg_hist
        p.clear()
        p.addItem(pg.InfiniteLine(pos=0, angle=0,
                                  pen=pg.mkPen(theme.LINE, width=1)))
        h = self.hist
        if not h or h["n"] == 0:
            return
        n = h["n"]
        t = h["time"] + (np.arange(n) - n + 1) * h["T"]
        P = h["P"]
        p.plot(t, P[1::2], pen=pg.mkPen(theme.ACC2, width=1))   # QP
        p.plot(t, P[0::2], pen=pg.mkPen(theme.ACC, width=1))    # IP
        R = float(self.cb_r.currentText())
        p.setYRange(-R, R, padding=0)
        p.setXRange(h["time"] - float(self.cb_t.currentText()),
                    h["time"], padding=0)
