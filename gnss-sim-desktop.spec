# -*- mode: python ; coding: utf-8 -*-
"""gnss-sim-desktop 桌面版 PyInstaller spec（onedir）。

构建：.venv/Scripts/python.exe -m PyInstaller -y gnss-sim-desktop.spec
产物：dist/gnss-sim-desktop/gnss-sim-desktop.exe（同目录随包 libgnsssynth.dll、frontend、地图轮廓）
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)

hidden = []
hidden += collect_submodules("backend")
hidden += collect_submodules("desktop")
hidden += [
    "pyqtgraph",
    "pyqtgraph.graphicsItems.ScatterPlotItem",
    "pyqtgraph.console",          # pyqtgraph 可选入口，显式排除反例：不引
    "georinex",
    "georinex.nav3",
    "fastapi",
    "starlette",
    "pydantic",
    "multipart",                  # fastapi UploadFile
    "anyio",
    "anyio._backends._asyncio",
]
hidden = [h for h in hidden if not h.endswith(".console")]

datas = [
    ("backend/synth/native/libgnsssynth.dll", "backend/synth/native"),
    ("frontend", "frontend"),
    ("desktop/assets/world_land.geojson", "desktop/assets"),
    ("desktop/assets/app.ico", "desktop/assets"),
]
datas += collect_data_files("georinex")
datas += collect_data_files("xarray")
datas += collect_data_files("pyqtgraph")

a = Analysis(
    ["pyi_entry.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "matplotlib", "tkinter", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick",
        "PySide6.QtQuick3D", "PySide6.Qt3DCore", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtMultimedia",
        "PySide6.QtBluetooth", "PySide6.QtNetworkAuth", "PySide6.QtSerialPort",
        "PySide6.QtWebSockets", "PySide6.QtPdf", "serial", "usb",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gnss-sim-desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    contents_directory="_internal",
    icon=str(ROOT / "desktop" / "assets" / "app.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="gnss-sim-desktop",
)
