# -*- coding: utf-8 -*-
"""主窗：顶栏 + 左侧 rail 四页 + 状态栏；引擎/WS 生命周期在此编排。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..core.engine_mgr import EngineMgr, VARIANTS
from ..core.session import Session
from ..core.wslink import WsLink
from . import theme
from .pages.advanced import AdvancedPage
from .pages.console import ConsolePage
from .pages.data import DataPage
from .pages.logpage import LogPage
from .pages.monitor import MonitorPage
from .pages.solution import SolutionPage

PAGES = [("console", "控制台", "▶"), ("monitor", "监控", "◎"),
         ("advanced", "高级", "∿"), ("solution", "定位", "⌖"),
         ("data", "数据", "≡"), ("log", "日志", "☰")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PocketSDR Desktop")
        self.resize(1280, 820)
        self.session = Session()
        self.log = self.session.log
        self.engine = EngineMgr(log_fn=self.log)
        self.ws = WsLink(self)
        self._pending_cmds: list[dict] = []
        self._auto_start = False            # 引擎拉起后自动发 start

        # 顶栏
        top = QWidget(objectName="TopBar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 8, 16, 8)
        tl.addWidget(QLabel('<font id="Logo">PocketSDR</font> '
                            '<font color="#7d90b5" size="2">Desktop</font>'))
        tl.addStretch(1)
        self.dot_engine = QLabel("● 引擎停止")
        self.dot_engine.setStyleSheet(f"color:{theme.DIM};font-size:11px;")
        self.dot_ws = QLabel("○ WS")
        self.dot_ws.setStyleSheet(f"color:{theme.DIM};font-size:11px;")
        tl.addWidget(self.dot_engine)
        tl.addSpacing(14)
        tl.addWidget(self.dot_ws)
        tl.addSpacing(14)
        tl.addWidget(QLabel('<font color="#55648a" size="1">v0.1</font>'))

        # 左 rail
        rail = QWidget()
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(6, 10, 6, 10)
        rl.setSpacing(6)
        self._rail_btns: dict[str, QPushButton] = {}
        for key, name, icon in PAGES:
            b = QPushButton(f"{icon}\n{name}")
            b.setObjectName("RailBtn")
            b.setCheckable(True)
            b.setFixedWidth(58)
            b.clicked.connect(lambda _=False, k=key: self.goto(k))
            rl.addWidget(b)
            self._rail_btns[key] = b
        rl.addStretch(1)

        # 页面栈
        self.stack = QStackedWidget()
        self.page_console = ConsolePage(self)
        self.page_monitor = MonitorPage(self)
        self.page_advanced = AdvancedPage(self)
        self.page_solution = SolutionPage(self)
        self.page_data = DataPage(self)
        self.page_log = LogPage(self)
        self._by_key = {"console": self.page_console,
                        "monitor": self.page_monitor,
                        "advanced": self.page_advanced,
                        "solution": self.page_solution,
                        "data": self.page_data,
                        "log": self.page_log}
        for p in self._by_key.values():
            self.stack.addWidget(p)
        self.goto("console")

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(rail)
        body.addWidget(self.stack, 1)

        # 状态栏
        foot = QWidget(objectName="Footer")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(16, 4, 16, 4)
        self.foot_l = QLabel("就绪")
        self.foot_l.setObjectName("Foot")
        fl.addWidget(self.foot_l)
        fl.addStretch(1)
        self.foot_r = QLabel("")
        self.foot_r.setObjectName("Foot")
        fl.addWidget(self.foot_r)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(top)
        lay.addLayout(body, 1)
        lay.addWidget(foot)
        self.setCentralWidget(root)

        # 信号接线
        self.engine.started.connect(
            lambda port: (self._set_engine_dot(True), self.ws.connect_to(port)))
        self.engine.exited.connect(lambda _rc: self._on_engine_gone())
        self.ws.status.connect(self._ws_status)
        self.ws.msg.connect(self._dispatch)

    # ── 导航 ────────────────────────────────────────────────────
    def goto(self, key: str):
        for k, b in self._rail_btns.items():
            b.setChecked(k == key)
        cur = self.stack.currentWidget()
        if cur is not None and cur is not self._by_key[key] \
                and hasattr(cur, "on_hide"):
            cur.on_hide()                      # 先退订旧页，再进新页
        self.stack.setCurrentWidget(self._by_key[key])
        if hasattr(self._by_key[key], "on_show"):
            self._by_key[key].on_show()

    # ── 回放生命周期（控制台页调用）─────────────────────────────
    def start_replay(self, variant: str, setup_cmds: list[dict]):
        """拉起引擎并按序下发 set_inp/set_sig/sub，最后自动 start。"""
        try:
            if not self.engine.running:
                self.engine.start(variant, self.session.runlog_dir())
            elif self.engine.variant != variant:
                self.engine.stop()
                self.engine.start(variant, self.session.runlog_dir())
        except RuntimeError as e:
            self.log(str(e), "bad")
            return
        # 首条为 set_inp（stop 状态下允许配置）；随后 start
        self._pending_cmds = list(setup_cmds) + [{"cmd": "start"}]
        self._auto_start = True
        if self.ws.isRunning():
            self._flush_cmds()

    def stop_replay(self):
        if self.ws.isRunning():
            self.ws.cmd({"cmd": "stop"})
        self._auto_start = False
        self._pending_cmds = []
        QTimer.singleShot(400, self._teardown_link)

    def _teardown_link(self):
        self.ws.close()
        self.engine.stop()

    def _flush_cmds(self):
        for c in self._pending_cmds:
            self.ws.cmd(c)
        if self._pending_cmds:
            self.log(f"下发 {len(self._pending_cmds)} 条命令（含 start）", "ok")
        self._pending_cmds = []

    # ── 状态显示 ────────────────────────────────────────────────
    def _set_engine_dot(self, on: bool):
        if on:
            name = VARIANTS[self.engine.variant][0]
            self.dot_engine.setText(f"● 引擎运行（{name}）")
            self.dot_engine.setStyleSheet(
                f"color:{theme.ACC2};font-size:11px;font-weight:700;")
        else:
            self.dot_engine.setText("● 引擎停止")
            self.dot_engine.setStyleSheet(
                f"color:{theme.DIM};font-size:11px;")

    def _on_engine_gone(self):
        self._set_engine_dot(False)
        self.dot_ws.setText("○ WS")
        self.dot_ws.setStyleSheet(f"color:{theme.DIM};font-size:11px;")

    def _ws_status(self, s: str):
        if s == "connected":
            self.dot_ws.setText("● WS 已连接")
            self.dot_ws.setStyleSheet(f"color:{theme.ACC};font-size:11px;")
            if self._auto_start:
                QTimer.singleShot(150, self._flush_cmds)
        elif s == "connecting":
            self.dot_ws.setText("◌ 连接中")
            self.dot_ws.setStyleSheet(f"color:{theme.WARN};font-size:11px;")
        else:
            self.dot_ws.setText("○ WS 断开")
            self.dot_ws.setStyleSheet(f"color:{theme.BAD};font-size:11px;")

    # ── topic 分发 ──────────────────────────────────────────────
    def _dispatch(self, m: dict):
        t = m.get("type")
        if t == "ack" and not m.get("ok", True):
            self.log(f"命令被拒 {m.get('cmd')}: {m.get('msg', '')}", "warn")
        elif t == "rcv_stat":
            self.page_console.set_rcv_stat(m.get("str", ""))
            self.foot_r.setText(m.get("str", "")[:120])
        elif t == "ch_stat":
            self.page_monitor.update_ch_stat(m.get("str", ""))
            self.page_advanced.update_ch_stat_opt(m.get("str", ""))
            self.page_data.update_ch_stat(m.get("str", ""))
        elif t == "bin":
            self.page_advanced.on_bin(m)
        elif t == "sat_stat":
            self.page_monitor.update_sat_stat(m.get("sats", []))
            self.page_data.update_sat_stat(m.get("sats", []))
        elif t == "pvt_sol":
            self.page_solution.update_pvt(m.get("str", ""))
        elif t == "log":
            for ln in m.get("lines", []):
                self._engine_line(ln)

    def _engine_line(self, ln: str):
        lvl = "info"
        low = ln.lower()
        if any(w in low for w in ("error", "cannot", "fail", "invalid")):
            lvl = "bad"
        elif any(w in low for w in ("warn", "not found", "reject")):
            lvl = "warn"
        elif any(w in low for w in ("start", "found", "fix")):
            lvl = "ok"
        self.log(ln, lvl)

    def ws_cmd(self, d: dict):
        """页面直发命令（订阅类），未连接时静默忽略。"""
        if self.ws.isRunning():
            self.ws.cmd(d)

    def closeEvent(self, ev):                        # noqa: N802
        try:
            self.ws.close()
            self.engine.stop()
        finally:
            super().closeEvent(ev)
