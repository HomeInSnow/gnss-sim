# type: ignore
"""E 侧相干环 A/B：monkeypatch SVTracker，按系统注入覆盖参数，跑 tracked fix，
打印 error_m / 分系统 phRMS / err_avg RMS。生产代码零改动。

Usage: python tune_e_phase.py [RUN] [track_s] [overrides-json]
overrides-json 例: {"E": {"pll_kp": 0.35}, "*": {"pll_bw": 0.5}}
  支持键: pll_kp, pll_ki(直接设值,Hz 语义同 tracker), t_coh_ms, clean_frac(单块
  干净窗 |P| 门限比例), drop_frac(coh 掉窗门限), lag_l(E 跨窗 lag 块数)
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.synth import signals
from backend.ephem import ephemeris
from backend.analysis import tracker as tmod
from backend.analysis.l1_fix import default_atmo_fn, fix_from_iq_l1_multi_tracked

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
TRACK_S = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
OVR = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(meta.get("systems") or tuple(
    sorted({s["sys"] for s in meta["provenance"]["svs"]})))
rinex = cfg["rinex_path"]
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
engine = meta.get("provenance", {}).get("engine")
eph = ephemeris.parse_rinex_multi(rinex, systems, at_gps=gps_start)
eph = ephemeris.align_for_run(eph, week, sow, engine)
marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)

_Real = tmod.SVTracker


class Tuned(_Real):
    def __init__(self, *a, **kw):
        sysc = a[2] if len(a) > 2 else kw.get("sysc", "?")
        o = dict(OVR.get("*", {})); o.update(OVR.get(sysc, {}))
        if o.get("t_coh_ms"):
            kw["t_coh_ms"] = float(o["t_coh_ms"])
        super().__init__(*a, **kw)
        if o.get("pll_kp") is not None:
            self._pll_kp = float(o["pll_kp"])
        if o.get("pll_ki") is not None:
            self._pll_ki = float(o["pll_ki"])
        if o.get("clean_frac") is not None:
            self._clean_frac = float(o["clean_frac"])
        if o.get("lag_l") is not None:
            self._lag_l = int(o["lag_l"])
        if o.get("drop_frac") is not None:
            self._coh_drop = float(o["drop_frac"])


tmod.SVTracker = Tuned
try:
    afn = default_atmo_fn(rinex, marker, tow)
    # patch drop threshold consumption: _dll_update reads constants inline;
    # emulate via attribute if present else ignore
    tr = fix_from_iq_l1_multi_tracked(
        od, meta, eph, tow, approx_llh=marker, marker_llh=marker,
        atmo_fn=afn, track_s=TRACK_S, dll_bw_hz=0.5, dll_mode="coh")
finally:
    tmod.SVTracker = _Real

if "error" in tr:
    print("ERROR:", tr["error"]); sys.exit(1)
truth = np.array(geometry.llh_to_ecef(*marker))
te = float(np.linalg.norm(np.array(tr["ecef"]) - truth))
ecv = np.array([v["err_chips_avg"] for v in tr["per_sv"].values()
                if v.get("err_chips_avg") is not None])
print(f"[{json.dumps(OVR, ensure_ascii=False)}]  error_m={te:.3f} "
      f"err_avgRMS={np.sqrt(np.mean(ecv**2)):.5f}")
for sysp in sorted({k[0] for k in tr["per_sv"]}):
    sub = [v["phase_rms_cycles"] for k, v in tr["per_sv"].items()
           if k.startswith(sysp) and v.get("phase_rms_cycles") is not None]
    if sub:
        print(f"    {sysp}: phRMS mean={np.mean(sub):.5f} max={np.max(sub):.5f}")
worst = sorted((v.get("phase_rms_cycles") or 0, k)
               for k, v in tr["per_sv"].items())[-4:]
print("    worst:", [(k, round(r, 4)) for r, k in worst[::-1]])
