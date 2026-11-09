"""NC power-surface peak-tracking DLL + FLL on a real run SV.

Truth frame: the engine injects time-varying Doppler via trajectory knots, so
the acquisition-frame code phase follows the injected pseudorange pr_truth[k]
(recomputed from ephemeris+atmo), NOT the constant-code_doppler linear model.
chi vs (ph0 + chip/C*(pr_truth-pr_inj)) is the only correct RMS reference.
"""
import json, pathlib, sys, warnings
import numpy as np
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
from backend import inspector, config
from backend.analysis.l1_acquire import acquire_l1
from backend.analysis.tracker import SVTracker
from backend.synth.signals import SIGNALS

runid, svkey = sys.argv[1], sys.argv[2]
t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
ell = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
dll_bw = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
od = pathlib.Path("out") / runid
sim = json.loads((od / "trace_sim.json").read_text())
meta = json.loads((od / "meta.json").read_text())
sv = sim["svs"][svkey]
band = next(b for b in meta["bands"] if b["id"] == sv["band"])
bf, fs, fmt = od / band["file"], float(band["fs"]), meta["sample_format"]
chip_hz, code_len = float(sv["chip_hz"]), int(sv["code_len"])
sysc, prn, if_hz = sv["sys"], int(sv["prn"]), float(sv["if_hz"])
sig = SIGNALS[{"G":"GPS_L1CA","J":"QZSS_L1CA","S":"SBAS_L1","E":"GAL_E1",
               "C":"BDS_B1I","R":"GLO_G1"}[sysc]]
_c = {}
def get_window(t0, ns):
    key = (int(round(t0*fs)), ns)
    if key not in _c:
        if len(_c) > 900: _c.clear()
        _c[key] = inspector.read_iq(bf, fmt, max_samples=ns,
                                    offset_samples=key[0])
    return _c[key]

tg, fdg = np.array(sim["t_s"], float), np.array(sv["fd_geo_hz"], float)
def fd_fn(t):
    return float(np.interp(t, tg, fdg))

iq0 = inspector.read_iq(bf, fmt, max_samples=int(fs*0.020))
acq = acquire_l1(iq0, fs, sysc, prn, centre_offset_hz=if_hz)
print("acq seed:", {k: round(v,3) for k,v in acq.items() if isinstance(v,float)})
tr = SVTracker(get_window, fs, sysc, prn, chip_hz=chip_hz, code_len=code_len,
               carrier_hz=float(sig.carrier_hz), if_hz=if_hz,
               fd0=acq["doppler_hz"], chi0=acq["code_phase_chips"],
               boc=(sig.boc is not None), nc=True, fd_fn=fd_fn,
               ell=ell, dll_bw_hz=dll_bw)
tr.run(t_end=t_end, log_period_s=1.0, dll_bw_hz=dll_bw)

ph0 = float(sv["code_phase0_chips"])
pr_inj = float(sv["pr_inj_m"])
prt = np.array(sv["pr_truth_m"], float)
truth = [(ph0 + chip_hz/config.C*(prt[k] - pr_inj)) % code_len
         for k in range(len(sim["t_s"]))]
errs = []
for k in range(min(len(tr.t_log), len(sim["t_s"]))):
    if tr.t_log[k] != sim["t_s"][k]:
        continue
    m = tr.measure(tr.t_log[k])
    e = (m["chi_chips"] - truth[k] + code_len/2) % code_len - code_len/2
    errs.append((tr.t_log[k], e, m["doppler_hz"]))
for t, e, fd in errs:
    print(f"t={t:5.1f}  err={e:+9.5f} ch  fd={fd:9.2f}")
es = np.array([e for _, e, _ in errs[1:]])
m_ch = config.C/chip_hz
print(f"chipRMS(after t=1) = {np.sqrt(np.mean(es**2)):.5f}  "
      f"(= {np.sqrt(np.mean(es**2))*m_ch:.2f} m)  "
      f"max|e|={np.max(np.abs(es)):.5f}  drop={tr.n_dropped} "
      f"fll_off={tr._fll_off:+.2f}")
