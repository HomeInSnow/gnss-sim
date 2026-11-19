# -*- coding: utf-8 -*-
"""控制台页：IQ 文件/格式/信号/变体配置 + 启停 + 真值（gnss-sim run 联动）。"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ...core.engine_mgr import VARIANTS
from ...core.worker import FnWorker
from .. import theme
from ..widgets import Card, ChipGroup

FMTS = [("CS16 int16 IQ", 8), ("CS8 int8 IQ", 7), ("INT8X2", 2),
        ("RAW8", 3), ("RAW16", 4), ("RAW32", 6)]
SYSS = ["ALL", "GPS", "Galileo", "BeiDou", "QZSS", "GLONASS"]
# 留空信号集时按系统生成的默认捕获集（对齐官方 Web UI 默认）。
# 语法：空格分 token，token = sig:prn列表；prn 只认 "a-b" 范围与逗号。
# GLONASS 的 prn 列表是 FDMA 频槽号（sdr_rcv.c: ch->prn is FCN），
# 星号捕获范围由引擎 satno 默认（-7-6/1-27）兜底，勿在此串里塞 "/"。
DEFAULT_SIGS = {"GPS": "L1CA:1-32", "ALL": "L1CA:1-32",
                "Galileo": "E1B:1-36", "BeiDou": "B1I:1-63",
                "QZSS": "L1CA:1-9", "GLONASS": "G1CA:-7-6"}


def read_run_truth(runid: str) -> dict:
    """从 gnss-sim run meta.json 读真值配置（源码态 out/、frozen exe 旁 out/）。"""
    import sys as _s
    roots = []
    if getattr(_s, "frozen", False):
        exe = Path(_s.executable).resolve()
        roots += [exe.parent / "out", exe.parents[2] / "out",
                  Path.cwd() / "out"]
    else:
        roots.append(Path(__file__).resolve().parents[3] / "out")
    for r in roots:
        mp = r / runid / "meta.json"
        if mp.exists():
            cfg = json.loads(mp.read_text(encoding="utf-8")).get("config", {})
            return {"lat": cfg.get("lat"), "lon": cfg.get("lon"),
                    "alt": cfg.get("alt"), "fs": cfg.get("sample_rate"),
                    "fmt": cfg.get("sample_format"),
                    "dur": cfg.get("duration_s")}
    raise FileNotFoundError(f"未找到 run {runid} 的 meta.json")


class ConsolePage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._workers: list[FnWorker] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        lay.addWidget(self._card_inp())
        lay.addWidget(self._card_engine())
        lay.addWidget(self._card_truth())
        lay.addStretch(1)
        lay.addWidget(self._bar(), alignment=Qt.AlignBottom)

    # ── 卡片 ────────────────────────────────────────────────────
    def _form(self, body_layout) -> QFormLayout:
        f = QFormLayout()
        f.setLabelAlignment(Qt.AlignRight)
        f.setSpacing(6)
        body_layout.addLayout(f)
        return f

    def _card_inp(self) -> Card:
        c = Card("回放输入", "IF 数据文件（gnss-sim 产物直接可放）")
        f = self._form(c.body)
        row = QHBoxLayout()
        self.ed_file = QLineEdit()
        self.ed_file.setPlaceholderText("gpssim.bin / .bin（带 tag 则格式自动）")
        b = QPushButton("浏览…")
        b.setObjectName("FileBtn")
        b.clicked.connect(self._browse)
        row.addWidget(self.ed_file, 1)
        row.addWidget(b)
        w = QWidget(); w.setLayout(row)
        f.addRow("文件", w)
        self.cb_fmt = QComboBox()
        for name, v in FMTS:
            self.cb_fmt.addItem(name, v)
        self.cb_fmt.setCurrentIndex(0)
        f.addRow("格式", self.cb_fmt)
        self.sp_fs = QDoubleSpinBox(decimals=3, maximum=200, value=25.0,
                                    suffix=" MHz")
        f.addRow("采样率", self.sp_fs)
        self.ed_fo = QLineEdit("1575.42")
        self.ed_fo.setPlaceholderText("rfRF 中频 MHz，逗号分列，如 1575.42,1176.45")
        f.addRow("中频 fo", self.ed_fo)
        self.ed_iq = QLineEdit("2")
        self.ed_iq.setPlaceholderText("每 RF 通道 I/Q 数：2 或 1，逗号分列")
        f.addRow("IQ", self.ed_iq)
        self.ed_bits = QLineEdit("3")
        self.ed_bits.setPlaceholderText("每样本比特数 2/3，仅 RAW* 格式生效")
        self.ed_bits.setToolTip(
            "引擎按 2/3 裁剪（sdr_web.c CLIP 2..3）；CS16/CS8/INT8X2 等格式"
            "由格式本身决定位宽，本项被忽略")
        f.addRow("bits", self.ed_bits)
        self.sp_ts = QComboBox()
        self.sp_ts.addItem("实时 tscale=1", 1.0)
        self.sp_ts.addItem("2× tscale=2", 2.0)
        self.sp_ts.setToolTip("更快灌数会因 IF 缓冲>90% 拒绝捕获调度（已验证），勿加档位")
        f.addRow("节流", self.sp_ts)
        self.sp_toff = QDoubleSpinBox(decimals=3, minimum=-1e6, maximum=1e6,
                                      suffix=" s")
        f.addRow("时间偏移", self.sp_toff)
        self.ed_sigs = QLineEdit()
        self.ed_sigs.setPlaceholderText(
            "留空＝按系统过滤生成默认集；多组空格分列，如 L1CA:4,5 L1C:1-8")
        f.addRow("信号集", self.ed_sigs)
        self.cb_sys = QComboBox()
        self.cb_sys.addItems(SYSS)
        f.addRow("系统过滤", self.cb_sys)
        return c

    def _card_engine(self) -> Card:
        c = Card("接收机引擎", "PocketSDR 构建变体（子进程 + WS 回环）")
        self.chip = ChipGroup([VARIANTS[k][0] for k in VARIANTS],
                              multi=False)
        self.chip.set_selected([VARIANTS["bothoff"][0]])
        c.body.addWidget(self.chip)
        self.lbl_engine = QLabel("")
        self.lbl_engine.setObjectName("DimTxt")
        bad = self.win.engine.missing_exe()
        if bad:
            self.lbl_engine.setText(f"⚠ 引擎缺失：{bad}")
            self.lbl_engine.setStyleSheet(f"color:{theme.BAD}")
        c.body.addWidget(self.lbl_engine)
        return c

    def _card_truth(self) -> Card:
        c = Card("定位真值", "误差曲线基准；可从 gnss-sim run 一键读取")
        f = self._form(c.body)
        self.sp_lat = QDoubleSpinBox(decimals=7, minimum=-90, maximum=90)
        self.sp_lon = QDoubleSpinBox(decimals=7, minimum=-180, maximum=180)
        self.sp_alt = QDoubleSpinBox(decimals=3, minimum=-1000, maximum=10000,
                                     value=0)
        f.addRow("纬度", self.sp_lat)
        f.addRow("经度", self.sp_lon)
        f.addRow("椭高", self.sp_alt)
        row = QHBoxLayout()
        self.ed_run = QLineEdit()
        self.ed_run.setPlaceholderText("gnss-sim runid → 读 meta.json 真值/参数")
        b = QPushButton("从 run 读取")
        b.setObjectName("FileBtn")
        b.clicked.connect(self._read_run)
        row.addWidget(self.ed_run, 1)
        row.addWidget(b)
        w = QWidget(); w.setLayout(row)
        f.addRow("联动", w)
        return c

    def _bar(self) -> QWidget:
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 4, 0, 0)
        self.btn_run = QPushButton("▶ 开始回放")
        self.btn_run.setObjectName("Primary")
        self.btn_run.clicked.connect(self._start)
        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setObjectName("Ghost")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        self.lbl_stat = QLabel("引擎停止")
        self.lbl_stat.setObjectName("DimTxt")
        h.addWidget(self.btn_run)
        h.addWidget(self.btn_stop)
        h.addStretch(1)
        h.addWidget(self.lbl_stat)
        return bar

    # ── 交互 ────────────────────────────────────────────────────
    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "选择 IQ 文件", str(Path.cwd()),
            "IQ 数据 (*.bin *.dat *.int8 *.int16 *);;全部 (*)")
        if p:
            self.ed_file.setText(p)
            tag = Path(p).with_suffix(Path(p).suffix + ".tag")
            if tag.exists():
                self.lbl_stat.setText(
                    "检测到 .tag：引擎以 tag 内格式为准，开始回放时会按"
                    "界面参数自动校正重写")

    def _read_run(self):
        rid = self.ed_run.text().strip()
        if not rid:
            return
        wk = FnWorker(read_run_truth, rid, busy_msg="读取 run meta")
        wk.ok.connect(self._apply_run)
        wk.fail.connect(lambda e: self.win.log(f"读 run 失败 {e}", "bad"))
        self._workers.append(wk)
        wk.start()

    def _apply_run(self, t: dict):
        if t.get("lat") is not None:
            self.sp_lat.setValue(t["lat"])
            self.sp_lon.setValue(t["lon"])
            self.sp_alt.setValue(t.get("alt") or 0.0)
        if t.get("fs"):
            self.sp_fs.setValue(float(t["fs"]) / 1e6)
        if t.get("fmt") == "int16":
            self.cb_fmt.setCurrentIndex(0)
        elif t.get("fmt") == "int8":
            idx = self.cb_fmt.findData(7)
            self.cb_fmt.setCurrentIndex(max(0, idx))
        win_dir = self.ed_file.text().strip() or str(
            Path(__file__).resolve().parents[3] / "out" / self.ed_run.text().strip())
        cand = Path(win_dir) / "gpssim.bin"
        if cand.exists():
            self.ed_file.setText(str(cand))
        self.win.session.truth = {"lat": t.get("lat"), "lon": t.get("lon"),
                                  "alt": t.get("alt")}
        self.win.log(f"已载入 run 真值/参数（{t}）", "ok")

    def _start(self):
        f = str(Path(self.ed_file.text().strip()).resolve())
        if not f or not Path(f).exists():
            self.win.log("请先选择有效的 IQ 文件", "warn")
            return
        self.win.session.params.update({
            "file": f, "fmt": self.cb_fmt.currentData(),
            "fs": self.sp_fs.value(), "fo": self.ed_fo.text(),
            "iq": self.ed_iq.text(), "bits": self.ed_bits.text(),
            "sigs": self.ed_sigs.text(), "sys": self.cb_sys.currentText(),
            "toff": self.sp_toff.value(), "tscale": self.sp_ts.currentData(),
            "variant": self._variant_key()})
        self.win.session.save()
        self.win.session.truth = {"lat": self.sp_lat.value(),
                                  "lon": self.sp_lon.value(),
                                  "alt": self.sp_alt.value()}
        self.win.page_solution.reset()
        from ...core.engine_mgr import ensure_tag
        tg, act = ensure_tag(f, self.cb_fmt.currentData(), self.sp_fs.value(),
                             self.ed_fo.text() or "1575.42",
                             self.ed_iq.text() or "2",
                             self.ed_bits.text() or "3")
        if tg and act == "created":
            self.win.log(f"已自动补写 {Path(tg).name}（引擎要求 tag）", "info")
        elif tg and act == "rewritten":
            self.win.log(f"{Path(tg).name} 与界面参数不符，已按界面重写"
                         "（tag 存在时引擎以 tag 为准）", "warn")
        cmds = [{"cmd": "set_inp", "inp": 1, "fmt": self.cb_fmt.currentData(),
                 "fs": self.sp_fs.value(), "file": f,
                 "fo": self.ed_fo.text() or "1575.42",
                 "IQ": self.ed_iq.text() or "2",
                 "bits": self.ed_bits.text() or "3",
                 "tscale": self.sp_ts.currentData(),
                 "toff": self.sp_toff.value()}]
        sigs = self.ed_sigs.text().strip() or \
            DEFAULT_SIGS.get(self.cb_sys.currentText(), "L1CA:1-32")
        cmds.append({"cmd": "set_sig", "sigs": sigs})
        cmds.append({"cmd": "sub", "topic": "rcv_stat", "cyc": 500})
        cmds.append({"cmd": "sub", "topic": "log", "cyc": 300})
        cmds.append({"cmd": "sub", "topic": "pvt_sol", "cyc": 200})
        cmds.append({"cmd": "sub", "topic": "ch_stat", "cyc": 500,
                     "sys": self.cb_sys.currentText(), "chno": 0,
                     "min_lock": 2.0, "rfch": 0, "opt": 0})
        self.win.start_replay(self._variant_key(), cmds)
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_stat.setText("启动中…")

    def _stop(self):
        self.win.stop_replay()
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_stat.setText("已停止")

    def set_rcv_stat(self, s: str):
        self.lbl_stat.setText(s.strip()[:120] or "引擎空闲")
        if "stopped" in s.lower() or "idle" in s.lower():
            pass

    def _variant_key(self) -> str:
        sel = self.chip.selected()
        for k in VARIANTS:
            if VARIANTS[k][0] == (sel[0] if sel else ""):
                return k
        return "bothoff"

    def restore(self):
        p = self.win.session.params
        if not p:
            return
        self.ed_file.setText(p.get("file", ""))
        i = self.cb_fmt.findData(p.get("fmt", 8))
        self.cb_fmt.setCurrentIndex(max(0, i))
        self.sp_fs.setValue(p.get("fs", 25.0))
        self.ed_fo.setText(p.get("fo", "1575.42"))
        self.ed_iq.setText(p.get("iq", "2"))
        self.ed_bits.setText(p.get("bits", "3"))
        self.ed_sigs.setText(p.get("sigs", ""))
        self.cb_sys.setCurrentText(p.get("sys", "ALL"))
        self.sp_toff.setValue(p.get("toff", 0.0))
        i = self.sp_ts.findData(p.get("tscale", 1.0))
        self.sp_ts.setCurrentIndex(max(0, i))
        vk = p.get("variant")
        if vk in VARIANTS:
            self.chip.set_selected([VARIANTS[vk][0]])
