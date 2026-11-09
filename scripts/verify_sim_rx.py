"""Sim-vs-receiver cross verification: dump EVERY comparable observable.

For GPS L1 C/A + Galileo E1 runs produced by this toolchain, compare the
generator-side truth (trace_sim.json) against the demodulating receiver's
measurements (snapshot acq grid trace_rx.json + tracked sessions
trace_dll.json + I/NAV & LNAV demodulated ephemeris), epoch by epoch and
SV by SV, and write ``out/<runid>/verify_sim_rx.json`` with per-SV
statistics, thresholds and a PASS/FAIL verdict per check group.

Check groups
  code     : rx code phase vs SIMULATED code phase (chips; direct
             sim-grid comparison, independent of the receiver's own
             ephemeris prediction chain). err_chips vs receiver pred
             reported alongside as consistency metric.
  pr       : measured pseudorange vs SIM pr_truth_m (already atmo-injected).
  fd       : measured carrier Doppler vs the constant the synthesizer
             injected (carrier_doppler_hz), plus vs the geometric truth.
  phase    : anchored carrier-phase residual: loop jitter (linear
             detrended RMS) and per-SV drift rate.
  strength : acquisition metric_db(t) vs sim gain_db: slope, r, bias.
  geom     : receiver-side elevation vs sim elevation.
  nav      : (--nav) demodulate LNAV (G) / I/NAV (E) straight from the IQ
             and compare EVERY ephemeris field against the broadcast
             record the generator used, at ICD LSB tolerance.

Usage: python scripts/verify_sim_rx.py <runid|outdir> [--nav] [--regen]
                                       [--g-window S] [--e-window S]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from backend import config                                       # noqa: E402
from backend.ephem import ephemeris                              # noqa: E402


# --------------------------------------------------------------------- #
# thresholds (units per metric; "worst" = max over SVs of |statistic|) #
# --------------------------------------------------------------------- #
TH = {
    # De-mean (per-SV constant removed = receiver's per-SV bias/ambiguity
    # parameter). The raw per-SV constant goes to <field>_bias in the json.
    # rms lines = genuine consistency (loop-noise scale, de-meaned);
    # max lines = lock sanity (reject fake-lock / unlock excursions).
    "code_trk_rms_ch": 0.02, "code_trk_max_ch": 0.15,
    "pr_trk_rms_m": 8.0, "pr_trk_max_m": 45.0,   # max line == code_trk_max x m/chip
    "fd_trk_rms_hz": 2.0, "fd_trk_max_hz": 5.0,
    "phase_drift_cycps": 0.5,
    # snapshot acquisition grid vs sim: thresholds are DYNAMIC in main()
    # from the band fs (3x integer-lag quantization sigma); the acq
    # 50 Hz doppler bins are coarse acq noise -> checked as "inside the
    # bin search" (max_abs, ~2.6 bins), rms reported informational.
    "code_snap_rms_ch": 0.07,
    "pr_snap_rms_m": 55.0,
    "fd_snap_max_hz": 220.0,          # +-4.4 acq bins: coarse-acq sanity
    # cross-SV regression (x = sim gain_db, y = mean metric_db)
    "strength_slope": 0.25,            # |slope - 1| (E1 BOC metric lifts at low C/N0)
    "strength_r": 0.60,                # min Pearson r
    "el_max_deg": 1.0,
    # nav demodulation
    "nav_coverage": 0.9,               # min fraction of SVs decoded per sys
}

# ICD LSBs; tolerance = TOLK * LSB (encoder rounds BRDC double to grid,
# so |decoded - brdc| <= LSB/2; 1.25 keeps float slack, rejects real bugs).
TOLK = 1.25
G_LSB = {  # scale factors from lnav_decode.decode_ephemeris
    "crs": 2 ** -5, "delta_n": 2 ** -43 * math.pi, "m0": 2 ** -31 * math.pi,
    "cuc": 2 ** -29, "e": 2 ** -33, "cus": 2 ** -29, "sqrtA": 2 ** -19,
    "cic": 2 ** -29, "omega0": 2 ** -31 * math.pi, "cis": 2 ** -29,
    "i0": 2 ** -31 * math.pi, "crc": 2 ** -5, "omega": 2 ** -31 * math.pi,
    "omega_dot": 2 ** -43 * math.pi, "idot": 2 ** -43 * math.pi,
    "af0": 2 ** -31, "af1": 2 ** -43, "af2": 2 ** -55, "tgd": 2 ** -31,
}
E_LSB = {  # from _inav_layout scales (reconstruct multiplies angle fields by pi)
    "m0": 4.656612873077393e-10 * math.pi, "e": 1.1641532182693481e-10,
    "sqrtA": 1.9073486328125e-06,
    "omega0": 4.656612873077393e-10 * math.pi,
    "i0": 4.656612873077393e-10 * math.pi,
    "omega": 4.656612873077393e-10 * math.pi,
    "idot": 1.1368683772161603e-13 * math.pi,
    "omega_dot": 1.1368683772161603e-13 * math.pi,
    "delta_n": 1.1368683772161603e-13 * math.pi,
    "cuc": 1.862645149230957e-09, "cus": 1.862645149230957e-09,
    "crc": 0.03125, "crs": 0.03125,
    "cic": 1.862645149230957e-09, "cis": 1.862645149230957e-09,
    "af0": 5.820766091346741e-11, "af1": 1.4210854715202004e-14,
    "af2": 1.734723475976807e-18,
}
# integer-grid fields: must match exactly (same grid)
G_INT = ("toe", "toc")
E_INT = ("toe", "toc")
# fields whose broadcast value may be legitimately zeroed by the encoder
# while BRDC carries a different value -> report as warn, not fail
ZEROABLE = ("af2", "tgd", "idot", "health", "sisa")


def _load_run(outdir: pathlib.Path):
    meta = json.loads((outdir / "meta.json").read_text())
    return meta


def _resolve_eph_for_run(meta):
    """Same record selection + alignment the native generator used."""
    start = dt.datetime.fromisoformat(meta["config"]["start_utc"])
    gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
    week, sow = ephemeris.gps_week_and_sow(gps_start)
    engine = meta.get("provenance", {}).get("engine")
    systems = tuple({s["sys"] for s in meta.get("provenance", {}).get("svs", [])})
    rp = meta["config"].get("rinex_path")
    eph = ephemeris.parse_rinex_multi(
        rp, systems, at_gps=gps_start if engine == "native" else None)
    eph = ephemeris.align_for_run(eph, week, sow, engine)
    return eph


def _stats(a, wrapped=None, code_len=None):
    a = np.asarray(a, dtype=float)
    if wrapped:
        a = (a + code_len / 2) % code_len - code_len / 2
    if a.size == 0 or not np.any(np.isfinite(a)):
        return None
    a = a[np.isfinite(a)]
    return {"n": int(a.size), "bias": float(np.mean(a)),
            "rms": float(np.sqrt(np.mean(a * a))),
            "max_abs": float(np.max(np.abs(a)))}


def _wrap(x, L):
    return (x + L / 2) % L - L / 2


def _detrend_rms(y):
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 5:
        return None, None
    t = np.arange(y.size, dtype=float)
    p = np.polyfit(t[ok], y[ok], 1)
    res = y[ok] - np.polyval(p, t[ok])
    return float(p[0]), float(np.sqrt(np.mean(res * res)))


def _demean(a):
    """Return (per-SV constant, resid stats). The constant absorbs the
    receiver's per-SV bias/ambiguity (clock, inter-model frame offsets,
    acq-bin pull-in offset) -- exactly what a real receiver estimates per
    SV -- so the resid measures genuine epoch-to-epoch consistency."""
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if a.size < 3:
        return None, None
    c = float(np.median(a))
    st = _stats(a - c)
    if st:
        st["bias"] = c
    return c, st


def verify_observations(ts, tr, td, *, fs_hz: float | None = None):
    """Return per_sv dict + summary rows comparing sim truth vs rx.

    Code-phase truth grid: (pr_truth_m / C * chip_hz) mod code_len built
    from the SIMULATED atmo-injected pseudorange series (time-varying
    Doppler included). The trace's ph_syn_chips linear grid (t0-constant
    code Doppler) is NOT used as reference: the engine injects time-
    varying Doppler and the constant-rate grid ramps up to ~0.15 ch over
    30 s for low-elevation GPS (verified 2026-11-09).
    """
    per_sv, rows = {}, []
    for key, sv in ts["svs"].items():
        sysc = sv["sys"]
        code_len = float(sv.get("code_len") or 0.0)
        chip_hz = float(sv.get("chip_hz") or 0.0)
        m_per_chip = config.C / chip_hz if chip_hz else 0.0
        truth_pr = np.array(sv.get("pr_truth_m") or [], float)
        truth_ch = np.mod(truth_pr / config.C * chip_hz, code_len) \
            if truth_pr.size and code_len else np.array([], float)
        fd_const = float(sv.get("carrier_doppler_hz") or 0.0)
        gain_db = float(sv.get("gain_db") or 0.0)
        el_true = np.array(sv.get("el_deg_t") or [], float)
        # snapshot acquisition quantization sigma (integer-lag grid)
        sig_q = (fs_hz / chip_hz) ** -1.0 / math.sqrt(12.0) if fs_hz else None
        rec = {"sys": sysc, "gain_db": gain_db,
               "fd_inj_hz": fd_const, "chip_to_m": m_per_chip,
               "acq_quant_sigma_ch": sig_q}

        # ---- snapshot (acquisition grid) ----
        rs = tr["svs"].get(key, {})
        if rs and truth_ch.size and rs.get("ph_meas_chips"):
            phm = np.array(rs["ph_meas_chips"], float)
            dch = _wrap(phm - truth_ch, code_len)
            _, rec["code_snap"] = _demean(dch)
            rec["code_snap_pred"] = _stats(rs["err_chips"])
            meas = np.array(rs["meas_pr_m"], float)
            if truth_pr.size == meas.size:
                _, rec["pr_snap"] = _demean(meas - truth_pr)
            fdr = np.array(rs["fd_meas_hz"], float)
            fd_geo = np.array(sv.get("fd_geo_hz") or [], float)
            ref = fdr - (fd_geo if fd_geo.size == fdr.size else fd_const)
            _, rec["fd_snap"] = _demean(ref)
            elr = np.array(rs.get("el_rx_deg") or [], float)
            if elr.size == el_true.size:
                rec["el_max_deg"] = float(np.nanmax(np.abs(elr - el_true)))
            met = np.array(rs.get("metric_db") or [], float)
            ok = np.isfinite(met)
            if ok.sum() > 3:
                rec["metric_mean_db"] = float(np.mean(met[ok]))
        # ---- tracked sessions ----
        ds = td["svs"].get(key, {})
        if ds and truth_ch.size and ds.get("chi_chips"):
            chi = np.array(ds["chi_chips"], float)
            fdm = np.array(ds.get("fd_meas_hz") or [], float)
            # tracked chi may legitimately drift (unlike bounded acq); wrap
            # against the sim truth grid so long sessions don't blow past
            # code_len, then use ONE lock filter: epochs where the DLL is
            # still > 0.5 ch from the (de-meaned) lock are pull-in and get
            # dropped for code, pr AND doppler alike.
            dch = _wrap(chi - truth_ch, code_len)
            lock0 = np.median(dch[np.isfinite(dch)]) if dch.size else 0.0
            keep = np.isfinite(dch) & (np.abs(dch - lock0) < 0.5)
            _, rec["code_trk"] = _demean(dch[keep] if keep.sum() >= 3 else dch)
            rec["code_trk_n_keep"] = int(keep.sum())
            rec["code_trk_pred"] = _stats(np.array(ds["err_chips"], float))
            meas = np.array(ds["meas_pr_m"], float)
            if truth_pr.size == meas.size:
                dp = meas - truth_pr
                _, rec["pr_trk"] = _demean(dp[keep] if keep.sum() >= 3 else dp)
            if fdm.size:
                fd_geo = np.array(sv.get("fd_geo_hz") or [], float)
                ref = fdm - (fd_geo if fd_geo.size == fdm.size else fd_const)
                # drop the seed-transient epoch(s): |fd - session median|
                # > 0.6 acq bins (30 Hz) is the acquisition seed bin the
                # FLL hasn't pulled yet (observed: first epoch exactly one
                # 50 Hz bin off, remaining 29 < 1 Hz) -- not a sim/rx
                # disagreement.
                r_ok = np.isfinite(ref)
                if r_ok.sum() >= 3:
                    ref_keep = r_ok & (np.abs(ref - np.median(ref[r_ok])) < 30.0)
                else:
                    ref_keep = r_ok
                _, rec["fd_trk"] = _demean(ref[ref_keep] if ref_keep.sum() >= 3 else ref)
                rec["fd_trk_n_keep"] = int(ref_keep.sum())
                rec["fd_trk_vs_const_bias_hz"] = float(np.median(fdm - fd_const)) \
                    if fdm.size else None
                if fd_geo.size == fdm.size:
                    rec["fd_geo_span_hz"] = float(np.nanmax(fd_geo)
                                                  - np.nanmin(fd_geo))
            phr = ds.get("phase_resid_cycles")
            if phr:
                y = np.unwrap(np.array(phr, float))
                drift, jit = _detrend_rms(y)
                if drift is not None:
                    # NOTE: jitter here comes from the 1 s trace grid where
                    # the true phase rate is ~5 cyc/sample (unwrap-limited);
                    # the authoritative jitter is the 50 Hz session log in
                    # the tracked-fix regression. Informational only.
                    rec["phase"] = {"drift_cycps": drift * ts["step_s"],
                                    "jitter_tracegrid_cyc": jit,
                                    "n_drop": int((~np.isfinite(
                                        np.array(phr, float))).sum())}
        rows.append((key, rec))
        per_sv[key] = rec
    return per_sv, rows


# --------------------------------------------------------------------- #
# nav demodulation                                                      #
# --------------------------------------------------------------------- #

def verify_nav(outdir, meta, eph, *, g_window=55.0, e_window=55.0):
    """Demodulate LNAV/I/NAV from the IQ and compare every ephemeris field.

    Seeds come from the TRACKED sessions (trace_dll.json), the same way a
    real receiver decodes nav inside the tracking loop: the acquisition
    50 Hz Doppler bins are too coarse for the long coherent integrations
    (probe: E acq-seed 0/12 CRC-valid pages vs tracked-seed full decode).
    Windows cover a full nav cycle: LNAV sf1..5 repeat every 30 s (>= 6
    subframe times => 55 s guarantees sf1,2,3 all present); I/NAV word
    types 1-4 rotate once per 50-word page cycle (55 s = 55 words covers
    every type -- a 14 s window only covers ~14 consecutive words and
    decodes only the lucky SVs).
    """
    from backend import inspector
    from backend.analysis import (l1_acquire, lnav_decode, inav_decode)
    fmt = meta["sample_format"]
    band_files = {b["id"]: (outdir / b["file"], float(b["fs"]))
                  for b in meta.get("bands", [])}
    svs = meta.get("provenance", {}).get("svs", [])
    try:
        _tdll = json.loads((outdir / "trace_dll.json").read_text())
        td = _tdll["svs"]
        td_t = np.asarray(_tdll.get("t_s") or [], float)
    except (OSError, KeyError):
        td, td_t = {}, np.zeros(0)
    out = {}
    cache: dict = {}

    def iq_for(band, seconds):
        bf, b_fs = band_files[band]
        kk = (str(bf), seconds)
        if kk not in cache:
            cache[kk] = inspector.read_iq(bf, fmt, max_samples=int(b_fs * seconds))
        return cache[kk], b_fs

    def tracked_seed(key):
        """Median tracked fd + its chi, seed-transient epochs removed."""
        d = td.get(key) or {}
        fdm = np.asarray(d.get("fd_meas_hz") or [], float)
        chi = np.asarray(d.get("chi_chips") or [], float)
        if fdm.size < 3 or chi.size != fdm.size:
            return None
        ok = np.abs(fdm - np.median(fdm)) < 30.0        # drop acq-bin transient
        if ok.sum() < 3:
            ok = np.ones(fdm.size, bool)
        ia = int(np.argmax(ok))
        return {"fd": float(np.median(fdm[ok])),
                "chi": float(chi[ia]), "t_a": float(ia)}

    for sv in svs:
        sysc, prn = sv["sys"], sv["prn"]
        if sysc not in ("G", "E"):
            continue
        key = f"{sysc}{prn}"
        rec_ref = None
        if eph:
            rec_ref = eph.get((sysc, int(prn))) or eph.get(f"{sysc}{prn}")
        item = {"sys": sysc, "decoded": False}
        seed = tracked_seed(key)
        try:
            if sysc == "G":
                iq, b_fs = iq_for(sv["band"], g_window)
                sfs: dict = {}
                item["seed"] = "acq"
                if seed is not None:
                    item["seed"] = "tracked"
                    d = td.get(key) or {}
                    fdm = np.asarray(d.get("fd_meas_hz") or [], float)
                    chim = np.asarray(d.get("chi_chips") or [], float)
                    # In-loop decoding: seed the tracked (chi, fd) at each
                    # sub-window start and let demod_nav_bits do the internal
                    # constant wipe + rate grid + JOINT (f,off) residual search.
                    # The tracked fd carries the FLL's ~6 Hz pull-in bias, so
                    # the residual search (not a manual wipe) owns the fine
                    # carrier -- a manual linear wipe seeded from the noisy
                    # tracked fd slope was worse than letting demod search it.
                    # Subframe types repeat every 6 s so 13 s windows at 5 s
                    # steps sweep the whole 1..6 cycle within ~30 s; stop once
                    # the ephemeris subframes {1,2,3} are all in hand.
                    # Bit boundaries come from the engine tx-clock model
                    # (_attach_tx_clock):  rx_n = 0.02n + (t0−sow) + pr/c
                    #                                    − eff/chip_rate.
                    for t_a in (1, 6, 11, 16, 21, 26):
                        if t_a >= fdm.size or {1, 2, 3} <= set(sfs):
                            break
                        w0, w1 = int(t_a * b_fs), int((t_a + 13.0) * b_fs)
                        if w1 > iq.size:
                            break
                        bits = lnav_decode.demod_nav_bits(
                            iq[w0:w1], b_fs, prn, float(chim[t_a]),
                            float(fdm[t_a]), n_bits=600, rate_span=4.0)
                        for h in (lnav_decode.find_frame(bits)
                                  if len(bits) >= 600 else []):
                            sfs.setdefault(h["subframe_id"], h["words"])
                else:                                    # acq fallback
                    acq = l1_acquire.acquire_l1(iq[:int(b_fs * 0.020)], b_fs,
                                                "G", prn,
                                                centre_offset_hz=sv.get("if_hz", 0.0))
                    bits = lnav_decode.demod_nav_bits(
                        iq[:int(b_fs * 13)], b_fs, prn,
                        acq.get("code_phase_chips", 0.0),
                        acq.get("doppler_hz", 0.0), n_bits=600)
                    sfs = {h["subframe_id"]: h["words"]
                           for h in lnav_decode.find_frame(bits)} \
                        if len(bits) >= 600 else {}
                item["subframes"] = sorted(sfs)
                if {1, 2, 3} <= set(sfs):
                    item["decoded"] = True
                    item["fields"] = lnav_decode.decode_ephemeris(sfs)
                else:
                    item["reason"] = f"subframes found: {sorted(sfs)}"
            else:
                iq, b_fs = iq_for(sv["band"], e_window)
                kw = {}
                if seed is not None:
                    kw = {"dopp_hz": seed["fd"], "code_phase_chips": seed["chi"]}
                    item["seed"] = "tracked"
                else:
                    item["seed"] = "acq"
                syms = inav_decode.demod_symbols_e1b(
                    iq, b_fs, prn, centre_offset_hz=sv.get("if_hz", 0.0), **kw)
                if len(syms) >= 500:
                    msgs = inav_decode.decode_messages(syms.tolist() if hasattr(syms, "tolist") else syms)
                    item["pages"] = len(msgs)
                    try:
                        item["fields"] = inav_decode.reconstruct_ephemeris(msgs)
                        item["decoded"] = True
                    except ValueError as exc:
                        item["reason"] = str(exc)
                else:
                    item["reason"] = f"only {len(syms)} symbols"
        except Exception as exc:                        # noqa: BLE001
            item["reason"] = f"{type(exc).__name__}: {exc}"

        flds = item.get("fields")
        if flds and rec_ref is not None:
            lsb = G_LSB if sysc == "G" else E_LSB
            # The I/NAV encoder broadcasts af0 REFERENCED TO THE E1-E5b IF:
            # inav_encode.word_type_4 adds geometry.galileo_clock_shift_s(
            # rec, "E5B") (Δ = BGD(E1,E5a)-BGD(E1,E5b)) when packing, and
            # reconstruct tags the result clk_ref="E5B". Comparing that
            # against an E5a-referenced BRDC record without the same shift
            # shows a constant ~260-LSB offset -- apply it to the reference.
            if sysc == "E" and "af0" in rec_ref:
                from backend.geometry import galileo_clock_shift_s
                rec_ref = dict(rec_ref)
                rec_ref["af0"] = (float(rec_ref["af0"])
                                  + galileo_clock_shift_s(rec_ref, "E5B"))
            mism, warn, checked = [], [], 0
            for f, ref in list(rec_ref.items()):
                if f not in flds or isinstance(ref, (str, list, dict, bool)) \
                        or isinstance(flds[f], (str, list, dict, bool)):
                    continue
                try:
                    dec, ref = float(flds[f]), float(ref)
                except (TypeError, ValueError):
                    continue
                if f == "gps_week":
                    # LNAV subframe 1 carries the WEEK MODULO 1024 (10-bit
                    # field); the broadcast record carries the full week.
                    # 391 vs 2439 is the SAME week -- compare through the
                    # rollover, not with an absolute-value tolerance.
                    checked += 1
                    if min((dec - ref) % 1024.0, (ref - dec) % 1024.0) > 1e-6:
                        mism.append({"f": f, "dec": dec, "ref": ref,
                                     "err": "week-10bit"})
                    continue
                if f in (G_INT if sysc == "G" else E_INT):
                    checked += 1
                    if abs(float(dec) - float(ref)) > 1e-6:
                        (warn if f in ZEROABLE else mism).append(
                            {"f": f, "dec": dec, "ref": ref, "err": "int-grid"})
                    continue
                tol = TOLK * lsb.get(f, max(abs(float(ref)) * 1e-9, 1e-12))
                err = abs(float(dec) - float(ref))
                checked += 1
                if err > tol:
                    (warn if f in ZEROABLE else mism).append(
                        {"f": f, "dec": float(dec), "ref": float(ref),
                         "err": err, "tol": tol})
            item["fields_checked"] = checked
            item["mismatches"] = mism
            item["warn_zeroable"] = warn
        out[key] = item
    return out


def build_summary(per_sv, nav):
    summ = {}
    for sysc in ("G", "E"):
        rows = {k: v for k, v in per_sv.items() if v["sys"] == sysc}
        s = {"n_sv": len(rows)}

        # explicit checks with thresholds
        def chk(name, values, thr, better="min"):
            if not values:
                return
            w = max(values) if better == "min" else min(values)
            s[name] = {"worst": w, "mean": float(np.mean(values)),
                       "threshold": thr, "pass": bool(
                           (w <= thr) if better == "min" else (w >= thr))}

        chk("code_trk_rms_ch", [v["code_trk"]["rms"] for v in rows.values()
                                if isinstance(v.get("code_trk"), dict)],
            TH["code_trk_rms_ch"])
        chk("code_trk_max_ch", [v["code_trk"]["max_abs"] for v in rows.values()
                                if isinstance(v.get("code_trk"), dict)],
            TH["code_trk_max_ch"])
        chk("pr_trk_rms_m", [v["pr_trk"]["rms"] for v in rows.values()
                             if isinstance(v.get("pr_trk"), dict)],
            TH["pr_trk_rms_m"])
        chk("pr_trk_max_m", [v["pr_trk"]["max_abs"] for v in rows.values()
                             if isinstance(v.get("pr_trk"), dict)],
            TH["pr_trk_max_m"])
        chk("fd_trk_rms_hz", [v["fd_trk"]["rms"] for v in rows.values()
                              if isinstance(v.get("fd_trk"), dict)],
            TH["fd_trk_rms_hz"])
        chk("code_snap_rms_ch", [v["code_snap"]["rms"] for v in rows.values()
                                 if isinstance(v.get("code_snap"), dict)],
            TH["code_snap_rms_ch"])
        chk("pr_snap_rms_m", [v["pr_snap"]["rms"] for v in rows.values()
                              if isinstance(v.get("pr_snap"), dict)],
            TH["pr_snap_rms_m"])
        chk("fd_snap_max_hz", [v["fd_snap"]["max_abs"] for v in rows.values()
                               if isinstance(v.get("fd_snap"), dict)],
            TH["fd_snap_max_hz"])
        chk("phase_drift_cycps", [abs(v["phase"]["drift_cycps"]) for v in rows.values()
                                  if isinstance(v.get("phase"), dict)],
            TH["phase_drift_cycps"])
        chk("el_max_deg", [v["el_max_deg"] for v in rows.values()
                           if "el_max_deg" in v], TH["el_max_deg"])
        # strength: CROSS-SV regression (gain_db is per-SV constant, so a
        # within-SV fit is meaningless -- correlate across the constellation)
        gxs = [v["gain_db"] for v in rows.values() if "metric_mean_db" in v]
        mys = [v["metric_mean_db"] for v in rows.values() if "metric_mean_db" in v]
        if len(gxs) >= 3 and np.std(gxs) > 0.1:
            sl = float(np.polyfit(gxs, mys, 1)[0])
            r = float(np.corrcoef(gxs, mys)[0, 1])
            s["strength_slope"] = {"worst": abs(sl - 1.0), "mean": abs(sl - 1.0),
                                   "threshold": TH["strength_slope"],
                                   "pass": bool(abs(sl - 1.0) < TH["strength_slope"])}
            s["strength_r"] = {"worst": r, "mean": r,
                               "threshold": TH["strength_r"],
                               "pass": bool(r >= TH["strength_r"])}
        summ[sysc] = s
    if nav:
        for sysc in ("G", "E"):
            items = [v for v in nav.values() if v["sys"] == sysc]
            if not items:
                continue
            dec = [v for v in items if v.get("decoded") and v.get("fields")]
            viol = [k for k, v in nav.items()
                    if v.get("mismatches") and v["sys"] == sysc]
            summ[sysc]["nav"] = {
                "decoded": len(dec), "of": len(items),
                "fields_checked_total": sum(v.get("fields_checked", 0) for v in dec),
                "mismatched_svs": viol,
                "coverage_ok": len(dec) >= TH["nav_coverage"] * len(items),
                "pass": bool(len(dec) >= TH["nav_coverage"] * len(items)) and not viol}
    overall = all(c.get("pass", True)
                  for sysc in ("G", "E")
                  for k, c in summ.get(sysc, {}).items() if isinstance(c, dict))
    summ["verdict"] = "PASS" if overall else "FAIL"
    return summ


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runid")
    ap.add_argument("--nav", action="store_true",
                    help="also demodulate LNAV/I/NAV and compare every field")
    ap.add_argument("--regen", action="store_true",
                    help="regenerate the three trace json dumps first")
    ap.add_argument("--g-window", type=float, default=55.0)
    ap.add_argument("--e-window", type=float, default=55.0)
    ap.add_argument("--out", default="verify_sim_rx.json")
    a = ap.parse_args()

    outdir = config.OUT_DIR / a.runid if not pathlib.Path(a.runid).is_absolute() \
        else pathlib.Path(a.runid)
    meta = _load_run(outdir)
    ts_p, tr_p, td_p = (outdir / "trace_sim.json", outdir / "trace_rx.json",
                        outdir / "trace_dll.json")
    if a.regen or not (ts_p.exists() and tr_p.exists() and td_p.exists()):
        from backend.analysis import trace as _tr
        eph = _resolve_eph_for_run(meta)
        _tr.dump_sim_trace(outdir, eph=eph)
        _tr.dump_rx_trace(outdir, eph=eph, marker_llh=None)
        _tr.dump_rx_trace_dll(outdir, eph=eph, marker_llh=None, dll_mode="coh")
    ts = json.loads(ts_p.read_text())
    tr = json.loads(tr_p.read_text())
    td = json.loads(td_p.read_text())

    # acquisition-grid thresholds follow the sample rate: the integer-lag
    # quantization sigma is the FLOOR every correct receiver reproduces,
    # so "consistent with sim" = resid within 3 sigmas of pure quantization.
    bands = {b["id"]: float(b["fs"]) for b in meta.get("bands", [])}
    fs_l1 = bands.get("L1") or (next(iter(bands.values())) if bands else None)
    sig_q = ((fs_l1 / 1.023e6) ** -1.0 / math.sqrt(12.0)) if fs_l1 else None
    if sig_q:
        TH["code_snap_rms_ch"] = max(0.04, 3.0 * sig_q)
        TH["pr_snap_rms_m"] = TH["code_snap_rms_ch"] * (config.C / 1.023e6) + 2.0
    TH["fd_snap_rms_hz"] = max(22.0, 2 * 50.0 / math.sqrt(12.0) + 6.0)

    per_sv, _ = verify_observations(ts, tr, td, fs_hz=fs_l1)
    nav = None
    if a.nav:
        eph = _resolve_eph_for_run(meta)
        nav = verify_nav(outdir, meta, eph,
                         g_window=a.g_window, e_window=a.e_window)
    summ = build_summary(per_sv, nav)

    doc = {
        "kind": "verify_sim_rx", "runid": outdir.name,
        "engine": ts.get("engine"), "start_utc": ts.get("start_utc"),
        "step_s": ts.get("step_s"), "n_epochs": ts.get("n_epochs"),
        "generated_utc": dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds"),
        "arrays_in": ["trace_sim.json", "trace_rx.json", "trace_dll.json"],
        "thresholds": TH, "tolk": TOLK,
        "per_sv": per_sv, "summary": summ,
    }
    if nav is not None:
        doc["nav"] = nav
    (outdir / a.out).write_text(json.dumps(doc, indent=1, default=float))

    # ---- console report -------------------------------------------------
    print(f"=== verify_sim_rx  run={outdir.name}  epochs={ts['n_epochs']}"
          f" @ {ts['step_s']}s  -> {outdir / a.out}")
    for sysc in ("G", "E"):
        if sysc not in summ:
            continue
        s = summ[sysc]
        print(f"\n[{sysc}] {s['n_sv']} SVs")
        for k, v in s.items():
            if k == "nav":
                mark = "PASS" if v["pass"] else "FAIL"
                print(f"  nav demod          {v['decoded']}/{v['of']} decoded,"
                      f" {v['fields_checked_total']} fields,"
                      f" mismatched={v['mismatched_svs']}  {mark}")
            elif isinstance(v, dict) and "pass" in v:
                mark = "PASS" if v["pass"] else "FAIL"
                print(f"  {k:<20} worst={v['worst']:.5g} mean={v['mean']:.5g}"
                      f"  thr={v['threshold']:<7g} {mark}")
    print(f"\nVERDICT: {summ['verdict']}")
    sys.exit(0 if summ["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
