# -*- coding: utf-8 -*-
"""验证页：内置接收机 Verify Fix（快照 + 跟踪解）+ KPI + 逐星表。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QComboBox, QCheckBox,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView)

from .. import theme
from ..widgets import Card, StatCard, fmt_bytes

import pyqtgraph as pg
pg.setConfigOptions(background=theme.BG, foreground=theme.MUT,
                    antialias=True)


def _mk(val, unit="", good=None, bad=None):
    """（保留位）KPI 阈值着色由 _done 内联处理。"""
    return val


class VerifyPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.session = win.session
        self._worker = None
        self._workers: list = []
        self._result: dict | None = None
        self._trace_rx: dict | None = None
        self._trace_dll: dict | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        lay.addWidget(self._card_run())
        lay.addLayout(self._row_kpi())
        lay.addWidget(self._card_result())
        lay.addWidget(self._card_errcurve(), 3)
        lay.addWidget(self._card_track(), 3)
        lay.addWidget(self._card_lnav(), 2)

    # ══ 误差曲线（trace_rx / trace_dll）══════════════════════════
    def _card_errcurve(self) -> Card:
        c = Card("逐历元码相位误差", "trace_rx.json 捕获 / trace_dll.json 跟踪")
        row = QHBoxLayout()
        self.cb_sv = QComboBox()
        self.cb_sv.setMinimumWidth(160)
        self.cb_sv.currentIndexChanged.connect(self._draw_err)
        row.addWidget(QLabel("卫星"))
        row.addWidget(self.cb_sv)
        self.ck_dll = QCheckBox("叠加跟踪解曲线（coh 会话 chi）")
        self.ck_dll.setChecked(True)
        self.ck_dll.toggled.connect(self._draw_err)
        row.addWidget(self.ck_dll)
        b = QPushButton("刷新曲线")
        b.setObjectName("FileBtn")
        b.clicked.connect(self._load_traces)
        row.addWidget(b)
        self.curve_hint = QLabel("运行验证（含 trace）后可绘制")
        self.curve_hint.setObjectName("DimTxt")
        row.addWidget(self.curve_hint, 1)
        c.body.addLayout(row)
        self.p_err = pg.PlotWidget()
        self.p_err.showGrid(x=True, y=True, alpha=0.18)
        self.p_err.setLabel("bottom", "历元时刻 s")
        self.p_err.setLabel("left", "err_chips")
        self.p_err.setMinimumHeight(180)
        c.body.addWidget(self.p_err, 1)
        return c

    def _load_traces(self):
        outdir = self.ed_outdir.text().strip()
        if not outdir:
            return
        from desktop.core import bridge
        self._trace_rx = bridge.trace_json(outdir, "trace_rx.json")
        self._trace_dll = bridge.trace_json(outdir, "trace_dll.json")
        keys = sorted((self._trace_rx or {}).get("svs", {}).keys())
        self.cb_sv.blockSignals(True)
        self.cb_sv.clear()
        self.cb_sv.addItems(keys)
        self.cb_sv.blockSignals(False)
        if keys:
            self.curve_hint.setText(
                f"捕获星 {len(keys)}｜跟踪 {'有' if self._trace_dll else '无'}")
            self._draw_err()
        else:
            self.p_err.clear()
            self.curve_hint.setText("该场景无 trace_rx.json（验证时勾选逐历元 trace）")

    def _draw_err(self):
        key = self.cb_sv.currentData() or self.cb_sv.currentText()
        self.p_err.clear()
        if not key:
            return
        tr = ((self._trace_rx or {}).get("svs") or {}).get(key) or {}
        t = (self._trace_rx or {}).get("t_s") or []
        if tr.get("err_chips") and t:
            self.p_err.plot(t, tr["err_chips"],
                                pen=pg.mkPen(theme.ACC, width=1.6),
                                name="捕获 err_chips")
        if self.ck_dll.isChecked() and self._trace_dll:
            td = ((self._trace_dll or {}).get("svs") or {}).get(key) or {}
            td_t = (self._trace_dll or {}).get("t_s") or t
            if td.get("err_chips"):
                self.p_err.plot(td_t, td["err_chips"],
                                    pen=pg.mkPen(theme.ACC2, width=1.6),
                                    name="跟踪 chi")
        self.p_err.addLegend(offset=(10, 10))

    # ══ LNAV 电文面板 ═════════════════════════════════════════════
    def _card_lnav(self) -> Card:
        c = Card("导航电文回放", "L1CA 子帧字段级解释（lnav_display）")
        row = QHBoxLayout()
        row.addWidget(QLabel("PRN"))
        self.ed_lnav_prn = QLineEdit("1")
        self.ed_lnav_prn.setFixedWidth(56)
        row.addWidget(self.ed_lnav_prn)
        b = QPushButton("解释电文")
        b.setObjectName("Ghost")
        b.clicked.connect(self._load_lnav)
        row.addWidget(b)
        self.lnav_hint = QLabel("取该星生成时刻实际写入 IQ 的广播星历字段")
        self.lnav_hint.setObjectName("DimTxt")
        row.addWidget(self.lnav_hint, 1)
        c.body.addLayout(row)
        from PySide6.QtWidgets import QPlainTextEdit
        self.txt_lnav = QPlainTextEdit()
        self.txt_lnav.setObjectName("LogView")
        self.txt_lnav.setReadOnly(True)
        self.txt_lnav.setMaximumHeight(160)
        self.txt_lnav.setPlaceholderText("PRN + 解释电文")
        c.body.addWidget(self.txt_lnav)
        return c

    def _load_lnav(self):
        outdir = self.ed_outdir.text().strip()
        if not outdir:
            self.lnav_hint.setText("请先指定场景")
            return
        try:
            prn = int(self.ed_lnav_prn.text().strip())
        except ValueError:
            return
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        self.lnav_hint.setText(f"解析 PRN{prn} 电文…")
        w = FnWorker(bridge.lnav, prn, outdir)
        w.ok.connect(lambda d, p=prn: self._fill_lnav(d, p))
        w.fail.connect(lambda m: self.lnav_hint.setText(
            f"电文失败：{m.splitlines()[0]}"))
        self._workers.append(w)
        w.start()

    def _fill_lnav(self, d, prn: int):
        lines = [f"══ PRN {prn} L1CA 导航电文（写入 IQ 的字段）══"]

        def emit_list(lst, depth, label=""):
            pref = f"{label} = " if label else ""
            pad = "  " * depth
            if lst and all(not isinstance(x, (dict, list)) for x in lst):
                shown = "".join(str(x) for x in lst[:32])
                lines.append(pad + pref + f"[{len(lst)} 项] {shown}"
                             + ("…" if len(lst) > 32 else ""))
            else:
                lines.append(pad + pref)
                for x in lst:
                    walk(x, depth + 1)

        def walk(obj, depth=0):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, dict):
                        lines.append("  " * depth + f"[{k}]")
                        walk(v, depth + 1)
                    elif isinstance(v, list):
                        emit_list(v, depth, k)
                    else:
                        lines.append("  " * depth + f"{k} = {v}")
            elif isinstance(obj, list):
                emit_list(obj, depth)
            else:
                lines.append("  " * depth + str(obj))
        walk(d if isinstance(d, dict) else {"value": d})
        self.txt_lnav.setPlainText("\n".join(lines))
        self.lnav_hint.setText("完成")

    # ══ 运行控制 ═════════════════════════════════════════════════
    def _card_run(self) -> Card:
        c = Card("内置接收机 Verify Fix", "backend/analysis 内核直跑")
        row = QHBoxLayout()
        self.ed_outdir = QLineEdit()
        self.ed_outdir.setPlaceholderText("out/<runid>（可手填或从历史页载入）")
        self.cb_track = QCheckBox("跟踪解（SVTracker DLL+PLL）")
        self.cb_track.setChecked(True)
        self.cb_trace = QCheckBox("逐历元 trace")
        self.cb_trace.setChecked(True)
        self.cb_dll = QComboBox()
        self.cb_dll.addItems(["coh 相干E/L+PLL", "el 非相干E/L", "nc 峰追踪"])
        self.ed_tracks = QLineEdit()
        self.ed_tracks.setPlaceholderText("可选")
        self.ed_bw = QLineEdit()
        self.ed_bw.setPlaceholderText("0.5")
        self.ed_bw.setToolTip("跟踪 DLL 环路带宽 Hz（空=内核默认 0.5）")
        self.ed_mindb = QLineEdit()
        self.ed_mindb.setPlaceholderText("9/15")
        self.ed_mindb.setToolTip(
            "捕获质量门限 dB：快照解默认 9，跟踪解默认 15（空=按路径默认）")
        self.ed_mlat = QLineEdit()
        self.ed_mlon = QLineEdit()
        self.ed_malt = QLineEdit()
        for w in (self.ed_mlat, self.ed_mlon, self.ed_malt):
            w.setPlaceholderText("任务值")
            w.setFixedWidth(92)
        self.btn_run = QPushButton("▶ 运行验证")
        self.btn_run.setObjectName("Primary")
        self.btn_run.clicked.connect(lambda: self.run_verify())
        self.status_lbl = QLabel("—")
        self.status_lbl.setObjectName("Mut")
        row.addWidget(QLabel("场景"))
        row.addWidget(self.ed_outdir, 2)
        row.addWidget(self.cb_track)
        row.addWidget(QLabel("判别器"))
        row.addWidget(self.cb_dll)
        row.addWidget(QLabel("track_s"))
        row.addWidget(self.ed_tracks, 0)
        self.ed_tracks.setFixedWidth(56)
        row.addWidget(QLabel("dll_bw"))
        row.addWidget(self.ed_bw, 0)
        self.ed_bw.setFixedWidth(56)
        row.addWidget(QLabel("min_db"))
        row.addWidget(self.ed_mindb, 0)
        self.ed_mindb.setFixedWidth(56)
        row.addWidget(self.cb_trace)
        row.addWidget(self.btn_run)
        row.addWidget(self.status_lbl, 1)
        c.body.addLayout(row)
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("基准点 纬/经/高"))
        mrow.addWidget(self.ed_mlat, 0)
        mrow.addWidget(self.ed_mlon, 0)
        mrow.addWidget(self.ed_malt, 0)
        m = QLabel("空 = 取当前仿真任务位置（跨场景验证时请填该场景生成位置）")
        m.setObjectName("DimTxt")
        mrow.addWidget(m, 1)
        c.body.addLayout(mrow)
        return c

    def _row_kpi(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.kpi_err = StatCard("3D 误差 m", "green")
        self.kpi_2d = StatCard("水平误差 m", "green")
        self.kpi_pdop = StatCard("PDOP", "blue")
        self.kpi_rms = StatCard("残差 RMS m", "blue")
        self.kpi_sats = StatCard("定位星数", "blue")
        self.kpi_clk = StatCard("接收机钟差 s", "green")
        self.kpi_trk = StatCard("跟踪解误差 m", "green")
        for k in (self.kpi_err, self.kpi_2d, self.kpi_pdop, self.kpi_rms,
                  self.kpi_sats, self.kpi_clk, self.kpi_trk):
            row.addWidget(k)
        return row

    def _card_result(self) -> Card:
        c = Card("快照解算", "Snapshot LS")
        self.lbl_fix = QLabel("尚未运行")
        self.lbl_fix.setObjectName("MonoVal")
        c.body.addWidget(self.lbl_fix)
        return c

    def _card_track(self) -> Card:
        c = Card("逐星明细", "Per-SV")
        self.tbl = QTableWidget(0, 0)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        c.body.addWidget(self.tbl, 1)
        return c

    # ══ 逻辑 ═════════════════════════════════════════════════════
    def set_outdir(self, outdir: str):
        self.ed_outdir.setText(outdir)

    def on_show(self):
        t = self.session.current()
        if not self.ed_outdir.text().strip():
            self.ed_outdir.setText(t.last_outdir or self.session.last_outdir)
        if self.ed_outdir.text().strip() and self._trace_rx is None:
            self._load_traces()

    def run_verify(self, auto: bool = False):
        if self._worker and self._worker.isRunning():
            return
        outdir = self.ed_outdir.text().strip()
        if not outdir:
            self.session.bus.log("请先指定场景（out/<runid>）", "warn")
            return
        t = self.session.current()
        # 基准点：手填优先，留空回落到当前任务位置（跨场景验证时须手填
        # 该场景的生成位置，否则 3D 误差掺入两位置之差）
        def _mv(w, dv):
            try:
                return float(w.text().strip())
            except ValueError:
                return dv
        marker = {"lat": _mv(self.ed_mlat, t.lat),
                  "lon": _mv(self.ed_mlon, t.lon),
                  "alt": _mv(self.ed_malt, t.alt)}
        kw: dict = {"trace": self.cb_trace.isChecked()}
        # 捕获质量门限（快照解与跟踪解都生效，空=快照 9 / 跟踪 15 dB）
        md = self.ed_mindb.text().strip()
        if md:
            kw["min_metric_db"] = float(md)
        if self.cb_track.isChecked():
            kw["tracking"] = True
            kw["dll_mode"] = ("coh", "el", "nc")[self.cb_dll.currentIndex()]
            ts = self.ed_tracks.text().strip()
            if ts:
                kw["track_s"] = float(ts)
            bw = self.ed_bw.text().strip()
            if bw:
                kw["dll_bw_hz"] = float(bw)
        self.btn_run.setEnabled(False)
        self.status_lbl.setText("验证中…（大场景可能较久）")
        self.session.bus.set_status(f"Verify Fix：{outdir}")
        self.session.bus.log(
            f"开始验证：out/{outdir}｜跟踪={'开' if kw.get('tracking') else '关'}"
            + (f"（{kw.get('dll_mode')}）" if kw.get("tracking") else "")
            + ("（自动生成触发）" if auto else ""), "info")
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        w = FnWorker(bridge.receiver, outdir, marker, kw=kw)
        w.ok.connect(self._done)
        w.fail.connect(self._fail)
        self._worker = w
        w.start()

    def _fmt(self, v, fmt="{:.3f}", dash="—"):
        if isinstance(v, (int, float)):
            return fmt.format(v)
        return dash

    def _done(self, res: dict):
        self.btn_run.setEnabled(True)
        if not isinstance(res, dict) or "error" in res:
            err = (res or {}).get("error", "验证返回异常")
            self.status_lbl.setText("验证失败")
            self.session.bus.log(f"验证失败：{err}", "bad")
            return
        self._result = res
        self.session.verify_result = res
        self.status_lbl.setText("验证完成")
        llh = res.get("llh") or [None, None, None]
        err = res.get("error_m")
        pdop = res.get("pdop")
        rms = res.get("residual_rms_m")
        prns = res.get("prns_used") or []
        clk = res.get("clock_bias_s")
        self.kpi_err.set(self._fmt(err, "{:.2f}"))
        if isinstance(err, (int, float)) and err > 10:
            self.kpi_err.v.setStyleSheet(f"color:{theme.BAD}")
        else:
            self.kpi_err.v.setStyleSheet(f"color:{theme.ACC2}")
        self.kpi_pdop.set(self._fmt(pdop))
        self.kpi_rms.set(self._fmt(rms))
        self.kpi_sats.set(len(prns) if prns else "—")
        self.kpi_clk.set(self._fmt(clk, "{:.3e}"))
        self.kpi_trk.set("—")
        self.kpi_2d.set("—")
        self.lbl_fix.setText(
            f"fix = ({self._fmt(llh[0], '{:.6f}')}, {self._fmt(llh[1], '{:.6f}')}, "
            f"{self._fmt(llh[2], '{:.2f}')} m)　"
            f"marker = 任务位置（桌面版以仿真高程为真值）")
        self.session.bus.log(
            f"验证完成：error_m={self._fmt(err, '{:.2f}')}｜PDOP={self._fmt(pdop)}"
            f"｜残差RMS={self._fmt(rms)}｜星数={len(prns)}", "ok")
        tfix = res.get("tracking_fix")
        if isinstance(tfix, dict) and "error" not in tfix:
            te = tfix.get("error_m")
            self.kpi_trk.set(self._fmt(te, "{:.2f}"))
            if isinstance(te, (int, float)) and te > 10:
                self.kpi_trk.v.setStyleSheet(f"color:{theme.BAD}")
            else:
                self.kpi_trk.v.setStyleSheet(f"color:{theme.ACC2}")
            self.session.bus.log(f"跟踪解完成：error_m={self._fmt(te, '{:.2f}')}", "ok")
            self._fill_table(tfix.get("per_sv") or {})
        elif isinstance(tfix, dict):
            self.session.bus.log(f"跟踪解失败：{tfix.get('error')}", "warn")
        # 快照解逐星：prns_used 无详细字段时列出 PRN 清单
        if not (isinstance(tfix, dict) and tfix.get("per_sv")):
            self._fill_snapshot_table(prns)
        # 水平/垂直拆分（若有 wls.ecef 则从 ecef 无法直接得，用 llh 与 marker 差近似）
        try:
            import math as _m
            t = self.session.current()
            dlat = (llh[0] - t.lat) * 111320.0
            dlon = (llh[1] - t.lon) * 111320.0 * _m.cos(_m.radians(t.lat))
            self.kpi_2d.set(f"{_m.hypot(dlat, dlon):.2f}")
        except Exception:                        # noqa: BLE001
            pass
        self._load_traces()

    def _fail(self, msg: str):
        self.btn_run.setEnabled(True)
        self.status_lbl.setText("验证失败")
        head = msg.splitlines()[0] if msg else "未知"
        self.session.bus.log(f"验证异常：{head}", "bad")

    def _fill_table(self, per_sv: dict):
        entries = [(str(k), d) for k, d in sorted(per_sv.items())
                   if isinstance(d, dict)]
        if not entries:
            self.tbl.setRowCount(0)
            self.tbl.setColumnCount(0)
            return
        cols: list[str] = []
        for _, d in entries:
            for k in d:
                if not isinstance(d[k], (dict, list)) and k not in cols:
                    cols.append(k)
        self.tbl.setColumnCount(1 + len(cols))
        self.tbl.setRowCount(len(entries))
        self.tbl.setHorizontalHeaderLabels(["星"] + cols)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r, (key, d) in enumerate(entries):
            it = QTableWidgetItem(key)
            it.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, 0, it)
            for c, col in enumerate(cols):
                it = QTableWidgetItem(self._fmt(d.get(col), "{:.5g}"))
                it.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(r, c + 1, it)

    def _fill_snapshot_table(self, prns: list):
        self.tbl.setColumnCount(1)
        self.tbl.setRowCount(len(prns))
        self.tbl.setHorizontalHeaderLabels(["定位星 PRN"])
        for r, p in enumerate(prns):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(p)))
