# -*- coding: utf-8 -*-
"""PocketSDR 配置实验分析：解析 $POS 日志与 stdout，对真值统计 N/E/U。
真值（Tampere）: lat 60.182537, lon 24.82826, 椭高 47.248 m。
"""
import math
import re
import statistics
import sys

TRUTH_LAT, TRUTH_LON, TRUTH_H = 60.182537, 24.82826, 47.248
M_PER_DEG = 111320.0


def parse_pos(log_path):
    """返回 [(t, lat, lon, h, ns, urv, ure, un, dtr)]"""
    rows = []
    with open(log_path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if not ln.startswith("$POS,"):
                continue
            p = ln.strip().split(",")
            # $POS,time,y,m,d,h,mi,s, lat, lon, h, 5, ns, urv, ure, un, dtr
            rows.append(dict(t=float(p[1]), lat=float(p[8]), lon=float(p[9]),
                             h=float(p[10]), ns=int(p[12]),
                             urv=float(p[13]), ure=float(p[14]),
                             un=float(p[15]), dtr=float(p[16])))
    return rows


def enu_err(r):
    dn = (r["lat"] - TRUTH_LAT) * M_PER_DEG
    de = (r["lon"] - TRUTH_LON) * M_PER_DEG * math.cos(math.radians(TRUTH_LAT))
    du = r["h"] - TRUTH_H
    return dn, de, du


def summarize(tag, log_path):
    rows = parse_pos(log_path)
    print(f"\n===== {tag}: {log_path} =====")
    if not rows:
        print("  (no $POS rows)")
        return
    n = min(10, len(rows))
    stable = rows[-n:]
    print(f"  epochs={len(rows)}  last_ts={rows[-1]['t']:.1f}s  "
          f"ns(last)={rows[-1]['ns']}  URV(last)={rows[-1]['urv']:.2f}")
    for key, fmt in (("lat", "%.9f"), ("lon", "%.9f"), ("h", "%.3f")):
        vals = [r[key] for r in stable]
        print(f"  {key:3s}: mean={format(statistics.fmean(vals), fmt.lstrip('%'))}  "
              f"std={statistics.pstdev(vals):.6f}")
    dns = [enu_err(r)[0] for r in stable]
    des = [enu_err(r)[1] for r in stable]
    dus = [enu_err(r)[2] for r in stable]
    print(f"  N err mean={statistics.fmean(dns):+.3f} m  (std {statistics.pstdev(dns):.3f})")
    print(f"  E err mean={statistics.fmean(des):+.3f} m  (std {statistics.pstdev(des):.3f})")
    print(f"  U err mean={statistics.fmean(dus):+.3f} m  (std {statistics.pstdev(dus):.3f})")
    hr = math.hypot(statistics.fmean(dns), statistics.fmean(des))
    print(f"  horiz(mean)={hr:.3f} m")


def parse_stdout(out_path):
    """stdout trace 行: 'HH:MM:SS lat lon h stat ns/nsat DTR=..'"""
    fix, lock = [], []
    try:
        with open(out_path, encoding="utf-8", errors="ignore") as f:
            for ln in f:
                if " FIX " in ln or ln.rstrip().endswith("FIX"):
                    fix.append(ln.rstrip())
                m = re.search(r"LOCK:\s*(\d+)/(\d+)", ln)
                if m:
                    lock.append(ln.rstrip())
    except FileNotFoundError:
        pass
    return fix, lock


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    for tag, stem in (("baseline(original: atmo-on+clk-on)", "bl2"),
                      ("scene-match(both-off+clk-on)", "bo2"),
                      ("satclk_off(both-off+clk-off)", "sco")):
        summarize(tag, f"{base}/{stem}.log")
        fix, lock = parse_stdout(f"{base}/{stem}.stdout.txt")
        print(f"  FIX epochs={len(fix)}; last FIX line: {fix[-1] if fix else 'NONE'}")
        if lock:
            print(f"  LOCK(last): {lock[-1]}")
