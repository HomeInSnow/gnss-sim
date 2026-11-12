"""Multi-GNSS L1 code-phase receiver position fix.

Computes pseudoranges from L1-group acquisitions across GPS, QZSS, SBAS,
Galileo, BeiDou, and GLONASS, applies satellite clock, group delay bias,
and atmospheric corrections, and solves for receiver position.
"""
from __future__ import annotations

import math
import numpy as np

from backend import config, geometry
from backend.analysis.l1_acquire import acquire_l1
from backend.analysis.receiver import _ecef_to_llh, solve_position
from backend.ephem import ephemeris
from backend.models import atmosphere
from backend.synth import engine, signals


def default_atmo_fn(rinex_path, approx_llh, t_gps_sow, *,
                    ionosphere=None, troposphere=None):
    """Build the receiver-side atmosphere model for a run.

    ``ionosphere`` / ``troposphere`` are per-run injection-policy booleans
    (from ``meta.config.atmosphere``): pass False to force that component to
    zero, None to fall back to the generator default policy. A receiver must
    only remove what the engine actually injected -- e.g. an
    ``atmosphere: off`` run has NO delays in the IQ, so subtracting
    Saastamoinen there biases pseudoranges ~-15 m at low elevation.
    """
    lat_deg, lon_deg, h_m = approx_llh
    cfg = atmosphere.AtmosphereConfig.from_dict(engine._DEFAULT_ATMOSPHERE)
    if ionosphere is False:
        cfg.ionosphere = "off"
    if troposphere is False:
        cfg.troposphere = "off"
    try:
        hdr = dict(ephemeris.rinex_header_iono_utc(rinex_path) or {})
    except Exception:
        hdr = {}
    if cfg.ionosphere == "klobuchar" and hdr.get("iono_alpha") and hdr.get("iono_beta"):
        cfg.klobuchar_alpha = tuple(float(x) for x in hdr["iono_alpha"][:4])
        cfg.klobuchar_beta = tuple(float(x) for x in hdr["iono_beta"][:4])

    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)

    def _atmo_parts(az_rad: float, el_rad: float, carrier_hz: float,
                    sysc: str | None = None) -> tuple[float, float]:
        # Mirror the engine's injection policy (synth/engine.py _atmo_for):
        # Galileo I/NAV broadcasts NeQuick-G ai0..ai2 = 0, so the generator
        # injects NO ionosphere for E (troposphere still applies). A receiver
        # must only remove what was actually injected -- applying Klobuchar
        # to E pseudoranges added a -0.03..-0.08 ch bias that grew at low
        # elevation and dominated the multi-GNSS LS error.
        iono = (
            atmosphere.klobuchar_delay_m(
                cfg.klobuchar_alpha,
                cfg.klobuchar_beta,
                t_gps_sow,
                lat_rad,
                lon_rad,
                az_rad,
                el_rad,
                freq_hz=carrier_hz,
            )["delay_m"]
            if cfg.ionosphere == "klobuchar" and sysc != "E"
            else 0.0
        )
        tropo = (
            atmosphere.saastamoinen_delay_m(
                el_rad,
                h_m,
                cfg.pressure_hpa,
                cfg.temperature_k,
                cfg.humidity,
            )["delay_m"]
            if cfg.troposphere == "saastamoinen"
            else 0.0
        )
        return float(iono), float(tropo)

    def atmo_delay(az_rad: float, el_rad: float, carrier_hz: float,
                   sysc: str | None = None) -> float:
        # CODE-side total delay (ionospheric + tropospheric group delay).
        i, t = _atmo_parts(az_rad, el_rad, carrier_hz, sysc)
        return i + t

    # Carrier-phase anchor needs the split: the generator advances the
    # CARRIER by the ionosphere while delaying code AND carrier phase by the
    # troposphere (engine _trajectory_knots: geo - iono + tropo). Anchoring
    # phi on the code total (geo + iono + tropo) instead injects a 2*iono
    # term whose slow rate looks like per-SV carrier-phase drift.
    atmo_delay.components = _atmo_parts        # (iono_m, tropo_m)
    return atmo_delay


