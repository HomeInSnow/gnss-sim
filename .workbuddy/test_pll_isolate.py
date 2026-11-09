"""Isolate the PLL: hold chi at truth, seed fd off by +50 Hz, step _pll_update.
Expect fd -> fd_true if loop sign/form is right; watch e per step."""
import sys
import warnings

import numpy as np

sys.path.insert(0, ".")
warnings.filterwarnings("ignore")

exec(open(".workbuddy/test_tracker_synth.py").read().split("# seeds:")[0])

tr = SVTracker(get_window, fs, "G", 5, chip_hz=chip_hz, code_len=code_len,
               carrier_hz=carrier_hz, if_hz=if_hz, fd0=fd_true + 50.0,
               chi0=tau_true)
for k in range(30):
    t0 = k * 0.001
    tr.chi = tau_true % code_len            # pin code loop
    P = tr._pll_update(t0)
    print(f"k={k:2d} t={t0:6.3f}  fd={tr.fd:9.2f}  |P|={abs(P):7.2f} "
          f"angP={np.angle(P):+7.3f}")
