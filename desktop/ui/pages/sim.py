# -*- coding: utf-8 -*-
"""仿真页：全量配置卡（镜像 Web 通道卡）+ Skyplot/星表 + 生成动作条。"""
from __future__ import annotations

import datetime as dt
import secrets

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QPushButton, QComboBox,
                               QCheckBox, QDateTimeEdit, QProgressBar,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFileDialog, QAbstractItemView)

from .. import theme
from ..widgets import (Card, form_row, ChipGroup, StatCard, Skyplot,
                       fmt_bytes, MapWidget)
from ...core.model import (SimTask, SYSTEMS, BANDS, IMP_PRESETS,
                           MDL_PRESETS)

SR_ITEMS = ["auto", "2600000", "4000000", "5000000", "8000000", "10000000",
            "15000000", "20000000", "25000000", "27500000", "30720000",
            "61440000"]


class SimPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.session = win.session
        self._prev_worker = None
        self._gen_worker = None
        self._loading = False                 # load_task 期间抑制联动

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        mid = QHBoxLayout()
        mid.setSpacing(12)
        mid.addLayout(self._build_config_col(), 5)
        mid.addLayout(self._build_geo_col(), 4)
        lay.addLayout(mid, 1)
        lay.addWidget(self._build_action_bar())

    # ══ 控件工厂 ═════════════════════════════════════════════════
    def _line(self, text: str = "", ph: str = "") -> QLineEdit:
        e = QLineEdit(str(text))
        if ph:
            e.setPlaceholderText(ph)
        return e

    def _combo(self, items, cur=None) -> QComboBox:
        c = QComboBox()
        for it in items:
            c.addItem(it if isinstance(it, str) else it[0],
                      None if isinstance(it, str) else it[1])
        if cur is not None:
            idx = c.findText(cur if isinstance(cur, str) else str(cur))
            if idx >= 0:
                c.setCurrentIndex(idx)
        return c

    def _check(self, text: str, val: bool = False) -> QCheckBox:
        c = QCheckBox(text)
        c.setChecked(bool(val))
        return c

    def _file_row(self, line: QLineEdit, kinds: str,
                  allow_empty: bool = True) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(line, 1)
        b = QPushButton("…")
        b.setObjectName("FileBtn")
        b.setFixedWidth(30)
        b.clicked.connect(lambda: self._browse(line, kinds, allow_empty))
        row.addWidget(b)
        return row

    def _browse(self, line: QLineEdit, kinds: str, allow_empty: bool):
        p, _ = QFileDialog.getOpenFileName(self, "选择文件", "", kinds)
        if p:
            line.setText(p)

    # ══ 左列：配置卡 ═════════════════════════════════════════════
    def _build_config_col(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._cfg_scroll = scroll
        holder = QWidget()
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 0, 4, 0)
        col.setSpacing(10)
        col.addWidget(self._card_timing())
        col.addWidget(self._card_eph())
        col.addWidget(self._card_const())
        col.addWidget(self._card_models())
        col.addWidget(self._card_imp())
        col.addWidget(self._card_fade())
        col.addWidget(self._card_pos())
        col.addWidget(self._card_scenario())
        col.addStretch(1)
        scroll.setWidget(holder)
        wrap = QHBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return wrap

    def _card_timing(self) -> Card:
        c = Card("定时与输出", "Timing")
        self.dt_start = QDateTimeEdit()
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDateTime(QDateTime.currentDateTime())
        self.ed_dur = self._line("60")
        self.cb_sr = self._combo(SR_ITEMS, "auto")
        self.cb_sr.setEditable(True)
        self.cb_fmt = self._combo(["int16", "int12", "int8"], "int16")
        c.body.addLayout(form_row("开始 UTC", self.dt_start))
        row = QHBoxLayout()
        row.addWidget(QLabel("时长 s"))
        row.addWidget(self.ed_dur, 1)
        row.addWidget(QLabel("采样率"))
        row.addWidget(self.cb_sr, 2)
        row.addWidget(QLabel("格式"))
        row.addWidget(self.cb_fmt)
        c.body.addLayout(row)
        return c

    def _card_eph(self) -> Card:
        c = Card("星历与场景", "Ephemeris")
        self.ed_rinex = self._line("AUTO", "AUTO = 使用 data/rinex 当日 BRDC")
        self.cb_ephmode = self._combo(["broadcast", "precise"], "broadcast")
        self.ed_sp3 = self._line("", "仅 precise 模式需要")
        self.ck_fb = self._check("precise 失败时降级广播星历")
        self.ck_fb.setToolTip("勾选：取不到 SP3 产品时自动改用广播星历并告警；"
                              "不勾：precise 数据不可用直接报错")
        c.body.addLayout(self._eph_row())
        c.body.addLayout(form_row("星历模式", self.cb_ephmode))
        c.body.addLayout(self._file_row(self.ed_sp3, "SP3 (*.sp3 *.SP3);;所有文件 (*)"))
        fb_row = QHBoxLayout()
        fb_row.addSpacing(96 + 8)
        fb_row.addWidget(self.ck_fb)
        fb_row.addStretch(1)
        c.body.addLayout(fb_row)
        self.cb_ephmode.currentTextChanged.connect(self._sync_eph_mode)
        return c

    def _eph_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        lab = QLabel("RINEX 路径")
        lab.setObjectName("Mut")
        lab.setMinimumWidth(96)
        row.addWidget(lab)
        row.addWidget(self.ed_rinex, 1)
        b = QPushButton("…")
        b.setObjectName("FileBtn")
        b.setFixedWidth(30)
        b.clicked.connect(lambda: self._browse(
            self.ed_rinex, "RINEX (*.rnx *.r*);;所有文件 (*)"))
        row.addWidget(b)
        return row

    def _sync_eph_mode(self, mode):
        self.ed_sp3.setEnabled(mode == "precise")
        self.ck_fb.setEnabled(mode == "precise")

    def _card_const(self) -> Card:
        c = Card("星座与信号", "Constellations")
        self.chip_sys = ChipGroup(SYSTEMS, ["G"])
        self.chip_band = ChipGroup(BANDS, [])
        self.ed_mask = self._line("5", "几何预览/生成的截止高度角（度）")
        self.ck_osnma = self._check("OSNMA (Galileo)")
        self.cb_nmas = self._combo(["2 operational", "1 test", "3 don't use"])
        row = QHBoxLayout()
        row.addWidget(self.ck_osnma)
        row.addWidget(QLabel("NMA status"))
        row.addWidget(self.cb_nmas)
        row.addStretch(1)
        c.body.addLayout(form_row("星座", self.chip_sys))
        c.body.addLayout(form_row("频段", self.chip_band, "空 = 各系统本征频段"))
        c.body.addLayout(form_row("截止高度角 °", self.ed_mask))
        c.body.addLayout(row)
        # OSNMA 只对 Galileo 有意义：未选 E 时禁用并取消勾选（与 Web 联动一致）
        self.chip_sys.changed.connect(self._sync_osnma)
        self.ck_osnma.toggled.connect(self._sync_osnma)
        return c

    def _sync_osnma(self):
        if self._loading:
            return
        has_e = "E" in self.chip_sys.selected()
        if not has_e and self.ck_osnma.isChecked():
            self.ck_osnma.setChecked(False)
            self.session.bus.log("OSNMA 仅适用于 Galileo：未选 E 系统，已取消勾选",
                                 "warn")
        self.ck_osnma.setEnabled(has_e)
        self.cb_nmas.setEnabled(has_e and self.ck_osnma.isChecked())

    def _card_models(self) -> Card:
        c = Card("传播模型", "Channel Models")
        self.cb_mdlpreset = self._combo(
            [("Custom 自定义", "manual"), ("Open sky 开阔天空", "open-sky"),
             ("Urban canyon 城市峡谷", "urban-canyon"),
             ("Foliage 树荫弱星", "foliage-weak")], "manual")
        self.cb_iono = self._combo(["off", "klobuchar"], "off")
        self.cb_tropo = self._combo(["off", "saastamoinen"], "off")
        self.cb_rxclk = self._combo(["off", "poly"], "off")
        self.ed_clk_bias = self._line("0")
        self.ed_clk_drift = self._line("0")
        self.ed_clk_driftrate = self._line("0")
        self.ed_clk_sawamp = self._line("0")
        self.ed_clk_sawper = self._line("0")
        self.cb_mp = self._combo(["off", "specular"], "off")
        self.ed_mp1d = self._line("0")
        self.ed_mp1a = self._line("0")
        self.ed_mp1p = self._line("3.14159")
        self.ed_mp2d = self._line("0")
        self.ed_mp2a = self._line("0")
        self.ed_mp2p = self._line("3.14159")
        self.ck_models_iq = self._check(
            "模型注入 IQ（钟差/多径；大气延迟始终注入）")
        self.ck_models_iq.setToolTip(
            "勾选后接收机钟差/多径写进 IQ；不勾仅参与预览/真值。\n"
            "注意：电离层/对流层延迟由引擎无条件注入 IQ，不受此开关影响。")
        self.ck_svclock = self._check("卫星钟差注入（broadcast 钟差参数）")
        self.ck_svclock.setToolTip(
            "关闭后引擎不注入卫星钟差/群延迟（验证端按 meta 对称回读）")
        c.body.addLayout(form_row("预设", self.cb_mdlpreset))
        cells = [("电离层", self.cb_iono), ("对流层", self.cb_tropo),
                 ("接收机钟", self.cb_rxclk),
                 ("钟偏 s", self.ed_clk_bias), ("钟漂 s/s", self.ed_clk_drift),
                 ("钟漂率 s/s²", self.ed_clk_driftrate),
                 ("锯齿幅度 s", self.ed_clk_sawamp),
                 ("锯齿周期 s", self.ed_clk_sawper),
                 ("多径", self.cb_mp),
                 ("径1 延迟 m", self.ed_mp1d), ("径1 幅度", self.ed_mp1a),
                 ("径1 相位 rad", self.ed_mp1p),
                 ("径2 延迟 m", self.ed_mp2d), ("径2 幅度", self.ed_mp2a),
                 ("径2 相位 rad", self.ed_mp2p)]
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        for i, (lab, w) in enumerate(cells):
            r, col = divmod(i, 3)
            g.addWidget(QLabel(lab), r, col * 2)
            g.addWidget(w, r, col * 2 + 1)
        c.body.addLayout(g)
        c.body.addWidget(self.ck_models_iq)
        c.body.addWidget(self.ck_svclock)
        self.cb_mdlpreset.currentIndexChanged.connect(self._apply_mdl_preset)
        self.cb_rxclk.currentTextChanged.connect(
            lambda v: self._set_enabled(
                (self.ed_clk_bias, self.ed_clk_drift, self.ed_clk_driftrate,
                 self.ed_clk_sawamp, self.ed_clk_sawper), v == "poly"))
        self.cb_mp.currentTextChanged.connect(
            lambda v: self._set_enabled(
                (self.ed_mp1d, self.ed_mp1a, self.ed_mp1p,
                 self.ed_mp2d, self.ed_mp2a, self.ed_mp2p),
                v == "specular"))
        return c

    def _set_enabled(self, widgets, on: bool):
        if self._loading:
            for w in widgets:
                w.setEnabled(True)            # load 时先放开再统一回填
            return
        for w in widgets:
            w.setEnabled(bool(on))

    def _apply_mdl_preset(self, _idx):
        if self._loading:
            return
        key = self.cb_mdlpreset.currentData()
        p = MDL_PRESETS.get(key)
        if not p:
            return
        self.cb_iono.setCurrentText(p["iono"])
        self.cb_tropo.setCurrentText(p["tropo"])
        self.cb_rxclk.setCurrentText(p["rxclk"])
        self.ed_clk_bias.setText(repr(p["rxclk_bias"]))
        self.ed_clk_drift.setText(repr(p["rxclk_drift"]))
        self.ed_clk_driftrate.setText(repr(p["rxclk_driftrate"]))
        self.ed_clk_sawamp.setText(repr(p["rxclk_sawamp"]))
        self.ed_clk_sawper.setText(repr(p["rxclk_sawper"]))
        self.cb_mp.setCurrentText(p["mp"])
        self.ed_mp1d.setText(repr(p["mp1_delay"]))
        self.ed_mp1a.setText(repr(p["mp1_amp"]))
        self.ed_mp1p.setText(repr(p["mp1_phase"]))
        self.ed_mp2d.setText(repr(p["mp2_delay"]))
        self.ed_mp2a.setText(repr(p["mp2_amp"]))
        self.ed_mp2p.setText(repr(p["mp2_phase"]))
        self.session.bus.log(f"传播模型预设：{key}", "info")

    def _card_imp(self) -> Card:
        c = Card("RF 损伤", "Impairments")
        self.ck_imp = self._check("启用损伤注入")
        self.cb_imppreset = self._combo(
            [("Custom 自定义", "manual"), ("Bench 线缆台架", "bench"),
             ("Field 外场典型", "field"), ("Urban 城区恶化", "urban")],
            "manual")
        self.ed_impseed = self._line("0")
        self.ed_impcfo = self._line("0")
        self.ed_impppm = self._line("0")
        self.ed_impphn = self._line("0")
        self.ed_impgain = self._line("0")
        self.ed_impiqph = self._line("0")
        self.ed_impdci = self._line("0")
        self.ed_impdq = self._line("0")
        self.ed_impsnr = self._line("", "空 = 不加噪声")
        self.ed_impclip = self._line("0")
        self.ed_impbits = self._line("0")
        c.body.addLayout(form_row("预设", self.cb_imppreset))
        g = QGridLayout()
        pairs = [("seed", self.ed_impseed), ("CFO Hz", self.ed_impcfo),
                 ("时钟 ppm", self.ed_impppm), ("相噪 °rms", self.ed_impphn),
                 ("IQ 幅度 dB", self.ed_impgain), ("IQ 相位 °", self.ed_impiqph),
                 ("DC-I", self.ed_impdci), ("DC-Q", self.ed_impdq),
                 ("SNR dB", self.ed_impsnr), ("削波率", self.ed_impclip),
                 ("量化 bit", self.ed_impbits)]
        for i, (lab, w) in enumerate(pairs):
            r, col = divmod(i, 2)
            g.addWidget(QLabel(lab), r, col * 2)
            g.addWidget(w, r, col * 2 + 1)
        c.body.addWidget(self.ck_imp)
        c.body.addLayout(g)
        self.cb_imppreset.currentIndexChanged.connect(self._apply_imp_preset)
        self.ck_imp.toggled.connect(
            lambda v: self._set_enabled(
                (self.cb_imppreset, self.ed_impseed, self.ed_impcfo,
                 self.ed_impppm, self.ed_impphn, self.ed_impgain,
                 self.ed_impiqph, self.ed_impdci, self.ed_impdq,
                 self.ed_impsnr, self.ed_impclip, self.ed_impbits), v))
        return c

    def _apply_imp_preset(self, _idx):
        if self._loading:
            return
        key = self.cb_imppreset.currentData()
        p = IMP_PRESETS.get(key)
        if not p:
            return
        self.ck_imp.setChecked(True)
        m = {self.ed_impseed: p["seed"], self.ed_impcfo: p["cfo"],
             self.ed_impppm: p["ppm"], self.ed_impphn: p["phn"],
             self.ed_impgain: p["gain"], self.ed_impiqph: p["iqphase"],
             self.ed_impdci: p["dci"], self.ed_impdq: p["dcq"],
             self.ed_impsnr: p["snr"], self.ed_impclip: p["clip"],
             self.ed_impbits: p["bits"]}
        for w, v in m.items():
            w.setText(str(v))
        self.session.bus.log(f"RF 损伤预设：{key}", "info")

    def _card_fade(self) -> Card:
        c = Card("信道衰落", "Fading")
        self.cb_fade = self._combo(
            [("off 关", "off"), ("seeded 可复现", "seeded"),
             ("keyed 密钥流", "keyed")], "off")
        self.cb_fadeenv = self._combo(
            [("open 开阔", "open"), ("rural 郊区树荫", "rural"),
             ("suburban 半城区", "suburban"), ("urban 城区", "urban")],
            "suburban")
        self.ed_fadespeed = self._line("", "空 = 轨迹自动")
        self.ed_fadeseed = self._line("1")
        self.ed_fadekey = self._line("")
        self.btn_faderand = QPushButton("随机密钥")
        self.btn_faderand.setObjectName("FileBtn")
        self.btn_faderand.clicked.connect(
            lambda: self.ed_fadekey.setText(secrets.token_hex(8)))
        self.ck_faderec = self._check("记录密钥到 meta")
        row = QHBoxLayout()
        row.addWidget(self.cb_fade, 1)
        row.addWidget(self.cb_fadeenv, 1)
        c.body.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("速度 m/s"))
        row2.addWidget(self.ed_fadespeed, 1)
        row2.addWidget(QLabel("seed"))
        row2.addWidget(self.ed_fadeseed, 1)
        c.body.addLayout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("密钥"))
        row3.addWidget(self.ed_fadekey, 2)
        row3.addWidget(self.btn_faderand)
        c.body.addLayout(row3)
        c.body.addWidget(self.ck_faderec)
        self.cb_fade.currentIndexChanged.connect(self._sync_fade_mode)
        return c

    def _sync_fade_mode(self, _idx=None):
        mode = self.cb_fade.currentData()
        self._set_enabled((self.ed_fadeseed,), mode == "seeded")
        self._set_enabled((self.ed_fadekey, self.btn_faderand,
                           self.ck_faderec), mode == "keyed")

    def _card_pos(self) -> Card:
        c = Card("接收机位置", "Location · 单击地图选点")
        self.ed_lat = self._line("60.182537")
        self.ed_lon = self._line("24.82826")
        self.ed_alt = self._line("47.248")
        g = QGridLayout()
        g.addWidget(QLabel("纬度"), 0, 0)
        g.addWidget(self.ed_lat, 0, 1)
        g.addWidget(QLabel("经度"), 0, 2)
        g.addWidget(self.ed_lon, 0, 3)
        g.addWidget(QLabel("高程 m"), 1, 0)
        g.addWidget(self.ed_alt, 1, 1)
        g.addWidget(QLabel("轨迹"), 1, 2)
        self.lbl_route = QLabel("静态点")
        self.lbl_route.setObjectName("DimTxt")
        g.addWidget(self.lbl_route, 1, 3)
        c.body.addLayout(g)
        self.map = MapWidget()
        c.body.addWidget(self.map, 1)

        def _map_click(lat, lon):
            self.ed_lat.setText(f"{lat:.6f}")
            self.ed_lon.setText(f"{lon:.6f}")
            self._sync_map_from_fields()
            self.session.bus.log(f"地图选点：{lat:.5f}, {lon:.5f}", "info")
        self.map.clicked.connect(_map_click)
        for ed in (self.ed_lat, self.ed_lon):
            ed.editingFinished.connect(self._sync_map_from_fields)
        return c

    def _sync_map_from_fields(self):
        try:
            self.map.set_pos(float(self.ed_lat.text()), float(self.ed_lon.text()))
        except ValueError:
            pass

    def _card_scenario(self) -> Card:
        c = Card("场景库", "与 Web 互通")
        self.ed_scn = self._line("", "场景名")
        self.cb_scn = self._combo(["载入已存场景…"])
        btn_ref = QPushButton("刷新")
        btn_ref.setObjectName("FileBtn")
        btn_ref.clicked.connect(self.refresh_scenarios)
        btn_load = QPushButton("载入")
        btn_load.setObjectName("FileBtn")
        btn_load.clicked.connect(self._load_scenario)
        btn_save = QPushButton("保存")
        btn_save.setObjectName("Ghost")
        btn_save.clicked.connect(self._save_scenario)
        row = QHBoxLayout()
        row.addWidget(self.ed_scn, 2)
        row.addWidget(btn_save)
        c.body.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(self.cb_scn, 1)
        row2.addWidget(btn_ref)
        row2.addWidget(btn_load)
        c.body.addLayout(row2)
        return c

    # ══ 右列：几何预览 ═══════════════════════════════════════════
    def _build_geo_col(self):
        col = QVBoxLayout()
        col.setSpacing(10)
        kpirow = QHBoxLayout()
        kpirow.setSpacing(10)
        self.kpi_sats = StatCard("可见卫星", "blue")
        self.kpi_pdop = StatCard("PDOP", "blue")
        self.kpi_gdop = StatCard("GDOP", "green")
        self.kpi_size = StatCard("产物估算", "green")
        for k in (self.kpi_sats, self.kpi_pdop, self.kpi_gdop, self.kpi_size):
            kpirow.addWidget(k)
        col.addLayout(kpirow)

        sky_card = Card("Skyplot 星空图", "Preview")
        self.skyplot = Skyplot()
        sky_card.body.addWidget(self.skyplot, 1)
        col.addWidget(sky_card, 5)

        tbl_card = Card("可见卫星表", "Az / El / Range / Doppler")
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["PRN", "系统", "方位°", "仰角°", "距离 km", "载波多普勒 Hz", "信号"])
        self.tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        tbl_card.body.addWidget(self.tbl, 1)
        col.addWidget(tbl_card, 4)

        warn_card = Card("告警", "Warnings")
        self.warn_view = QLabel("—")
        self.warn_view.setWordWrap(True)
        self.warn_view.setObjectName("Mut")
        warn_card.body.addWidget(self.warn_view)
        col.addWidget(warn_card)
        return col

    # ══ 动作条 ═══════════════════════════════════════════════════
    def _build_action_bar(self) -> QWidget:
        bar = Card()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.btn_preview = QPushButton("Preview 几何预览")
        self.btn_preview.setObjectName("Ghost")
        self.btn_preview.clicked.connect(self.on_preview)
        self.btn_gen = QPushButton("▶ Generate 生成 IQ")
        self.btn_gen.setObjectName("Primary")
        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setObjectName("Ghost")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_verify = QPushButton("Verify Fix 验证")
        self.btn_verify.setObjectName("Ghost")
        self.btn_verify.clicked.connect(self.on_verify)
        self.ck_autover = self._check("生成后自动验证", True)
        self.pb = QProgressBar()
        self.pb.setRange(0, 1000)
        self.pb.setValue(0)
        self.pb.setFixedWidth(220)
        self.hint = QLabel("就绪")
        self.hint.setObjectName("Mut")
        row.addWidget(self.btn_preview)
        row.addWidget(self.btn_gen)
        row.addWidget(self.btn_stop)
        row.addWidget(self.pb)
        row.addWidget(self.hint, 1)
        row.addWidget(self.ck_autover)
        row.addWidget(self.btn_verify)
        bar.body.addLayout(row)
        return bar

    # ══ 任务装载/回写 ════════════════════════════════════════════
    def load_task(self, t: SimTask):
        self._loading = True
        qdt = QDateTime.fromString(t.start_utc.replace("T", " "),
                                   "yyyy-MM-dd HH:mm:ss")
        if qdt.isValid():
            self.dt_start.setDateTime(qdt)
        self.ed_dur.setText(str(t.duration_s))
        self.cb_sr.setCurrentText(str(t.sample_rate))
        self.cb_fmt.setCurrentText(t.sample_format)
        self.ed_rinex.setText(t.rinex_path)
        self.cb_ephmode.setCurrentText(t.ephemeris_mode)
        self.ed_sp3.setText(t.sp3_path)
        self.ck_fb.setChecked(bool(t.fallback_to_broadcast))
        self.chip_sys.set_selected(t.systems)
        self.chip_band.set_selected(t.bands)
        self.ed_mask.setText(repr(t.mask_deg))
        self.ck_osnma.setChecked(t.osnma_enabled and "E" in t.systems)
        idx = {"1": 1, "2": 0, "3": 2}.get(str(t.osnma_nmas), 0)
        self.cb_nmas.setCurrentIndex(idx)
        self.cb_mdlpreset.setCurrentIndex(
            max(0, self.cb_mdlpreset.findData(t.mdl_preset)))
        self.cb_iono.setCurrentText(t.iono)
        self.cb_tropo.setCurrentText(t.tropo)
        self.cb_rxclk.setCurrentText(t.rxclk)
        for w, v in ((self.ed_clk_bias, t.rxclk_bias),
                     (self.ed_clk_drift, t.rxclk_drift),
                     (self.ed_clk_driftrate, t.rxclk_driftrate),
                     (self.ed_clk_sawamp, t.rxclk_sawamp),
                     (self.ed_clk_sawper, t.rxclk_sawper),
                     (self.ed_mp1d, t.mp1_delay), (self.ed_mp1a, t.mp1_amp),
                     (self.ed_mp1p, t.mp1_phase), (self.ed_mp2d, t.mp2_delay),
                     (self.ed_mp2a, t.mp2_amp), (self.ed_mp2p, t.mp2_phase)):
            w.setText(repr(v))
        self.cb_mp.setCurrentText(t.mp)
        self.ck_models_iq.setChecked(t.models_to_iq)
        self.ck_svclock.setChecked(bool(t.sv_clock))
        self.ck_imp.setChecked(t.imp_enabled)
        self.cb_imppreset.setCurrentIndex(
            max(0, self.cb_imppreset.findData(t.imp_preset)))
        for w, v in ((self.ed_impseed, t.imp_seed), (self.ed_impcfo, t.imp_cfo),
                     (self.ed_impppm, t.imp_ppm), (self.ed_impphn, t.imp_phn),
                     (self.ed_impgain, t.imp_gain),
                     (self.ed_impiqph, t.imp_iqphase),
                     (self.ed_impdci, t.imp_dci), (self.ed_impdq, t.imp_dcq),
                     (self.ed_impsnr, t.imp_snr),
                     (self.ed_impclip, t.imp_clip),
                     (self.ed_impbits, t.imp_bits)):
            w.setText("" if v == "" or v is None else str(v))
        self.cb_fade.setCurrentIndex(max(0, self.cb_fade.findData(t.fade_model)))
        self.cb_fadeenv.setCurrentIndex(
            max(0, self.cb_fadeenv.findData(t.fade_env)))
        self.ed_fadespeed.setText(t.fade_speed)
        self.ed_fadeseed.setText(str(t.fade_seed))
        self.ed_fadekey.setText(t.fade_key)
        self.ck_faderec.setChecked(t.fade_record_key)
        self.ed_lat.setText(repr(t.lat))
        self.ed_lon.setText(repr(t.lon))
        self.ed_alt.setText(repr(t.alt))
        self.map.set_pos(t.lat, t.lon)
        self.lbl_route.setText(
            f"轨迹 {len(t.route)} 点" if t.route else "静态点")
        self.ed_scn.setText(t.name)
        self._loading = False
        # 联动启用态
        self._sync_eph_mode(t.ephemeris_mode)
        self.cb_rxclk.currentTextChanged.emit(t.rxclk)
        self.cb_mp.currentTextChanged.emit(t.mp)
        self.ck_imp.toggled.emit(t.imp_enabled)
        self._sync_osnma()
        self._sync_fade_mode()
        if t.last_preview:
            self._fill_preview(t.last_preview)
        self._update_size_est()

    def _f(self, w: QLineEdit, default=0.0):
        try:
            return float(w.text().strip())
        except ValueError:
            return default

    def store_task(self) -> SimTask:
        t = self.session.current()
        t.start_utc = self.dt_start.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        t.duration_s = int(self._f(self.ed_dur, 60))
        srt = self.cb_sr.currentText().strip()
        t.sample_rate = "auto" if srt in ("auto", "") else float(
            srt.replace(",", ""))
        t.sample_format = self.cb_fmt.currentText()
        t.rinex_path = self.ed_rinex.text().strip() or "AUTO"
        t.ephemeris_mode = self.cb_ephmode.currentText()
        t.sp3_path = self.ed_sp3.text().strip()
        t.fallback_to_broadcast = self.ck_fb.isChecked()
        t.systems = self.chip_sys.selected() or ["G"]
        t.bands = self.chip_band.selected()
        t.mask_deg = self._f(self.ed_mask, 5.0)
        t.osnma_enabled = self.ck_osnma.isChecked()
        t.osnma_nmas = int(self.cb_nmas.currentText()[0])
        t.mdl_preset = self.cb_mdlpreset.currentData() or "manual"
        t.iono = self.cb_iono.currentText()
        t.tropo = self.cb_tropo.currentText()
        t.rxclk = self.cb_rxclk.currentText()
        t.rxclk_bias = self._f(self.ed_clk_bias)
        t.rxclk_drift = self._f(self.ed_clk_drift)
        t.rxclk_driftrate = self._f(self.ed_clk_driftrate)
        t.rxclk_sawamp = self._f(self.ed_clk_sawamp)
        t.rxclk_sawper = self._f(self.ed_clk_sawper)
        t.mp = self.cb_mp.currentText()
        t.mp1_delay, t.mp1_amp, t.mp1_phase = (
            self._f(self.ed_mp1d), self._f(self.ed_mp1a),
            self._f(self.ed_mp1p, 3.14159))
        t.mp2_delay, t.mp2_amp, t.mp2_phase = (
            self._f(self.ed_mp2d), self._f(self.ed_mp2a),
            self._f(self.ed_mp2p, 3.14159))
        t.models_to_iq = self.ck_models_iq.isChecked()
        t.sv_clock = self.ck_svclock.isChecked()
        t.imp_enabled = self.ck_imp.isChecked()
        t.imp_preset = self.cb_imppreset.currentData() or "manual"
        t.imp_seed = self._f(self.ed_impseed)
        t.imp_cfo = self._f(self.ed_impcfo)
        t.imp_ppm = self._f(self.ed_impppm)
        t.imp_phn = self._f(self.ed_impphn)
        t.imp_gain = self._f(self.ed_impgain)
        t.imp_iqphase = self._f(self.ed_impiqph)
        t.imp_dci = self._f(self.ed_impdci)
        t.imp_dcq = self._f(self.ed_impdq)
        t.imp_snr = self.ed_impsnr.text().strip()
        t.imp_clip = self._f(self.ed_impclip)
        t.imp_bits = self._f(self.ed_impbits)
        t.fade_model = self.cb_fade.currentData() or "off"
        t.fade_env = self.cb_fadeenv.currentData() or "suburban"
        t.fade_speed = self.ed_fadespeed.text().strip()
        t.fade_seed = self._f(self.ed_fadeseed, 1)
        t.fade_key = self.ed_fadekey.text().strip()
        t.fade_record_key = self.ck_faderec.isChecked()
        t.lat = self._f(self.ed_lat, t.lat)
        t.lon = self._f(self.ed_lon, t.lon)
        t.alt = self._f(self.ed_alt, t.alt)
        nm = self.ed_scn.text().strip()
        if nm:
            t.name = nm
        return t

    # ══ 场景库 ═══════════════════════════════════════════════════
    def refresh_scenarios(self):
        try:
            from desktop.core import bridge
            names = bridge.scenario_list()
        except Exception as e:                # noqa: BLE001
            self.win.log(f"场景库读取失败：{e}", "warn")
            return
        cur = self.cb_scn.currentData()
        self.cb_scn.clear()
        self.cb_scn.addItem("载入已存场景…", None)
        for n in names:
            self.cb_scn.addItem(n, n)
        if cur:
            self.cb_scn.setCurrentIndex(max(0, self.cb_scn.findData(cur)))

    def _save_scenario(self):
        t = self.store_task()
        name = self.ed_scn.text().strip() or t.name
        try:
            from desktop.core import bridge
            bridge.scenario_save(name, t.to_dict())
            self.session.bus.log(f"场景已保存：{name}（与 Web 场景库互通）", "ok")
            self.refresh_scenarios()
        except Exception as e:                # noqa: BLE001
            self.session.bus.log(f"场景保存失败：{e}", "bad")

    def _load_scenario(self):
        name = self.cb_scn.currentData()
        if not name:
            return
        try:
            from desktop.core import bridge
            params = bridge.scenario_load(name)
        except Exception as e:                # noqa: BLE001
            self.session.bus.log(f"场景载入失败：{e}", "bad")
            return
        t = self.session.current()
        merged = t.to_dict()
        merged.update({k: v for k, v in params.items()
                       if k in SimTask.__dataclass_fields__})
        merged.pop("last_outdir", None)
        self.session.tasks[self.session.cur] = SimTask.from_dict(merged)
        self.session.save()
        self.load_task(self.session.current())
        self.win.refresh_tasks(select_current=True)
        self.session.bus.log(f"场景已载入：{name}", "ok")

    # ══ Preview ══════════════════════════════════════════════════
    def _ensure_precise(self, t):
        """precise 模式且填了本地 SP3：先装载进内核（与 Web "Load this
        file" 同一 _precise_provider 入口），否则填了路径也不会生效。"""
        if t.ephemeris_mode != "precise" or not t.sp3_path.strip():
            return
        from desktop.core import bridge
        try:
            st = bridge.precise_load(t.sp3_path.strip())
            self.session.bus.log(
                f"precise：已装载 {st.get('source')}"
                f"（卫星 {st.get('satellites')}，历元 {st.get('epochs')}）",
                "ok")
        except Exception as e:                        # noqa: BLE001
            self.session.bus.log(
                f"SP3 装载失败：{e}（precise 将尝试自动下载/降级）", "warn")

    def on_preview(self):
        if self._prev_worker and self._prev_worker.isRunning():
            return
        t = self.store_task()
        self.session.save()
        self._ensure_precise(t)
        if t.bands:
            self.session.bus.log(
                "提示：几何预览按各系统默认信号计算，频段选择仅生成时生效",
                "info")
        self.btn_preview.setEnabled(False)
        self.hint.setText("几何预览计算中…")
        self.session.bus.set_status("Preview 计算中…")
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        w = FnWorker(bridge.preview, t.preview_body(),
                     busy_msg="preview")
        w.ok.connect(self._preview_done)
        w.fail.connect(self._preview_fail)
        self._prev_worker = w
        w.start()

    def _preview_done(self, res: dict):
        self.btn_preview.setEnabled(True)
        t = self.session.current()
        t.last_preview = res
        self._fill_preview(res)
        self.hint.setText("预览完成")
        self.session.bus.set_status("预览完成")
        self.session.bus.log(
            f"预览：可见星 {len(res.get('satellites', []))}，"
            f"PDOP {res.get('dop', {}).get('pdop')}", "ok")

    def _preview_fail(self, msg: str):
        self.btn_preview.setEnabled(True)
        self.hint.setText("预览失败")
        self.session.bus.set_status("预览失败")
        self.session.bus.log(f"预览失败：{msg.splitlines()[0]}", "bad")

    def _fill_preview(self, res: dict):
        sats = res.get("satellites", []) or []
        self.skyplot.set_satellites(sats)
        dop = res.get("dop", {}) or {}

        def _num(v, fmt="{:.2f}"):
            return fmt.format(v) if isinstance(v, (int, float)) else "—"
        self.kpi_sats.set(len(sats))
        self.kpi_pdop.set(_num(dop.get("pdop")))
        self.kpi_gdop.set(_num(dop.get("gdop")))
        self.tbl.setRowCount(len(sats))
        for r, s in enumerate(sats):
            sysk = s.get("sys", "G")
            cells = [
                str(s.get("prn", "")),
                sysk,
                f"{s.get('az_deg', 0):.1f}",
                f"{s.get('el_deg', 0):.1f}",
                f"{s.get('geo_range_m', 0) / 1000:.1f}",
                f"{s.get('carrier_doppler_hz', 0):+.1f}",
                str(s.get("signal_id", "")),
            ]
            for c, txt in enumerate(cells):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignCenter)
                if c == 1:
                    it.setForeground(QColor(theme.SYS_COLOR.get(sysk, theme.MUT)))
                self.tbl.setItem(r, c, it)
        warns = res.get("warnings", []) or []
        self.warn_view.setText("；".join(warns) if warns else "无告警")
        # 星座缺记录属于"结果与所选不符"，必须醒目提示而不是混在普通信息里
        degraded = any(("no records" in w or "omitted" in w) for w in warns)
        self.warn_view.setStyleSheet(
            f"color:{theme.BAD}; font-weight:bold;" if degraded else "")

    # ══ Generate ═════════════════════════════════════════════════
    def _update_size_est(self):
        t = self.session.current()
        srt = str(t.sample_rate)
        bpf = 2 if t.sample_format == "int8" else 4   # I+Q 每样本字节
        if srt in ("auto", "None", ""):
            self.kpi_size.set("—", "auto 采样率")
            return
        try:
            fs = float(srt)
        except ValueError:
            self.kpi_size.set("—")
            return
        self.kpi_size.set(fmt_bytes(fs * t.duration_s * bpf),
                          f"{fs / 1e6:.1f} Msps")

    def on_generate(self):
        if self._gen_worker and self._gen_worker.isRunning():
            return
        t = self.store_task()
        self.session.save()
        self._ensure_precise(t)
        self._update_size_est()
        body = t.generate_body()
        self.btn_gen.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.pb.setValue(0)
        self.hint.setText("生成中…（native 引擎）")
        self.session.bus.set_status(f"生成中：{t.name}")
        self.session.bus.log(
            f"开始生成：{t.name}｜{t.lat:.4f},{t.lon:.4f},{t.alt:.1f}｜"
            f"{t.duration_s}s × {self.cb_sr.currentText()} × {t.sample_format}"
            f"｜星座 {''.join(t.systems)}", "info")
        from desktop.core.worker import GenerateWorker
        w = GenerateWorker(body)
        # progress 携带 0..1 浮点比例；QProgressBar 量程 0..1000 且 setValue 收 int，
        # 直连会被 PySide 截断成 0（进度条全程 0%、结束才跳 100%），必须换算后转接。
        w.progress.connect(
            lambda f: self.pb.setValue(
                int(round(max(0.0, min(1.0, float(f))) * 1000))))
        w.ok.connect(self._gen_done)
        w.fail.connect(self._gen_fail)
        self._gen_worker = w
        w.start()

    def on_stop(self):
        if self._gen_worker and self._gen_worker.isRunning():
            self._gen_worker.request_stop()
            self.hint.setText("已请求停止…")

    def _gen_done(self, done: dict):
        self.btn_gen.setEnabled(True)
        self.btn_preview.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.pb.setValue(1000)
        outdir = done.get("outdir", "")
        t = self.session.current()
        t.last_outdir = outdir
        self.session.last_outdir = outdir
        self.win.foot_right.setText(f"最近产物：out/{outdir}")
        size = done.get("size_bytes")
        svs = done.get("svs")
        self.hint.setText(
            f"生成完成 out/{outdir}"
            + (f"（{fmt_bytes(size)}）" if size else ""))
        self.session.bus.set_status(f"生成完成：out/{outdir}")
        self.session.bus.log(
            f"生成完成：out/{outdir}"
            + (f"｜{fmt_bytes(size)}" if size else "")
            + (f"｜卫星 {len(svs)} 颗" if isinstance(svs, list) else ""), "ok")
        for wl in done.get("warnings", []) or []:
            self.session.bus.log(f"生成告警：{wl}", "warn")
        for k in ("fading", "trace_sim_file", "ephemeris_mode"):
            if done.get(k) is not None:
                self.session.bus.log(f"  {k} = {done[k]}", "info")
        if self.ck_autover.isChecked() and outdir:
            self.win.pages["verify"].run_verify(auto=True)
            self.win.goto("verify")

    def _gen_fail(self, msg: str):
        self.btn_gen.setEnabled(True)
        self.btn_preview.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.pb.setValue(0)
        self.hint.setText("生成失败")
        self.session.bus.set_status("生成失败")
        head = msg.splitlines()[0] if msg else "未知错误"
        self.session.bus.log(f"生成失败：{head}", "bad")
        for ln in msg.splitlines()[1:6]:
            self.session.bus.log(f"    {ln}", "bad")

    def on_verify(self):
        t = self.session.current()
        outdir = t.last_outdir or self.session.last_outdir
        if not outdir:
            self.session.bus.log("尚未生成任何场景，先 Preview/Generate", "warn")
            return
        self.win.pages["verify"].set_outdir(outdir)
        self.win.goto("verify")
