"""Per-SV diagnostic for the built-in multi-GNSS L1 receiver fix.

Replicates backend.analysis.l1_fix.fix_from_iq_l1_multi step by step on a
stored run, printing per-SV predicted phase, measured phase, err_chips,
svb (plan-side vs receiver-side band argument) and the corrected pseudorange
residual against the independently computed geometric range.
"""
import json, sys, math, datetime as dt
import numpy as np

from backend import config, geometry
from backend.ephem import ephemeris
from backend.synth import engine, signals
from backend.analysis.l1_acquire import acquire_l1
from backend.analysis.l1_fix import default_atmo_fn

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T014431475490"
ONLY = sys.argv[2] if len(sys.argv) > 2 else ""   # e.g. "G4,G8,C1,E112"

import pathlib
od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]
prov = meta.get("provenance", {})
start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(sorted({s["sys"] for s in prov.get("svs", [])}))
print(f"run={RUN} systems={systems} start_utc={cfg['start_utc']}")

# ---- same ephemeris chain as /api/receiver (incl. run-start at_gps pick) ----
rinex = cfg.get("rinex_path")
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
at = gps_start if prov.get("engine") == "native" else None
eph_full = ephemeris.parse_rinex_multi(rinex, systems, at_gps=at) \
    if set(systems) - {"G"} else ephemeris.parse_rinex(rinex, at_gps=at)
print(f"week={week} sow={sow!r} sow%1={sow % 1.0!r}")
eph = ephemeris.align_for_run(eph_full, week, sow, prov.get("engine"))

