"""Self-check for tau-curve peak estimators on a KNOWN synthetic delay.

Signal mimics the engine: chip edges quantised to SAMPLES --
signal chip index at sample n = floor(n*cpc - d_true) mod L -- so the
code-comb/sample-comb fractional alignment is arbitrary, like a real SV.
Non-coherent 8 blocks, carrier derotated upstream (fd=0 here).

Estimators (parabola over a tau curve, then compared to d_true):
  naive : replica re-quantised with floor at tau (staircased, biased)
  bl    : BAND-LIMITED replica via exact cyclic sub-sample delay,
          FFT(g_tau) = FFT(local) * exp(+2j*pi*k*tau/npp)  (smooth in tau)
Pass criterion: |mean err| < 0.003 ch and std < 0.01.
"""
import sys, warnings
import numpy as np
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
from backend.analysis.tracker import _code_table

fs = 5e6
chip_hz = 1.023e6
L = 1023
npp = int(round(fs * L / chip_hz))
code = _code_table("G", 7, L)
rng = np.random.default_rng(7)
cpc = chip_hz / fs
PAD = 32
t = np.arange(npp) / fs

local0 = code[np.floor(t * chip_hz).astype(np.int64) % L].astype(np.float64)
LOCS = []
for p in range(PAD):
    idx = np.floor(t * chip_hz - (p / PAD) * cpc).astype(np.int64) % L
    LOCS.append(np.conj(np.fft.fft(code[idx].astype(np.float64))))
_locf = np.fft.fft(local0)
_k = np.arange(npp) / npp
LOCS_BL = [np.conj(_locf * np.exp(2j * np.pi * _k * (p / PAD)))
           for p in range(PAD)]


def peak_est(Fb, locs):
    """NC power coarse argmax, then parabola over the tau curve at that lag."""
    nper = Fb.shape[0]
    acc = np.zeros(npp)
    for j in range(nper):
        acc += np.abs(np.fft.ifft(Fb[j] * locs[0])) ** 2
    k = int(np.argmax(acc))
    Ps = np.empty(PAD)
    for p in range(PAD):
        c = np.fft.ifft(Fb * locs[p][None, :], axis=1)[:, k]
        Ps[p] = float(np.sum(np.abs(c) ** 2))
    p0 = int(np.argmax(Ps))
    a, b, cc = Ps[p0 - 1], Ps[p0], Ps[(p0 + 1) % PAD]
    den = a - 2 * b + cc
    d = 0.5 * (a - cc) / den if den else 0.0
    return (k + (p0 + d) / PAD) * cpc


print(f"{'d_true':>9} {'naive':>9} {'n_err':>8} {'bl':>9} {'bl_err':>8}")
errs_n, errs_b = [], []
for d_true in [500.000, 500.103, 500.372, 500.617, 500.845, 700.0]:
    n = np.arange(npp)[:, None] + np.arange(8)[None, :] * npp
    idx = np.floor(n * cpc - d_true).astype(np.int64) % L
    x = code[idx] * 0.05 + 0.02 * (
        rng.standard_normal(x_shape := (npp, 8))
        + 1j * rng.standard_normal((npp, 8)))
    Fb = np.fft.fft(x.T, axis=1)
    dn = peak_est(Fb, LOCS)
    db = peak_est(Fb, LOCS_BL)
    errs_n.append(dn - d_true); errs_b.append(db - d_true)
    print(f"{d_true:9.3f} {dn:9.3f} {dn - d_true:+8.4f} "
          f"{db % L:9.3f} {(db - d_true):+8.4f}")
print(f"naive: mean={np.mean(errs_n):+.4f} std={np.std(errs_n):.4f}")
print(f"bl   : mean={np.mean(errs_b):+.4f} std={np.std(errs_b):.4f}")
