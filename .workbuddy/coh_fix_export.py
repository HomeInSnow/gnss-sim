"""coh（相干 E/L + Costas PLL）跟踪解算数据导出——报告专用。

跑 fix_from_iq_l1_multi_tracked(dll_mode="coh", track_s, dll_bw)，把完整解算
结果落盘 out/<RUN>/tracking_fix_coh.json：三维定位误差、ENU 分量、PDOP、
残差 RMS、逐星 err_chips/err_chips_avg（另存米制换算列）与会话抖动/相位指标。
与 HTTP /api/receiver {"tracking": true} 同配方，但不跑快照基线（省时）。

Usage: python coh_fix_export.py [RUN] [track_s] [dll_bw]
默认 RUN=20261106T084558776704, track_s=10, dll_bw=0.5（0.17 m 基线配方）
"""
import sys, json, pathlib, datetime as dt
import numpy as np

from backend import config, geometry
from backend.ephem import ephemeris
from backend.analysis.l1_fix import default_atmo_fn, fix_from_iq_l1_multi_tracked

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
track_s = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
dll_bw = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

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

print(f"run={RUN} track_s={track_s} bw={dll_bw} mode=coh", flush=True)
afn = default_atmo_fn(rinex, marker, tow) if rinex else None
tr = fix_from_iq_l1_multi_tracked(
    od, meta, eph, tow, approx_llh=marker, marker_llh=marker,
    atmo_fn=afn, track_s=track_s, dll_bw_hz=dll_bw, dll_mode="coh")
if "error" in tr:
    print(f"ERROR: {tr['error']}  skipped={json.dumps(tr.get('skipped', {}))}")
    sys.exit(1)

truth = np.array(geometry.llh_to_ecef(*marker))
sol = np.array(tr["ecef"])
d = sol - truth
lat, lon = marker[0], marker[1]
# ENU 分解（局部东/北/天单位向量）
slat, clat, slon, clon = np.sin(np.radians(lat)), np.cos(np.radians(lat)), \
    np.sin(np.radians(lon)), np.cos(np.radians(lon))
e = -slon * d[0] + clon * d[1]
n = -slat * clon * d[0] - slat * slon * d[1] + clat * d[2]
u = clat * clon * d[0] + clat * slon * d[1] + slat * d[2]

m2ch = {}   # key -> m/chip（码速率 1.023 MHz → 293.05 m/chip，G/E 相同）
for k, v in tr["per_sv"].items():
    chip_hz = config.CHIP_HZ_L1 if hasattr(config, "CHIP_HZ_L1") else 1.023e6
    m2ch[k] = config.C / chip_hz
    v["err_m"] = v["err_chips"] * m2ch[k]
    v["err_avg_m"] = (None if v.get("err_chips_avg") is None
                      else v["err_chips_avg"] * m2ch[k])

out = {
    "kind": "tracking_fix_coh", "runid": RUN, "track_s": track_s,
    "dll_bw_hz": dll_bw, "dll_mode": "coh",
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "n_sv": len(tr["prns_used"]),
    "error_m": tr.get("error_m"), "enu_m": [e, n, u],
    "ecef": sol.tolist(), "truth_ecef": truth.tolist(),
    "llh": tr["llh"], "clock_bias_s": tr["clock_bias_s"],
    "pdop": tr["pdop"], "residual_rms_m": tr["residual_rms_m"],
    "acquired": tr["acquired"], "skipped": tr["skipped"],
    "per_sv": tr["per_sv"],
}
p = od / "tracking_fix_coh.json"
p.write_text(json.dumps(out, indent=1), encoding="utf-8")

ecv = np.array([v["err_avg_m"] for v in tr["per_sv"].values()
                if v.get("err_avg_m") is not None])
ec = np.array([v["err_m"] for v in tr["per_sv"].values()])
print(f"error_m={tr.get('error_m'):.3f}  enu=({e:+.3f},{n:+.3f},{u:+.3f})  "
      f"pdop={tr['pdop']:.3f}  resid_rms={tr['residual_rms_m']:.3f}  n={len(tr['prns_used'])}")
print(f"PR err (LS 均值列 err_avg_m): RMS={np.sqrt(np.mean(ecv**2)):.4f} m  "
      f"mean|.|={np.mean(np.abs(ecv)):.4f} m  max|.|={np.max(np.abs(ecv)):.4f} m")
print(f"PR err (锁定点 err_m):        RMS={np.sqrt(np.mean(ec**2)):.4f} m  "
      f"max|.|={np.max(np.abs(ec)):.4f} m")
for s in ("G", "E"):
    sub = np.array([v["err_avg_m"] for k, v in tr["per_sv"].items()
                    if k.startswith(s) and v.get("err_avg_m") is not None])
    if sub.size:
        print(f"  {s}: n={sub.size} RMS={np.sqrt(np.mean(sub**2)):.4f} m  "
              f"mean|.|={np.mean(np.abs(sub)):.4f} m  max|.|={np.max(np.abs(sub)):.4f} m")
print(f"written {p}")
