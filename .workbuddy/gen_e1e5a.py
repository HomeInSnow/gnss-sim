# -*- coding: utf-8 -*-
"""Galileo E1 + E5a 双频仿真生成（PocketSDR 双频回放落地路线 ②）。

场景与 900s/60s GPS 基准同构：Tampere, 2023-09-28T23:20:00Z, afzero2 BRDC,
atmosphere off, sv_clock on, native 引擎, AWGN -18.33 dB (seed 20261117)。
差异：systems=("E",)，bands=["L1","L5"] 双带，两带同 fs=25 MHz（PocketSDR 单
rcv->fs 硬约束），int16。

用法: python .workbuddy/gen_e1e5a.py [DUR]   # 冒烟 5，正式 60
"""
import datetime as dt
import sys
import time

sys.path.insert(0, ".")

from backend import scenario                       # noqa: E402
from backend.synth import engine as signal_engine  # noqa: E402

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 60

req = scenario.ScenarioRequest(
    rinex_path="D:/workbuddy/GNSSSignal/gnss-sim/data/rinex/BRDC_2023271_whu_afzero2.rnx",
    lat=60.182537, lon=24.82826, alt=47.248,
    start=dt.datetime(2023, 9, 28, 23, 20, 0),      # naive UTC, 与基准 run 一致
    duration_s=DUR,
    sample_rate=25_000_000.0,
    l5_sample_rate=25_000_000.0,                    # 双带同 fs（合并交错文件前提）
    sample_format="int16",
    systems=("E",),
    bands=["L1", "L5"],
    atmosphere={"ionosphere": "off", "troposphere": "off"},
    sv_clock=True,
    engine="native",
    nav_message=True,
    impairments={"enabled_flag": True, "snr_db": -18.33, "seed": 20261117},
)

est = scenario.estimate_bytes(req)
print(f"estimate_bytes = {est:,} = {est/2**30:.2f} GiB", flush=True)

last = [0.0]


def cb(f):
    if f - last[0] >= 0.05:
        last[0] = f
        print(f"{time.strftime('%H:%M:%S')} progress {f*100:5.1f}%", flush=True)


t0 = time.time()
outdir = signal_engine.run(req, progress_cb=cb)
print(f"DONE outdir={outdir} elapsed={time.time()-t0:.0f}s", flush=True)
