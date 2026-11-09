"""Where does the ELL power discriminator cross zero vs true grid offset?"""
import sys, warnings
import numpy as np
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
exec(open(".workbuddy/test_tracker_synth.py").read().split("# seeds:")[0])

for t0, T in [(0.0, 0.020), (0.5, 0.020), (1.5, 0.020)]:
    tr = SVTracker(get_window, fs, "G", 5, chip_hz=chip_hz, code_len=code_len,
                   carrier_hz=carrier_hz, if_hz=if_hz, fd0=fd_true,
                   chi0=tau_true)
    tr.fd = fd_true
    truth = (tau_true + fd_true*chip_hz/carrier_hz*t0) % code_len
    ds, nn = tr._derot_window(t0, T)
    grid = np.arange(-0.20, 0.201, 0.01)
    Ds = []
    for d in grid:
        tr.chi = (truth + d) % code_len
        D, _ = tr._raw_disc(t0, T)
        Ds.append(D)
    Ds = np.array(Ds)
    # linear root near 0 using points around the steepest slope
    i0 = int(np.argmin(np.abs(Ds)))
    slope = np.gradient(Ds)[i0]
    root = grid[i0] - Ds[i0]/slope if slope != 0 else np.nan
    print(f"t0={t0:4.1f}  D zero at truth{root:+.4f} ch   slope={slope:+.3f}/ch")
