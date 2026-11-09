"""Decisive probe: is the per-SV DLL bias the parabola-on-integer-lag S-curve?

For one SV at several epochs, build the non-coherent FFT power surface
P(lag) EXACTLY like acquire_l1/tracker (ifft(fft(block*rot)*conj(fft(local)))).
Compare three peak estimators against the pr_truth acquisition-frame lag:
  int3   -- tracker's current integer-lag 3-point parabola
  fine   -- same surface evaluated on a pad-times zero-padded lag grid
            (sinc-interpolated matched filter) + parabola
Expectation if the hypothesis holds: int3 shows the per-SV constant bias
seen in trace_dll, fine tracks truth to a few thousandths of a chip.

Usage: python probe_peakbias.py <runid> <svkey> [n_epochs]
"""
import json, pathlib, sys, warnings
import numpy as np
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
from backend import inspector, config
from backend.synth.signals import SIGNALS
from backend.synth._lib import code as _codegen
from backend.synth.engine import _glo_g1_code

runid, svkey = sys.argv[1], sys.argv[2]
n_ep = int(sys.argv[3]) if len(sys.argv) > 3 else 3
PAD = 16
od = pathlib.Path("out") / runid
sim = json.loads((od / "trace_sim.json").read_text())
meta = json.loads((od / "meta.json").read_text())
sv = sim["svs"][svkey]
band = next(b for b in meta["bands"] if b["id"] == sv["band"])
bf, fs, fmt = od / band["file"], float(band["fs"]), meta["sample_format"]
chip_hz, code_len = float(sv["chip_hz"]), int(sv["code_len"])
sysc, prn, if_hz = sv["sys"], int(sv["prn"]), float(sv["if_hz"])
sig = SIGNALS[{"G": "GPS_L1CA", "J": "QZSS_L1CA", "S": "SBAS_L1",
               "E": "GAL_E1", "C": "BDS_B1I", "R": "GLO_G1"}[sysc]]
fd_syn = float(sv.get("carrier_doppler_hz") or 0.0)
npp = int(round(fs * code_len / chip_hz))

# ---- local replica, exact acquire_l1 convention ------------------------
_ENUM = {"G": 0, "J": 1, "S": 2, "C": 3, "E": 6}
if sysc == "R":
    code = _glo_g1_code().astype(np.float64)
else:
    sec_len = 25 if sysc == "E" else 0
    code = _codegen(_ENUM[sysc], prn, code_len, sec_len)[0].astype(np.float64)
t = np.arange(npp) / fs
chip_phase = t * chip_hz
idx = np.floor(chip_phase).astype(int) % code_len
local = code[idx].astype(np.float64)
if sysc == "E":
    sub = np.where(np.floor(2.0 * chip_phase).astype(np.int64) & 1, -1.0, 1.0)
    local = local * sub
L = npp * PAD
LOC = np.conj(np.fft.fft(local, n=L))

nper = 4


def surfaces(t0):
    """P on the padded grid AND its integer decimation (tracker surface)."""
    ns = npp * nper + 16
    iq = inspector.read_iq(bf, fmt, max_samples=ns,
                           offset_samples=int(round(t0 * fs)))[:npp * nper]
    rot = np.exp(-2j * np.pi * (fd_syn + if_hz) * np.arange(npp) / fs)
    blocks = iq.reshape(nper, npp) * rot[None, :]
    F = np.fft.fft(blocks, n=L, axis=1)
    P = np.abs(np.fft.ifft(F * LOC[None, :], axis=1)) ** 2
    return P.sum(axis=0)                     # NC power, lag grid 1/PAD sample


def parab(y0, y1, y2):
    den = y0 - 2 * y1 + y2
    return 0.5 * (y0 - y2) / den if den else 0.0


def peak_int3(P):
    Pi = P[::PAD][:npp]
    k = int(np.argmax(Pi))
    d = parab(Pi[k - 1], Pi[k], Pi[(k + 1) % npp])
    return k + d                              # samples


def peak_fine(P):
    k = int(np.argmax(P))
    d = parab(P[k - 1], P[k], P[(k + 1) % L])
    return (k + d) / PAD                      # samples


ph0 = float(sv["code_phase0_chips"])
pr_inj = float(sv["pr_inj_m"])
prt = np.array(sv["pr_truth_m"], float)
t_s = np.array(sim["t_s"], float)
chips_per_sample = chip_hz / fs

print(f"{runid} {svkey}: int3 vs fine peak vs pr_truth "
      f"(chips; sample = {chips_per_sample:.3f} ch)")
print(f"  ph0={ph0:.4f}  pr_inj={pr_inj:.1f}  fd_syn={fd_syn:.1f}  "
      f"if_hz={if_hz:.0f}  npp={npp}  chip/smp={chips_per_sample:.4f}")

# control: plain acquire_l1 on the SAME window (no preshift, wide search),
# and preshifted narrow search (dump convention) -- where do THEIR peaks sit?
from backend.analysis.l1_acquire import acquire_l1
for kk in range(1, 1 + n_ep):
    tk = float(t_s[kk])
    off = int(round(tk * fs))
    iq = inspector.read_iq(bf, fmt, max_samples=npp * 4 + 16, offset_samples=off)
    a1 = acquire_l1(iq, fs, sysc, prn, centre_offset_hz=if_hz)
    rot = np.exp(-2j * np.pi * fd_syn * np.arange(len(iq)) / fs)
    a2 = acquire_l1(iq * rot, fs, sysc, prn, centre_offset_hz=if_hz,
                    dopp_hz=300.0, dopp_step_hz=50.0, nperiods=4)
    P = surfaces(tk)
    lf = peak_fine(P)
    truth = (ph0 + chip_hz / config.C * (prt[kk] - pr_inj)) % code_len
    print(f"  t={tk:4.0f}s truth={truth:9.3f}  "
          f"acq_wide={a1['code_phase_chips']:9.3f}({a1['metric_db']:.0f}dB) "
          f"acq_narrow={a2['code_phase_chips']:9.3f}({a2['metric_db']:.0f}dB) "
          f"probe_fine={lf*chips_per_sample:9.3f}  "
          f"P@truth/Pmax={float(P[int(round(truth/chips_per_sample*PAD))])/float(P.max()):.3f}")
