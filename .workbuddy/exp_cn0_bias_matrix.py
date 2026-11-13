# -*- coding: utf-8 -*-
"""C/N0 estimator-bias decomposition matrix (whu60b -3.2 dB question).

3 signal groups x 2 estimators, same synthesis math as exp_clip_cn0.py
(real PRN via engine _lib.code, per-SV gains from run meta, nominal noise):

  groups:  solo      -- target SV + noise only (NO cross-correlation)
           real      -- 12 SVs, real GPS Gold codes (cross-corr present)
           rand      -- 12 SVs, random codes (isolates PRN cross-corr)

  estimators:
    N/P (whu60 audit):  1 ms non-coherent acc, gamma = peak/sideband - 1,
                        side band = correlation bins 0.8..3.0 chips from peak
    FGI CN0fromSNR:     sigP = mean|P|^2 ; noiseLevel = |N finger|^2 at
                        -2 chips (corrFingers[noiseFingerIndex=1]);
                        CN0 = 10log10(sigP / var(noiseLevel) / PDI)

Decoding:
  solo bias of an estimator     = estimator-inherent bias
  real - rand (same estimator)  = true PRN cross-correlation contribution
"""
import math
import sys

import numpy as np

sys.path.insert(0, ".")
from backend.synth import _lib  # noqa: E400

fs = 25e6
L = 1023
NPP = 25000
T_C = 0.001
CHIP_HZ = 1.023e6
CHIP_SAMP = fs / CHIP_HZ
NOISE_FINGER_BINS = round(2 * CHIP_SAMP)
PRNS = [4, 5, 9, 11, 12, 18, 20, 25, 26, 28, 29, 31]
GAINS = np.array([0.6488, 0.6853, 0.546, 0.8367, 0.6844, 0.6009, 0.8077,
                  0.9347, 0.7688, 0.8856, 0.9899, 0.8816])
SIG_C2 = 2.808e9
SIG = math.sqrt(SIG_C2 / 2.0)
SCALE = 0.25 * 32767 / math.sqrt(12)
N_MS = 1000                                    # 1 s window
N = int(fs * N_MS / 1000)

rng0 = np.random.default_rng(7)
CODES = {}
for i, prn in enumerate(PRNS):
    CODES[("real", i)] = np.asarray(_lib.code(0, prn, L, 0)[0], dtype=np.float64)
    CODES[("rand", i)] = rng0.choice(np.array([-1.0, 1.0]), size=L)

NOM = 10 * np.log10((GAINS ** 2 * SCALE ** 2) / SIG_C2 * fs)


def composite(kind, tgt=None):
    tt = np.arange(N) / fs
    rng = np.random.default_rng(11)
    comp = rng.normal(0, SIG, N) + 1j * rng.normal(0, SIG, N)
    idxs = {}
    for i in range(12):
        if kind == "solo" and i != tgt:
            continue
        idx = np.floor(tt * CHIP_HZ + i * 83.0).astype(np.int64) % L
        idxs[i] = idx
        comp = comp + GAINS[i] * SCALE * CODES[(kind if kind != "solo" else "real", i)][idx] \
               * np.exp(2j * np.pi * (400.0 + i * 250.0) * tt)
    return comp, tt, idxs


def measure_one(comp, kind, i, idx):
    tt = np.arange(N) / fs
    kindk = "real" if kind == "solo" else kind
    loc_full = CODES[(kindk, i)][idx[i]]
    ph = np.exp(-2j * np.pi * (400.0 + i * 250.0) * tt)
    acc = np.zeros(NPP)
    for b in range(N_MS):
        k0 = b * NPP
        blk = comp[k0:k0 + NPP] * ph[k0:k0 + NPP]
        LOC = np.conj(np.fft.fft(loc_full[k0:k0 + NPP]))
        acc += np.abs(np.fft.ifft(np.fft.fft(blk) * LOC)) ** 2
    lag = int(np.argmax(acc))
    rel = (np.arange(NPP) - lag) % NPP
    mask = (rel > 0.8 * CHIP_SAMP) & (rel < 3.0 * CHIP_SAMP)
    nb = (lag - NOISE_FINGER_BINS) % NPP
    p_acc, side = 0.0, 0.0
    nl = np.empty(N_MS)  # FGI noiseLevel = I_E_E + Q_E_E (amplitudes, -2 ch finger)
    for b in range(N_MS):
        k0 = b * NPP
        blk = comp[k0:k0 + NPP] * ph[k0:k0 + NPP]
        LOC = np.conj(np.fft.fft(loc_full[k0:k0 + NPP]))
        c = np.fft.ifft(np.fft.fft(blk) * LOC)
        a = np.abs(c) ** 2
        p_acc += a[lag]
        side += a[mask].mean()
        nl[b] = c[nb].real + c[nb].imag
    cn0_np = 10 * math.log10(max(p_acc / side - 1.0, 1e-9) / T_C)
    # FGI CN0fromSNR: sigP = mean|P|^2 ; noiseVariance = var(noiseLevel); PDI = 1 ms
    cn0_fgi = 10 * math.log10((p_acc / N_MS) / float(np.var(nl)) / T_C)
    return cn0_np, cn0_fgi, float(np.var(nl))


for kind in ("solo", "real", "rand"):
    if kind == "solo":
        rows = []
        for tgt in range(12):
            comp, _, idxs = composite("solo", tgt)
            rows.append(measure_one(comp, "solo", tgt, idxs))
            del comp
    else:
        comp, _, idxs = composite(kind)
        rows = [measure_one(comp, kind, i, idxs) for i in range(12)]
        del comp
    npv = np.array([r[0] for r in rows])
    fg = np.array([r[1] for r in rows])
    print(f"[{kind:5s}] N/P mean {npv.mean():6.2f}  bias {npv.mean()-NOM.mean():+.2f} dB  "
          f"(min {npv.min():.2f} max {npv.max():.2f})")
    print(f"[{kind:5s}] FGI mean {fg.mean():6.2f}  bias {fg.mean()-NOM.mean():+.2f} dB  "
          f"(min {fg.min():.2f} max {fg.max():.2f})")
print(f"nominal mean {NOM.mean():.2f} dB-Hz  (per-SV nominal {np.round(NOM,1)})")
