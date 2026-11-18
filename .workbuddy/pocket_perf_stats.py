# -*- coding: utf-8 -*-
"""PocketSDR 双回放精度统计：解析 pvt.nmea(GGA) → 水平/垂直误差。

真值 = 场景配置（Tampere 60.182537N 24.82826E 椭高47.248）。
用法: python .workbuddy/pocket_perf_stats.py <outdir_base>
"""
import math
import pathlib
import re
import sys

TRUTH = (60.182537, 24.82826, 47.248)  # lat, lon, 椭高 m


def gga_lines(nmea_path):
    """返回 [(fix_quality, lat, lon, alt, nsat, hdop)]，仅 fix_quality>=1。"""
    out = []
    for ln in nmea_path.read_text(errors="ignore").splitlines():
        if not ln.startswith("$GNGGA") and not ln.startswith("$GPGGA"):
            continue
        body = ln.split("*")[0]
        f = body.split(",")
        if len(f) < 10:
            continue
        try:
            fq = int(f[6] or 0)
            if fq < 1:
                continue
            lat = dms(f[2], f[3]); lon = dms(f[4], f[5])
            # PocketSDR GGA alt 为正高(MSL)，+大地水准面差距 → WGS84 椭高
            alt = float(f[9]) + float(f[11] or 0)
            nsat = int(f[7] or 0); hdop = float(f[8] or 0)
        except (ValueError, IndexError):
            continue
        if lat is None or lon is None:
            continue
        out.append((fq, lat, lon, alt, nsat, hdop))
    return out


def dms(v, h):
    if not v or not h:
        return None
    deg = float(v[:2]) if len(v) > 7 else float(v[:3])
    # 通用解析：ddmm.mmmm
    dot = v.find(".")
    dpart = v[:dot - 2]
    return float(dpart) + float(v[dot - 2:]) / 60.0 * (1 if h in "NE" else -1)


def hdist(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def stats(path: pathlib.Path):
    rows = gga_lines(path)
    if not rows:
        return None
    lat0, lon0, alt0 = TRUTH
    he = [hdist(r[1], r[2], lat0, lon0) for r in rows]
    ve = [r[3] - alt0 for r in rows]
    n = len(rows)
    rms = lambda xs: math.sqrt(sum(x*x for x in xs) / len(xs))
    return dict(
        n_fix=n, n_sat_avg=sum(r[4] for r in rows)/n,
        h_rms=rms(he), h_avg=sum(he)/n, h_max=max(he),
        v_rms=rms(ve), v_avg=sum(ve)/n,
        fq3=sum(1 for r in rows if r[0] >= 3),
    )


def main(base):
    b = pathlib.Path(base)
    for v in ("orig", "bothoff"):
        d = b / v
        cands = list(d.glob("*.nmea")) + [d / "f"] + list(d.glob("*nmea*.txt"))
        cands = [p for p in cands if p.exists()]
        if not cands:
            print(f"{v:9s}: 无 nmea 文件（目录内容: {[p.name for p in d.iterdir()]}）")
            continue
        p = max(cands, key=lambda q: q.stat().st_size)
        st = stats(p)
        if st is None:
            print(f"{v:9s}: {p.name} 中无有效定位（检查 stdout.txt）")
            continue
        print(f"{v:9s}: {p.name} 解数={st['n_fix']} (固定解={st['fq3']}) "
              f"星数均值={st['n_sat_avg']:.1f} | 水平 RMS={st['h_rms']:.3f} "
              f"均值={st['h_avg']:.3f} 最大={st['h_max']:.3f} | "
              f"垂直 RMS={st['v_rms']:.3f} 均值={st['v_avg']:+.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
