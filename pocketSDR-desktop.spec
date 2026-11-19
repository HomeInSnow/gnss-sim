# -*- coding: utf-8 -*-
"""PyInstaller 打包：pocketSDR-desktop（引擎三变体 + html 随包）。

构建：.venv/Scripts/python.exe -m PyInstaller -y pocketSDR-desktop.spec \
      --distpath dist --workpath .workbuddy/pyi_build_pocket
产物：dist/pocketSDR-desktop/pocketSDR-desktop.exe
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
# 仓库兄弟目录：改名后优先 pocketSDR-desktop，兼容旧名 PocketSDR（同 engine_dir 策略）
for _cand in (root.parent / "pocketSDR-desktop", root.parent / "PocketSDR"):
    if (_cand / "local_build").is_dir():
        psdr = _cand
        break
else:
    raise FileNotFoundError("未找到兄弟目录 pocketSDR-desktop/PocketSDR（缺 local_build）")

ENGINE_EXES = ("pocket_web_local.exe", "pocket_web_both_off.exe",
               "pocket_web_iflc.exe")
datas = [(str(psdr / "local_build" / e), "engine") for e in ENGINE_EXES
         if (psdr / "local_build" / e).exists()]
if (psdr / "html").exists():
    datas.append((str(psdr / "html"), "engine/html"))
datas.append((str(root / "pocket_desktop" / "assets"), "pocket_desktop/assets"))
datas += collect_data_files("pyqtgraph")

hiddenimports = (collect_submodules("pocket_desktop")
                 + collect_submodules("websockets")
                 + ["pyqtgraph"])

a = Analysis(
    ["pyi_entry_pocket.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "scipy", "pytest",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
              "PySide6.QtMultimedia", "PySide6.QtSerialPort",
              "PySide6.QtBluetooth", "PySide6.QtWebChannel"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="pocketSDR-desktop",
    debug=False, strip=False, upx=False,
    console=False,
    icon=str(root / "pocket_desktop" / "assets" / "app.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas,
               strip=False, upx=False, name="pocketSDR-desktop")
