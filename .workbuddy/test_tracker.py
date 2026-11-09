"""Quick convergence test for backend/analysis/tracker.py on one SV.

Usage: python .workbuddy/test_tracker.py <runid> <SVKEY> [t_end]
Seeds from acquire_l1 at the run start (legitimate receiver info), then
scores the tracked chi against trace_sim.json's synthesizer truth.
"""
import json
import pathlib
import sys
import warnings

import numpy as np

sys.path.insert(0, ".")
warnings.filterwarnings("ignore")

from backend import inspector, config                          # noqa: E402
from backend.analysis.l1_acquire import acquire_l1             # noqa: E402
from backend.analysis.tracker import SVTracker                 # noqa: E402
from backend.synth.signals import SIGNALS                      # noqa: E402

runid = sys.argv[1]
svkey = sys.argv[2]
t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0

od = pathlib.Path("out") / runid
sim = json.loads((od / "trace_sim.json").read_text())
meta = json.loads((od / "meta.json").read_text())
sv = sim["svs"][svkey]
band = next(b for b in meta["bands"] if b["id"] == sv["band"])
bf = od / band["file"]
fs = float(band["fs"])
fmt = meta["sample_format"]
chip_hz, code_len = float(sv["chip_hz"]), int(sv["code_len"])
sysc, prn = sv["sys"], int(sv["prn"])
if_hz = float(sv["if_hz"])

_sig = {"G": "GPS_L1CA", "J": "QZSS_L1CA", "S": "SBAS_L1",
        "E": "GAL_E1", "C": "BDS_B1I", "R": "GLO_G1"}[sysc]
sig = SIGNALS[_sig]
carrier_hz = float(sig.carrier_hz)

_cache = {}


def get_window(t0, ns):
    n0 = int(round(t0 * fs))
    key = (n0, ns)
    hit = _cache.get(key)
    if hit is None:
        hit = inspector.read_iq(bf, fmt, max_samples=ns, offset_samples=n0)
        _cache[key] = hit
        if len(_cache) > 400:
            _cache.clear()
    return hit


# --- acquisition seed (run start, 20 ms) -- the same info the fix uses ----
iq0 = inspector.read_iq(bf, fmt, max_samples=int(fs * 0.020))
acq = acquire_l1(iq0, fs, sysc, prn, centre_offset_hz=if_hz)
print("acq seed:", {k: round(v, 3) if isinstance(v, float) else v
                    for k, v in acq.items()})

tr = SVTracker(get_window, fs, sysc, prn, chip_hz=chip_hz,
               code_len=code_len, carrier_hz=carrier_hz, if_hz=if_hz,
               fd0=acq["doppler_hz"], chi0=acq["code_phase_chips"],
               boc=(sig.boc is not None))
tr.run(t_end=t_end, log_period_s=1.0)

truth_ph = sim["svs"][svkey]["ph_syn_chips"]
t_s = sim["t_s"]
errs = []
for k in range(min(len(tr.t_log), len(t_s))):
    if tr.t_log[k] != t_s[k]:
        continue
    m = tr.measure(tr.t_log[k])
    e = (m["chi_chips"] - truth_ph[k] + code_len / 2) % code_len - code_len / 2
    errs.append((tr.t_log[k], e, m["doppler_hz"]))
print(f"updates={tr.n_dropped + len(traces_) if False else 'pll_skip'}",
      tr.n_pll_skipped, "dll_drop", tr.n_dropped, "sign", tr._k_sign)
for t, e, fd in errs:
    print(f"t={t:5.1f}  err={e:+9.5f} ch  fd={fd:9.2f} Hz")
es = np.array([e for _, e, _ in errs][1:]) if len(errs) > 1 else np.array([np.nan])
print(f"chipRMS(after t=1) = {float(np.sqrt(np.mean(es ** 2))):.5f}"
      f"   (= {float(np.sqrt(np.mean(es ** 2))) * config.C / chip_hz:.2f} m)")
