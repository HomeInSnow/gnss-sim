"""生成"无大气/无卫星钟差"信号仿真精度评估场景（任务 #32）。

复刻演示 run 20261106T084558776704 的全部参数（郑州 34.7466/113.6254/110 m、
2026-10-10T04:00:00Z 起 60 s、G+E、5 Msps int8、BRDC_2026283），但
atmosphere 两模型 off + sv_clock=False：IQ 只含纯几何伪距（+TGD/BGD 群延迟），
电离层/对流层/卫星钟（含相对论项）不注入；电文仍按 BRDC 忠实广播
（af0/af1/af2、Klobuchar α/β 照常打包，物理效应与消息内容解耦）。
"""
import datetime as dt
import sys

from backend import scenario
from backend.synth import engine as signal_engine

req = scenario.ScenarioRequest(
    rinex_path=r"D:\workbuddy\GNSSSignal\gnss-sim\data\rinex\BRDC_2026283.rnx",
    lat=34.7466, lon=113.6254, alt=110,
    start=dt.datetime(2026, 10, 10, 4, 0, 0),
    duration_s=60,
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
