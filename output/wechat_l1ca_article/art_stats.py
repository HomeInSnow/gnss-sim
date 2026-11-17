# -*- coding: utf-8 -*-
"""art1.nmea（PocketSDR WebUI 回放 L1CA）统计：$GNGGA 定位解与精度。
真值 Tampere: lat 60.182537, lon 24.82826, 椭高 47.248 m；
GGA 高度为 MSL，加 geoid sep（GGA 字段 11）还原椭高。
"""
import sys


def _dm(v, hemi, nd):
    deg = int(v[:nd]) + float(v[nd:]) / 60.0
    return -deg if hemi in "SW" else deg


TRUTH_LAT, TRUTH_LON, TRUTH_H = 60.182537, 24.82826, 47.248
M_PER_DEG = 111320.0
T0 = 23 * 3600 + 20 * 60   # 场景起点 23:20:00


def main(nmea_path):
    rows = []
    nmea_lines = 0
    with open(nmea_path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            nmea_lines += 1
            if not s.startswith("$GNGGA,"):
                continue
            p = s.split(",")
            if len(p) < 12 or not p[1] or not p[2] or not p[4]:
                continue
            ss = int(p[1][0:2]) * 3600 + int(p[1][2:4]) * 60 + int(p[1][4:6])
            geo = float(p[11]) if len(p) > 11 and p[11] else 0.0
            rows.append(dict(t=ss - T0, lat=_dm(p[2], p[3], 2),
                             lon=_dm(p[4], p[5], 3),
                             h=(float(p[9]) if p[9] else 0.0) + geo,
                             ns=int(p[7]) if p[7].isdigit() else 0))
    print("nmea lines:", nmea_lines, " $GNGGA fixes:", len(rows))
    if not rows:
        print("NO FIX")
        return
    print("first fix t=%.0fs ns=%d" % (rows[0]["t"], rows[0]["ns"]))
    good = [r for r in rows if r["ns"] >= 5]
    print("fixes ns>=5: %d/%d" % (len(good), len(rows)))
    use = good[-10:] if good else rows[-min(10, len(rows)):]
    lat = sum(r["lat"] for r in use) / len(use)
    lon = sum(r["lon"] for r in use) / len(use)
    h = sum(r["h"] for r in use) / len(use)
    dn = (lat - TRUTH_LAT) * M_PER_DEG
    de = (lon - TRUTH_LON) * M_PER_DEG * 0.4972  # cos(60.18)
    du = h - TRUTH_H
    print("mean(N,E,U) = %+.2f %+.2f %+.2f m  3D=%.2f m (last %d fixes)" % (
        dn, de, du, (dn * dn + de * de + du * du) ** 0.5, len(use)))
    best = min(
        ((r["lat"] - TRUTH_LAT) * M_PER_DEG) ** 2 +
        ((r["lon"] - TRUTH_LON) * M_PER_DEG * 0.4972) ** 2 +
        (r["h"] - TRUTH_H) ** 2 for r in rows) ** 0.5
    print("min 3D err: %.2f m" % best)
    hs = [(r["h"] - TRUTH_H) for r in rows]
    hor = [(((r["lat"] - TRUTH_LAT) * M_PER_DEG) ** 2 +
            ((r["lon"] - TRUTH_LON) * M_PER_DEG * 0.4972) ** 2) ** 0.5
           for r in rows]
    print("horiz RMS = %.2f m   vert RMS = %.2f m" % (
        (sum(x * x for x in hor) / len(hor)) ** 0.5,
        (sum(x * x for x in hs) / len(hs)) ** 0.5))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "output/wechat_l1ca_article/art1.nmea")
