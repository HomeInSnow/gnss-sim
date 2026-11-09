# type: ignore
"""coh 假锁诊断：monkeypatch SVTracker 捕获 fix_from_iq_l1_multi_tracked 的
每星会话（run 完成后），对目标星打印 (1) err 轨迹（chi vs 预测相位），
(2) 末窗 D(chi) S 曲线扫描（probe=True，不动环路）。
Usage: python probe_coh_e6.py [RUN] [SYS] [PRN] [track_s] [dll_mode]
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.synth import signals
from backend.ephem import ephemeris
from backend.analysis import tracker as tmod
from backend.analysis.l1_fix import default_atmo_fn, fix_from_iq_l1_multi_tracked

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
SYS = sys.argv[2] if len(sys.argv) > 2 else "E"
PRN = int(sys.argv[3]) if len(sys.argv) > 3 else 6
TRACK_S = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
MODE = sys.argv[5] if len(sys.argv) > 5 else "coh"

od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(meta.get("systems") or tuple(
    sorted({s["sys"] for s in meta["provenance"]["svs"]})))
rinex = cfg["rinex_path"]
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
engine_name = meta.get("provenance", {}).get("engine")
eph = ephemeris.parse_rinex_multi(rinex, systems, at_gps=gps_start)
eph = ephemeris.align_for_run(eph, week, sow, engine_name)
marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)

captured: list = []
_Real = tmod.SVTracker


class Cap(_Real):
    def __init__(self, *a, **kw):
        self._cap_args = (a, kw)
        super().__init__(*a, **kw)
        self.trace = []          # (t0, chi_before, D_raw, |cP|, dropped)

    def run(self, **kw):
        super().run(**kw)
        captured.append(self)

    def _dll_update(self, t0):
        chi_b = self.chi
        out = super()._dll_update(t0)
        self.trace.append((t0, chi_b, getattr(self, "_lastD", 0.0),
                           abs(out), self.n_dropped))
        return out

    def _raw_disc(self, t0, T, probe=False):
        D, P = super()._raw_disc(t0, T, probe)
        if not probe:
            self._lastD = D
        return D, P


tmod.SVTracker = Cap
try:
    afn = default_atmo_fn(rinex, marker, tow)
    tr = fix_from_iq_l1_multi_tracked(
        od, meta, eph, tow, approx_llh=marker, marker_llh=marker,
        atmo_fn=afn, track_s=TRACK_S, dll_bw_hz=0.5, dll_mode=MODE)
finally:
    tmod.SVTracker = _Real

if "error" in tr:
    print("fix error:", tr["error"])

target = None
for trk in captured:
    a, kw = trk._cap_args
    if trk.sysc == SYS and int(a[3]) == PRN:
        target = trk
if target is None:
    sys.exit(f"{SYS}{PRN} not captured (captured {len(captured)})")
trk = target
print(f"n_dropped={trk.n_dropped}  n_pll_skipped={trk.n_pll_skipped} "
      f"p_ref={trk._p_ref:.1f}")
step = max(1, len(trk.trace) // 40)
print("update trace: t0 chi D_raw |cP| ndrop")
for i in range(0, len(trk.trace), step):
    t0, chib, d_raw, cp, nd = trk.trace[i]
    print(f"  {t0:6.3f} {chib:9.3f} {d_raw:+8.4f} {cp:10.2e} {nd}")
sig = signals.SIGNALS[{"G": "GPS_L1CA", "E": "GAL_E1", "C": "BDS_B1I"}[SYS]]
rec = eph.get((SYS, PRN), eph.get(PRN) if SYS == "G" else None)
if rec is None:
    from backend.synth import engine as _eng
    rp = PRN - _eng._PRN_OFFSET.get(SYS, 0)
    rec = eph.get((SYS, rp))
state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec
svb = geometry.group_delay_bias_s(SYS, "L1",
                                  rec if isinstance(rec, dict) else None)
rx = geometry.llh_to_ecef(*marker)

tl = np.array(trk.t_log)
cl = np.array(trk.chi_log)
print(f"{SYS}{PRN}: t_coh={trk.t_coh*1e3:.0f}ms npp={trk._npp} fs={trk.fs/1e6:.3g} "
      f"boc={trk.boc} ell={trk.ell} el_gain={trk._el_gain}")
print("err(t) [ch]:")
step = max(1, len(tl) // 20)
for i in range(0, len(tl), step):
    o = geometry.observables(state, rx, tow + float(tl[i]), signal=sig,
                             sv_clock_bias_s=svb)
    atmo_m = float(afn(np.radians(o["az_deg"]), np.radians(o["el_deg"]),
                       float(sig.carrier_hz), SYS))
    pp = ((o["pseudorange_m"] + atmo_m) / config.C * sig.chip_rate_hz) \
        % sig.code_len
    e = ((cl[i] - pp + sig.code_len / 2.0) % sig.code_len) - sig.code_len / 2.0
    lam = config.C / float(sig.carrier_hz)
    resid = (trk.phase_log[i] + (o["pseudorange_m"] + atmo_m) / lam)
    print(f"  t={tl[i]:5.2f}  chi={cl[i]:9.3f}  err={e:+8.4f}  "
          f"fd={trk.fd_log[i]:8.2f}  ph={trk.phase_log[i]:12.2f}  "
          f"resid={resid:12.3f} cyc")

# ---- replicate l1_fix phase_rms exactly, full resolution ------------------
lam = config.C / float(sig.carrier_hz)
t_g = np.arange(0.0, TRACK_S + 0.51, 0.25)
pr_n = []
for tk in t_g:
    o_n = geometry.observables(state, rx, tow + float(tk), signal=sig,
                               sv_clock_bias_s=svb)
    a_n = float(afn(np.radians(o_n["az_deg"]), np.radians(o_n["el_deg"]),
                    float(sig.carrier_hz), SYS))
    pr_n.append(o_n["pseudorange_m"] + a_n)
pr_n = np.array(pr_n)
tl2 = np.array(trk.t_log, float)
ph2 = np.array(trk.phase_log, float)
s2 = tl2 >= 1.0
raw = ph2[s2] + np.interp(tl2[s2], t_g, pr_n) / lam
raw = raw - raw.mean()
unw = np.unwrap(ph2[s2] + np.interp(tl2[s2], t_g, pr_n) / lam)
unw = unw - unw.mean()
print(f"\nphase_rms replicate ({s2.sum()} samples t>=1s): "
      f"raw={np.sqrt((raw*raw).mean()):.5f}  "
      f"unwrap={np.sqrt((unw*unw).mean()):.5f}  "
      f"range=[{raw.min():+.4f},{raw.max():+.4f}]")
# full-resolution dump (no subsampling) so jitter vs drift is visible
print("full resid(t) t>=1s [cyc, mean-removed]:")
r0 = (ph2[s2] + np.interp(tl2[s2], t_g, pr_n) / lam)
r0 = r0 - r0.mean()
for i in range(len(r0)):
    print(f"  {tl2[s2][i]:6.2f} {r0[i]:+9.4f}")

# ---- S-curve scan: multi-window average (single 4 ms windows are noise-
# dominated; D noise ~ +-0.5 swamps the S-curve shape) ----------------------
chi_end = float(cl[-1])
t_end = float(tl[-1])
NW = 12
print(f"\nS-curve over {NW} windows from t={t_end:.3f}, chi_locked={chi_end:.3f}:")
print(f"{'dchi':>7} {'D_avg':>10} {'D_sd':>9} {'|P|':>12}")
for d in np.arange(-0.65, 0.651, 0.05):
    trk.chi = (chi_end + d) % sig.code_len
    ds, ps = [], []
    ph0 = trk.phase
    for k in range(NW):
        D, P = trk._raw_disc(t_end + 0.004 * k, trk.t_coh, probe=True)
        ds.append(D)
        ps.append(abs(P))
        trk.phase = ph0 + 2.0 * np.pi * trk.fd * 0.004 * k
    trk.phase = ph0
    print(f"{d:+7.2f} {np.mean(ds):+10.5f} {np.std(ds):9.4f} "
          f"{np.mean(ps):12.3e}")
trk.chi = chi_end
