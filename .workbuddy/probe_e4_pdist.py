"""Real-IQ C/N0 root-cause probe (no decode, no worker).

For G1 and E4 of the 300 s run: acquire (coarse+fine, worker recipe),
coh-track 15 s, then hand-correlate 4 ms blocks at the steady state and
report the |P| distribution (Rician r, bimodality fraction), a +-1.5-chip
coherent peak scan (false-lock guard), and for E a CS25-offset sweep
(25 alignments) to test whether the engine rides CS25 on the tracked
component at all.
"""
import sys
import warnings

import numpy as np

sys.path.insert(0, ".")
warnings.filterwarnings("ignore")

import json
import datetime as dt
import pathlib

from backend import config
from backend import inspector
from backend.ephem import ephemeris
from backend.analysis.l1_acquire import acquire_l1
from backend.analysis.tracker import SVTracker
from backend.synth import _lib, signals

RUN = "20261110T084902599874"
outdir = config.OUT_DIR / RUN
meta = json.loads((outdir / "meta.json").read_text())
cfg = meta["config"]
band = meta["bands"][0]
fs = float(band["fs"])
bf = outdir / band["file"]


def case(sysc, prn, track_s=15.0, T_blk=0.004):
    sv = next(s for s in meta["provenance"]["svs"]
              if s["sys"] == sysc and int(s["prn"]) == prn)
    signame = "GPS_L1CA" if sysc == "G" else "GAL_E1"
    sig = signals.SIGNALS[signame]
    chip_hz, L = float(sig.chip_rate_hz), int(sig.code_len)
    if_hz = float(sv.get("if_hz") or 0.0)

    def rd(t0, ns):
        return inspector.read_iq(bf, meta["sample_format"], max_samples=ns,
                                 offset_samples=int(round(t0 * fs)))

    npp1 = int(round(fs * L / chip_hz))              # one code period
    nc_c, nc_f = 50, 150
    iq_c = rd(0.0, npp1 * nc_c + 16)
    tt0 = np.arange(len(iq_c)) / fs
    a1 = acquire_l1(iq_c, fs, sysc, prn, centre_offset_hz=if_hz, nperiods=nc_c)
    seg1 = iq_c * np.exp(-2j * np.pi * a1["doppler_hz"] * tt0)
    a2 = acquire_l1(seg1[:npp1 * nc_f + 16], fs, sysc, prn,
                    centre_offset_hz=if_hz, dopp_hz=300.0, dopp_step_hz=10.0,
                    nperiods=nc_f)
    fd_seed = float(a1["doppler_hz"]) + float(a2["doppler_hz"])
    chi_seed = float(a2["code_phase_chips"])

    cache = {}

    def gw(t0, ns):
        k = (int(round(t0 * fs)), ns)
        if k not in cache:
            if len(cache) > 300:
                cache.clear()
            cache[k] = rd(t0, ns)
        return cache[k]

    trk = SVTracker(gw, fs, sysc, prn, chip_hz=chip_hz, code_len=L,
                    carrier_hz=float(sig.carrier_hz), if_hz=if_hz,
                    fd0=fd_seed, chi0=chi_seed, boc=(sig.boc is not None),
                    t_coh_ms=(20 if sysc == "G" else 4), mode="coh",
                    cn0_est=True)
    trk.run(t_end=track_s, log_period_s=0.1)

    # ---- steady-state hand correlation on 4 ms blocks --------------------
    npp = int(round(T_blk * fs))                    # 4 ms block samples
    t0 = track_s - 1.0
    dseg, nsz = trk._derot_window(t0, 20 * npp / fs)   # 20 blocks = 80 ms
    drift = trk._aid_sign * trk.chip_hz * trk.fd / trk.carrier_hz
    tau_bar = 0.5 * 20 * T_blk

    def blocks(dchi):
        # chi MUST be read back to t0 via _chi_at (loop books at window-end)
        _, bp, _ = trk._block_replicas(20, npp,
                                       -(trk._chi_at(t0) + dchi) - drift * tau_bar,
                                       0.0)
        return dseg[:20 * npp].reshape(20, npp), bp

    x, bP = blocks(0.0)
    pk = (x * bP.conj()).sum(1)
    # Costas-style per-block sign chain (nav bits ride the blocks for G;
    # even E1 can straddle if engine symbol timing is block-offset)
    s, ref = np.ones(20), None
    for k in range(20):
        if ref is not None and (pk[k] * np.conj(ref)).real < 0:
            s[k] = -1.0
        ref = s[k] * pk[k]
    mag = np.abs(s * pk)

    def stats(m, tag):
        med = float(np.median(m)); mean = float(np.mean(m))
        r = float(np.mean(m ** 4) / np.mean(m ** 2) ** 2)
        frac = float(np.mean(m < 0.25 * med)) if med > 0 else 1.0
        print(f"  {tag:26s} med={med:9.3e} mean={mean:9.3e} r={r:5.3f} "
              f"frac<.25med={frac:5.2f} max/med={np.max(m) / max(med, 1e-30):6.2f}")
        return med

    print(f"[{sysc}{prn}] acq1 {a1['doppler_hz']:.1f}Hz/{a1['metric_db']:.1f}dB "
          f"acq2 {a2['doppler_hz']:.1f}Hz/{a2['metric_db']:.1f}dB  "
          f"track fd={trk.fd:+.2f} drop={trk.n_dropped}")
    m0 = stats(mag, f"{sysc}{prn} asis")

    def coherent_mean(dchi=0.0, cw=None):
        xx, bp = blocks(dchi)
        rp = bp if cw is None else (bp * cw)
        pkk = (xx * rp.conj()).sum(1)
        ss, ref = np.ones(20), None
        for k in range(20):
            if ref is not None and (pkk[k] * np.conj(ref)).real < 0:
                ss[k] = -1.0
            ref = ss[k] * pkk[k]
        return float(np.mean(np.abs(ss * pkk)))

    ds = np.arange(-1.5, 1.501, 0.1)
    curve = np.array([coherent_mean(float(d)) for d in ds])
    bi = int(np.argmax(curve))
    print(f"  peak scan best dchi={ds[bi]:+.2f} ch x{curve[bi] / max(curve[0], 1e-30):.2f}"
          "\n    curve/asis: "
          + " ".join(f"{v / max(curve[0], 1e-30):.1f}" for v in curve))

    if sysc == "E":
        cs = _lib.code(6, prn, L, 25)[1]
        print(f"  CS25 raw: {np.asarray(cs).tolist()}")
        cs = np.asarray(cs, dtype=np.float64)
        abs_i = int(round(t0 * fs)) + np.arange(20 * npp)
        per = (abs_i // npp1) % 25                    # 4 ms period counter
        bb = np.array([coherent_mean(0.0, np.roll(cs, -off)[per].reshape(20, npp))
                       for off in range(25)])
        print(f"  CS25 sweep: max/asis={bb.max() / max(bb[0], 1e-30):.2f} "
              f"argmax_off={int(np.argmax(bb))} spread(max-min)/mean="
              f"{(bb.max() - bb.min()) / max(bb.mean(), 1e-30):.2f}")


case("G", 1)
case("E", 4)
