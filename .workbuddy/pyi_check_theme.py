# -*- coding: utf-8 -*-
"""验收：从 PyInstaller onedir exe 的 PYZ 里提取主题模块，确认色板已更新。

用法: .venv/Scripts/python.exe .workbuddy/pyi_check_theme.py <exe路径> <模块名> <色值token>
示例: ... dist/gnss-sim/gnss-sim.exe desktop.ui.theme eef2f8
"""
import marshal
import sys

from PyInstaller.archive.readers import CArchiveReader

exe, mod, token = sys.argv[1], sys.argv[2], sys.argv[3].encode()
r = CArchiveReader(exe)
data = None
for cand in ("PYZ.pyz", "PYZ"):
    try:
        z = r.open_embedded_archive(cand)
        data = z.extract(mod)
        break
    except Exception:
        continue
if data is None:
    # 兜底：遍历嵌入式档案
    try:
        for name in r.toc:
            try:
                z = r.open_embedded_archive(name)
                data = z.extract(mod)
                break
            except Exception:
                continue
    except Exception:
        pass
if data is None:
    print(f"PYI-CHECK-FAIL cannot read {mod} from {exe}")
    sys.exit(1)
if not isinstance(data, (bytes, bytearray)):   # code object → 重序列化
    data = marshal.dumps(data)
ok = token in data
print(("PYI-CHECK-OK " if ok else "PYI-CHECK-BAD ")
      + f"{exe} :: {mod} size={len(data)} token={token.decode()} found={ok}")
sys.exit(0 if ok else 1)
