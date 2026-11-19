# -*- coding: utf-8 -*-
"""设置对话框：目录/引擎信息（打包环境路径自查也靠它）。"""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QDialogButtonBox)

from . import theme
from .widgets import Card


def _open_path(p: str):
    try:
        if os.name == "nt":
            os.startfile(p)               # noqa: S606
        else:
            subprocess.Popen(["xdg-open", p])
    except OSError:
        pass


class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("设置 · gnss-sim 桌面版")
        self.resize(560, 420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        frozen = getattr(sys, "frozen", False)
        mode = ("PyInstaller 打包（frozen）" if frozen
                else f"源码运行（{sys.executable}）")

        rows: list[tuple[str, str, str]] = []
        try:
            from backend import config as bconfig
            rows += [("输出目录 out/", str(bconfig.OUT_DIR), str(bconfig.OUT_DIR)),
                     ("数据目录 data/", str(bconfig.DATA_DIR), str(bconfig.DATA_DIR))]
            try:
                from backend.synth import _lib
                ok = _lib.LIB_PATH.exists()
                rows.append(("native 引擎",
                             f"{_lib.LIB_PATH.name}｜ABI v{_lib.ABI_VERSION}｜"
                             + ("已就位 ✓" if ok else "缺失 ✗"),
                             str(_lib.LIB_PATH.parent) if ok else ""))
            except Exception as e:        # noqa: BLE001
                rows.append(("native 引擎", f"探测失败：{e}", ""))
        except Exception as e:            # noqa: BLE001
            rows.append(("后端配置", f"未加载（{e}）", ""))
        rows.append(("任务存档", str(self.win.session._file),
                     str(self.win.session._file.parent)))
        rows.append(("运行模式", mode, ""))
        rows.append(("Python/Qt",
                     f"{sys.version.split()[0]} · PySide6 "
                     f"{__import__('PySide6').__version__}", ""))

        c = Card("路径与引擎", "Settings")
        for k, v, path in rows:
            row = QHBoxLayout()
            lab = QLabel(k)
            lab.setObjectName("Mut")
            lab.setMinimumWidth(96)
            val = QLabel(v)
            val.setObjectName("MonoVal")
            val.setWordWrap(True)
            row.addWidget(lab)
            row.addWidget(val, 1)
            if path and os.path.exists(path):
                b = QPushButton("打开")
                b.setObjectName("FileBtn")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _, pp=path: _open_path(pp))
                row.addWidget(b)
            c.body.addLayout(row)
        lay.addWidget(c)

        note = QLabel("界面主题：清淡浅白 v3（浅色）；硬件通道/播发功能按方案裁剪。\n"
                      "输出与数据目录可用环境变量 OUT_DIR / DATA_DIR 覆盖。")
        note.setObjectName("DimTxt")
        lay.addWidget(note)
        lay.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        btn = bb.button(QDialogButtonBox.Close)
        btn.setObjectName("Ghost")
        btn.setText("关闭")
        lay.addWidget(bb)
