"""Synthetic-signal unit test for the tracking loops (no engine involved).

GPS-like: C/A 1.023 Mcps, 5 Msps, 20 ms nav bits (one flip inside the
window history to exercise straddle rejection), constant Doppler, AWGN.
Seeds the tracker NEAR truth and checks chi/fd converge.
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
chip_hz, code_len = 1.023e6, 1023
carrier_hz, if_hz = 1575.42e6, 0.0
fd_true, tau_true = -1000.0, 512.37          # Hz, chips (acq frame)
dur = 2.0
n = int(fs * dur)
t = np.arange(n) / fs

code = _lib.code(0, 5, code_len, 0)[0].astype(np.float64)

# continuous-time signal built in chunks on the fine 1/8-sample grid,
# then decimated to the fs grid (fractional chip boundaries stay honest)
M = 8
chi_sig = tau_true % code_len
fd_code = fd_true * chip_hz / carrier_hz     # code Doppler [chips/s]
chunks = []
step = int(0.25 * fs) * M                    # 0.25 s per chunk
for i0 in range(0, n * M, step):
    i1 = min(i0 + step, n * M)
    tf = np.arange(i0, i1) / (fs * M)
    idx = np.mod(np.floor(chi_sig + (chip_hz + fd_code) * tf),
                 code_len).astype(np.int64)
    data = np.where(np.floor(tf / 0.020) == 50, -1.0, 1.0)
    wave = code[idx] * data
    chunks.append(wave * np.exp(1j * 2 * np.pi * (if_hz + fd_true) * tf))
iq = np.concatenate(chunks)[::M] \
    + rng.normal(0, 0.01, n) + 1j * rng.normal(0, 0.01, n)

cache = {}


def get_window(t0, ns):
    n0 = int(round(t0 * fs))
    key = (n0, ns)
    if key not in cache:
        if len(cache) > 600:
            cache.clear()
        cache[key] = iq[n0:n0 + ns]
    return cache[key]


# seeds: acquisition-level errors (fd +-200 Hz quantization, chi 1-sample grid)
fd0 = round(fd_true / 200) * 200
tau0 = int(tau_true * fs / chip_hz) * chip_hz / fs + 0.02

# --- sanity: _corr peak should sit at tau_true (acq-frame identity) ---------
probe = SVTracker(get_window, fs, "G", 5, chip_hz=chip_hz, code_len=code_len,
                  carrier_hz=carrier_hz, if_hz=if_hz, fd0=fd_true, chi0=tau_true)
dseg, nn = probe._derot_window(0.0, 0.001)
sweep = np.arange(-1.5, 1.5, 0.02)
prof = []
for dchi in sweep:
    probe.chi = (tau_true + dchi) % code_len
    prof.append(abs(SVTracker._corr(probe, dseg, nn, 0.001, 0.0, 0.0)))
prof = np.array(prof)
pk = sweep[int(np.argmax(prof))]
print(f"_corr peak at tau_true{pk:+.3f} (want ~0), "
      f"|c|pk/|c|@1.5 = {prof.max() / max(prof[-1], 1e-12):.1f}")

tr = SVTracker(get_window, fs, "G", 5, chip_hz=chip_hz, code_len=code_len,
               carrier_hz=carrier_hz, if_hz=if_hz, fd0=fd0, chi0=tau0,
               nc=False)
tr.run(t_end=dur - 0.05, log_period_s=0.2)

errs = []
for k, tsec in enumerate(tr.t_log):
    ph_t = tau_true + (fd_true * chip_hz / carrier_hz) * tsec   # advances
    e = (ph_t - tr.chi_log[k] + code_len / 2) % code_len - code_len / 2
    errs.append((tsec, e, tr.fd_log[k]))
for tsec, e, fd in errs:
    print(f"t={tsec:5.2f}  err={e:+9.5f} ch   fd={fd:9.2f}")
tail = np.array([e for _, e, _ in errs[5:]])
print("PLL fd end:", errs[-1][2], "(true", fd_true, ")")
print("dll_drop", tr.n_dropped, "pll_skip", tr.n_pll_skipped, "sign", tr._k_sign)
print(f"chipRMS(t>1.0) = {float(np.sqrt(np.mean(tail[len(tail)//2:] ** 2))):.6f}")

# --- NC mode: FFT-lag correlator lives in the ACQUISITION frame, where the
# reported phase is -grid mod L. Seed and truth must mirror that frame.
tr2 = SVTracker(get_window, fs, "G", 5, chip_hz=chip_hz, code_len=code_len,
                carrier_hz=carrier_hz, if_hz=if_hz, fd0=fd0,
                chi0=(-tau0) % code_len, nc=True)
tr2.run(t_end=dur - 0.05, log_period_s=0.2)
errs2 = []
for k, tsec in enumerate(tr2.t_log):
    ph_t = (-tau_true - (fd_true * chip_hz / carrier_hz) * tsec) % code_len
    e = (ph_t - tr2.chi_log[k] + code_len / 2) % code_len - code_len / 2
    errs2.append((tsec, e, tr2.fd_log[k]))
tail2 = np.array([e for _, e, _ in errs2[5:]])
print(f"NC chipRMS(t>1.0) = {float(np.sqrt(np.mean(tail2[len(tail2)//2:] ** 2))):.6f}"
      f"  fd end {errs2[-1][2]:.1f} (true {fd_true})  drop {tr2.n_dropped}")
