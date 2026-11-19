# -*- coding: utf-8 -*-
"""主窗：顶栏 + 左 rail 六页导航 + 任务列表 + 页面栈 + 底栏状态。"""
from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QPushButton, QFrame, QStackedWidget,
                               QButtonGroup, QScrollArea, QSizePolicy)

from . import theme
from .pages.sim import SimPage
from .pages.verify import VerifyPage
from .pages.iqpage import IqPage
from .pages.traj import TrajPage
from .pages.logpage import LogPage
from .pages.hist import HistPage

PAGES = [("sim", "仿真", "◈"), ("verify", "验证", "✓"), ("iq", "图谱", "∿"),
         ("traj", "轨迹", "⚑"), ("log", "日志", "☰"), ("hist", "历史", "◷")]


class MainWindow(QMainWindow):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setWindowTitle("gnss-sim-desktop · 中频信号仿真器（桌面版）")
        self.resize(1500, 920)
        self._rail_btns: dict[str, QPushButton] = {}
        self._task_btns: list[QPushButton] = []
        self._task_group = None

        root = QWidget()
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_rail())
        body.addWidget(self._build_taskpanel())

        self.stack = QStackedWidget()
        self.pages = {
            "sim": SimPage(self), "verify": VerifyPage(self),
            "iq": IqPage(self), "traj": TrajPage(self),
            "log": LogPage(self), "hist": HistPage(self),
        }
        for key, _, _ in PAGES:
            self.stack.addWidget(self.pages[key])
        body.addWidget(self.stack, 1)
        rl.addLayout(body, 1)
        rl.addWidget(self._build_footer())
        self.setCentralWidget(root)

        self.session.bus.status.connect(self.foot_lbl.setText)
        self.refresh_tasks(select_current=True)
        self.pages["sim"].load_task(self.session.current())
        self.goto("sim")
        self.session.bus.log("桌面版已启动（桥接层将按需加载 backend 内核）", "ok")

    # ══ 顶栏 ══════════════════════════════════════════════════════
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(46)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)
        logo = QLabel("GNSS·SIM")
        logo.setObjectName("Logo")
        sub = QLabel("IF Data Simulator · Desktop")
        sub.setObjectName("LogoSub")
        lay.addWidget(logo)
        lay.addWidget(sub)
        lay.addStretch(1)
        self.engine_dot = QLabel("●")
        self.engine_dot.setObjectName("Dot")
        self.engine_lbl = QLabel("native 引擎 · 待命")
        self.engine_lbl.setObjectName("Mut")
        openbtn = QPushButton("打开输出目录")
        openbtn.setObjectName("Link")
        openbtn.setCursor(Qt.PointingHandCursor)
        openbtn.clicked.connect(self._open_outdir)
        setbtn = QPushButton("设置")
        setbtn.setObjectName("Link")
        setbtn.setCursor(Qt.PointingHandCursor)
        setbtn.clicked.connect(self._open_settings)
        ver = QLabel("v0.9-desktop")
        ver.setObjectName("DimTxt")
        lay.addWidget(self.engine_dot)
        lay.addWidget(self.engine_lbl)
        lay.addSpacing(14)
        lay.addWidget(openbtn)
        lay.addWidget(setbtn)
        lay.addWidget(ver)
        return bar

    def _open_settings(self):
        from .settings import SettingsDialog
        SettingsDialog(self).exec()

    def _open_outdir(self):
        try:
            from desktop.core import bridge
            d = bridge.web().config.OUT_DIR
            d.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(d))                # noqa: S606
            else:
                subprocess.Popen(["xdg-open", str(d)])
            self.session.bus.log(f"已在资源管理器打开 {d}", "info")
        except Exception as e:                      # noqa: BLE001
            self.session.bus.log(f"打开输出目录失败：{e}", "warn")

    # ══ 左 rail ══════════════════════════════════════════════════
    def _build_rail(self) -> QFrame:
        rail = QFrame()
        rail.setFixedWidth(76)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(6)
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for i, (key, name, glyph) in enumerate(PAGES):
            b = QPushButton(f"{glyph}\n{name}")
            b.setObjectName("RailBtn")
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(58)
            b.clicked.connect(lambda _=False, k=key: self.goto(k))
            grp.addButton(b)
            lay.addWidget(b)
            self._rail_btns[key] = b
        lay.addStretch(1)
        return rail

    # ══ 任务面板 ══════════════════════════════════════════════════
    def _build_taskpanel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(232)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel("仿真任务")
        t.setObjectName("CardTitle")
        head.addWidget(t)
        head.addStretch(1)
        lay.addLayout(head)
        ops = QHBoxLayout()
        ops.setSpacing(4)
        for text, slot in (("新建", self._new_task), ("复制", self._dup_task),
                           ("删除", self._del_task)):
            b = QPushButton(text)
            b.setObjectName("FileBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            ops.addWidget(b)
        lay.addLayout(ops)
        self._task_scroll = QScrollArea()
        self._task_scroll.setWidgetResizable(True)
        holder = QWidget()
        self._task_lay = QVBoxLayout(holder)
        self._task_lay.setContentsMargins(0, 0, 0, 0)
        self._task_lay.setSpacing(6)
        self._task_lay.addStretch(1)
        self._task_scroll.setWidget(holder)
        lay.addWidget(self._task_scroll, 1)
        hint = QLabel("任务配置自动保存于\n~/.gnss-sim-desktop/tasks.json")
        hint.setObjectName("DimTxt")
        lay.addWidget(hint)
        return panel

    def refresh_tasks(self, select_current: bool = False):
        while self._task_lay.count() > 1:
            item = self._task_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._task_btns = []
        for i, t in enumerate(self.session.tasks):
            b = QPushButton(f"{t.name}\n{t.lat:.3f}, {t.lon:.3f} · {t.duration_s}s")
            b.setObjectName("TaskItem")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            b.clicked.connect(lambda _=False, idx=i: self._select_task(idx))
            self._task_lay.insertWidget(i, b)
            self._task_btns.append(b)
        if select_current and 0 <= self.session.cur < len(self._task_btns):
            self._task_btns[self.session.cur].setChecked(True)

    def _commit_edits(self):
        """切换/新建/删除前固化仿真页未保存的控件值，避免静默回滚。"""
        try:
            self.pages["sim"].store_task()
        except Exception:                           # noqa: BLE001
            pass                                    # 页面未就绪时忽略

    def _select_task(self, i: int):
        if i != self.session.cur:
            self._commit_edits()
        self.session.select(i)
        for j, b in enumerate(self._task_btns):
            b.setChecked(j == i)
        self.pages["sim"].load_task(self.session.current())
        self.session.bus.log(f"切换到任务：{self.session.current().name}", "info")

    def _new_task(self):
        self._commit_edits()
        self.session.new_task()
        self.refresh_tasks(select_current=True)
        self.pages["sim"].load_task(self.session.current())

    def _dup_task(self):
        self._commit_edits()                       # 先固化当前编辑
        self.session.duplicate_task()
        self.refresh_tasks(select_current=True)
        self.pages["sim"].load_task(self.session.current())

    def _del_task(self):
        self._commit_edits()
        if not self.session.delete_task(self.session.cur):
            self.session.bus.log("至少保留一个任务", "warn")
        self.refresh_tasks(select_current=True)
        self.pages["sim"].load_task(self.session.current())

    # ══ 底栏 ══════════════════════════════════════════════════════
    def _build_footer(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("Footer")
        bar.setFixedHeight(26)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        self.foot_lbl = QLabel("就绪")
        self.foot_lbl.setObjectName("Foot")
        lay.addWidget(self.foot_lbl)
        lay.addStretch(1)
        self.foot_right = QLabel("")
        self.foot_right.setObjectName("Foot")
        lay.addWidget(self.foot_right)
        return bar

    # ══ 导航 ══════════════════════════════════════════════════════
    def goto(self, key: str):
        for k, b in self._rail_btns.items():
            b.setChecked(k == key)
        idx = next(i for i, (k, _, _) in enumerate(PAGES) if k == key)
        self.stack.setCurrentIndex(idx)
        name = dict((k, n) for k, n, _ in PAGES)[key]
        onshow = getattr(self.pages[key], "on_show", None)
        if onshow:
            onshow()

    def log(self, msg: str, level: str = "info"):
        self.session.bus.log(msg, level)
