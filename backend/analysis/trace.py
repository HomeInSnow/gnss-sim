"""Sim-truth vs receiver-measurement traces on one shared time grid.

The generator (native engine) and the built-in receiver live on different
sides of the IQ file: the engine knows the EXACT signal it synthesized
(code phase trajectory, Doppler, per-SV gain), the receiver only knows what
acquisition pulled out of the samples. Comparing the FINAL fix hides where
an error comes from; comparing the underlying observables per epoch does not.

Both dumps use the identical grid ``t_k = k * step_s`` (seconds from run
start) so ``scripts/plot_trace.py`` can pair them by index:

* ``trace_sim.json`` -- what the synthesizer transmitted:
  provenance constants (code phase at sample 0, constant carrier/code
  Doppler, gain taper) -> reconstructed code-phase trajectory in the
  ACQUISITION frame, ``ph_syn(t) = (ph0 - fd_code*t) mod code_len``
  (the engine's file code grid advances at +code_dop; acquire_l1 reports
  the mirrored phase, see dump_sim_trace for the derivation), plus
  per-epoch geometric
  series (range, Doppler, az/el, atmosphere) recomputed from the SAME
  ephemeris copy the run used (``align_for_run`` + ``at_gps``).
* ``trace_rx.json`` -- what the receiver measured, epoch by epoch: a narrow
  acquisition around the SV's own synthesized carrier Doppler yields
  measured code phase / Doppler / acquisition metric; the anchored
  pseudorange recipe of ``l1_fix.fix_from_iq_l1_multi`` is replicated
  exactly (observables + atmo -> pred_pr, wrapped chip error -> measured_pr)
  so the trace and the position fix can never disagree.

Cost note: per-epoch acquisition dominates. The search is pre-shifted to
the known synthesized Doppler and cut to +-``dopp_span_hz`` with 2 code
periods, which keeps a 30-epoch x ~40-SV dump at the minute scale.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib

import numpy as np

from backend import config, geometry
from backend.analysis import l1_fix
from backend.analysis.l1_acquire import acquire_l1
from backend.ephem import ephemeris
from backend.inspector import read_iq
from backend.models import atmosphere
from backend.synth import engine, signals

_SIGNAL_KEYS = {
    "G": "GPS_L1CA", "J": "QZSS_L1CA", "S": "SBAS_L1",
    "E": "GAL_E1", "C": "BDS_B1I", "R": "GLO_G1",
}

_TRACE_SYSTEMS = tuple(_SIGNAL_KEYS)


def _parse_utc(text: str) -> dt.datetime:
    """ISO-8061 -> naive UTC (same contract as backend.app._parse_utc)."""
    t = dt.datetime.fromisoformat(text)
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return t


def _wrap(x: float, length: float) -> float:
    return (x + length / 2.0) % length - length / 2.0


def _load_run(outdir: pathlib.Path) -> dict:
    meta = json.loads((outdir / "meta.json").read_text())
    prov = meta.get("provenance", {}) or {}
    cfg = meta.get("config", {}) or {}
    start = _parse_utc(cfg["start_utc"])
    gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
    week, sow = ephemeris.gps_week_and_sow(gps_start)
    systems = tuple(meta.get("systems") or cfg.get("systems")
                    or sorted({s.get("sys") for s in prov.get("svs", [])}
                              - {None}))
    return {
        "outdir": outdir, "meta": meta, "prov": prov, "cfg": cfg,
        "engine": prov.get("engine"), "start": start, "gps_start": gps_start,
        "week": week, "sow": float(sow), "systems": systems,
        "bands": {b["id"]: b for b in meta.get("bands", []) or []},
        "svs": prov.get("svs", []) or [],
    }


def _load_eph(ctx: dict):
    """The verification-side ephemeris copy: same file, same run-start record
    selection (at_gps) and same align_for_run the /api/receiver path uses."""
    if ctx["engine"] != "native":
        return None
    rinex_path = ctx["cfg"].get("rinex_path")
    if not rinex_path or not pathlib.Path(rinex_path).exists():
        return None
    try:
        eph = ephemeris.parse_rinex_multi(
            rinex_path, tuple(ctx["systems"] or ("G",)),
            at_gps=ctx["gps_start"])
        return ephemeris.align_for_run(eph, ctx["week"], ctx["sow"], "native")
    except Exception:                            # noqa: BLE001 - degrade
        return None


def _lookup_rec(eph: dict, sysc: str, prn: int):
    """Provenance prn -> rinex record, with l1_fix's legacy GPS key fallback."""
    rinex_prn = prn - engine._PRN_OFFSET.get(sysc, 0)
    rec = eph.get((sysc, rinex_prn))
    if rec is None and sysc == "G":
        rec = eph.get(rinex_prn)
    return rec


