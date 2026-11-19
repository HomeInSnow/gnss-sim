# -*- coding: utf-8 -*-
"""RINEX 3.04 版 afzero：武大 BRDC00IGS_R 混合导航文件 af0/af1/af2 清零。

用途同 make_afzero_brdc.py（FGI satClkCorr 无开关，sv_clock=false 场景消息
af 必须为零），区别：输入是 RINEX 3.04 mixed（G/E/C 记录，PRN 形如 "G28"，
年份 4 位，秒字段为整数 SS，af 用 E/D 指数混排）。af 字段用 token 法置零
（记录首行时间字段后恰有 3 个 20 列宽浮点 token，之后是整数 IODC）。

真实广播 toe 天然在 16s 网格（脚本校验 G 记录第 4 行）。
不覆盖 GFZ 拟合版 BRDC_2023271_afzero.rnx（主 run provenance 输入）。
"""
import re

SRC = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271.rnx"
DST = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271_whu_afzero.rnx"

# RINEX3 记录首行：PRN(如 G28) + 完整日期时间（秒为整数或带小数）
REC_START = re.compile(r"^\s*[GEJCRSI][0-9A-Z]{2} 20\d\d \d\d \d\d \d\d \d\d \d\d(\.\d)?[ ]*[ -]\d\.\d{12}[ED]")
# 20 列浮点 token（可含前导空格）
DFLOAT = re.compile(r"[ -]\d\.\d{12}[ED][+-]\d{2}")


def zero_af(line: str) -> str:
    toks = [m for m in DFLOAT.finditer(line)]
    if len(toks) < 3:
        raise SystemExit(f"记录首行 D 字段不足 3 个: {line!r}")
    out = list(line.rstrip("\n"))
    n0 = len(out)
    for m in toks[:3][::-1]:
        s, e = m.span()
        w = e - s
        assert w >= 18, f"token 宽异常 {line!r}"
        # "0.000000000000E+00" 本身 18 字符——右对齐补空格，宽度严格不变
        zero = (" " * (w - 18)) + "0.000000000000E+00"
        out[s:e] = list(zero)
    assert len(out) == n0, "记录首行宽度被改动"
    return "".join(out) + "\n"


def main():
    n_rec = 0
    off_grid = []
    cur = None
    pos = -1
    with open(SRC, "r", encoding="ascii") as fi, \
         open(DST, "w", encoding="ascii", newline="") as fo:
        in_header = True
        for line in fi:
            if in_header:
                fo.write(line)
                if "END OF HEADER" in line:
                    in_header = False
                continue
            if REC_START.match(line):
                n_rec += 1
                pos = 0
                cur = line.strip()[:3]
                fo.write(zero_af(line))
            else:
                pos += 1
                if pos == 3 and cur and cur.startswith("G"):
                    tok = line[3:23].strip()
                    try:
                        toe = float(tok.replace("D", "E"))
                        if abs(toe / 16.0 - round(toe / 16.0)) > 1e-9:
                            off_grid.append((cur, tok))
                    except ValueError:
                        off_grid.append((cur, "unparsed:" + tok))
                fo.write(line)
    print(f"records zeroed: {n_rec}")
    if off_grid:
        print(f"WARNING toe off 16s grid: {off_grid[:6]} ({len(off_grid)} total)")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
