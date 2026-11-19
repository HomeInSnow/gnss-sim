# -*- coding: utf-8 -*-
"""生成 af0/af1/af2 清零 + toe 对齐 16s 网格的 BRDC 拷贝（tgd 与轨道参数保留）。

用途：FGI-GSRx 的 applyClockCorrections 无开关，会无条件从 LNAV 消息
af 字段做卫星钟差修正。本引擎场景 sv_clock=false（信号未注入钟差），
消息 af 若非零会让 FGI 减去不存在的钟差 → 几十 km 崩掉。
把 BRDC 的 af 三字段清零重新生成场景，消息里 af=0，FGI 修正量为 0,
与论文"省略卫星钟误差"设置对齐。

第二项修正（2026-11-11）：本 BRDC 的 30 条记录 toe 均为 428418，不在
GPS 广播电文的 16s 网格上。编码器 subframe2 按 round(toe/16)*16 发送
428416，而引擎注入侧用原始 428418 传播 → 消息与真实轨道 toe 相差 2s
→ FGI 用消息 toe 传播的卫星位置偏差 ≈ v_sat*2s（LOS 投影 ±0.2~1.7km），
主导 LSE 残差。把 BRDC 的 toe 也 snap 到同一 round(toe/16)*16，注入与
广播完全一致（真实 GPS 的 toe 本来就在 16s 网格上）。

RINEX 2.x GPS nav 记录首行（8 行记录中的第 1 行）：
  PRN yy mm dd hh mm ss.fff af0 af1 af2
只替换首行的三个 D 型浮点字段；记录第 4 行 toe 字段（列 4-22）snap；
其余行（含 tgd）原样保留。
"""
import re
import sys

SRC = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271.rnx"
DST = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271_afzero.rnx"

# 记录首行特征：PRN + yy mm dd hh mm + ss.f（年份 23）
REC_START = re.compile(r"^\s*\d{1,2} 23 \d{2} \d{2} \d{2} \d{2} \d{2}\.\d")
# D20.12 风格的科学计数法 token（前导符号可为空格）
DFLOAT = re.compile(r"[ -]\d\.\d{12}E[+-]\d{2}")


def zero_af(line: str) -> str:
    toks = list(DFLOAT.finditer(line))
    if len(toks) < 3:
        raise SystemExit(f"记录首行 D 字段不足 3 个: {line!r}")
    out = list(line.rstrip("\n"))
    # 从后往前替换，避免位移失效
    for m in toks[:3][::-1]:
        s, e = m.span()
        w = e - s
        zero = " 0.000000000000E+00"[-w:] if w <= 19 else \
               " " * (w - 19) + "0.000000000000E+00"
        zero = zero.rjust(w)
        if len(zero) > w:
            zero = zero[:w]
        out[s:e] = list(zero)
    return "".join(out) + "\n"


def snap_toe(line: str) -> str:
    """记录第 4 行（toe Cic W0 Cis）：toe 字段在列 4-22（切片 [3:22]），
    snap 到编码器同款 16s 网格 round(toe/16)*16，宽度不变。"""
    tok = line[3:22]
    toe = float(tok.replace("D", "E"))
    q = round(toe / 16.0) * 16.0
    if q == toe:
        return line
    new = "%19.11E" % q
    if new[0] not in " -":
        new = " " + new[:18]
    assert len(new) == 19, (tok, new)
    return line[:3] + new + line[22:]


def main():
    n_rec = 0
    n_snap = 0
    with open(SRC, "r", encoding="ascii") as fi, \
         open(DST, "w", encoding="ascii", newline="") as fo:
        in_header = True
        pos = -1  # 记录内行号（0=首行）
        for line in fi:
            if in_header:
                fo.write(line)
                if "END OF HEADER" in line:
                    in_header = False
                continue
            if REC_START.match(line):
                n_rec += 1
                pos = 0
                fo.write(zero_af(line))
            else:
                pos += 1
                if pos == 3:
                    before = line[3:22]
                    line = snap_toe(line)
                    if line[3:22] != before:
                        n_snap += 1
                fo.write(line)
    print(f"records zeroed: {n_rec}; toe snapped: {n_snap}")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