def _sim_atmo_factory(rinex_path, lat_rad, lon_rad, h_m, sow0):
    """Re-implement engine._run_impl._atmo_for: Klobuchar (header params)
    for every system EXCEPT Galileo (I/NAV publishes zero NeQuick-G, so the
    engine never injects iono into E), Saastramoinen for all."""
    cfg = atmosphere.AtmosphereConfig.from_dict(engine._DEFAULT_ATMOSPHERE)
    try:
        hdr = dict(ephemeris.rinex_header_iono_utc(rinex_path) or {})
    except Exception:                            # noqa: BLE001
        hdr = {}
    if cfg.ionosphere == "klobuchar":
        if hdr.get("iono_alpha") and hdr.get("iono_beta"):
            cfg.klobuchar_alpha = tuple(float(x) for x in hdr["iono_alpha"][:4])
            cfg.klobuchar_beta = tuple(float(x) for x in hdr["iono_beta"][:4])

    def f(sysc, az_rad, el_rad, carrier_hz, t_rel):
        iono = 0.0
        if cfg.ionosphere == "klobuchar" and sysc != "E":
            iono = atmosphere.klobuchar_delay_m(
                cfg.klobuchar_alpha, cfg.klobuchar_beta,
                sow0 + t_rel, lat_rad, lon_rad, az_rad, el_rad,
                freq_hz=carrier_hz)["delay_m"]
        tropo = 0.0
        if cfg.troposphere == "saastamoinen":
            tropo = atmosphere.saastamoinen_delay_m(
                el_rad, h_m, cfg.pressure_hpa, cfg.temperature_k,
                cfg.humidity)["delay_m"]
        return float(iono), float(tropo)
    return f


def _grid(step_s: float, n_epochs: int) -> list[float]:
    return [round(k * step_s, 6) for k in range(n_epochs)]


# --------------------------------------------------------------------------
# generation side
# --------------------------------------------------------------------------

