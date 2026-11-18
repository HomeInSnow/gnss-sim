# -*- coding: utf-8 -*-
"""图谱页（M2）：IQ 波形 scrubber / 星座图 / 频谱 / 相关峰捕获度量。

数据源与 Web Status 页同源内核（inspector.read_iq / spectrum / acquire /
correlation_curve），经桥接层进程内直调。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QSlider, QGridLayout)

import pyqtgraph as pg

from .. import theme
from ..widgets import Card

pg.setConfigOptions(background=theme.BG, foreground=theme.MUT,
                    antialias=True)


class IqPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.session = win.session
        self._workers: list = []
        self._total = 0
        self._n = 2000
        self._deb = QTimer(self)
        self._deb.setSingleShot(True)
        self._deb.setInterval(150)
        self._deb.timeout.connect(self._load_iq)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        lay.addWidget(self._card_top())

        grid = QGridLayout()
        grid.setSpacing(10)
        self.p_wave = _plot("IQ 波形")
        self.p_cons = _plot("星座图 I-Q")
        self.p_spec = _plot("频谱")
        self.p_corr = _plot("相关峰（捕获度量）")
        for i, p in enumerate((self.p_wave, self.p_cons, self.p_spec,
                               self.p_corr)):
            grid.addWidget(p["card"], i // 2, i % 2)
        lay.addLayout(grid, 1)

    # ══ 顶部控制条 ═══════════════════════════════════════════════
    def _card_top(self) -> Card:
        c = Card("IQ 图谱", "backend/inspector 同源内核")
        row = QHBoxLayout()
        row.addWidget(QLabel("场景"))
        self.ed_outdir = QLineEdit()
        self.ed_outdir.setPlaceholderText("out/<runid>")
        row.addWidget(self.ed_outdir, 2)
        b_load = QPushButton("载入")
        b_load.setObjectName("Primary")
        b_load.clicked.connect(self._load_iq)
        row.addWidget(b_load)
        row.addWidget(QLabel("窗口样本"))
        self.ed_n = QLineEdit("2000")
        self.ed_n.setFixedWidth(64)
        row.addWidget(self.ed_n)
        row.addWidget(QLabel("偏移"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(lambda _: self._deb.start())
        row.addWidget(self.slider, 2)
        self.lbl_off = QLabel("0")
        self.lbl_off.setObjectName("MonoVal")
        self.lbl_off.setFixedWidth(90)
        row.addWidget(self.lbl_off)
        row.addSpacing(12)
        row.addWidget(QLabel("PRN"))
        self.ed_prn = QLineEdit("1")
        self.ed_prn.setFixedWidth(48)
        row.addWidget(self.ed_prn)
        b_corr = QPushButton("相关峰")
        b_corr.setObjectName("Ghost")
        b_corr.clicked.connect(self._load_corr)
        row.addWidget(b_corr)
        self.hint = QLabel("—")
        self.hint.setObjectName("Mut")
        row.addWidget(self.hint, 1)
        c.body.addLayout(row)
        return c

    def on_show(self):
        if not self.ed_outdir.text().strip():
            t = self.session.current()
            self.ed_outdir.setText(t.last_outdir or self.session.last_outdir)

    def set_outdir(self, outdir: str, autocorr: bool = False):
        self.ed_outdir.setText(outdir)
        if outdir:
            self._load_iq()
            if autocorr:
                self._load_corr()

    # ══ IQ 三图 ══════════════════════════════════════════════════
    def _load_iq(self):
        outdir = self.ed_outdir.text().strip()
        if not outdir:
            self.hint.setText("请先指定场景")
            return
        try:
            self._n = max(256, int(self.ed_n.text().strip() or 2000))
        except ValueError:
            self._n = 2000
        off = int(self.slider.value())
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        w = FnWorker(bridge.iqplot, outdir, self._n, off)
        w.ok.connect(lambda d, o=off: self._fill_iq(d, o))
        w.fail.connect(lambda m: self.hint.setText(f"载入失败：{m.splitlines()[0]}"))
        self._workers.append(w)
        w.start()

    def _fill_iq(self, res: dict, off: int):
        if not isinstance(res, dict):
            return
        self._total = int(res.get("total_samples", 0))
        span = max(0, self._total - self._n)
        self.slider.blockSignals(True)
        self.slider.setRange(0, span)
        self.slider.setValue(off)
        self.slider.blockSignals(False)
        self.lbl_off.setText(f"{off} / {self._total}")
        fs = res.get("sample_rate") or 1.0
        i = res.get("i") or []
        q = res.get("q") or []
        t = [k / fs * 1e6 for k in range(len(i))]          # µs
        self.p_wave["plot"].clear()
        self.p_wave["plot"].plot(i, pen=pg.mkPen(theme.ACC, width=1))
        self.p_wave["plot"].plot(q, pen=pg.mkPen(theme.ACC2, width=1))
        self.p_wave["plot"].setLabel("bottom", "样本时刻 µs")
        self.p_cons["plot"].clear()
        sc = pg.ScatterPlotItem(size=2, brush=pg.mkBrush(theme.ACC),
                                pen=pg.mkPen(None))
        sc.setData(x=i, y=q)
        self.p_cons["plot"].addItem(sc)
        self.p_cons["plot"].setLabel("bottom", "I")
        self.p_cons["plot"].setLabel("left", "Q")
        fq = res.get("spectrum_freq_hz") or []
        db = res.get("spectrum_db") or []
        self.p_spec["plot"].clear()
        if fq:
            self.p_spec["plot"].plot([f / 1e6 for f in fq], db,
                                         pen=pg.mkPen(theme.WARN, width=1))
        self.p_spec["plot"].setLabel("bottom", "频率 MHz")
        self.p_spec["plot"].setLabel("left", "dB")
        band_note = ""
        if res.get("bands"):
            band_note = "｜频带: " + ",".join(b["id"] for b in res["bands"])
        self.hint.setText(
            f"fs={fs / 1e6:.2f} Msps｜{res.get('sample_format', '')}"
            f"{band_note}")

    # ══ 相关峰 ════════════════════════════════════════════════════
    def _load_corr(self):
        outdir = self.ed_outdir.text().strip() or (
            self.session.current().last_outdir or self.session.last_outdir)
        if not outdir:
            self.hint.setText("请先指定场景")
            return
        try:
            prn = int(self.ed_prn.text().strip())
        except ValueError:
            prn = 1
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        self.hint.setText(f"C/A 相关捕获扫描 PRN{prn}（10 ms 块）…")
        w = FnWorker(bridge.correlation, outdir, prn)
        w.ok.connect(lambda d, p=prn: self._fill_corr(d, p))
        w.fail.connect(lambda m: self.hint.setText(
            f"相关峰失败：{m.splitlines()[0]}"))
        self._workers.append(w)
        w.start()

    def _fill_corr(self, res: dict, prn: int):
        if not isinstance(res, dict):
            return
        ch = res.get("code_phase_chips") or []
        amp = res.get("amplitude") or []
        p = self.p_corr["plot"]
        p.clear()
        p.plot(ch, amp, pen=pg.mkPen(theme.ACC2, width=1.5))
        p.setXRange(0, 1023)
        p.setTitle(f"PRN {res.get('prn', prn)}  fd={res.get('doppler_hz', 0):+.0f} Hz"
                   f"  metric={res.get('metric_db', 0):.1f} dB")
        self.hint.setText(
            f"PRN{prn} 捕获：fd={res.get('doppler_hz', 0):+.1f} Hz｜"
            f"度量 {res.get('metric_db', 0):.1f} dB")


def _plot(title: str) -> dict:
    card = Card(title)
    pw = pg.PlotWidget()
    pw.showGrid(x=True, y=True, alpha=0.18)
    pw.setMinimumHeight(200)
    card.body.addWidget(pw, 1)
    return {"card": card, "plot": pw}
