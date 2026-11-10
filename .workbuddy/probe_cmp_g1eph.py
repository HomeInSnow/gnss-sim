# 对照探针：G1 自解星历（probe_g1c.json）vs BRDC 生成侧星历
import datetime as dt
import json
import sys

import numpy as np

sys.path.insert(0, ".")
from backend import config, geometry
from backend.ephem import ephemeris

out = json.loads(open(".workbuddy/probe_g1c.json").read())
fields = out["fields"]

meta = json.loads((config.OUT_DIR / "20261110T084902599874" /
                   "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow0 = ephemeris.gps_week_and_sow(gps_start)

syst = {s["sys"] for s in meta["provenance"]["svs"]}
eph = ephemeris.parse_rinex_multi(cfg["rinex_path"], tuple(syst),
                                  at_gps=gps_start
                                  if meta["provenance"].get("engine") ==
                                  "native" else None)
eph = ephemeris.align_for_run(eph, week, sow0,
                              meta["provenance"].get("engine"))
ref = eph[("G", 1)]

keys = sorted(set(fields) | set(ref))
print(f"{'field':<12} {'decoded':>16} {'BRDC':>16} {'diff':>12}")
for k in keys:
    dv, rv = fields.get(k), ref.get(k)
    if k in ("prn", "sys"):
        continue
    try:
        d = float(dv) if dv is not None else None
        r = float(rv) if rv is not None else None
    except (TypeError, ValueError):
        print(f"{k:<12} {str(dv):>16} {str(rv):>16}")
        continue
    diff = (d - r) if (d is not None and r is not None) else None
    flag = "  <== " if diff is not None and abs(diff) > max(
        1e-9, 1e-6 * abs(r)) else ""
    print(f"{k:<12} {'' if d is None else format(d, '.10g'):>16} "
          f"{'' if r is None else format(r, '.10g'):>16} "
          f"{'' if diff is None else format(diff, '.3g'):>12}{flag}")

# 卫星位置/速度对比
sig = None
from backend.synth import signals
sig = signals.SIGNALS["GPS_L1CA"]
for t in (sow0, sow0 + 30.0, sow0 + 60.0):
    p_d, v_d, _ = geometry.state_fn_for(dict(fields, prn=1))(t)
    p_r, v_r, _ = geometry.state_fn_for(dict(ref, prn=1))(t)
    dp = np.linalg.norm(p_d - p_r)
    dv = np.linalg.norm(v_d - v_r)
    print(f"t={t - sow0:5.0f}s  dPos={dp:12.2f} m  dVel={dv:9.3f} m/s"
          f"  v_r_radial={np.dot(v_r, p_r / np.linalg.norm(p_r)):8.2f}"
          f" v_d_radial={np.dot(v_d, p_d / np.linalg.norm(p_d)):8.2f}")

# 真值注入 pr（meta）与两组 observables pr 对比
svs_meta = {f"G{s['prn']}": s for s in meta["provenance"]["svs"]}
m1 = svs_meta["G1"]
print("meta pr_inj_m@0:", m1.get("pseudorange_m"),
      " fd:", m1.get("carrier_doppler_hz"))
mk = geometry.llh_to_ecef(float(cfg["lat"]), float(cfg["lon"]),
                          float(cfg["alt"]))
for t in (sow0, sow0 + 30.0, sow0 + 60.0):
    for tag, f in (("dec", fields), ("ref", dict(ref, prn=1, sys="G"))):
        try:
            st = geometry.state_fn_for(dict(f, prn=1, sys="G"))
            o = geometry.observables(st, mk, t, signal=sig, sv_clock=False)
            print(f"t={t - sow0:5.0f}s {tag}: pr={o['pseudorange_m']:14.3f} "
                  f"fd={o['carrier_doppler_hz']:9.3f}")
        except Exception as exc:                       # noqa: BLE001
            print(f"t={t - sow0:5.0f}s {tag}: ERR {exc}")
