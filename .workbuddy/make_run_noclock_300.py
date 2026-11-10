"""300 s 真实接收机评估场景（任务 #34）。

同 make_run_noclock.py 演示口径（郑州 34.7466/113.6254/110 m、2026-10-10T04:00:00Z、
G+E 25 星、5 Msps int8、BRDC_2026283、atmosphere off + sv_clock=False），
唯一差异 duration_s=300 —— 供"捕获→连续跟踪→逐秒观测/比特流→电文→逐秒定位"
真实接收机流程与逐秒评估使用。gpssim.bin ≈ 3 GB。
"""
import datetime as dt

from backend import scenario
from backend.synth import engine as signal_engine

req = scenario.ScenarioRequest(
    rinex_path=r"D:\workbuddy\GNSSSignal\gnss-sim\data\rinex\BRDC_2026283.rnx",
    lat=34.7466, lon=113.6254, alt=110,
    start=dt.datetime(2026, 10, 10, 4, 0, 0),
    duration_s=300,
    sample_rate=5e6, sample_format="int8",
    systems=("G", "E"), engine="native",
    atmosphere={"ionosphere": "off", "troposphere": "off"},
    sv_clock=False,
)


def _prog(f):
    if abs(f - _prog.last) >= 0.05 or f >= 1.0:
        _prog.last = f
        print(f"progress {f:.2f}", flush=True)
_prog.last = -1.0


outdir = signal_engine.run(req, progress_cb=_prog)
print("OUTDIR", outdir.name, flush=True)