# _gps_tow replica
delta = start - dt.datetime(1980, 1, 6)
tow = (delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
approx_time = (tow + config.GPS_UTC_LEAP_S) % (7 * 86400)
print(f"approx_time_gps={approx_time!r}  (approx_time%1={approx_time % 1.0!r})")

approx_llh = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
atmo_fn = default_atmo_fn(rinex, approx_llh, approx_time)

# ---- IQ buffer exactly as fix_from_iq builds it ----
iq_by_band = {}
for b in meta.get("bands", []):
    bf = od / b["file"]
    if bf.exists():
        from backend import inspector
        iq_by_band[b["id"]] = (inspector.read_iq(bf, meta["sample_format"],
                                                 max_samples=int(b["fs"] * 0.020)),
                               b["fs"])
print("bands loaded:", {k: (len(v[0]), v[1]) for k, v in iq_by_band.items()})

sig_keys = {"G": "GPS_L1CA", "J": "QZSS_L1CA", "S": "SBAS_L1",
            "E": "GAL_E1", "C": "BDS_B1I", "R": "GLO_G1"}

rows = []
for sv in prov.get("svs", []):
    key = f"{sv['sys']}{sv['prn']}"
    if ONLY and key not in ONLY.split(","):
        continue
    sysc, prn = sv["sys"], sv["prn"]
    rinex_prn = prn - engine._PRN_OFFSET.get(sysc, 0)
    rec = eph.get((sysc, rinex_prn))
    if rec is None and sysc == "G":
        rec = eph.get(rinex_prn)
    if rec is None:
        print(f"{key:>6}  NO EPHEMERIS (rinex prn {rinex_prn})")
        continue
    sig = signals.SIGNALS[sig_keys[sysc]]
    state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec

    # receiver-side svb uses band "L1" (l1_fix line 116-118); plan-side uses sig.band
    svb_rx = geometry.group_delay_bias_s(sysc, "L1", rec if isinstance(rec, dict) else None)
    svb_pl = geometry.group_delay_bias_s(sysc, getattr(sig, "band", "L1"),
                                         rec if isinstance(rec, dict) else None)

    o = geometry.observables(state, approx_rx, approx_time, signal=sig,
                             sv_clock_bias_s=svb_rx)
    carrier_hz = sig.carrier_hz + (int(sv["glo_k"]) * 562_500.0 if sysc == "R" else 0.0)
    atmo_m = float(atmo_fn(math.radians(o["az_deg"]), math.radians(o["el_deg"]),
                           carrier_hz)) if atmo_fn else 0.0
    pred_pr = o["pseudorange_m"] + atmo_m
    pred_phase = (pred_pr / config.C * sig.chip_rate_hz) % sig.code_len
    # plan-side formula for comparison (engine.py:1205)
    pred_phase_plan = ((pred_pr / config.C - (sow % 1.0)) * sig.chip_rate_hz) % sig.code_len

    iq, fs = iq_by_band[sv["band"]]
    acq = acquire_l1(iq, fs, sysc, prn, centre_offset_hz=sv["if_hz"],
                     glo_k=(int(sv["glo_k"]) if sysc == "R" else None))

    err_chips = ((acq["code_phase_chips"] - pred_phase + sig.code_len / 2.0)
                 % sig.code_len) - sig.code_len / 2.0
    m_per_chip = config.C / sig.chip_rate_hz
    measured_pr = pred_pr + err_chips * m_per_chip
    pos, _vel, _tof, clk = geometry.solve_transmit_time(state, approx_rx, approx_time)
    corrected_pr = measured_pr + config.C * (clk + svb_rx) - atmo_m
    geo_direct = float(np.linalg.norm(pos - approx_rx))

    fd_plan_back = sv.get("code_doppler_hz", 0.0) * sig.carrier_hz / sig.chip_rate_hz
    tau_chip = (pred_pr / config.C * sig.chip_rate_hz) % sig.code_len
    neg_tau_chip = (-pred_pr / config.C * sig.chip_rate_hz) % sig.code_len
    rows.append(dict(key=key, db=acq["metric_db"],
                     meas_cp=acq["code_phase_chips"], pred_cp=pred_phase,
                     err=err_chips, err_m=err_chips * m_per_chip,
                     fd_meas=acq["doppler_hz"], fd_plan=fd_plan_back,
                     svb_rx=svb_rx, svb_pl=svb_pl,
                     corr_minus_geo=corrected_pr - geo_direct,
                     el=o["el_deg"], atmo=atmo_m,
                     el_plan=sv.get("el_deg"), az=o["az_deg"],
                     az_plan=sv.get("az_deg"), tau=tau_chip,
                     neg_tau=neg_tau_chip,
                     meas_minus_negtau=((acq["code_phase_chips"] - neg_tau_chip
                                         + sig.code_len / 2.0) % sig.code_len)
                     - sig.code_len / 2.0))

print(f"\n{'SV':>6} {'dB':>5} {'meas_cp':>9} {'pred_cp':>9} {'err_ch':>9} "
      f"{'fd_meas':>9} {'fd_plan':>9} {'el_rx':>6} {'el_pl':>6} {'az_rx':>7} {'az_pl':>7} "
      f"{'neg_tau':>8} {'m-negtau':>9} {'corr-geo_m':>11} {'atmo_m':>7}")
for r in rows:
    print(f"{r['key']:>6} {r['db']:5.1f} {r['meas_cp']:9.2f} {r['pred_cp']:9.2f} "
          f"{r['err']:9.2f} {r['fd_meas']:9.1f} {r['fd_plan']:9.1f} "
          f"{r['el']:6.2f} {r['el_plan'] if r['el_plan'] is not None else -99:6.2f} "
          f"{r['az']:7.2f} {r['az_plan'] if r['az_plan'] is not None else -99:7.2f} "
          f"{r['neg_tau']:8.2f} {r['meas_minus_negtau']:9.2f} "
          f"{r['corr_minus_geo']:11.1f} {r['atmo']:7.1f}")

# quick least-squares feeler on the corrected pseudoranges
if len(rows) >= 4:
    from backend.analysis.receiver import solve_position
    keys = [r["key"] for r in rows if r["db"] >= 15.0]
    if len(keys) >= 4:
        pr = {r["key"]: r["corrected_pr"] if "corrected_pr" in r else r["corr_minus_geo"]
              for r in rows}
        # rebuild pr properly
        pr, sp = {}, {}
        for sv, r in zip([s for s in prov["svs"]], []):
            pass
        # simpler: redo the solve from stored values
        prs, satp = {}, {}
        idx = 0
        for sv in prov.get("svs", []):
            key = f"{sv['sys']}{sv['prn']}"
            if ONLY and key not in ONLY.split(","):
                continue
            rr = next((x for x in rows if x["key"] == key), None)
            if rr is None or rr["db"] < 15.0:
                continue
            rinex_prn = sv["prn"] - engine._PRN_OFFSET.get(sv["sys"], 0)
            rec = eph.get((sv["sys"], rinex_prn)) or (eph.get(rinex_prn) if sv["sys"] == "G" else None)
            state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec
            pos, _, _, _ = geometry.solve_transmit_time(state, approx_rx, approx_time)
            # corrected_pr was folded as measured_pr + C(clk+svb) - atmo;
            # reconstruct from corr_minus_geo + geo_direct
            prs[key] = rr["corr_minus_geo"] + float(np.linalg.norm(pos - approx_rx))
            satp[key] = pos
        try:
            sol = solve_position(prs, satp, x0=[*approx_rx, 0.0])
            lat, lon, h = geometry.ecef_to_llh(*sol["ecef"])
            err = float(np.linalg.norm(np.array(sol["ecef"]) - approx_rx))
            print(f"\nFIX: lat={lat:.6f} lon={lon:.6f} h={h:8.1f} "
                  f"err_vs_marker={err:9.1f} m  residual_rms={sol['residual_rms_m']:.1f} m")
        except Exception as e:
            print("solve failed:", e)
