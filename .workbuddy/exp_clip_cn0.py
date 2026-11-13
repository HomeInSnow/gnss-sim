"""Synthetic experiment: net effect of int16 saturation clipping on the
correlator-domain C/N0 (independent N/P estimator, same math as the
whu60 audit: gamma = Ppk/Pn - 1 = (C/N0)*Tc).

Synthesizes a 12-SV C/A constellation with the run's per-SV gains and the
nominal noise (sigma per dim = sqrt(2.808e9/2)) at int16 scale, then
measures C/N0 (a) unclipped float, (b) after int16 saturation clip.
"""
import math
import sys

import numpy as np

sys.path.insert(0, ".")
from backend.synth import _lib  # noqa: E402

fs = 25e6
L = 1023
NPP = 25000
T_C = 0.001
CHIP_HZ = 1.023e6

# per-SV complex power: P_i = 3.437e6 * g_i^2 / mean(g^2) * ... use gains
GAINS = np.array([0.6488, 0.6853, 0.546, 0.8367, 0.6844, 0.6009, 0.8077,
                  0.9347, 0.7688, 0.8856, 0.9899, 0.8816])
SIG_C2 = 2.808e9                      # nominal complex noise power
SIG = math.sqrt(SIG_C2 / 2.0)         # per-dim sigma
SCALE = 0.25 * 32767 / math.sqrt(12)   # mixer composite scale

rng = np.random.default_rng(7)
WIN = 2.0
n = int(fs * WIN)
tt = np.arange(n) / fs

# composite signal at int16 scale (unit-amplitude BPSK × gain × scale)
sigs = []
for i, g in enumerate(GAINS):
    code = np.asarray(_lib.code(0, [4, 5, 9, 11, 12, 18, 20, 25, 26, 28,
                                     29, 31][i], L, 0)[0], dtype=np.float64)
    idx = np.floor(tt * CHIP_HZ + i * 83.0).astype(np.int64) % L
    c = code[idx]
    fd = 400.0 + i * 250.0
    s = g * c * np.exp(2j * np.pi * fd * tt)
    sigs.append((fd, s * g * SCALE * SCALE / g if False else s * SCALE))

def measure(xc, tags):
    """per-SV C/N0 via N/P for the given IQ array (list of complex128)."""
    out = []
    for i, (fd, s) in enumerate(sigs):
        code = np.asarray(_lib.code(0, [4, 5, 9, 11, 12, 18, 20, 25, 26,
                                         28, 29, 31][i], L, 0)[0],
                          dtype=np.float64)
        acc = np.zeros(NPP)
        ph = np.exp(-2j * np.pi * fd * tt)
        nb = int(n // NPP)
        for b in range(nb):
            k0 = b * NPP
            idx = (np.floor(tt[k0:k0 + NPP] * CHIP_HZ + i * 83.0)
                   .astype(np.int64) % L)
            local = code[idx]
            LOC = np.conj(np.fft.fft(local))
            blk = xc[k0:k0 + NPP] * ph[k0:k0 + NPP]
            acc += np.abs(np.fft.ifft(np.fft.fft(blk) * LOC)) ** 2
        lag = int(np.argmax(acc))
        rel = (np.arange(NPP) - lag) % NPP
        mask = (rel > 0.8 * NPP / L) & (rel < 3.0 * NPP / L)
        p_n = acc[mask].mean()
        gamma = acc.max() / p_n - 1.0
        out.append(10 * math.log10(max(gamma, 1e-9) / T_C))
    return np.array(out)

noise = ((rng.normal(0, SIG, n) + 1j * rng.normal(0, SIG, n)))
comp = noise.copy()
for fd, s in sigs:
    comp = comp + s

print("nominal composite C/N0 mean = "
      f"{10*math.log10((GAINS**2*SCALE**2).mean()*fs/SIG_C2):.2f} dB-Hz "
      "(linear-mean convention)")

m_lin = measure(comp, "linear")
print(f"[A] unclipped float : mean {m_lin.mean():.2f}  "
      f"min {m_lin.min():.2f} max {m_lin.max():.2f}")

print(f"sat fraction per dim = "
      f"{float(np.mean(np.abs(comp.real) >= 32767)):.3f}")
qc = np.clip(np.round(comp.real), -32767, 32767) \
    + 1j * np.clip(np.round(comp.imag), -32767, 32767)
m_clip = measure(qc, "clip")
print(f"[B] int16 clipped   : mean {m_clip.mean():.2f}  "
      f"min {m_clip.min():.2f} max {m_clip.max():.2f}")
print(f"clip effect = {m_clip.mean()-m_lin.mean():+.2f} dB")
