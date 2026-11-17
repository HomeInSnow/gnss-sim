# -*- coding: utf-8 -*-
"""三口径对照：单频 E1B baseline / 单频 E1B 场景匹配 / 双频 IFLC（+IFLC-tropo-off 诊断）
口径复用 output/pvt_config_exp_20261115/analyze.py：$POS 末 min(10,n) 历元均值对真值算 N/E/U。
真值（Tampere）: lat 60.182537, lon 24.82826, 椭高 47.248 m。
"""
import math
import statistics
import sys

TRUTH_LAT, TRUTH_LON, TRUTH_H = 60.182537, 24.82826, 47.248
M_PER_DEG = 111320.0


def parse_pos(log_path):
    rows = []
    with open(log_path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if not ln.startswith("$POS,"):
                continue
            p = ln.strip().split(",")
            if len(p) < 17:
                continue
            rows.append(dict(t=float(p[1]), lat=float(p[8]), lon=float(p[9]),
                             h=float(p[10]), ns=int(p[12]), urv=float(p[13]),
                             ure=float(p[14]), un=float(p[15])))
    return rows


def enu_err(r):
    dn = (r["lat"] - TRUTH_LAT) * M_PER_DEG
    de = (r["lon"] - TRUTH_LON) * M_PER_DEG * math.cos(math.radians(TRUTH_LAT))
    du = r["h"] - TRUTH_H
    return dn, de, du


def summarize(tag, log_path):
    try:
        rows = parse_pos(log_path)
    except FileNotFoundError:
        print(f"{tag:28s}  (log missing)")
        return None
    if not rows:
        print(f"{tag:28s}  (no $POS rows)")
        return None
    n = min(10, len(rows))
    st = rows[-n:]
    dns = [enu_err(r)[0] for r in st]
    des = [enu_err(r)[1] for r in st]
    dus = [enu_err(r)[2] for r in st]
    mn, me, mu = statistics.fmean(dns), statistics.fmean(des), statistics.fmean(dus)
    d3_all = [math.sqrt(enu_err(r)[0]**2 + enu_err(r)[1]**2 + enu_err(r)[2]**2)
              for r in rows]
    hr = math.hypot(mn, me)
    print(f"{tag:28s} epochs={len(rows):3d} firstFIX={rows[0]['t']:5.1f}s "
          f"ns={rows[-1]['ns']} | mean(last{n}): N{mn:+6.2f} E{me:+6.2f} U{mu:+6.2f} "
          f"horiz={hr:6.2f} 3D={math.sqrt(hr*hr+mu*mu):6.2f} | "
          f"std N{statistics.pstdev(dns):5.2f} E{statistics.pstdev(des):5.2f} "
          f"U{statistics.pstdev(dus):5.2f} | min3D={min(d3_all):5.2f}")
    return dict(tag=tag, epochs=len(rows), first=rows[0]["t"], ns=rows[-1]["ns"],
                n=mn, e=me, u=mu, horiz=hr, d3=math.sqrt(hr*hr+mu*mu),
                min3d=min(d3_all))


if __name__ == "__main__":
    base = "D:/workbuddy/GNSSSignal/gnss-sim/output/e1e5a_dualfreq/"
    cases = [("E1B single-freq baseline", "e1b_base.log"),
             ("E1B single-freq scene-match", "e1b_match.log"),
             ("E1+E5a dual-freq IFLC", "iflc_fixA.log"),
             ("IFLC + tropo-off (diag)", "iflc_tropoff.log")]
    if len(sys.argv) > 1:  # 覆盖为 (tag, file) 对
        cases = [(sys.argv[i], sys.argv[i + 1]) for i in range(1, len(sys.argv), 2)]
    out = []
    for tag, fn in cases:
        r = summarize(tag, base + fn)
        if r:
            out.append(r)
    # markdown 表（便于直接贴 results.md）
    print("\n| 口径 | 解数 | 首FIX(s) | ns | N(m) | E(m) | U(m) | 水平(m) | 3D(m) | min3D(m) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in out:
        print(f"| {r['tag']} | {r['epochs']} | {r['first']:.0f} | {r['ns']} | "
              f"{r['n']:+.2f} | {r['e']:+.2f} | {r['u']:+.2f} | {r['horiz']:.2f} | "
              f"{r['d3']:.2f} | {r['min3d']:.2f} |")
