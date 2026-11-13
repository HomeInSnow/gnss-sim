# -*- coding: utf-8 -*-
"""Confirm mechanism of FGI CN0fromSNR bias: 20 ms coherent block +
50 bps navigation bit sign flips randomize the target's -2 chip
autocorrelation leak -> inflates noiseVariance.

Controlled pairs on identical 12-SV real-Gold synthesis:
  bits=0/1   : 50 bps data modulation on all SVs (own bits)
  FGI replica uses 20 ms coherent blocks (blockSize=500000, PDI=0.02),
  exactly as trackingMode '20msTracking' stores in the whu60b state
  (blockSize 500000, PDIcode 0.02).

Expected: bits=0 FGI bias ~= matrix real group (~-0.9);
          bits=1 adds per-SV extra bias proportional to |R(-2ch)|^2.
Also prints measured per-SV var(nl) to compare with state-mat spreads
(min 2.10e6, G28 4.08e6 -> 2.8 dB spread).
"""
import math
import sys

import numpy as np

sys.path.insert(0, ".")
from backend.synth import _lib  # noqa: E402

fs = 25e6
L = 1023
NPP = 25000
CHIP_HZ = 1.023e6
CHIP_SAMP = fs / CHIP_HZ
PRNS = [4, 5, 9, 11, 12, 18, 20, 25, 26, 28, 29, 31]
GAINS = np.array([0.6488, 0.6853, 0.546, 0.8367, 0.6844, 0.6009, 0.8077,
                  0.9347, 0.7688, 0.8856, 0.9899, 0.8816])
SIG_C2 = 2.808e9
SIG = math.sqrt(SIG_C2 / 2.0)
SCALE = 0.25 * 32767 / math.sqrt(12)
NOM = 10 * np.log10((GAINS ** 2 * SCALE ** 2) / SIG_C2 * fs)
BLK20 = 500000          # 20 ms
PDI = 0.02
NF20 = round(2 * CHIP_SAMP * 20)  # -2 chips in 20ms-block samples (fractional ok via floor)
N_S = int(2 * fs)
rng0 = np.random.default_rng(7)
CODES = {prn: np.asarray(_lib.code(0, prn, L, 0)[0], dtype=np.float64)
         for prn in PRNS}

tt = np.arange(N_S) / fs


def composite(with_bits):
    rng = np.random.default_rng(11)
    comp = rng.normal(0, SIG, N_S) + 1j * rng.normal(0, SIG, N_S)
    for i, prn in enumerate(PRNS):
        idx = np.floor(tt * CHIP_HZ + i * 83.0).astype(np.int64) % L
        c = CODES[prn][idx]
        if with_bits:
            rngb = np.random.default_rng(1000 + prn)
            bits = rngb.choice(np.array([-1.0, 1.0]), size=N_S // BLK20)
            bt = np.repeat(bits, BLK20)
            bt = np.resize(bt, N_S)
            c = c * bt
        comp = comp + GAINS[i] * SCALE * c \
            * np.exp(2j * np.pi * (400.0 + i * 250.0) * tt)
    return comp


def fgi20(comp, i):
    """FGI replica: 20 ms coherent blocks, P at loop peak lag, noise at -2ch."""
    prn = PRNS[i]
    code = CODES[prn]
    fd = 400.0 + i * 250.0
    ph = np.exp(-2j * np.pi * fd * tt)
    nb = int(round((i * 83.0 - 2.0) * CHIP_SAMP)) % L  # chip index offset; see note
    # correlation via FFT on 20 ms blocks using local code at same chip timeline
    nbl = N_S // BLK20
    p_acc = 0.0
    nl = np.empty(nbl)
    peaks = []
    for b in range(nbl):
        k0 = b * BLK20
        t = tt[k0:k0 + BLK20]
        idx = np.floor(t * CHIP_HZ + i * 83.0).astype(np.int64) % L
        loc = code[idx]
        blk = comp[k0:k0 + BLK20] * ph[k0:k0 + BLK20]
        a = np.fft.ifft(np.fft.fft(blk) * np.conj(np.fft.fft(loc)))
        peaks.append(a)
    ap = np.mean(np.abs(np.array(peaks)) ** 2, axis=0)
    lag = int(np.argmax(ap))
    nb_lag = (lag - round(2 * CHIP_SAMP)) % BLK20
    for b in range(nbl):
        a = peaks[b]
        p_acc += abs(a[lag]) ** 2
        c = a[nb_lag]
        nl[b] = c.real + c.imag
    sigP = p_acc / nbl
    return 10 * math.log10(sigP / float(np.var(nl)) / PDI), float(np.var(nl))


comp0 = composite(False)
comp1 = composite(True)
print(f"{'SV':4s} {'NOM':>6s} {'FGI_bits0':>9s} {'FGI_bits1':>9s} {'var0':>10s} {'var1':>10s} {'gap1-0':>7s}")
b0l, b1l = [], []
for i, prn in enumerate(PRNS):
    c0, v0 = fgi20(comp0, i)
    c1, v1 = fgi20(comp1, i)
    b0l.append(c0 - NOM[i])
    b1l.append(c1 - NOM[i])
    print(f"G{prn:<3d} {NOM[i]:6.2f} {c0:9.2f} {c1:9.2f} {v0:10.3e} {v1:10.3e} {c1-c0:+7.2f}")
print(f"mean bias bits0 {np.mean(b0l):+.2f} dB   bits1 {np.mean(b1l):+.2f} dB")
