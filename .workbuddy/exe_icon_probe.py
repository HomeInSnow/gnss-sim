# -*- coding: utf-8 -*-
"""验收：提取打包 exe 的文件图标（PE 资源 MAINICON），存 PNG 供 ViewImage 亲审。

用法: QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe .workbuddy/exe_icon_probe.py <exe> <out.png>
原理: Windows 下 QFileIconProvider 经 SHGetFileInfo 返回 exe 内嵌图标（非文件类型默认图标）。
"""
import sys

from PySide6.QtCore import QFileInfo
from PySide6.QtWidgets import QApplication, QFileIconProvider

exe, out = sys.argv[1], sys.argv[2]
app = QApplication([])
ic = QFileIconProvider().icon(QFileInfo(exe))
if ic.isNull():
    print("EXE-ICON-NULL", exe)
    sys.exit(1)
pm = ic.pixmap(128, 128)
ok = pm.save(out)
# 与默认空白图标对比：采样中心区域是否含非灰彩色像素
img = pm.toImage()
colored = 0
for y in range(0, img.height(), 4):
    for x in range(0, img.width(), 4):
        c = img.pixelColor(x, y)
        if c.alpha() > 0 and (max(c.red(), c.green(), c.blue()) - min(c.red(), c.green(), c.blue())) > 40:
            colored += 1
print(f"EXE-ICON-OK {exe} saved={ok} colored_px={colored}")
sys.exit(0 if ok and colored > 20 else 1)
