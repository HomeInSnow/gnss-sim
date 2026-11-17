# -*- coding: utf-8 -*-
"""双频 IQ 合并为 PocketSDR CH-planar cyc-interleaved 单文件 + .tag。

输入: gnss-sim run 目录的 gpssim.bin (L1/E1) 与 gpssim_l5.bin (L5/E5a)，
两者同 fs（PocketSDR 单 rcv->fs 硬约束）、同 int16 量化、同 run 起点。
输出: <outdir>/pocket_e1e5a.bin —— 每 1 ms 周期先写 CH0(E1) 的 fs*0.001
样本，再写 CH1(E5a)，循环；配套 pocket_e1e5a.bin.tag 供 sdr_tag_read()
识别（tag 存在时命令行 fmt/fs/fo 被忽略）。

用法: python .workbuddy/merge_tag.py <run_dir> [fs_mhz]
"""
import datetime as dt
import json
import pathlib
import shutil
import sys

CHUNK_MS = 1  # PocketSDR 以 1 ms 周期为交错单位（rcv_open_file 整周期 seek），
              # 必须每 ms 先 CH0(E1) 后 CH1(E5a)，不可跨 ms 攒块

def main(run_dir: str, fs_mhz: float = 25.0):
    run = pathlib.Path(run_dir)
    if not run.is_absolute() and run.parts[0] != "out":
        run = pathlib.Path("out") / run
    meta = json.load(open(run / "meta.json", encoding="utf-8"))
    bands = {b["id"]: b for b in meta["bands"]}
    fs = float(bands["L1"]["fs"])
    assert abs(fs - float(bands["L5"]["fs"])) < 1.0, "双带 fs 必须一致"
    assert abs(fs - fs_mhz * 1e6) < 1.0, "fs 与命令行参数不符"

    f1 = run / bands["L1"]["file"]
    f5 = run / bands["L5"]["file"]
    n_bytes = f1.stat().st_size
    assert n_bytes == f5.stat().st_size, "两带文件长度不一致"
    n_samp = n_bytes // 4                      # int16 I+Q = 4 B/样本
    n_ms = n_samp // int(fs * 0.001)
    assert n_samp % int(fs * 0.001) == 0, "样本数非整毫秒"

    out = run / "pocket_e1e5a.bin"
    npp = int(fs * 0.001) * CHUNK_MS           # 每块样本数
    with open(f1, "rb") as a, open(f5, "rb") as b, open(out, "wb") as w:
        for _ in range(n_ms // CHUNK_MS):
            w.write(a.read(npp * 4))
            w.write(b.read(npp * 4))
        rem = n_ms % CHUNK_MS
        if rem:
            w.write(a.read(rem * npp // CHUNK_MS * 4))
            w.write(b.read(rem * npp // CHUNK_MS * 4))
    total = out.stat().st_size
    assert total == 2 * n_bytes, f"合并输出尺寸异常 {total} != {2*n_bytes}"

    # run 起点（meta.config.start_utc 为 naive UTC）→ tag TIME 原样写入
    # （rcv_open_file 对 tag 的 TIME 传 NULL，不解析；仅作记录）
    assert meta.get("sample_format") == "int16", "本脚本仅适用 int16(CS16)"
    start = meta.get("config", {}).get("start_utc") or "unknown"
    tag = out.with_suffix(out.suffix + ".tag")
    tag.write_text(
        f"PROG = gnss-sim\n"
        f"TIME = {str(start).replace('T', ' ')}\n"
        f"FMT = CS16\n"
        f"NCH = 2\n"
        f"F_S = {fs_mhz:.6f}\n"
        f"F_LO = 1575.420000,1176.450000\n"
        f"IQ = 2,2\n"
        f"BITS = 16,16\n",
        encoding="ascii",
    )
    print(f"merged: {out} ({total:,} B, {n_ms} ms)")
    print(f"tag   : {tag}")
    return str(out)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 25.0)