def dump_sim_trace(outdir, *, step_s: float = 1.0, n_max: int = 30,
                   eph: dict | None = None) -> dict | None:
    """Write ``<outdir>/trace_sim.json`` from meta.json + the run's ephemeris.

    Returns the written dict (or None when the run predates traceable
    provenance, e.g. the legacy gps-sdr-sim engine). A missing/unparsable
    ephemeris only drops the per-epoch geometric series, never the dump.
    """
    outdir = pathlib.Path(outdir)
    ctx = _load_run(outdir)
    if ctx["engine"] != "native" or not ctx["svs"]:
        return None                              # not traceable through meta
    if eph is None:
        eph = _load_eph(ctx)
    rx_ecef = geometry.llh_to_ecef(float(ctx["cfg"].get("lat", 0.0)),
                                   float(ctx["cfg"].get("lon", 0.0)),
                                   float(ctx["cfg"].get("alt", 0.0)))
    atmo_f = _sim_atmo_factory(
        ctx["cfg"].get("rinex_path"),
        math.radians(float(ctx["cfg"].get("lat", 0.0))),
        math.radians(float(ctx["cfg"].get("lon", 0.0))),
        float(ctx["cfg"].get("alt", 0.0)), ctx["sow"]) \
        if ctx["cfg"].get("rinex_path") else None

    # Bound the grid by the shortest band, so rx traces can never fall off
    # the end of the file.
    dur_s = float(ctx["cfg"].get("duration_s") or 0.0)
    n_epochs = max(1, min(int(n_max), int(dur_s / step_s)) if dur_s > 0 else n_max)
    t_s = _grid(step_s, n_epochs)

    out = {
        "kind": "sim", "runid": outdir.name, "engine": ctx["engine"],
        "start_utc": ctx["cfg"].get("start_utc"), "sow0": ctx["sow"],
        "step_s": step_s, "n_epochs": n_epochs, "t_s": t_s,
        "geometry_source": "recomputed" if (eph and atmo_f) else "constants",
        "svs": {},
    }
    for sv in ctx["svs"]:
        sysc, prn = sv.get("sys"), sv.get("prn")
        if sysc not in _TRACE_SYSTEMS or prn is None:
            continue
        key = f"{sysc}{prn}"
        code_len = float(sv.get("code_len") or 0.0)
        chip_hz = float(sv.get("chip_hz") or 0.0)
        fd_code = sv.get("code_doppler_hz")
        ph0 = sv.get("code_phase_chips")
        base = {
            "sys": sysc, "prn": prn, "band": sv.get("band"),
            "if_hz": sv.get("if_hz"), "chip_hz": chip_hz,
            "code_len": code_len,
            "code_phase0_chips": ph0,
            "code_doppler_hz": fd_code,
            "carrier_doppler_hz": sv.get("carrier_doppler_hz"),
            "pr_inj_m": sv.get("pseudorange_m"),
            "gain": sv.get("gain"), "gain_db": sv.get("gain_db"),
            "fading_model": sv.get("fading_model", 0),
        }
        if ph0 is not None and fd_code is not None and code_len > 0:
            # Acquisition-frame truth. The engine advances its file code-grid
            # argument g(t) = -pr(t)*chip/C (physically correct: the chip a
            # receiver sees at t was transmitted at t - pr/C), so g drifts at
            # +code_dop ch/s; acquire_l1 reports -g mod code_len (peak lag d
            # with x[j] = local[j-d] -> phase = c*d = -g), hence the MINUS
            # sign here. Verified on run 20261106T084558776704 (G2): acq
            # phase rises at -code_dop = +0.235 ch/s from ph0.
            base["ph_syn_chips"] = [(ph0 - fd_code * t) % code_len
                                    for t in t_s]
        if eph is not None and atmo_f is not None:
            rec = _lookup_rec(eph, sysc, int(prn))
            sig = signals.SIGNALS[_SIGNAL_KEYS[sysc]] \
                if sv.get("band") in ctx["bands"] else None
            if rec is not None and sig is not None:
                gk = sv.get("glo_k")
                carrier_hz = float(sig.carrier_hz)
                if sysc == "R" and isinstance(gk, int):
                    carrier_hz += gk * 562_500.0
                svb = geometry.group_delay_bias_s(sysc, sig.band,
                                                  rec if isinstance(rec, dict)
                                                  else None)
                state = geometry.state_fn_for(rec) if isinstance(rec, dict) \
                    else rec
                pr_t, fd_t, fdc_t, at_t, el_t, az_t = [], [], [], [], [], []
                for t in t_s:
                    o = geometry.observables(state, rx_ecef, ctx["sow"] + t,
                                             signal=sig, sv_clock_bias_s=svb)
                    iono, tropo = atmo_f(sysc, math.radians(o["az_deg"]),
                                         math.radians(o["el_deg"]),
                                         carrier_hz, t)
                    pr_t.append(o["pseudorange_m"] + iono + tropo)
                    fd_t.append(o["carrier_doppler_hz"])
                    fdc_t.append(o["code_doppler_hz"])
                    at_t.append(iono + tropo)
                    el_t.append(o["el_deg"])
                    az_t.append(o["az_deg"])
                base.update({"pr_truth_m": pr_t, "fd_geo_hz": fd_t,
                             "fd_code_geo_hz": fdc_t, "atmo_m": at_t,
                             "el_deg_t": el_t, "az_deg_t": az_t})
        out["svs"][key] = base
    (outdir / "trace_sim.json").write_text(
        json.dumps(out, indent=1, default=float))
    return out


