# 解码 iflc_fix4.log 中 E07/E5AI 各页的 type + tow 字段（用 _fnav_layout 位布局）
import re, sys
sys.path.insert(0, ".")
from backend.analysis import _fnav_layout as L

def bits_from_hex(h):
    v = int(h, 16)
    nbits = len(h) * 4
    return [(v >> (nbits - 1 - i)) & 1 for i in range(nbits)]

def fields_of(wtype):
    tbl = getattr(L, f"WORD{wtype}", None) or getattr(L, f"word{wtype}", None) \
          or L.LAYOUTS.get(wtype) if hasattr(L, "LAYOUTS") else None
    return tbl

# 先看 layout 模块结构
print([a for a in dir(L) if not a.startswith('_')][:20])
