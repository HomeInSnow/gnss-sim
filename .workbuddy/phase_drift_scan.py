# type: ignore
"""coh 会话全星相位残差结构扫描：捕获 fix_from_iq_l1_multi_tracked 的每个
SVTracker 会话，对 resid(t)=phase_log+pr(t)/λ 做线性拟合，打印
slope[cyc/s] / 去趋势 RMS / raw RMS，按 |slope| 排序。
Usage: python phase_drift_scan.py [RUN] [track_s]
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.synth import signals
from backend.ephem import ephemeris
from backend.analysis import tracker as tmod
from backend.analysis.l1_fix import default_atmo_fn, fix_from_iq_l1_multi_tracked

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
TRACK_S = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]
start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(meta.get("systems") or tuple(
    sorted({s["sys"] for s in meta["provenance"]["svs"]})))
rinex = cfg["rinex_path"]
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
engine = meta.get("provenance", {}).get("engine")
eph = ephemeris.parse_rinex_multi(rinex, systems, at_gps=gps_start)
eph = ephemeris.align_for_run(eph, week, sow, engine)
marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)

captured = []
_Real = tmod.SVTracker


class Cap(_Real):
    def __init__(self, *a, **kw):
        self._cap = (a, kw)
        super().__init__(*a, **kw)

    def run(self, **kw):
        super().run(**kw)
        captured.append(self)


tmod.SVTracker = Cap
try:
    afn = default_atmo_fn(rinex, marker, tow)
    tr = fix_from_iq_l1_multi_tracked(
        od, meta, eph, tow, approx_llh=marker, marker_llh=marker,
        atmo_fn=afn, track_s=TRACK_S, dll_bw_hz=0.5, dll_mode="coh")
finally:
    tmod.SVTracker = _Real
if "error" in tr:
    sys.exit("fix error: " + tr["error"])

rx = geometry.llh_to_ecef(*marker)
SIG = {"G": "GPS_L1CA", "E": "GAL_E1", "C": "BDS_B1I"}
print(f"run={RUN} track_s={TRACK_S}  error_m="
      f"{np.linalg.norm(np.array(tr['ecef']) - np.array(geometry.llh_to_ecef(*marker))):.3f}")
print(f"{'sv':6s} {'el':>5s} {'fd':>8s} {'slope':>9s} {'detRMS':>8s} "
      f"{'rawRMS':>8s} {'nDrop':>6s} {'nSkip':>6s}")
rows = []
for trk in captured:
    a, kw = trk._cap
    sysc, prn = trk.sysc, int(a[3])
    sig = signals.SIGNALS[SIG[sysc]]
    rec = eph.get((sysc, prn), eph.get(prn) if sysc == "G" else None)
    if rec is None:
        from backend.synth import engine as _eng
        rec = eph.get((sysc, prn - _eng._PRN_OFFSET.get(sysc, 0)))
    state = geometry.state_fn_for(rec) if isinstance(rec, dict) else rec
    svb = geometry.group_delay_bias_s(sysc, "L1",
                                      rec if isinstance(rec, dict) else None)
    lam = config.C / float(kw.get("carrier_hz", sig.carrier_hz))
    tl = np.array(trk.t_log, float)
    ph = np.array(trk.phase_log, float)
    sel = tl >= 1.0
    if sel.sum() < 16:
        continue
    pr = np.empty(sel.sum())
    for i, tv in enumerate(tl[sel]):
        o = geometry.observables(state, rx, tow + float(tv), signal=sig,
                                 sv_clock_bias_s=svb)
        # carrier-consistent anchor: geo - iono + tropo (engine cph model)
        ion, tro = afn.components(np.radians(o["az_deg"]),
                                  np.radians(o["el_deg"]),
                                  float(sig.carrier_hz), sysc)
        pr[i] = o["pseudorange_m"] - ion + tro
    r_ = ph[sel] + pr / lam
    p1 = np.polyfit(tl[sel], r_, 1)
    det = r_ - np.polyval(p1, tl[sel])
    o0 = geometry.observables(state, rx, tow + 5.0, signal=sig,
                              sv_clock_bias_s=svb)
    rows.append((f"{sysc}{prn}", o0["el_deg"], trk.fd, p1[0],
                 float(np.sqrt((det * det).mean())),
                 float(np.sqrt(((r_ - r_.mean())**2).mean())),
                 trk.n_dropped, trk.n_pll_skipped))
rows.sort(key=lambda r: -abs(r[3]))
for k, el, fd, sl, dr, rr, nd, ns in rows:
    print(f"{k:6s} {el:5.1f} {fd:+8.1f} {sl:+9.4f} {dr:8.5f} {rr:8.5f} "
          f"{nd:6d} {ns:6d}")
G = [r for r in rows if r[0][0] == "G"]
E = [r for r in rows if r[0][0] == "E"]
for tag, sub in (("G", G), ("E", E)):
    if sub:
        print(f"  {tag}: |slope| mean={np.mean([abs(r[3]) for r in sub]):.4f} "
              f"detRMS mean={np.mean([r[4] for r in sub]):.5f} "
              f"rawRMS mean={np.mean([r[5] for r in sub]):.5f}")
# common-mode slope (clock) check
slopes = np.array([r[3] for r in rows])
el_s = np.array([r[1] for r in rows])
print(f"  slope: mean={slopes.mean():+.4f} std={slopes.std():.4f}  "
      f"corr(slope,fd)={np.corrcoef(slopes, [r[2] for r in rows])[0,1]:+.2f}  "
      f"corr(slope,el)={np.corrcoef(slopes, el_s)[0,1]:+.2f}")
