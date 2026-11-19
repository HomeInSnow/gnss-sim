# -*- coding: utf-8 -*-
"""RINEX 3.04 版 afzero2：在 afzero3 基础上把 GPS 记录 TGD 也清零。

用途（任务⑧改正①的配套）：sv_clock=true 场景下引擎真值伪距含 −C·clk
（af 已清零 → 只剩相对论项，与 FGI mulSatpos 无条件 relcorr 自洽抵消）；
TGD 在 native 引擎侧本就未注入（rec 非 dict → svb=0），但合成导航电文会
原样携带星历 T_GD，FGI 读电文后会做 TGD 改正 → 双侧共同偏差。
把源星历 TGD 清零后：电文 T_GD=0，FGI 改正量为 0，双侧一致消除。

GPS 记录 8 行，TGD 在第 7 行（记录内 pos==6）第 3 个 20 列 DFLOAT token
（同行依次 SVacc, health(显示为 d.xxExx), TGD, IODC）。清零用原位替换，
宽度严格不变。af 清零逻辑同 make_afzero3_whu.py（首行前 3 个 DFLOAT）。

输出 data/rinex/BRDC_2023271_whu_afzero2.rnx，不动 afzero 版。
"""
import re

SRC = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271.rnx"
DST = r"D:\workbuddy\GNSSSignal\gnss-sim-desktop\data\rinex\BRDC_2023271_whu_afzero2.rnx"

REC_START = re.compile(r"^\s*[GEJCRSI][0-9A-Z]{2} 20\d\d \d\d \d\d \d\d \d\d \d\d(\.\d)?[ ]*[ -]\d\.\d{12}[ED]")
DFLOAT = re.compile(r"[ -]\d\.\d{12}[ED][+-]\d{2}")

ZERO = "0.000000000000E+00"  # 18 字符


def zero_tokens(line: str, idxs) -> str:
    """把 line 中第 idxs 个 DFLOAT token 原位替换为 0（右对齐补空格，宽度不变）。"""
    toks = [m for m in DFLOAT.finditer(line)]
    for i in idxs:
        if i >= len(toks):
            raise SystemExit(f"token 索引 {i} 越界({len(toks)}): {line!r}")
    out = list(line.rstrip("\n"))
    n0 = len(out)
    for i in sorted(idxs, reverse=True):
        s, e = toks[i].span()
        w = e - s
        assert w >= 18, f"token 宽异常 {line!r}"
        out[s:e] = list((" " * (w - 18)) + ZERO)
    assert len(out) == n0, "行宽被改动"
    return "".join(out) + "\n"


def main():
    n_rec = 0
    n_tgd = 0
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
                fo.write(zero_tokens(line, [0, 1, 2]))  # af0/af1/af2
            else:
                pos += 1
                if pos == 6 and cur and cur.startswith("G"):
                    # GPS 第 7 行：SVacc, health, TGD, IODC —— 清第 3 个 token
                    before = line
                    line = zero_tokens(line, [2])
                    if before != line:
                        n_tgd += 1
                fo.write(line)
    print(f"records zeroed(af): {n_rec}; TGD zeroed: {n_tgd}")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
