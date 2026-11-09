"""End-to-end regression: run the real /api/receiver path (backend.app.run_receiver)
on stored out/ runs and report the fix error vs the marker.

Usage: python regress_rx.py <RUN>
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.ephem import ephemeris
from backend.analysis import receiver

RUN = sys.argv[1]
od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]

# replicate backend.app.run_receiver verbatim
start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(meta.get("systems")
                or cfg.get("systems")
                or tuple(sorted({s["sys"] for s in meta["provenance"]["svs"]})))
rinex = cfg["rinex_path"]
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
engine = meta.get("provenance", {}).get("engine")
# THE paths under test — run-start record selection (at_gps for native; was a
# file-midday pick) + align_for_run (was align_epochs without keep_real)
at = gps_start if engine == "native" else None
if set(systems) - {"G"}:
    eph = ephemeris.parse_rinex_multi(rinex, systems, at_gps=at)
else:
    eph = ephemeris.parse_rinex(rinex, at_gps=at)
eph = ephemeris.align_for_run(eph, week, sow, engine)
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)

marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
res = receiver.fix_from_iq(
    od / "gpssim.bin", meta["sample_format"], meta["sample_rate"],
    eph, tow, marker_llh=marker, systems=systems)

if "error" in res:
    print(f"{RUN}: ERROR -> {res['error']}  prns={res.get('prns_used')}")
    if "skipped" in res:
        print("  skipped:", json.dumps(res["skipped"]))
    sys.exit(1)

truth = np.array(geometry.llh_to_ecef(*marker))
err = float(np.linalg.norm(np.array(res["ecef"]) - truth))
llh = res["llh"]
print(f"{RUN}")
print(f"  systems      = {systems}")
print(f"  prns_used    = {res['prns_used']}")
print(f"  fix llh      = {llh[0]:.6f}, {llh[1]:.6f}, {llh[2]:.1f} m")
print(f"  marker llh   = {marker[0]:.6f}, {marker[1]:.6f}, {marker[2]:.1f} m")
print(f"  error_m      = {err:.2f} m")
print(f"  pdop         = {res.get('pdop'):.2f}   residual_rms = {res['residual_rms_m']:.2f} m")
print(f"  clock_bias_s = {res['clock_bias_s']:.3e}")
verdict = "PASS" if err < 50.0 else "FAIL"
print(f"  VERDICT: {verdict} (threshold 50 m)")
