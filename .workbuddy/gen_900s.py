# -*- coding: utf-8 -*-
"""900 s 仿真生成：完全复刻 out/20261113T033315803665 场景设置（Tampere 12 星
GPS L1 C/A, 25 Msps int16, atmosphere off, sv_clock on, afzero2 BRDC, AWGN -18.33 dB），
仅 duration_s 60 -> 900。进程内直调 signal_engine.run（与 POST /api/generate 同链路）。
"""
import datetime as dt
import sys
import time

sys.path.insert(0, ".")

from backend import scenario                       # noqa: E402
from backend.synth import engine as signal_engine  # noqa: E402

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 900   # 冒烟用小值，正式 900

req = scenario.ScenarioRequest(
    rinex_path="D:/workbuddy/GNSSSignal/gnss-sim/data/rinex/BRDC_2023271_whu_afzero2.rnx",
    lat=60.182537, lon=24.82826, alt=47.248,
    start=dt.datetime(2023, 9, 28, 23, 20, 0),      # naive UTC, 与原 run 一致
    duration_s=DUR,
    sample_rate=25_000_000.0,
    sample_format="int16",
    atmosphere={"ionosphere": "off", "troposphere": "off"},
    sv_clock=True,
    engine="native",
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
