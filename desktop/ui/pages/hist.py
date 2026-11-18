# -*- coding: utf-8 -*-
"""历史页：out/ 场景列表（meta 摘要 + 验证误差），支持载入任务/打开目录/再验证。"""
from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView)

from ..widgets import Card, fmt_bytes

COLS = ["runid", "开始 UTC", "时长s", "采样率", "格式", "星座",
        "大气注入", "error_m", "体积", "引擎"]


class HistPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._worker = None
        self._runs: list[dict] = []
        self._loaded_once = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        c = Card("历史场景", "out/ 目录扫描")
        self.tbl = QTableWidget(0, len(COLS))
        self.tbl.setHorizontalHeaderLabels(COLS)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemDoubleClicked.connect(
            lambda *_: self._open_dir())
        c.body.addWidget(self.tbl, 1)
        row = QHBoxLayout()
        for text, slot in (("刷新", self.refresh),
                           ("载入到当前任务", self._load_to_task),
                           ("打开目录", self._open_dir),
                           ("跳转验证", self._goto_verify)):
            b = QPushButton(text)
            b.setObjectName("Ghost" if text == "载入到当前任务" else "FileBtn")
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        self.hint = QLabel("双击行 = 打开目录")
        self.hint.setObjectName("DimTxt")
        row.addWidget(self.hint)
        c.body.addLayout(row)
        lay.addWidget(c, 1)

    def on_show(self):
        if not self._loaded_once:
            self.refresh()

    def refresh(self):
        if self._worker and self._worker.isRunning():
            return
        from desktop.core import bridge
        from desktop.core.worker import FnWorker
        self.hint.setText("扫描 out/ …")
        w = FnWorker(bridge.list_runs, 120)
        w.ok.connect(self._fill)
        w.fail.connect(lambda m: self.hint.setText(f"扫描失败：{m.splitlines()[0]}"))
        self._worker = w
        w.start()

    def _fill(self, runs: list[dict]):
        self._runs = runs or []
        self._loaded_once = True
        self.hint.setText(f"共 {len(self._runs)} 个场景（双击行 = 打开目录）")
        self.tbl.setRowCount(len(self._runs))
        for r, info in enumerate(self._runs):
            fs = info.get("sample_rate")
            atmo = info.get("atmosphere") or {}
            if isinstance(atmo, dict):
                at = "/".join(str(atmo.get(k, "off"))
                              for k in ("ionosphere", "troposphere"))
            else:
                at = str(atmo)
            err = info.get("error_m")
            cells = [
                info.get("outdir", ""),
                str(info.get("start_utc", ""))[:19],
                str(info.get("duration_s", "")),
                f"{fs / 1e6:.2f}M" if isinstance(fs, (int, float)) else "—",
                str(info.get("sample_format", "")),
                "".join(info.get("systems") or []),
                at,
                f"{err:.2f}" if isinstance(err, (int, float)) else "—",
                fmt_bytes(info.get("size_bytes", 0)),
                str(info.get("engine", "")),
            ]
            for c, txt in enumerate(cells):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(r, c, it)

    def _selected(self) -> dict | None:
        r = self.tbl.currentRow()
        if 0 <= r < len(self._runs):
            return self._runs[r]
        return None

    def _open_dir(self):
        info = self._selected()
        if not info:
            return
        p = info.get("path", "")
        try:
            if os.name == "nt":
                os.startfile(p)               # noqa: S606
            else:
                subprocess.Popen(["xdg-open", p])
        except OSError as e:
            self.win.log(f"打开失败：{e}", "warn")

    def _goto_verify(self):
        info = self._selected()
        if not info:
            return
        self.win.pages["verify"].set_outdir(info["outdir"])
        self.win.goto("verify")

    def _load_to_task(self):
        """把 run 的 meta.config 映射回当前任务（可复现编辑）。"""
        info = self._selected()
        if not info:
            return
        try:
            import json
            import pathlib
            meta = json.loads(
                (pathlib.Path(info["path"]) / "meta.json").read_text(
                    encoding="utf-8"))
        except (OSError, ValueError) as e:
            self.win.log(f"读取 meta 失败：{e}", "warn")
            return
        cfg = meta.get("config", {})
        t = self.session_task()
        for key in ("lat", "lon", "alt"):
            if isinstance(cfg.get(key), (int, float)):
                setattr(t, key, float(cfg[key]))
        if cfg.get("start_utc"):
            t.start_utc = str(cfg["start_utc"]).replace("Z", "")[:19]
        if isinstance(cfg.get("duration_s"), (int, float)):
            t.duration_s = int(cfg["duration_s"])
        if isinstance(meta.get("sample_rate"), (int, float)):
            t.sample_rate = float(meta["sample_rate"])
        if meta.get("sample_format"):
            t.sample_format = str(meta["sample_format"])
        if info.get("systems"):
            t.systems = list(info["systems"])
        atmo = cfg.get("atmosphere")
        if isinstance(atmo, dict):
            t.iono = atmo.get("ionosphere", "off")
            t.tropo = atmo.get("troposphere", "off")
        if cfg.get("rinex_path"):
            t.rinex_path = str(cfg["rinex_path"])
        t.last_outdir = info["outdir"]
        self.session.save()
        self.win.pages["sim"].load_task(t)
        self.win.refresh_tasks(select_current=True)
        self.win.log(f"已将 out/{info['outdir']} 参数载入当前任务", "ok")

    def session_task(self):
        return self.session.current()

    @property
    def session(self):
        return self.win.session
