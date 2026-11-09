"""Per-record propagation check: for each broadcast record of the given GPS
PRNs in the BRDC file, propagate at the scenario transmit time and report
elevation at the marker. Shows which record align_epochs/the pipeline picks
on each side vs what the plan used.
"""
import sys, json, datetime as dt
import numpy as np
from backend import config, geometry
from backend.ephem import ephemeris

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T014431475490"
PRNS = [int(p) for p in (sys.argv[2] if len(sys.argv) > 2 else "4,8").split(",")]

import pathlib
meta = json.loads((pathlib.Path("out") / RUN / "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
rinex = cfg["rinex_path"]
rx = np.array(geometry.llh_to_ecef(cfg["lat"], cfg["lon"], cfg["alt"]))
delta = start - dt.datetime(1980, 1, 6)
t_gps = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
         + config.GPS_UTC_LEAP_S) % (7 * 86400)
print(f"t_gps={t_gps} (sow), rx=({cfg['lat']},{cfg['lon']},{cfg['alt']})")

# parse ALL records via georinex-backed helper if available; else parse_rinex
from backend.ephem import ephemeris as E
import inspect as _ins
funcs = [n for n in dir(E) if "parse" in n or "records" in n]
print("parse helpers:", funcs)

gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = E.gps_week_and_sow(gps_start)

# what the receiver-side chain selects:
eph_multi = E.parse_rinex_multi(rinex, ("G", "C", "E"))
aligned = E.align_epochs(eph_multi, week, sow,
                         kepler_grid_s=E.toe_grid_for("native"))
for prn in PRNS:
    rec = aligned.get(("G", prn), aligned.get(prn))
    key_used = ("G", prn) if ("G", prn) in aligned else (prn if prn in aligned else None)
    if rec is None:
        print(f"G{prn}: MISSING in aligned"); continue
    pos, vel, clk = geometry.sat_state(rec, t_gps)
    los = pos - rx; d = np.linalg.norm(los)
    lat = geometry.ecef_to_llh(*rx)
    e, n, u = geometry._enu(rx)
    el = float(np.degrees(np.arcsin(np.clip(los / d @ u, -1, 1))))
    az = float(np.degrees(np.arctan2(los @ e, los @ n))) % 360
    print(f"G{prn} receiver-side aligned record key={key_used}: "
          f"toc={rec.get('toc')} toe={rec.get('toe')} week={rec.get('gps_week')} "
          f"-> el={el:6.2f} az={az:7.2f}  clk={clk:.3e}")

# every raw record of these PRNs around the window
print("\nAll raw records (per-record propagation):")
for prn in PRNS:
    try:
        recs = E.parse_rinex_records(rinex, "G", prn) if hasattr(E, "parse_rinex_records") else None
    except Exception as ex:
        recs = None
        print("records helper failed:", ex)
    if recs is None:
        print("(no per-record parser; skipping raw sweep)")
        break
    for i, rec in enumerate(recs):
        toc = rec.get("toc", 0.0)
        # only near-window records (UTC 2026-10-01)
        pos, vel, clk = geometry.sat_state(rec, t_gps)
        los = pos - rx; d = np.linalg.norm(los)
        e, n, u = geometry._enu(rx)
        el = float(np.degrees(np.arcsin(np.clip(los / d @ u, -1, 1))))
        print(f"  G{prn} rec{i}: toc={toc} toe={rec.get('toe')} "
              f"-> el={el:6.2f} {'<== plan-ish' if 85 < el < 87 and prn==8 else ''}")