def fix_from_iq_l1_multi(
    iq_by_band,
    meta,
    eph_by_key,
    approx_time_gps,
    *,
    approx_llh,
    marker_llh=None,
    atmo_fn=None,
    sv_clock: bool = True,
) -> dict:
    """``sv_clock=False`` mirrors a run synthesized WITHOUT the broadcast
    satellite clock (meta.config.sv_clock false): the prediction and the
    clock correction term both drop the af-polynomial (TGD/BGD stays).
    Pass it together with ``atmo_fn=None`` for a no-atmosphere run."""
    approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
    skipped = {}
    pr = {}
    sat_pos = {}
    per_sv = {}

    for sv in meta.get("provenance", {}).get("svs", []):
        key = f"{sv['sys']}{sv['prn']}"
        sysc = sv.get("sys")

        # a. Checks
        if sysc not in ("G", "J", "S", "E", "C", "R"):
            skipped[key] = "unsupported system"
            continue
        if sysc == "R" and sv.get("glo_k") is None:
            skipped[key] = "missing glo_k"
            continue
        if sv.get("band") not in iq_by_band:
            skipped[key] = "no band data"
            continue

        # b. Ephemeris lookup
        rinex_prn = sv["prn"] - engine._PRN_OFFSET.get(sysc, 0)
        rec = eph_by_key.get((sysc, rinex_prn))
        if rec is None and sysc == "G":
            rec = eph_by_key.get(rinex_prn)
        if rec is None:
            skipped[key] = "no ephemeris"
            continue

        # c. Signal, group delay, state function
        sig = signals.SIGNALS[
            {
                "G": "GPS_L1CA",
                "J": "QZSS_L1CA",
                "S": "SBAS_L1",
                "E": "GAL_E1",
                "C": "BDS_B1I",
                "R": "GLO_G1",
            }[sysc]
        ]
        svb = geometry.group_delay_bias_s(
            sysc, "L1", rec if isinstance(rec, dict) else None
        )
        state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec

        # d. Observables, elevation check, atmospheric delay, predicted phase
        o = geometry.observables(
            state, approx_rx, approx_time_gps, signal=sig, sv_clock_bias_s=svb,
            sv_clock=sv_clock
        )
        if o["el_deg"] < 5.0:
            skipped[key] = "low elevation"
            continue
        carrier_hz = sig.carrier_hz + (
            int(sv["glo_k"]) * 562_500.0 if sysc == "R" else 0.0
        )
        atmo_m = (
            float(
                atmo_fn(
                    math.radians(o["az_deg"]),
                    math.radians(o["el_deg"]),
                    carrier_hz,
                    sysc,
                )
            )
            if atmo_fn
            else 0.0
        )
        pred_pr = o["pseudorange_m"] + atmo_m
        pred_phase = (pred_pr / config.C * sig.chip_rate_hz) % sig.code_len

        # e. Acquire L1 code phase
        iq, fs = iq_by_band[sv["band"]]
        acq = acquire_l1(
            iq,
            fs,
            sysc,
            sv["prn"],
            centre_offset_hz=sv["if_hz"],
            glo_k=(int(sv["glo_k"]) if sysc == "R" else None),
        )
        if acq["metric_db"] < 15.0:
            skipped[key] = f"weak ({acq['metric_db']:.1f} dB)"
            continue

        # f. Measured pseudorange
        err_chips = (
            (acq["code_phase_chips"] - pred_phase + sig.code_len / 2.0)
            % sig.code_len
        ) - sig.code_len / 2.0
        measured_pr = pred_pr + err_chips * (config.C / sig.chip_rate_hz)

        # g. Transmit time, corrected pseudorange
        pos, _vel, _tof, clk = geometry.solve_transmit_time(
            state, approx_rx, approx_time_gps
        )
        corrected_pr = measured_pr + config.C * (
            (clk if sv_clock else 0.0) + svb) - atmo_m
        pr[key] = corrected_pr
        sat_pos[key] = pos
        per_sv[key] = {
            "measured_pr_m": measured_pr,
            "corrected_pr_m": corrected_pr,
            "metric_db": acq["metric_db"],
            "el_deg": o["el_deg"],
        }

    if len(pr) < 4:
        return {
            "error": f"only {len(pr)} SVs usable",
            "prns_used": sorted(pr),
            "skipped": skipped,
        }

    sol = solve_position(pr, sat_pos, x0=[*approx_rx, 0.0])
    lat, lon, h = _ecef_to_llh(*sol["ecef"])
    entries = []
    for k in sorted(pr):
        los = sat_pos[k] - np.array(sol["ecef"])
        entries.append({"_los": (los / np.linalg.norm(los)).tolist()})

    acquired: dict[str, list[int]] = {}
    for k in sorted(pr):
        s = k[0]
        p = int(k[1:])
        acquired.setdefault(s, []).append(p)
    for s in acquired:
        acquired[s].sort()

    out = {
        "ecef": sol["ecef"],
        "llh": [lat, lon, h],
        "clock_bias_s": sol["clock_bias_s"],
        "prns_used": sorted(pr),
        "pdop": geometry.dop(entries, sol["ecef"])["pdop"],
        "residual_rms_m": sol["residual_rms_m"],
        "per_sv": per_sv,
        "skipped": skipped,
        "acquired": acquired,
    }
    if marker_llh:
        truth = np.array(geometry.llh_to_ecef(*marker_llh))
        out["error_m"] = float(np.linalg.norm(np.array(sol["ecef"]) - truth))
    return out


