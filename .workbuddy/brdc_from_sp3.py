"""Build data/rinex/BRDC_2023271.rnx from GFZ final SP3 + SINEX CLK.

Purpose: reproduce the paper's Skydel scenario (Helsinki, 2023-09-28
23:20:00 UTC) without CDDIS/BKG access. Thin DRIVER over the project's
production precise->broadcast machinery (backend/ephem/ephemeris_fit.
fit_satellite -- Levenberg-Marquardt in normalised coordinates against the
exact geometry._orbit forward model, plus the independent dense post-fit
validation). Satellite clocks come from the 30 s SINEX AS rows (fallback:
the coarse 15 min SP3 clock column).

Time bookkeeping: SP3/SINEX stamps are read as GPS time (GPS-UTC = 18 s is
config.GPS_UTC_LEAP_S). The fitted record carries the REAL toe
(2023-09-28 23:00:18 GPS = 23:00:00 UTC, week 2281), so align_for_run's
keep_real_within_s=14400 branch keeps it untouched on BOTH the generator
and the receiver side -- the closed loop is self-consistent by construction
and the synthesised sky tracks the real one of that day.

Usage:  .venv/Scripts/python.exe .workbuddy/brdc_from_sp3.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import config, geometry                      # noqa: E402
from backend.gpstime import GPSTime                        # noqa: E402
from backend.ephem import ephemeris, ephemeris_fit, precise  # noqa: E402

OUT = config.DATA_DIR / "rinex" / "BRDC_2023271.rnx"
REPORT = ROOT / ".workbuddy" / "brdc_fit_report_2023271.json"

WEEK = 2281
TOE_UTC = dt.datetime(2023, 9, 28, 23, 0, 0)
GPS_START_UTC = dt.datetime(2023, 9, 28, 23, 20, 0)        # run start

SP3_FILES = [ROOT / "GFZ0OPSFIN_20232710000_01D_15M_ORB.SP3.gz",
             ROOT / "GFZ0OPSFIN_20232720000_01D_15M_ORB.SP3.gz"]
CLK_FILES = [ROOT / "GFZ0OPSFIN_20232710000_01D_30S_CLK.CLK.gz",
             ROOT / "GFZ0OPSFIN_20232720000_01D_30S_CLK.CLK.gz"]


def gz_text(p: pathlib.Path) -> str:
    return gzip.open(p, "rt", encoding="latin-1", errors="replace").read()


def read_sinex_clk(paths):
    """prn(int) -> (sow[n], clk[n]) sorted. 'AS G01 2023 9 28 0 0 0.0 1
    0.164576392211E-03' (valid flag column 1)."""
    data: dict[int, list] = {}
    for p in paths:
        for ln in gzip.open(p, "rt", encoding="latin-1", errors="replace"):
            if ln[:3] != "AS " or ln[3] != "G":
                continue
            parts = ln.split()
            if len(parts) < 11 or parts[9] != "1":
                continue
            try:
                when = dt.datetime(*(int(parts[i]) for i in range(2, 8)))
                c = float(parts[10])
            except ValueError:
                continue
            gt = GPSTime.from_gps_datetime(when)
            if gt.week != WEEK:
                continue
            data.setdefault(int(parts[1][1:]), []).append((gt.sow, c))
    out = {}
    for prn, rows in data.items():
        rows.sort()
        sow = np.array([r[0] for r in rows])
        clk = np.array([r[1] for r in rows])
        keep = np.concatenate(([True], np.diff(sow) > 0))    # dedupe
        out[prn] = (sow[keep], clk[keep])
    return out


