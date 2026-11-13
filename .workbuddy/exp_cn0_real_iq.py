# -*- coding: utf-8 -*-
"""Run N/P and FGI CN0fromSNR replicas on the REAL whu60b IQ (first 5 s).

Same estimator math as exp_cn0_bias_matrix.py, applied to the actual int16
IQ file.  Per-SV Doppler seed from the builtin tracking json (fd_meas_hz),
code phase from FFT parallel-code-phase peak, Doppler refined by a +-150 Hz
grid (0.25 s non-coherent).  Outputs per-SV readings of both estimators.

N/P here doubles as an estimator-external truth reference:
  gamma = Ppk/Pside - 1 uses the signal-free correlation sidelobe region as
  the N0 proxy, so it measures C/N0 at the correlator output directly.
"""
import json
import math
import sys

import numpy as np

sys.path.insert(0, ".")
from backend.synth import _lib  # noqa: E402

RUN = "20261113T033315803665"
FREQ = 25e6
L = 1023
NPP = 25000
T_C = 0.001
CHIP_HZ = 1.023e6
CHIP_SAMP = FREQ / CHIP_HZ
CAR = 1.57542e9
NOISE_FINGER_BINS = round(2 * CHIP_SAMP)
PRNS = [4, 5, 9, 11, 12, 18, 20, 25, 26, 28, 29, 31]
SEC = 5.0
N = int(FREQ * SEC)

raw = np.fromfile(f"out/{RUN}/gpssim.bin", dtype=np.int16, count=2 * N)
iq = raw[0::2].astype(np.float64) + 1j * raw[1::2].astype(np.float64)
del raw
print(f"loaded {N/FREQ:.0f} s int16 IQ, mean |x|^2 = {np.mean(np.abs(iq)**2):.3e}")

trk = json.load(open(f".workbuddy/trk_{RUN}_coh.json"))
per_sv = trk["tracked"]["per_sv"]


def corr_acc(fd, rate, b0, nb_blk):
    """non-coherent |corr|^2 accumulation over nb_blk 1-ms blocks."""
    acc = np.zeros(NPP)
    for b in range(nb_blk):
        k0 = (b0 + b) * NPP
        t = (k0 + np.arange(NPP)) / FREQ
        idx = np.floor(t * rate).astype(np.int64) % L
        c = code[idx]
        blk = iq[k0:k0 + NPP] * np.exp(-2j * np.pi * fd * t)
        acc += np.abs(np.fft.ifft(np.fft.fft(blk) * np.conj(np.fft.fft(c)))
                      ) ** 2
    return acc


print(f"{'SV':4s} {'fd_seed':>9s} {'lag':>6s} {'NP':>7s} {'FGI':>7s} {'pk/sd':>8s}")
npv, fg = [], []
for prn in PRNS:
    key = f"G{prn}"
    fd = float(per_sv[key]["fd_meas_hz"])
    code = np.asarray(_lib.code(0, prn, L, 0)[0], dtype=np.float64)
    rate = CHIP_HZ * (1.0 + fd / CAR)
    # pass A: code-phase lag search, 0.5 s
    acc = corr_acc(fd, rate, 0, 500)
    lag = int(np.argmax(acc))
    pk_ratio = acc[lag] / np.median(acc)
    # pass B: Doppler refinement +-150 Hz, 0.25 s, lag fixed
    best_fd, best_s = fd, -1.0
    for dd in np.arange(-150.0, 150.1, 10.0):
        s = 0.0
        for b in range(250):
            k0 = b * NPP
            t = (k0 + np.arange(NPP)) / FREQ
            idx = np.floor(t * rate).astype(np.int64) % L
            blk = iq[k0:k0 + NPP] * np.exp(-2j * np.pi * (fd + dd) * t)
            c = code[idx]
            a = np.fft.ifft(np.fft.fft(blk) * np.conj(np.fft.fft(c)))
            s += abs(a[lag]) ** 2
        if s > best_s:
            best_s, best_fd = s, fd + dd
    # measurement pass, full SEC window
    fd = best_fd
    rel = (np.arange(NPP) - lag) % NPP
    mask = (rel > 0.8 * CHIP_SAMP) & (rel < 3.0 * CHIP_SAMP)
    nb = (lag - NOISE_FINGER_BINS) % NPP
    p_acc, side = 0.0, 0.0
    n_blk = int(N // NPP)
    nl = np.empty(n_blk)
    for b in range(n_blk):
        k0 = b * NPP
        t = (k0 + np.arange(NPP)) / FREQ
        idx = np.floor(t * rate).astype(np.int64) % L
        blk = iq[k0:k0 + NPP] * np.exp(-2j * np.pi * fd * t)
        c = code[idx]
        cc = np.fft.ifft(np.fft.fft(blk) * np.conj(np.fft.fft(c)))
        a = np.abs(cc) ** 2
        p_acc += a[lag]
        side += a[mask].mean()
        nl[b] = cc[nb].real + cc[nb].imag
    p_mean = p_acc / n_blk
    side_mean = side / n_blk
    cn0_np = 10 * math.log10(max(p_mean / side_mean - 1.0, 1e-9) / T_C)
    cn0_fgi = 10 * math.log10(p_mean / float(np.var(nl)) / T_C)
    npv.append(cn0_np)
    fg.append(cn0_fgi)
    print(f"G{prn:<3d} {best_fd:9.1f} {lag:6d} {cn0_np:7.2f} {cn0_fgi:7.2f} "
          f"{pk_ratio:8.1f}")

npv = np.array(npv)
fg = np.array(fg)
print(f"\nN/P  mean {npv.mean():6.2f}  min {npv.min():.2f}  max {npv.max():.2f}")
print(f"FGI  mean {fg.mean():6.2f}  min {fg.min():.2f}  max {fg.max():.2f}")
print(f"FGI - N/P  mean {np.mean(fg-npv):+.2f} dB")