def fix_from_iq_l1_multi_tracked(
    outdir,
    meta,
    eph_by_key,
    approx_time_gps,
    *,
    approx_llh,
    marker_llh=None,
    atmo_fn=None,
    sv_clock: bool = True,
    track_s: float = 3.0,
    dll_bw_hz: float = 0.5,
    min_metric_db: float = 15.0,
    dll_mode: str = "coh",
) -> dict:
    """Position fix from CARRIER-AIDED DLL tracking pseudoranges.

    ``dll_mode`` selects the code discriminator of the tracking sessions:
    "coh" (default) = coherent E/L + second-order Costas PLL with a
    carrier-phase observable, "el" = classic non-coherent EARLY/LATE power
    discriminator, "nc" = power-surface peak-tracking DLL (see
    ``tracker.SVTracker``). All modes share the acquisition seed,
    fd_fn carrier aiding and the anchored-pseudorange recipe. Identical
    anchoring recipe to ``fix_from_iq_l1_multi`` (pred_pr from the
    marker geometry, wrapped chip error, clock/group-delay corrections, same
    LS solver) -- the ONLY change is where the per-SV code phase comes from:
    instead of one integer-lag acquisition snapshot (quantization sigma =
    chip-per-sample/sqrt(12) ~ 0.06 chips ~ 17 m at 5 Msps), each SV runs a
    continuous ``SVTracker`` session (coherent E/L, or E/L / peak-tracking on
    the FFT power surface + FLL, seeded by that same acquisition) and the
    fix uses its chi -- a sub-0.01-chip measurement on this IQ, i.e. the
    pseudorange noise floor moves from sample-grid quantization to loop
    tracking error. Precision upgrades for the tracking path: the LS
    pseudorange uses the SESSION-MEDIAN wrapped chip error (median of the
    chi-minus-prediction series over the session, t >= 1 s, instead of the
    single fix-epoch sample), and coh mode additionally reports the tracked
    carrier phase (cycles) plus its anchored-residual RMS --
    wrap(phi + pred_pr/lambda) minus its session mean should be a few
    thousandths of a cycle for a healthy lock (the engine injects exactly
    -rho_carrier/lambda + per-SV constant). All SVs are measured on the
    SAME epoch so the LS solve stays coherent; observables/satellite
    positions are evaluated at ``approx_time_gps + track_s``.
    """
    import pathlib

    from backend.analysis.tracker import SVTracker
    from backend.inspector import read_iq

    outdir = pathlib.Path(outdir)
    # Marker/approx may arrive as a {lat,lon,alt} dict (HTTP body) or a
    # plain tuple -- normalize once up front so llh_to_ecef(*mk) is safe.
    if isinstance(marker_llh, dict):
        marker_llh = (marker_llh.get("lat", 0.0), marker_llh.get("lon", 0.0),
                      marker_llh.get("alt", 0.0))
    if isinstance(approx_llh, dict):
        approx_llh = (approx_llh.get("lat", 0.0), approx_llh.get("lon", 0.0),
                      approx_llh.get("alt", 0.0))
    sample_format = meta.get("sample_format", "int8")
    approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
    band_files = {b["id"]: (outdir / b["file"], float(b["fs"]))
                  for b in meta.get("bands", []) if (outdir / b["file"]).exists()}
    win_cache: dict[str, dict] = {bid: {} for bid in band_files}

    def get_window_for(bid: str):
        bf, fs = band_files[bid]
        cache = win_cache[bid]

        def get_window(t0: float, ns: int) -> np.ndarray:
            key = (int(round(t0 * fs)), ns)
            hit = cache.get(key)
            if hit is None:
                hit = read_iq(bf, sample_format, max_samples=ns,
                              offset_samples=key[0])
                if len(cache) > 600:
                    cache.clear()
                cache[key] = hit
            return hit
        return get_window

    skipped = {}
    pr = {}
    sat_pos = {}
    per_sv = {}

    for sv in meta.get("provenance", {}).get("svs", []):
        key = f"{sv['sys']}{sv['prn']}"
        sysc = sv.get("sys")
        if sysc not in ("G", "J", "S", "E", "C", "R"):
            skipped[key] = "unsupported system"
            continue
        if sysc == "R" and sv.get("glo_k") is None:
            skipped[key] = "missing glo_k"
            continue
        bid = sv.get("band")
        if bid not in band_files:
            skipped[key] = "no band data"
            continue
        rinex_prn = sv["prn"] - engine._PRN_OFFSET.get(sysc, 0)
        rec = eph_by_key.get((sysc, rinex_prn))
        if rec is None and sysc == "G":
            rec = eph_by_key.get(rinex_prn)
        if rec is None:
            skipped[key] = "no ephemeris"
            continue
        sig = signals.SIGNALS[{
            "G": "GPS_L1CA", "J": "QZSS_L1CA", "S": "SBAS_L1",
            "E": "GAL_E1", "C": "BDS_B1I", "R": "GLO_G1"}[sysc]]
        svb = geometry.group_delay_bias_s(
            sysc, "L1", rec if isinstance(rec, dict) else None)
        state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec

        # --- seed acquisition, then track up to the common fix epoch. The
        # seed follows dump_rx_trace_dll EXACTLY: pre-shift the block by the
        # synthesized Doppler and search a narrow +-300/50 Hz grid, so the
        # seed Doppler lands within the FLL's +-25 Hz unambiguous pull-in
        # range. (A raw +-5 kHz / 200 Hz-grid acquisition seed sits hundreds
        # of Hz off; the leaky FLL then never converges inside the short
        # window, the code-rate aiding chip_hz*fd/carrier is wrong by
        # ~0.1 ch/s, and err_chips blew up to 0.06 RMS / 0.14 max.)
        bf, fs = band_files[bid]
        npp = int(round(fs * sig.code_len / sig.chip_rate_hz))
        iq0 = read_iq(bf, sample_format, max_samples=npp * 4 + 16)
        fd_syn = sv.get("carrier_doppler_hz")
        if fd_syn is not None:
            seg0 = iq0 * np.exp(-2j * np.pi * float(fd_syn)
                                * np.arange(len(iq0)) / fs)
            acq = acquire_l1(seg0, fs, sysc, sv["prn"],
                             centre_offset_hz=sv["if_hz"],
                             glo_k=(int(sv["glo_k"]) if sysc == "R" else None),
                             dopp_hz=300.0, dopp_step_hz=50.0, nperiods=4)
            fd_seed = float(fd_syn) + acq["doppler_hz"]
        else:
            acq = acquire_l1(iq0, fs, sysc, sv["prn"],
                             centre_offset_hz=sv["if_hz"],
                             glo_k=(int(sv["glo_k"]) if sysc == "R" else None))
            fd_seed = acq["doppler_hz"]
        if acq["metric_db"] < min_metric_db:
            skipped[key] = f"weak ({acq['metric_db']:.1f} dB)"
            continue
        # Per-epoch geometric Doppler aiding grid (0.25 s steps over the
        # track window); the in-session FLL absorbs the clock/atmo-rate
        # residual -- same recipe as dump_rx_trace_dll, verified 0.003-0.02 ch.
        # The same nodes carry the predicted pseudorange (0.25 s curvature
        # ~2 mm, linear-interpolation error far below loop noise), which the
        # session-median code error and the phase residual are measured
        # against.
        carrier_hz = sig.carrier_hz + (
            int(sv["glo_k"]) * 562_500.0 if sysc == "R" else 0.0)
        t_g = np.arange(0.0, track_s + 0.51, 0.25)
        fd_g = np.empty(len(t_g))
        pr_g = np.empty(len(t_g))
        pr_c_g = np.empty(len(t_g))          # CARRIER-consistent anchor
        comps = getattr(atmo_fn, "components", None) if atmo_fn else None
        for i, tk in enumerate(t_g):
            o_n = geometry.observables(state, approx_rx,
                                       approx_time_gps + float(tk),
                                       signal=sig, sv_clock_bias_s=svb,
                                       sv_clock=sv_clock)
            fd_g[i] = o_n["carrier_doppler_hz"]
            if comps is not None:
                iono_n, tropo_n = comps(math.radians(o_n["az_deg"]),
                                        math.radians(o_n["el_deg"]),
                                        carrier_hz, sysc)
                atmo_n = iono_n + tropo_n
            elif atmo_fn is not None:
                atmo_n = float(atmo_fn(math.radians(o_n["az_deg"]),
                                       math.radians(o_n["el_deg"]),
                                       carrier_hz, sysc))
                iono_n, tropo_n = 0.0, atmo_n
            else:
                atmo_n = iono_n = tropo_n = 0.0
            pr_g[i] = o_n["pseudorange_m"] + atmo_n
            # engine cph node model is geo - iono + tropo (iono ADVANCES the
            # carrier): anchoring the phase residual on the code total
            # (geo + iono + tropo) leaves 2*iono whose slow rate masquerades
            # as per-SV carrier-phase drift.
            pr_c_g[i] = o_n["pseudorange_m"] - iono_n + tropo_n
        trk = SVTracker(get_window_for(bid), fs, sysc, sv["prn"],
                        chip_hz=sig.chip_rate_hz, code_len=sig.code_len,
                        carrier_hz=float(sig.carrier_hz),
                        if_hz=float(sv["if_hz"]),
                        fd0=fd_seed,
                        chi0=acq["code_phase_chips"],
                        boc=(sig.boc is not None), mode=dll_mode,
                        cn0_est=True,
                        dll_bw_hz=dll_bw_hz,
                        fd_fn=(lambda t, tg=t_g, fg=fd_g:
                               float(np.interp(t, tg, fg))))
        trk.run(t_end=track_s + 1e-6, log_period_s=0.05)
        m = trk.measure(track_s)
        if not m:
            skipped[key] = "no track"
            continue

        # --- anchored pseudorange at the COMMON fix epoch (same recipe as
        # the snapshot fix, evaluated at t = track_s).
        o = geometry.observables(state, approx_rx,
                                 approx_time_gps + track_s,
                                 signal=sig, sv_clock_bias_s=svb,
                                 sv_clock=sv_clock)
        if o["el_deg"] < 5.0:
            skipped[key] = "low elevation"
            continue
        atmo_m = float(atmo_fn(math.radians(o["az_deg"]),
                              math.radians(o["el_deg"]), carrier_hz,
                              sysc)) if atmo_fn else 0.0
        pred_pr = o["pseudorange_m"] + atmo_m
        pred_phase = (pred_pr / config.C * sig.chip_rate_hz) % sig.code_len
        err_chips = ((m["chi_chips"] - pred_phase + sig.code_len / 2.0)
                     % sig.code_len) - sig.code_len / 2.0
        # Session-median wrapped chip error: chi_log vs the interpolated
        # predicted phase (averages loop jitter over the whole session,
        # t >= 1 s, instead of sampling one epoch).
        err_med = None
        if len(trk.chi_log) >= 16:
            tl = np.array(trk.t_log, float)
            cl = np.array(trk.chi_log, float)
            sel = tl >= 1.0
            if sel.sum() >= 16:
                pp = np.interp(tl[sel], t_g, pr_g) / config.C \
                    * sig.chip_rate_hz
                e_s = ((cl[sel] - pp + sig.code_len / 2.0) % sig.code_len) \
                    - sig.code_len / 2.0
                err_med = float(np.median(e_s))
        err_used = err_chips if err_med is None else err_med
        # Carrier-phase observable (coh): the tracked NCO phase follows
        # -rho_carr/lambda + per-SV constant, rho_carr = geo - iono + tropo
        # (engine _trajectory_knots cph). The anchored residual
        # phi + rho_carr/lambda is continuous (the tracker books phase to
        # absolute times); a genuine receiver estimates its per-SV constant
        # (ambiguity) AND a slow rate (clock/bias) anyway, so loop quality
        # is the LINEAR-DETRENDED RMS -- the raw RMS just re-displays that
        # deterministic drift (obs. E-side raw 0.32 cyc vs detrended 0.03).
        # unwrap() only guards against rare PLL step jumps.
        ph_cycles = m.get("carrier_phase_cycles")
        ph_rms = None
        ph_drift = None
        if ph_cycles is not None and len(trk.phase_log) >= 16:
            tl2 = np.array(trk.t_log, float)
            ph = np.array(trk.phase_log, float)
            sel2 = tl2 >= 1.0
            if sel2.sum() >= 16:
                lam = config.C / carrier_hz
                phr = np.unwrap(ph[sel2]
                                + np.interp(tl2[sel2], t_g, pr_c_g) / lam)
                pfit = np.polyfit(tl2[sel2], phr, 1)
                ph_drift = float(pfit[0])                  # cyc/s
                res = phr - np.polyval(pfit, tl2[sel2])
                ph_rms = float(np.sqrt(np.mean(res * res)))
        measured_pr = pred_pr + err_used * (config.C / sig.chip_rate_hz)
        pos, _vel, _tof, clk = geometry.solve_transmit_time(
            state, approx_rx, approx_time_gps + track_s)
        corrected_pr = measured_pr + config.C * (
            (clk if sv_clock else 0.0) + svb) - atmo_m
        pr[key] = corrected_pr
        sat_pos[key] = pos
        per_sv[key] = {
            "measured_pr_m": measured_pr,
            "corrected_pr_m": corrected_pr,
            "err_chips": err_chips,
            "err_chips_avg": err_med,
            "chip_rms_hist": None,      # filled below from session logs
            "fd_meas_hz": m["doppler_hz"],
            "carrier_phase_cycles": ph_cycles,
            "phase_rms_cycles": ph_rms,       # linear-detrended loop jitter
            "phase_drift_cycps": ph_drift,    # per-SV bias-rate (absorbed
                                              # by a real user's clock/amb. est.)
            "pll_off_hz": m.get("pll_off_hz"),
            "n_pll_skipped": m.get("n_pll_skipped"),
            "metric_db": acq["metric_db"],
            "el_deg": o["el_deg"],
            # Kay-1980 moment C/N0 (tracker.cn0_dbhz) over the fix-second of
            # the session -- same estimator family as the thesis (eq. 35).
            "cn0_dbhz": next((trk.cn0_dbhz(s) for s in
                              range(int(round(track_s)), 0, -1)
                              if trk.cn0_dbhz(s) is not None), None),
        }
        # Session jitter: chi legitimately SWEEPS at ~-code_dop (up to a few
        # ch/s), so spread vs a fixed base measures the ramp itself; unwrap,
        # detrend linearly, and report the residual RMS = loop jitter only.
        if len(trk.chi_log) >= 8:
            tl = np.array(trk.t_log, float)
            cl = np.unwrap(np.array(trk.chi_log, float))
            sel = tl >= 1.0
            if sel.sum() >= 8:
                pfit = np.polyfit(tl[sel], cl[sel], 1)
                res = cl[sel] - np.polyval(pfit, tl[sel])
                per_sv[key]["chip_rms_hist"] = float(
                    np.sqrt(np.mean(res * res)))

    if len(pr) < 4:
        return {"error": f"only {len(pr)} SVs usable (tracking)",
                "prns_used": sorted(pr), "skipped": skipped}

    sol = solve_position(pr, sat_pos, x0=[*approx_rx, 0.0])
    lat, lon, h = _ecef_to_llh(*sol["ecef"])
    entries = []
    for k in sorted(pr):
        los = sat_pos[k] - np.array(sol["ecef"])
        entries.append({"_los": (los / np.linalg.norm(los)).tolist()})
    acquired: dict[str, list[int]] = {}
    for k in sorted(pr):
        s = k[0]
        p = int(k[1:])
        acquired.setdefault(s, []).append(p)
    for s in acquired:
        acquired[s].sort()
    out = {
        "mode": "tracking",
        "dll_mode": dll_mode,
        "track_s": track_s,
        "ecef": sol["ecef"],
        "llh": [lat, lon, h],
        "clock_bias_s": sol["clock_bias_s"],
        "prns_used": sorted(pr),
        "pdop": geometry.dop(entries, sol["ecef"])["pdop"],
        "residual_rms_m": sol["residual_rms_m"],
        "per_sv": per_sv,
        "skipped": skipped,
        "acquired": acquired,
    }
    if marker_llh:
        truth = np.array(geometry.llh_to_ecef(*marker_llh))
        out["error_m"] = float(np.linalg.norm(np.array(sol["ecef"]) - truth))
    return out
