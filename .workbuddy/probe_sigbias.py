"""Loop-free, sub-0.001-ch measurement of the SIGNAL's physical code peak.

For each trace epoch: NC power surface around the coarse integer lag,
evaluated on 32 fractional replica delays (ideal boxcar chip waveform at
sub-sample offsets -- the same construction the tracker's local uses, just
fractionally shifted), then a parabola fit over the tau curve gives the
physical peak with ~0.001 ch resolution. polyfit bias(t) vs pr_truth:
  intercept+mean ~ 0.02 ch constant  -> engine-side injection bias (or
                                        correlator-inherent, loop can't fix)
  ~0 everywhere                        -> bias belongs to the loop/discriminator
  slope != 0                           -> injected code RATE mismatch

Usage: python probe_sigbias.py <runid> <svkey> [n_epochs]
"""
import json, pathlib, sys, warnings
import numpy as np
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
from backend import inspector, config
from backend.analysis.tracker import _code_table

runid, svkey = sys.argv[1], sys.argv[2]
n_ep = int(sys.argv[3]) if len(sys.argv) > 3 else 29
PAD = 32
od = pathlib.Path("out") / runid
sim = json.loads((od / "trace_sim.json").read_text())
meta = json.loads((od / "meta.json").read_text())
sv = sim["svs"][svkey]
band = next(b for b in meta["bands"] if b["id"] == sv["band"])
bf, fs, fmt = od / band["file"], float(band["fs"]), meta["sample_format"]
chip_hz, code_len = float(sv["chip_hz"]), int(sv["code_len"])
sysc, prn, if_hz = sv["sys"], int(sv["prn"]), float(sv["if_hz"])
fd_syn = float(sv.get("carrier_doppler_hz") or 0.0)
npp = int(round(fs * code_len / chip_hz))
code = _code_table(sysc, prn, code_len)
cpc = chip_hz / fs                                  # chips per sample
nper = 8

t = np.arange(npp) / fs
chip_phase = t * chip_hz
sub0 = (np.where(np.floor(2.0 * chip_phase).astype(np.int64) & 1, -1.0, 1.0)
        if sysc == "E" else None)

# precompute the 32 fractional-delay replica FFTs (convention == tracker)
LOCS = []
for p in range(PAD):
    tau = p / PAD
    idx = np.floor(chip_phase - tau * cpc).astype(np.int64) % code_len
    loc = code[idx].astype(np.float64)
    if sub0 is not None:
        loc = loc * sub0
    LOCS.append(np.fft.fft(loc))
LOC0 = np.conj(LOCS[0])


def sig_peak(t0):
    iq = inspector.read_iq(bf, fmt, max_samples=npp * nper + 16,
                           offset_samples=int(round(t0 * fs)))[:npp * nper]
    rot = np.exp(-2j * np.pi * (fd_syn + if_hz) * t)
    Fb = np.fft.fft(iq.reshape(nper, npp) * rot[None, :], axis=1)
    acc = np.zeros(npp)
    for j in range(nper):
        acc += np.abs(np.fft.ifft(Fb[j] * LOC0)) ** 2
    k = int(np.argmax(acc))
    # tau curve at lag k: P(tau) = sum_j |ifft(Fb_j conj(FFT loc_tau))[k]|^2
    Ps = np.empty(PAD)
    for p in range(PAD):
        c = np.fft.ifft(Fb * np.conj(LOCS[p])[None, :], axis=1)[:, k]
        Ps[p] = float(np.sum(np.abs(c) ** 2))
    p0 = int(np.argmax(Ps))
    a, b, cc = Ps[p0 - 1], Ps[p0], Ps[(p0 + 1) % PAD]
    den = a - 2 * b + cc
    d = 0.5 * (a - cc) / den if den else 0.0
    return (k + (p0 + d) / PAD) * cpc               # chips


ph0 = float(sv["code_phase0_chips"])
pr_inj = float(sv["pr_inj_m"])
prt = np.array(sv["pr_truth_m"], float)
t_s = np.array(sim["t_s"], float)
xs, ys = [], []
for kk in range(1, n_ep):
    tk = float(t_s[kk])
    meas = sig_peak(tk) % code_len
    truth = (ph0 + chip_hz / config.C * (prt[kk] - pr_inj)) % code_len
    e = (meas - truth + code_len / 2) % code_len - code_len / 2
    xs.append(tk); ys.append(e)
    if kk <= 4 or kk % 10 == 0:
        print(f"  t={tk:4.0f}s bias={e:+.4f} ch")
x = np.array(xs); y = np.array(ys)
c1, c0 = np.polyfit(x, y, 1)
print(f"{runid} {svkey}: bias(t) = {c0:+.4f} + {c1:+.5f}*(t-t0) ch   "
      f"rms(resid)={np.std(y - np.polyval([c1, c0], x)):.4f}  "
      f"mean={y.mean():+.4f} ch over {len(x)} epochs")