# --------------------------------------------------------------------------
# receiver side
# --------------------------------------------------------------------------

def dump_rx_trace(outdir, *, step_s: float = 1.0, n_max: int = 30,
                  eph: dict | None = None, marker_llh=None,
                  dopp_span_hz: float = 300.0, dopp_step_hz: float = 50.0,
                  nperiods: int = 2) -> dict | None:
    """Write ``<outdir>/trace_rx.json``: per-epoch acquisition + anchored
    pseudorange on the SAME grid ``dump_sim_trace`` uses.

    ``marker_llh`` (or meta config llh) anchors the prediction, exactly as
    ``receiver.fix_from_iq`` does; ``eph`` may be the caller's already
    aligned ephemeris to avoid re-parsing. Returns None for non-native runs.
    """
    outdir = pathlib.Path(outdir)
    ctx = _load_run(outdir)
    if ctx["engine"] != "native" or not ctx["svs"]:
        return None
    if eph is None:
        eph = _load_eph(ctx)
    if eph is None:
        return None
    sample_format = ctx["meta"].get("sample_format", "int8")
    mk = marker_llh
    if isinstance(mk, dict):
        mk = (mk.get("lat", 0.0), mk.get("lon", 0.0), mk.get("alt", 0.0))
    approx_llh = tuple(mk) if mk else (
        float(ctx["cfg"].get("lat", 0.0)), float(ctx["cfg"].get("lon", 0.0)),
        float(ctx["cfg"].get("alt", 0.0)))
    approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
    atmo_fn = l1_fix.default_atmo_fn(ctx["cfg"].get("rinex_path"),
                                     approx_llh, ctx["sow"])

    dur_s = float(ctx["cfg"].get("duration_s") or 0.0)
    n_epochs = max(1, min(int(n_max), int(dur_s / step_s)) if dur_s > 0 else n_max)
    t_s = _grid(step_s, n_epochs)

    band_files = {bid: (outdir / b["file"], float(b["fs"]))
                  for bid, b in ctx["bands"].items()}
    slice_cache: dict[tuple[str, int], tuple[np.ndarray, float]] = {}

    def band_slice(bid: str, k: int, npp: int, npp_total: int):
        ckey = (bid, k)
        hit = slice_cache.get(ckey)
        if hit is not None:
            return hit
        bf, fs = band_files[bid]
        if not bf.exists():
            return None
        off = int(round(t_s[k] * fs))
        iq = read_iq(bf, sample_format, max_samples=npp_total,
                     offset_samples=off)
        if len(iq) < npp:
            return None
        slice_cache[ckey] = (iq, fs)
        return slice_cache[ckey]

    out = {
        "kind": "rx", "runid": outdir.name, "engine": ctx["engine"],
        "start_utc": ctx["cfg"].get("start_utc"), "sow0": ctx["sow"],
        "step_s": step_s, "n_epochs": n_epochs, "t_s": t_s,
        "acq": {"dopp_span_hz": dopp_span_hz, "dopp_step_hz": dopp_step_hz,
                "nperiods": nperiods},
        "svs": {},
    }
    for sv in ctx["svs"]:
        sysc, prn = sv.get("sys"), sv.get("prn")
        key = f"{sysc}{prn}"
        if sysc not in _TRACE_SYSTEMS or prn is None:
            continue
        bid = sv.get("band")
        if bid not in band_files:
            continue
        rec = _lookup_rec(eph, sysc, int(prn))
        if rec is None:
            continue
        sig = signals.SIGNALS[_SIGNAL_KEYS[sysc]]
        chip_hz, code_len = float(sig.chip_rate_hz), float(sig.code_len)
        gk = sv.get("glo_k") if sysc == "R" else None
        svb = geometry.group_delay_bias_s(sysc, "L1",
                                         rec if isinstance(rec, dict) else None)
        state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec
        if_hz = float(sv.get("if_hz", 0.0))
        fd_syn = sv.get("carrier_doppler_hz")
        carrier_hz = float(sig.carrier_hz) + (
            int(gk) * 562_500.0 if sysc == "R" and gk is not None else 0.0)
        # l1_fix skips the iono for no system; the receiver-side atmo model
        # is applied uniformly here exactly like the fix path does.

        npp = int(round(band_files[bid][1] * code_len / chip_hz))
        npp_total = npp * max(1, nperiods) + 16
        # Pre-shift the slice by the known synthesized Doppler so the
        # acquisition only has to sweep a narrow window around zero.
        if fd_syn is not None:
            tt = np.arange(npp_total) / band_files[bid][1]
            # IQ carrier sits at if_hz + fd_syn -> shift DOWN by fd_syn so
            # the acquisition only sweeps +-dopp_span_hz around if_hz.
            derot = np.exp(-2j * np.pi * fd_syn * tt)
            span, step = dopp_span_hz, dopp_step_hz
        else:
            derot = None
            span, step = 5000.0, 200.0
        rows = {k: [] for k in ("ph_meas_chips", "fd_meas_hz", "metric_db",
                                "err_chips", "pred_pr_m", "meas_pr_m",
                                "el_rx_deg")}
        for k in range(n_epochs):
            got = band_slice(bid, k, npp, npp_total)
            if got is None:
                break
            iq, fs = got
            t = t_s[k]
            o = geometry.observables(state, approx_rx, ctx["sow"] + t,
                                     signal=sig, sv_clock_bias_s=svb)
            atmo_m = float(atmo_fn(math.radians(o["az_deg"]),
                                   math.radians(o["el_deg"]), carrier_hz,
                                   sysc))
            pred_pr = o["pseudorange_m"] + atmo_m
            ph_pred = (pred_pr / config.C * chip_hz) % code_len
            seg = iq[:npp_total] * (derot if derot is not None else 1.0)
            acq = acquire_l1(seg, fs, sysc, int(prn), centre_offset_hz=if_hz,
                             glo_k=(int(gk) if gk is not None else None),
                             dopp_hz=span, dopp_step_hz=step,
                             nperiods=nperiods)
            fd_meas = (fd_syn + acq["doppler_hz"]) if fd_syn is not None \
                else acq["doppler_hz"]
            rows["ph_meas_chips"].append(acq["code_phase_chips"])
            rows["fd_meas_hz"].append(fd_meas)
            rows["metric_db"].append(acq["metric_db"])
            rows["err_chips"].append(_wrap(acq["code_phase_chips"] - ph_pred,
                                           code_len))
            rows["pred_pr_m"].append(pred_pr)
            rows["meas_pr_m"].append(pred_pr
                                     + rows["err_chips"][-1] * config.C / chip_hz)
            rows["el_rx_deg"].append(o["el_deg"])
        if not rows["ph_meas_chips"]:
            continue
        out["svs"][key] = {
            "sys": sysc, "prn": prn, "band": bid, "if_hz": if_hz,
            "chip_hz": chip_hz, "code_len": code_len, **rows,
        }
    if not out["svs"]:
        return None
    (outdir / "trace_rx.json").write_text(
        json.dumps(out, indent=1, default=float))
    return out