def main():
    prods = [precise.parse_sp3(gz_text(p), source=p.name) for p in SP3_FILES]
    merged = precise.merge_sp3(prods)
    prov = precise.PreciseEphemerisProvider()
    prov.set_product(merged)
    clocks = read_sinex_clk(CLK_FILES)

    gps_start = GPS_START_UTC + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
    week, sow = ephemeris.gps_week_and_sow(gps_start)
    assert week == WEEK, f"run week {week} != expected {WEEK}"
    toe = GPSTime.from_datetime(TOE_UTC)
    assert toe.week == WEEK
    print(f"SP3: {merged.source}")
    print(f"toe  sow={toe.sow:.0f} ({TOE_UTC} UTC +18s)   run sow={sow:.0f}")

    fits, report = {}, []
    for sysc, prn in merged.satellites():
        if sysc != "G":
            continue
        base = prov.state_fn(("G", prn), week=WEEK, allow_boundary=True)
        tc, cc = clocks.get(prn, (None, None))

        def state(s, _b=base, _t=tc, _c=cc):
            pos, vel, clk = _b(float(s))
            if _t is not None and _t[0] - 300.0 <= float(s) <= _t[-1] + 300.0:
                clk = float(np.interp(float(s), _t, _c))
            return pos, vel, clk

        try:
            eph = ephemeris_fit.fit_satellite(
                state, toe, prn=prn, source="GFZ FINAL w2281 271+272",
                sys="G", strict=True)
        except (ephemeris_fit.EphemerisFitError,
                precise.PreciseProductError) as exc:
            print(f"G{prn:02d}: SKIP {type(exc).__name__} {str(exc)[:120]}")
            continue
        fits[prn] = eph
        f = eph["_fit"]
        report.append({"prn": prn,
                       "pos_rms_m": f["rms_pos_resid_m"],
                       "pos_max_m": f["max_pos_resid_m"],
                       "clk_max_s": f["max_clock_resid_s"],
                       "af0": eph["af0"], "sqrtA": eph["sqrtA"]})
        print(f"G{prn:02d}: dense rms={f['rms_pos_resid_m']:7.3f} "
              f"max={f['max_pos_resid_m']:7.3f} m   "
              f"clk_rms(s)=f{f['max_clock_resid_s']:.2e}  "
              f"af0={eph['af0']:+.4e}  sqA={eph['sqrtA']:.4f}")
    if not fits:
        raise SystemExit("no satellite fitted -- aborting, nav file NOT "
                         "written")

    # Body from the project writer; header replaced with a column-exact
    # RINEX-2 one (georinex checks s[60:80] once the line reaches 80 cols,
    # and to_rinex2_nav's own header -- built solely for gps-sdr-sim's atof
    # parser -- sits one column short). LF newlines forced: CRLF's stray \r
    # pushes the header to 80 cols and trips georinex's label check.
    body = "\n".join(ephemeris.to_rinex2_nav(fits).splitlines()[2:])
    hdr = ("     2.00           N" + " " * 39
           + "RINEX VERSION / TYPE\n"
           + " " * 60 + "END OF HEADER       \n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(hdr + body + "\n", newline="\n")
    REPORT.write_text(json.dumps({"toe_utc": str(TOE_UTC), "week": WEEK,
                                  "sats": report}, indent=1))
    worst = max(r["pos_max_m"] for r in report)
    print(f"\nwrote {OUT}  ({len(fits)} records, worst dense max {worst:.3f} m)")

    # ---- round-trip: what generator+receiver will actually use -----------
    eph = ephemeris.parse_rinex_multi(OUT, ("G",), at_gps=gps_start)
    eph = ephemeris.align_for_run(eph, week, sow, "native")
    rx = geometry.llh_to_ecef(60.182537, 24.828260, 47.248)
    worst_pos = worst_param = 0.0
    for prn in fits:
        rec = eph.get(prn) or eph.get(("G", prn))
        assert rec is not None, f"G{prn:02d} lost in round-trip"
        worst_param = max(worst_param,
                          abs(rec["sqrtA"] - fits[prn]["sqrtA"]),
                          abs(rec["af0"] - fits[prn]["af0"]))
        p, _, _ = geometry.sat_state(rec, sow)
        p0, _, _ = state_at(prv=prov, prn=prn, s=sow)
        worst_pos = max(worst_pos,
                        float(np.linalg.norm(np.asarray(p) - np.asarray(p0))))
    print(f"round-trip: {len(eph)} PRNs, parsed->sat_state vs SP3 at run "
          f"sow: worst {worst_pos:.3f} m  (field diff worst {worst_param:.2e})")


def state_at(prv, prn, s):
    st = prv.get_state(("G", prn), GPSTime(WEEK, s), allow_boundary=True)
    return (list(st.position_ecef_m), list(st.velocity_ecef_mps),
            st.clock_bias_s)


if __name__ == "__main__":
    main()
