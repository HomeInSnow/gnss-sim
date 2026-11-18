# -*- coding: utf-8 -*-
"""PyInstaller 打包入口（仓库根，保证 desktop/backend 包可解析）。"""
from desktop.app import main

if __name__ == "__main__":
    raise SystemExit(main())
