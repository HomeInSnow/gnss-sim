"""Step-by-step diagnostic of the GPS-only legacy fix path
(receiver.py lines ~732-823) on a stored run."""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry, inspector
from backend.ephem import ephemeris
from backend.analysis.receiver import solve_position

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T014835842141"
od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
rinex = cfg["rinex_path"]
eph = ephemeris.parse_rinex(rinex)
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
eph = ephemeris.align_for_run(eph, week, sow, meta["provenance"].get("engine"))
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)
approx_rx = np.array(geometry.llh_to_ecef(cfg["lat"], cfg["lon"], cfg["alt"]))
fs = meta["sample_rate"]
iq = inspector.read_iq(od / "gpssim.bin", meta["sample_format"],
                       max_samples=int(fs * 0.020))

acq = {}
for prn in sorted(eph):
    r = inspector.acquire(iq, fs, prn)
    if r["metric_db"] > 9:
        acq[prn] = r
print(f"acquired {len(acq)} PRNs: {sorted(acq)}  fs={fs}")

sat_pos, predicted, clk_map = {}, {}, {}
for prn in acq:
    pos, vel, tof, clk = geometry.solve_transmit_time(eph[prn], approx_rx, tow)
    sat_pos[prn] = pos
    predicted[prn] = np.linalg.norm(pos - approx_rx) - config.C * clk
    clk_map[prn] = clk

ref = max(acq, key=lambda p: predicted[p] * -1)
code_m = {p: (acq[p]["code_phase_chips"] / config.CA_CHIP_HZ) * config.C
          for p in acq}
print(f"{'PRN':>4} {'dB':>5} {'dopp':>8} {'cp':>8} {'code_m':>9} "
      f"{'predicted':>13} {'frac_m':>9} {'n_ms':>4} {'pr':>14}")
pr = {}
for prn in acq:
    n_ms = round((predicted[prn] - predicted[ref]
                  - (code_m[prn] - code_m[ref])) / (config.C * 1e-3))
    pr[prn] = predicted[ref] + (code_m[prn] - code_m[ref]) + n_ms * config.C * 1e-3 + config.C*clk_map[prn]
    frac = predicted[prn] % (config.C * 1e-3)
    print(f"{prn:>4} {acq[prn]['metric_db']:5.1f} {acq[prn]['doppler_hz']:8.1f} "
          f"{acq[prn]['code_phase_chips']:8.2f} {code_m[prn]:9.1f} "
          f"{predicted[prn]:13.1f} {frac:9.1f} {n_ms:>4} {pr[prn]:14.1f}")

sol = solve_position(pr, sat_pos, x0=[*approx_rx, 0.0])
lat, lon, h = geometry.ecef_to_llh(*sol["ecef"])
err = float(np.linalg.norm(np.array(sol["ecef"]) - approx_rx))
print(f"FIX lat={lat:.6f} lon={lon:.6f} h={h:9.1f} err={err:9.1f} m "
      f"resid={sol['residual_rms_m']:.1f} m")
# per-sat residual
rxv = np.array(sol["ecef"])
for prn in sorted(pr):
    r = pr[prn] - (np.linalg.norm(sat_pos[prn] - rxv) + sol["clock_bias_s"] * config.C)
    print(f"  resid G{prn:<3} {r:12.1f} m")
