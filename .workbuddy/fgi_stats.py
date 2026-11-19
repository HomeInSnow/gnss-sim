# -*- coding: utf-8 -*-
"""从 FGI nav/cn0 CSV 生成 stats.json（与 fgi_whu60_stats.json 同构）。

用法: python fgi_stats.py <prefix>    e.g. whu60 / whu60b
读取 out/fgi/<prefix>_nav.csv、out/fgi/<prefix>_cn0.csv，
真值 = Tampere 60.182537N 24.82826E 47.248m（场景固定）。
输出 out/fgi/<prefix>_stats.json；paper 节点沿用论文表 6.2（固定值）。
"""
import csv
import json
import math
import sys
import pathlib

FGI = pathlib.Path("D:/workbuddy/GNSSSignal/gnss-sim-desktop/out/fgi")
LAT, LON, HGT = 60.182537, 24.82826, 47.248
A, F = 6378137.0, 1.0 / 298.257223563
E2 = F * (2 - F)
PAPER = {"mean_cn0": 44.85, "cn0_lo": 38.0, "cn0_hi": 50.0,
         "h_rmse": 1.2517, "v_rmse": 2.0823, "d3_rmse": 2.4295,
         "mean_enu": [-0.255, -0.077, -0.6359],
         "std_enu": [0.6933, 1.0083, 1.9839], "n_sol": 892, "dur_s": 900}


def llh_to_ecef(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    sl, cl = math.sin(la), math.cos(la)
    N = A / math.sqrt(1 - E2 * sl * sl)
    return (N + h) * cl * math.cos(lo), (N + h) * cl * math.sin(lo), (N * (1 - E2) + h) * sl


def ecef_to_enu(x, y, z, ref):
    xr, yr, zr = ref
    dx, dy, dz = x - xr, y - yr, z - zr
    # rotation from geodetic of ref
    xr0, yr0, zr0 = ref
    r = math.sqrt(xr0 * xr0 + yr0 * yr0)
    lat = math.atan2(zr0, xr0 * (1 - E2))  # iterate once is enough at km scale
    for _ in range(3):
        n = math.sqrt(xr0 * xr0 + yr0 * yr0)
        lat = math.atan2(zr0, n * (1 - E2))
    sl, cl = math.sin(lat), math.cos(lat)
    lo = math.atan2(yr0, xr0)
    e = -sl * math.cos(lo) * dx - sl * math.sin(lo) * dy + cl * dz
    n = -math.sin(lo) * dx + math.cos(lo) * dy
    u = cl * math.cos(lo) * dx + cl * math.sin(lo) * dy + sl * dz
    return e, n, u


def main(prefix):
    ref = llh_to_ecef(LAT, LON, HGT)
    errs = []
    with open(FGI / f"fgi_{prefix}_nav.csv") as f:
        rd = csv.DictReader(f)
        for row in rd:
            if row["bvalid"] != "1":
                continue
            x, y, z = float(row["x"]), float(row["y"]), float(row["z"])
            errs.append(ecef_to_enu(x, y, z, ref))
    n = len(errs)
    if n == 0:
        raise SystemExit("no valid solutions")
    e = [p[0] for p in errs]; nn = [p[1] for p in errs]; u = [p[2] for p in errs]
    mean = [sum(v) / n for v in (e, nn, u)]
    std = [math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1) if n > 1 else 0.0)
           for v, m in zip((e, nn, u), mean)]
    rmse = [math.sqrt(sum(x * x for x in v) / n) for v in (e, nn, u)]
    # ---- cn0 per sat: per-prn stats of the mean_cn0 column ----
    acc = {}
    with open(FGI / f"fgi_{prefix}_cn0.csv") as f:
        rd = csv.DictReader(f)
        for row in rd:
            k = "G" + row["prn"].zfill(2)
            try:
                v = float(row["mean_cn0"])
            except ValueError:
                continue
            if v > 0.0:  # 锁定前的 0 值行剔除（两 run 统一口径）
                acc.setdefault(k, []).append(v)
    sats = {k: {"mean": round(sum(v) / len(v), 3),
                "std": round(math.sqrt(sum((x - sum(v) / len(v)) ** 2 for x in v) / max(len(v) - 1, 1)), 3),
                "n": len(v)} for k, v in acc.items()}
    allv = [x for v in acc.values() for x in v]
    out = {"n_sol": n, "mean_enu": [round(x, 4) for x in mean],
           "std_enu": [round(x, 4) for x in std],
           "rmse_enu": [round(x, 4) for x in rmse],
           "h_rmse": round(math.sqrt((rmse[0] ** 2 + rmse[1] ** 2)), 4),
           "v_rmse": round(rmse[2], 4),
           "d3_rmse": round(math.sqrt(sum(x * x for x in rmse)), 4),
           "cn0_sats": dict(sorted(sats.items(), key=lambda kv: -kv[1]["mean"])),
           "cn0_grand_mean": round(sum(allv) / len(allv), 3),
           "cn0_min": round(min(allv), 3), "cn0_max": round(max(allv), 3),
           "paper": PAPER}
    (FGI / f"fgi_{prefix}_stats.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_sol", "mean_enu", "std_enu",
                                          "h_rmse", "v_rmse", "d3_rmse",
                                          "cn0_grand_mean")}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "whu60b")
