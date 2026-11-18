# -*- coding: utf-8 -*-
"""会话状态：任务列表持久化 + 全局日志总线。"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

from PySide6.QtCore import QObject, Signal

from .model import SimTask

STORE_DIR = pathlib.Path.home() / ".gnss-sim-desktop"


class LogBus(QObject):
    """全局结构化日志（日志页订阅，状态栏订阅 status）。"""
    line = Signal(str, str, str)      # ts, level(info/ok/warn/bad), msg
    status = Signal(str)

    def log(self, msg: str, level: str = "info"):
        ts = dt.datetime.now().strftime("%H:%M:%S")
        self.line.emit(ts, level, str(msg))

    def set_status(self, msg: str):
        self.status.emit(str(msg))


class Session:
    """跨页面共享的应用状态（任务集合 + 最近产物指针）。"""

    def __init__(self):
        self.bus = LogBus()
        self.tasks: list[SimTask] = []
        self.cur = 0
        self.last_outdir: str = ""          # 最近一次生成的 runid
        self.verify_result: dict | None = None
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._file = STORE_DIR / "tasks.json"
        self._load()
        if not self.tasks:
            self.tasks.append(SimTask())
            self.cur = 0

    # ── 持久化 ──
    def _load(self):
        try:
            if self._file.exists():
                arr = json.loads(self._file.read_text(encoding="utf-8"))
                self.tasks = [SimTask.from_dict(d) for d in arr]
        except Exception:                   # noqa: BLE001 - 坏档不阻止启动
            self.tasks = []

    def save(self):
        try:
            self._file.write_text(
                json.dumps([t.to_dict() for t in self.tasks],
                           ensure_ascii=False, indent=1),
                encoding="utf-8")
        except OSError as e:
            self.bus.log(f"任务保存失败：{e}", "warn")

    # ── 任务操作 ──
    def current(self) -> SimTask:
        if not self.tasks:
            self.tasks.append(SimTask())
            self.cur = 0
        self.cur = min(self.cur, len(self.tasks) - 1)
        return self.tasks[self.cur]

    def select(self, i: int):
        if 0 <= i < len(self.tasks):
            self.cur = i

    def new_task(self) -> SimTask:
        t = SimTask(name=f"场景 {len(self.tasks) + 1}")
        self.tasks.append(t)
        self.cur = len(self.tasks) - 1
        self.save()
        return t

    def duplicate_task(self) -> SimTask:
        src = self.current()
        d = src.to_dict()
        d["name"] = src.name + " 副本"
        d["last_outdir"] = ""
        t = SimTask.from_dict(d)
        self.tasks.insert(self.cur + 1, t)
        self.cur += 1
        self.save()
        return t

    def delete_task(self, i: int) -> bool:
        if len(self.tasks) <= 1:
            return False
        if 0 <= i < len(self.tasks):
            del self.tasks[i]
            self.cur = max(0, min(self.cur, len(self.tasks) - 1))
            self.save()
        return True