def dump_rx_trace_dll(outdir, *, step_s: float = 1.0, n_max: int = 30,
                      eph: dict | None = None, marker_llh=None,
                      dll_bw_hz: float = 0.5, dopp_span_hz: float = 300.0,
                      dopp_step_hz: float = 50.0,
                      nperiods: int = 4, dll_mode: str = "coh") -> dict | None:
    """Write ``<outdir>/trace_dll.json``: TRACKING receiver on
    the SAME grid as ``dump_sim_trace``/``dump_rx_trace``.

    Where ``dump_rx_trace`` snapshots a fresh integer-lag acquisition every
    epoch (code phase quantized to the sample grid, sigma = chip-per-sample
    /sqrt(12) ~ 0.06 chips ~ 17 m), this dumps the state of the
    ``SVTracker`` carrier-aided code loop (dll_mode="coh": COHERENT E/L +
    Costas PLL, default; dll_mode="el": classic non-coherent EARLY/LATE
    power discriminator; dll_mode="nc": FFT power-surface peak-tracking
    DLL): its chi is continuous, so the per-epoch code phase is not
    quantized and the anchored-pseudorange error drops to the
    0.003-0.01-chip (sub-decimeter-to-few-metre) band on this IQ.
    coh mode additionally dumps the tracked carrier phase (cycles) and its
    anchored residual wrap(phi + pred_pr/lambda), which should be
    near-constant per SV (integer ambiguity + noise) on a healthy lock.

    Per SV one tracking session runs 0..t_s[-1] seeded by a narrowed
    acquisition at t=0 (same pre-shift trick and convention as
    ``dump_rx_trace``); the Doppler aiding fd_fn interpolates the
    per-epoch geometric Doppler, with the FLL absorbing any residual
    (engine clock/atmo rates). The anchored pseudorange recipe is
    replicated from ``dump_rx_trace`` exactly, so acq-vs-DLL-vs-truth can
    never disagree between the dumps. Shared per-band IQ-window caches keep
    a full multi-SV dump at one pass over the files.
    """
    from backend.analysis.tracker import SVTracker

    outdir = pathlib.Path(outdir)
    ctx = _load_run(outdir)
    if ctx["engine"] != "native" or not ctx["svs"]:
        return None
    if eph is None:
        eph = _load_eph(ctx)
    if eph is None:
        return None
    sample_format = ctx["meta"].get("sample_format", "int8")
    mk = marker_llh
    if isinstance(mk, dict):
        mk = (mk.get("lat", 0.0), mk.get("lon", 0.0), mk.get("alt", 0.0))
    approx_llh = tuple(mk) if mk else (
        float(ctx["cfg"].get("lat", 0.0)), float(ctx["cfg"].get("lon", 0.0)),
        float(ctx["cfg"].get("alt", 0.0)))
    approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
    atmo_fn = l1_fix.default_atmo_fn(ctx["cfg"].get("rinex_path"),
                                     approx_llh, ctx["sow"])

    dur_s = float(ctx["cfg"].get("duration_s") or 0.0)
    n_epochs = max(1, min(int(n_max), int(dur_s / step_s)) if dur_s > 0 else n_max)
    t_s = _grid(step_s, n_epochs)

    band_files = {bid: (outdir / b["file"], float(b["fs"]))
                  for bid, b in ctx["bands"].items()}
    win_cache: dict[str, dict] = {bid: {} for bid in band_files}

    def get_window_factory(bid: str):
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

    out = {
        "kind": "rx_dll", "runid": outdir.name, "engine": ctx["engine"],
        "start_utc": ctx["cfg"].get("start_utc"), "sow0": ctx["sow"],
        "step_s": step_s, "n_epochs": n_epochs, "t_s": t_s,
        "dll": {"bw_hz": dll_bw_hz, "seed_nperiods": nperiods,
                "dopp_span_hz": dopp_span_hz, "dopp_step_hz": dopp_step_hz,
                "mode": dll_mode},
        "svs": {},
    }
    for sv in ctx["svs"]:
        sysc, prn = sv.get("sys"), sv.get("prn")
        key = f"{sysc}{prn}"
        if sysc not in _TRACE_SYSTEMS or prn is None:
            continue
        bid = sv.get("band")
        if bid not in band_files:
            continue
        rec = _lookup_rec(eph, sysc, int(prn))
        if rec is None:
            continue
        sig = signals.SIGNALS[_SIGNAL_KEYS[sysc]]
        chip_hz, code_len = float(sig.chip_rate_hz), float(sig.code_len)
        gk = sv.get("glo_k") if sysc == "R" else None
        svb = geometry.group_delay_bias_s(sysc, "L1",
                                         rec if isinstance(rec, dict) else None)
        state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec
        if_hz = float(sv.get("if_hz", 0.0))
        fd_syn = sv.get("carrier_doppler_hz")
        carrier_hz = float(sig.carrier_hz) + (
            int(gk) * 562_500.0 if sysc == "R" and gk is not None else 0.0)

        fs = band_files[bid][1]
        npp = int(round(fs * code_len / chip_hz))
        npp_total = npp * max(1, nperiods) + 16
        # Seed acquisition on the first code periods, pre-shifted by the
        # synthesized Doppler (exact dump_rx_trace convention).
        iq0 = read_iq(band_files[bid][0], sample_format,
                      max_samples=npp_total)
        seg0 = iq0 * (np.exp(-2j * np.pi * fd_syn
                             * np.arange(len(iq0)) / fs)
                      if fd_syn is not None else 1.0)
        seed = acquire_l1(seg0, fs, sysc, int(prn), centre_offset_hz=if_hz,
                          glo_k=(int(gk) if gk is not None else None),
                          dopp_hz=(dopp_span_hz if fd_syn is not None
                                   else 5000.0),
                          dopp_step_hz=(dopp_step_hz if fd_syn is not None
                                         else 200.0),
                          nperiods=nperiods)
        if seed["metric_db"] < 10.0:             # not lockable: skip SV
            continue
        fd_seed = (fd_syn + seed["doppler_hz"]) if fd_syn is not None \
            else seed["doppler_hz"]

        # Per-epoch geometric Doppler for the aiding (FLL absorbs residual).
        fd_g = []
        for k in range(n_epochs):
            o = geometry.observables(state, approx_rx, ctx["sow"] + t_s[k],
                                     signal=sig, sv_clock_bias_s=svb)
            fd_g.append(o["carrier_doppler_hz"])
        fd_g = np.array(fd_g, float)

        trk = SVTracker(get_window_factory(bid), fs, sysc, int(prn),
                        chip_hz=chip_hz, code_len=int(code_len),
                        carrier_hz=carrier_hz, if_hz=if_hz,
                        fd0=fd_seed, chi0=seed["code_phase_chips"],
                        boc=(sig.boc is not None), mode=dll_mode,
                        dll_bw_hz=dll_bw_hz,
                        fd_fn=lambda t: float(np.interp(t, t_s, fd_g)))
        trk.run(t_end=t_s[-1] + 1e-6, log_period_s=step_s,
                dll_bw_hz=dll_bw_hz)

        rows = {k: [] for k in ("chi_chips", "fd_meas_hz", "p_abs",
                                "err_chips", "pred_pr_m", "meas_pr_m",
                                "el_rx_deg")}
        coh = dll_mode == "coh"
        if coh:
            rows["phase_cycles"] = []
            rows["phase_resid_cycles"] = []
        for k in range(n_epochs):
            m = trk.measure(t_s[k])
            if not m:
                break
            o = geometry.observables(state, approx_rx, ctx["sow"] + t_s[k],
                                     signal=sig, sv_clock_bias_s=svb)
            atmo_m = float(atmo_fn(math.radians(o["az_deg"]),
                                   math.radians(o["el_deg"]), carrier_hz,
                                   sysc))
            pred_pr = o["pseudorange_m"] + atmo_m
            ph_pred = (pred_pr / config.C * chip_hz) % code_len
            rows["chi_chips"].append(m["chi_chips"])
            rows["fd_meas_hz"].append(m["doppler_hz"])
            rows["p_abs"].append(m["p_abs"])
            rows["err_chips"].append(_wrap(m["chi_chips"] - ph_pred, code_len))
            rows["pred_pr_m"].append(pred_pr)
            rows["meas_pr_m"].append(pred_pr
                                     + rows["err_chips"][-1] * config.C / chip_hz)
            rows["el_rx_deg"].append(o["el_deg"])
            if coh:
                pc = m.get("carrier_phase_cycles")
                lam = config.C / carrier_hz
                rows["phase_cycles"].append(pc)
                rows["phase_resid_cycles"].append(
                    None if pc is None
                    else _wrap(pc + pred_pr / lam, 1.0))
        if not rows["chi_chips"]:
            continue
        out["svs"][key] = {
            "sys": sysc, "prn": prn, "band": bid, "if_hz": if_hz,
            "chip_hz": chip_hz, "code_len": code_len,
            "seed_metric_db": seed["metric_db"], **rows,
        }
    if not out["svs"]:
        return None
    (outdir / "trace_dll.json").write_text(
        json.dumps(out, indent=1, default=float))
    return out
