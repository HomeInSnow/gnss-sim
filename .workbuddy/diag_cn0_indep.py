"""Independent audit of a gnss-sim run IQ: clipping + per-SV C/N0.

(a) saturation fraction and composite power vs nominal noise power;
(b) FFT parallel correlator using the SAME hold-sampled replica as
    backend.analysis.l1_acquire (validated) -> per-SV peak/off-peak ratio:
    gamma = Ppk/Pn - 1 = (C/N0)*Tc   (complex baseband, no 1/2 factor)
    C/N0  = gamma / T_c
Validated against a synthetic positive control (--selftest).
"""
import json
import math
import sys

import numpy as np

sys.path.insert(0, ".")
from backend.synth import _lib  # noqa: E402

fs = 25e6
L = 1023
T_C = 0.001
NPP = 25000
CHIP_HZ = 1.023e6


def surface(xc, code, fd, cd, blocks):
    """non-coherent averaged |corr|^2 surface: deramp carrier at fd, track
    code Doppler cd (replica chip position advances across the window)."""
    ph = np.exp(-1j * 2 * np.pi * fd * tt_line)
    acc = np.zeros(NPP)
    rate = CHIP_HZ + cd
    for b in blocks:
        k0 = b * NPP
        idx = np.floor((k0 + tt_line) * (rate / fs)).astype(np.int64) % L
        local = code[idx]
        LOC = np.conj(np.fft.fft(local))
        blk = xc[k0:k0 + NPP] * ph
        acc += np.abs(np.fft.ifft(np.fft.fft(blk) * LOC)) ** 2
    return acc


tt_line = np.arange(NPP) / fs


def peak_cn0(xc, code, fd0, cd0, blocks, search=True):
    best = (-1.0, 0, 0.0, None)
    fds = ([s * (fd0 + d) for s in (+1, -1) for d in np.arange(-300, 301, 20.0)]
           if search else [fd0])
    for fd in fds:
        cd = cd0 * (abs(fd) / abs(fd0)) if fd0 else cd0
        acc = surface(xc, code, fd, cd, blocks)
        pk = acc.max()
        if pk > best[0]:
            best = (pk, int(np.argmax(acc)), fd, acc)
    pk, lag, fd, acc = best
    rel = (np.arange(NPP) - lag) % NPP
    mask = (rel > 0.8 * NPP / L) & (rel < 3.0 * NPP / L)
    p_n = float(acc[mask].mean())
    gamma = pk / p_n - 1.0
    return gamma, gamma / T_C, lag, fd  # cn0 (linear) = gamma/Tc


def selftest():
    rng = np.random.default_rng(1)
    code = np.asarray(_lib.code(0, 29, L, 0)[0], dtype=np.float64)
    # target C/N0 = 44.86 dB-Hz with complex noise power sigma_c^2 = 1:
    # C/N0 = A^2/(sigma_c^2/fs)  ->  A^2 = 10^(cno/10) * sigma_c^2/fs
    cno_t = 44.86
    amp = math.sqrt(10 ** (cno_t / 10) / fs)
    tt_abs = np.arange(NPP * 50) / fs
    x = (rng.normal(0, math.sqrt(0.5), NPP * 50)
         + 1j * rng.normal(0, math.sqrt(0.5), NPP * 50))
    idx = np.floor(tt_abs * CHIP_HZ).astype(np.int64) % L
    x = x + amp * code[idx] * np.exp(2j * np.pi * 1000 * tt_abs)
    blocks = np.arange(50)
    gamma, _, lag, fd = peak_cn0(x, code, 1000.0, 0.0, blocks)
    print(f"SELFTEST: gamma={gamma:.1f} (expect {10**(cno_t/10)*T_C:.1f})  "
          f"C/N0={10*math.log10(gamma/T_C):.2f} (expect {cno_t})  fd={fd}")


if "--selftest" in sys.argv:
    selftest()
    sys.exit(0)

RUN = sys.argv[1] if len(sys.argv) > 1 else "out/20261112T090748645439"
WIN_START = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
WIN_LEN = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
K_BLOCKS = int(sys.argv[4]) if len(sys.argv) > 4 else 200

meta = json.load(open(f"{RUN}/meta.json"))
fs = meta["sample_rate"]
svs = meta["provenance"]["svs"]
imp = meta["provenance"]["impairments"]["L1"]
noise_nominal = imp["noise_power"]

raw = np.fromfile(f"{RUN}/gpssim.bin", dtype=np.int16,
                  count=int(2 * int(fs) * WIN_LEN),
                  offset=int(2 * int(fs) * WIN_START))
xr = raw.reshape(-1, 2)
n = xr.shape[0]
frac_sat_i = float(np.mean(np.abs(xr[:, 0].astype(np.int64)) >= 32767))
frac_sat_q = float(np.mean(np.abs(xr[:, 1].astype(np.int64)) >= 32767))
xf = xr.astype(np.float64)
xc = xf[:, 0] + 1j * xf[:, 1]
p_tot = float(np.mean(xf[:, 0] ** 2 + xf[:, 1] ** 2))
sig_p_nom = noise_nominal * 10.0 ** (imp["measured_snr_db"] / 10.0)
print(f"window {WIN_START}..{WIN_START+WIN_LEN}s n={n}")
print(f"sat fraction I={frac_sat_i:.4f} Q={frac_sat_q:.4f}")
print(f"composite power      = {p_tot:.4e}")
print(f"nominal noise        = {noise_nominal:.4e} (+sig {sig_p_nom:.3e}"
      f" = {noise_nominal + sig_p_nom:.4e})")
print(f"power deficit vs nominal = {10*math.log10(p_tot/(noise_nominal+sig_p_nom)):+.2f} dB")

tt_abs0 = np.arange(n) / fs
step = max(1, (n // NPP) // K_BLOCKS)
blocks = np.arange(0, n // NPP, step)[:K_BLOCKS]
print(f"blocks per SV: {len(blocks)}")

rows = []
for sv in svs:
    prn = sv["prn"]
    code = np.asarray(_lib.code(0, prn, L, 0)[0], dtype=np.float64)
    gamma, _, lag, fd = peak_cn0(xc, code, sv["carrier_doppler_hz"],
                                 sv["code_doppler_hz"], blocks)
    cno = 10 * math.log10(max(gamma, 1e-9) / T_C)
    rows.append((prn, sv["gain_db"], sv["el_deg"], gamma, cno, lag * L / NPP, fd))

print(f"{'PRN':>4} {'gain_db':>8} {'el':>6} {'pk/n-1':>9} {'C/N0':>7} "
      f"{'lag_ch':>8} {'fd':>9}")
for r in rows:
    print(f"{r[0]:>4} {r[1]:>8.2f} {r[2]:>6.1f} {r[3]:>9.1f} {r[4]:>7.2f} "
          f"{r[5]:>8.2f} {r[6]:>9.1f}")
c2 = np.array([r[4] for r in rows])
print(f"mean C/N0 = {c2.mean():.2f}   median = {np.median(c2):.2f}")
print("nominal injected C/N0 = "
      f"{imp['measured_snr_db'] + 10*math.log10(fs) - 10*math.log10(len(svs)):.2f}")
