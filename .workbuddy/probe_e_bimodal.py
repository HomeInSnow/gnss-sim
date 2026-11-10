"""E-side C/N0 probe: is the CS25-modulated E1-C pilot riding on the E1-B
data component (engine OS, half power each) destroying the moment estimator
via per-block destructive cancellation?

Three cases, same tracker recipe (coh + cn0_est), target C/N0 48 dB-Hz
(estimator calibration: it reports 10*log10(y/T), y per-block Rician SNR):
  G      : GPS-like control (validates the estimator itself).
  E_b    : E1-B only      (half power -> expect 48-3 = 45)
  E_os   : E1-B + E1-C*CS25 same power (OS structure). If bimodal
           cancellation is real, the reported cn0 collapses far below 45.
Also dumps the pre-keep per-block |P| histogram for the steady state.
"""
import sys
import warnings

import numpy as np

sys.path.insert(0, ".")
warnings.filterwarnings("ignore")

from backend.synth import _lib                              # noqa: E402
from backend.analysis.tracker import SVTracker              # noqa: E402

rng = np.random.default_rng(7)
fs = 5e6
carrier_hz, if_hz = 1575.42e6, 0.0
CN0_TGT = 48.0                                               # dB-Hz, report frame
A = 1.0                                                      # component amplitude base


def wave_boc(code, tf, chip_hz, code_len, fd_code, chi_sig, data, sub=1):
    """BOC(1,1) waveform on the 1/8-sample fine grid, same floor-mh
    convention as SVTracker._block_replicas (sub multiplies ±1 per period)."""
    p = chi_sig + (chip_hz + fd_code) * tf
    mh = np.floor(2.0 * p).astype(np.int64)
    return code[np.mod(mh >> 1, code_len)] * np.where(mh & 1, -1.0, 1.0) * data


def run_case(name, sysc, chip_hz, code_len, t_coh_ms, bits_s,
             code_sys, prn, add_pilot, fd_true, dur=3.0):
    tau_true, fd0 = 300.17, -800.0
    fd_code = fd_true * chip_hz / carrier_hz
    prim = _lib.code(code_sys, prn, code_len, 0)[0].astype(np.float64)
    if add_pilot:
        cs25 = _lib.code(6, prn, code_len, 25)[1].astype(np.float64)
    M = 8
    chunks = []
    n = int(fs * dur)
    step = int(0.25 * fs) * M
    for i0 in range(0, n * M, step):
        i1 = min(i0 + step, n * M)
        tf = np.arange(i0, i1) / (fs * M)
        data = np.where(np.floor(tf * bits_s) % 2 == 1, -1.0, 1.0)
        w = wave_boc(prim, tf, chip_hz, code_len, fd_code, tau_true, data) * A
        if add_pilot:
            per = np.floor(tf * (chip_hz / code_len)).astype(np.int64)
            pilot = wave_boc(prim, tf, chip_hz, code_len, fd_code, tau_true,
                             cs25[np.mod(per, 25)]) * A
            w = (w + pilot) / np.sqrt(2.0)                   # OS: half power each
        chunks.append(w * np.exp(1j * 2 * np.pi * (if_hz + fd_true) * tf))
    sig = np.concatenate(chunks)[::M]
    # noise: report-frame y = (a_eff^2 * npp) / (2 sig^2) with npp=T*fs,
    # y = 10^(cn0/10) * T  (for the single-component amplitude a_eff=A)
    T = t_coh_ms * 1e-3
    y_tgt = 10.0 ** (CN0_TGT / 10.0) * T
    a_eff = A if not add_pilot else A / np.sqrt(2.0)         # E1-B tone present
    sig2 = (a_eff ** 2) * (T * fs) / (2.0 * y_tgt)
    iq = sig + rng.normal(0, np.sqrt(sig2), n) + 1j * rng.normal(0, np.sqrt(sig2), n)
    cache = {}

    def get_window(t0, ns):
        n0 = int(round(t0 * fs))
        key = (n0, ns)
        if key not in cache:
            if len(cache) > 600:
                cache.clear()
            cache[key] = iq[n0:n0 + ns]
        return cache[key]

    trk = SVTracker(get_window, fs, sysc, prn, chip_hz=chip_hz,
                    code_len=code_len, carrier_hz=carrier_hz, if_hz=if_hz,
                    fd0=fd0, chi0=tau_true, boc=(sysc == "E"),
                    t_coh_ms=t_coh_ms, mode="coh", cn0_est=True)
    trk.run(t_end=dur - 0.1, log_period_s=0.1)
    rep = [trk.cn0_dbhz(s) for s in (1, 2)]
    vals = [r for r in rep if r is not None]
    # steady-state per-block |P| (pre-keep) at t=2.0
    npp = int(round(trk._npp))
    trk2 = trk
    nb_blk = int(round(1.0 / (npp / fs)))               # blocks in one second
    dseg, nsz = trk2._derot_window(2.0, nb_blk * npp / fs)
    drift = trk2._aid_sign * trk2.chip_hz * trk2.fd / trk2.carrier_hz
    tau_bar = 0.5 * nb_blk * (npp / fs)
    bE, bP, bL = trk2._block_replicas(nb_blk, npp, -trk2.chi - drift * tau_bar,
                                      0.5 * trk2.ell)
    x = dseg[:nb_blk * npp].reshape(nb_blk, npp)
    mag = np.abs((x * bP).sum(1))
    med = float(np.median(mag))
    lo = float(np.sum(mag < 0.25 * med)) / nb_blk
    # hand-check the moment estimator on this mag sample
    m2 = float(np.mean(mag ** 2)); m4 = float(np.mean(mag ** 4))
    r = m4 / (m2 * m2)
    if 1.0 < r < 2.0:
        s = np.sqrt(2.0 - r); y_m = (s * s + s) / (r - 1.0)
        y_man = f"{10 * np.log10(y_m / (npp / fs)):.2f}"
    else:
        y_man = f"r={r:.3f}oos"
    print(f"{name:8s} cn0_report={np.mean(vals) if vals else float('nan'):6.2f} "
          f"[hand {y_man}] "
          f"(want {CN0_TGT - (0 if sysc == 'G' else 3):.0f})  "
          f"fd_end={trk.fd_log[-1]:8.1f}  drop={trk.n_dropped} "
          f"frac|P|<0.25med={lo:5.2f} med={med:.3e}")


run_case("G", "G", 1.023e6, 1023, 20, 50, 0, 5, False, fd_true=-1000.0)
run_case("E_b", "E", 1.023e6, 4092, 4, 250, 5, 4, False, fd_true=-800.0)
run_case("E_os", "E", 1.023e6, 4092, 4, 250, 5, 4, True, fd_true=-800.0)
