"""离线对比：快照捕获定位 vs 载波辅助 DLL 跟踪定位（同一 run、同一 eph 路径）。

复刻 regress_rx.py 的历元对齐链（parse_rinex_multi(at_gps) -> align_for_run），
先跑基线 receiver.fix_from_iq，再跑 l1_fix.fix_from_iq_l1_multi_tracked，
打印两者的 error_m / pdop / err_chips / 会话抖动，用于 Task #14 验收。

Usage: python test_tracked_fix.py [RUN] [track_s] [dll_bw] [dll_mode] [min_metric_db]
默认 RUN = 20261106T084558776704, dll_mode = coh（相干 E/L + Costas PLL；可传 el/nc 对照）
min_metric_db 默认 15.0（与 /api/receiver 同）；低仰角多的场景可降到 12 左右，
metric 分布 ~11-16 dB 时阈值 15 会随机淘汰边际星（噪声 realization 敏感）。
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.ephem import ephemeris
from backend.analysis import receiver
from backend.analysis.l1_fix import (default_atmo_fn,
                                     fix_from_iq_l1_multi_tracked)

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
track_s = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
dll_bw = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
dll_mode = sys.argv[4] if len(sys.argv) > 4 else "coh"
min_metric_db = float(sys.argv[5]) if len(sys.argv) > 5 else 15.0

od = pathlib.Path("out") / RUN
meta = json.loads((od / "meta.json").read_text())
cfg = meta["config"]

start = dt.datetime.fromisoformat(cfg["start_utc"])
systems = tuple(meta.get("systems") or cfg.get("systems")
                or tuple(sorted({s["sys"] for s in meta["provenance"]["svs"]})))
rinex = cfg["rinex_path"]
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
engine = meta.get("provenance", {}).get("engine")
if set(systems) - {"G"}:
    eph = ephemeris.parse_rinex_multi(rinex, systems, at_gps=gps_start)
else:
    eph = ephemeris.parse_rinex(rinex, at_gps=gps_start)
eph = ephemeris.align_for_run(eph, week, sow, engine)
delta = start - dt.datetime(1980, 1, 6)
tow = ((delta.days % 7) * 86400 + delta.seconds + delta.microseconds / 1e6
       + config.GPS_UTC_LEAP_S) % (7 * 86400)
marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))

print(f"run={RUN}  systems={systems}  engine={engine}  track_s={track_s}"
      f"  bw={dll_bw}  dll_mode={dll_mode}  min_metric_db={min_metric_db}")

# --- baseline: snapshot acquisition fix (the /api/receiver default path)
base = receiver.fix_from_iq(
    od / "gpssim.bin", meta["sample_format"], meta["sample_rate"],
    eph, tow, marker_llh=marker, systems=systems)
if "error" in base:
    print(f"baseline ERROR: {base['error']}")
    sys.exit(1)
truth = np.array(geometry.llh_to_ecef(*marker))
be = float(np.linalg.norm(np.array(base["ecef"]) - truth))
print(f"baseline : prns={len(base['prns_used'])}  error_m={be:.2f}  "
      f"pdop={base.get('pdop', float('nan')):.2f}  "
      f"resid_rms={base['residual_rms_m']:.2f}")

# --- tracking fix (carrier-aided DLL sessions)
# Mirror /api/receiver policy: remove only what the engine injected
# (meta.config.atmosphere + sv_clock; older runs default to injected).
_atm = cfg.get("atmosphere")
_iono_on = _atm is None or str(_atm.get("ionosphere", "off")) != "off"
_tropo_on = _atm is None or str(_atm.get("troposphere", "off")) != "off"
_svc = bool(cfg.get("sv_clock", True))
afn = default_atmo_fn(rinex, marker, tow, ionosphere=_iono_on,
                      troposphere=_tropo_on) \
    if (rinex and (_iono_on or _tropo_on)) else None
print(f"policy: iono_on={_iono_on} tropo_on={_tropo_on} sv_clock={_svc} "
      f"atmo_fn={'on' if afn else 'off'}")
tr = fix_from_iq_l1_multi_tracked(
    od, meta, eph, tow, approx_llh=marker, marker_llh=marker,
    atmo_fn=afn, sv_clock=_svc, track_s=track_s, dll_bw_hz=dll_bw,
    dll_mode=dll_mode, min_metric_db=min_metric_db)
if "error" in tr:
    print(f"tracked  ERROR: {tr['error']}  skipped={json.dumps(tr.get('skipped', {}))}")
    sys.exit(1)
te = float(np.linalg.norm(np.array(tr["ecef"]) - truth))
print(f"tracked  : prns={len(tr['prns_used'])}  error_m={te:.2f}  "
      f"pdop={tr.get('pdop', float('nan')):.2f}  "
      f"resid_rms={tr['residual_rms_m']:.2f}")
ec = np.array([v["err_chips"] for v in tr["per_sv"].values()])
ecv = np.array([v["err_chips_avg"] for v in tr["per_sv"].values()
                if v.get("err_chips_avg") is not None])
jt = np.array([v["chip_rms_hist"] for v in tr["per_sv"].values()
               if v["chip_rms_hist"] is not None])
print(f"  err_chips: RMS={np.sqrt(np.mean(ec**2)):.5f} ch  max={np.max(np.abs(ec)):.5f} ch")
if len(ecv):
    print(f"  err_chips_avg (LS meas): RMS={np.sqrt(np.mean(ecv**2)):.5f} ch"
          f"  max={np.max(np.abs(ecv)):.5f} ch")
prs = [v["phase_rms_cycles"] for v in tr["per_sv"].values()
       if v.get("phase_rms_cycles") is not None]
dru = [abs(v["phase_drift_cycps"]) for v in tr["per_sv"].values()
       if v.get("phase_drift_cycps") is not None]
if prs:
    prs = np.array(prs)
    print(f"  phase jitter (anchored, detrended): mean={prs.mean():.5f}"
          f"  max={prs.max():.5f} cyc"
          f"  (x{config.C / 1.57542098e9 * 100:.2f} cm/cyc)"
          + (f"  |drift| mean={np.mean(dru):.4f} max={np.max(dru):.4f} cyc/s"
             if dru else ""))
    for sysp in sorted({k[0] for k in tr["per_sv"]}):
        sub = [v["phase_rms_cycles"] for k, v in tr["per_sv"].items()
               if k.startswith(sysp) and v.get("phase_rms_cycles") is not None]
        sube = [abs(v["err_chips_avg"]) for k, v in tr["per_sv"].items()
                if k.startswith(sysp) and v.get("err_chips_avg") is not None]
        if sub:
            print(f"    {sysp}: phRMS mean={np.mean(sub):.5f} max={np.max(sub):.5f}"
                  f" | |err_avg| mean={np.mean(sube):.5f} max={np.max(sube):.5f} ch")
n_skip = sum(v.get("n_pll_skipped") or 0 for v in tr["per_sv"].values())
print(f"  PLL bit-flip coast count: {n_skip}")
if len(jt):
    print(f"  session jitter (detrended): mean={jt.mean():.5f}  max={jt.max():.5f} ch")
worst = sorted(tr["per_sv"].items(), key=lambda kv: -abs(kv[1]["err_chips"]))[:5]
for k, v in worst:
    phr = v.get("phase_rms_cycles")
    print(f"    {k:5s} err={v['err_chips']:+.5f} ch  jitter={v['chip_rms_hist']}  "
          f"phRMS={None if phr is None else round(phr, 5)}  "
          f"fd={v['fd_meas_hz']:+9.2f} Hz  el={v['el_deg']:5.1f}  metric={v['metric_db']:.1f} dB")
if tr.get("skipped"):
    print("  skipped:", json.dumps(tr["skipped"]))
verdict = "PASS" if te <= max(be, 10.0) else "FAIL"
print(f"VERDICT: {verdict}  (tracked {te:.2f} m vs baseline {be:.2f} m)")

# --- persist machine-readable result for report pipelines (whu FGI compare etc.)
out_json = pathlib.Path(__file__).with_name(f"trk_{RUN}_{dll_mode}.json")
out_json.write_text(json.dumps({
    "run": RUN, "dll_mode": dll_mode, "track_s": track_s, "dll_bw": dll_bw,
    "min_metric_db": min_metric_db, "marker": marker,
    "baseline": {k: base.get(k) for k in ("ecef", "pdop", "residual_rms_m")}
    | {"error_m": be, "prns_used": list(base["prns_used"])},
    "tracked": {k: tr.get(k) for k in ("ecef", "pdop", "residual_rms_m")}
    | {"error_m": te, "prns_used": list(tr["prns_used"]), "per_sv": tr["per_sv"],
       "skipped": tr.get("skipped", {})},
}, indent=2, default=float))
print(f"result json -> {out_json}")
