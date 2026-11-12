# -*- coding: utf-8 -*-
"""FGI-GSRx 处理 whu afzero 60s run 的两项对比：
① 逐星 C/N0（图 31 上方面板 L1 C/A，包络 38-50、表18 均值 44.85）
② 定位精度（表19：水平 RMSE 1.2517 / 垂直 2.0823 / 3D 2.4295 m）

输入（由 post_fgi_whu60.m 产出）：
  out/fgi/fgi_whu60_nav.csv   epoch,bvalid,fom,x,y,z,lat,lon,hgt,nrsats
  out/fgi/fgi_whu60_cn0.csv   prn,epoch_ms,cn0,mean_cn0
输出：
  out/fgi/fgi_whu60_compare.png
  out/fgi/fgi_whu60_stats.json
用法: python scripts/plot_fgi_whu60.py
"""
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = "out/fgi"
MARK = (60.182537, 24.82826, 47.248)  # lat deg, lon deg, hgt m (Otaniemi)
# 论文表18/19 权威值
PAPER = dict(mean_cn0=44.85, cn0_lo=38.0, cn0_hi=50.0,
             h_rmse=1.2517, v_rmse=2.0823, d3_rmse=2.4295,
             mean_enu=(-0.2550, -0.0770, -0.6359),
             std_enu=(0.6933, 1.0083, 1.9839), n_sol=892, dur_s=900)


def lla_to_enu(lat, lon, h, ref=MARK):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)

    def prime_v(la):
        return a / math.sqrt(1 - e2 * math.sin(la) ** 2)

    la, lo, = math.radians(lat), math.radians(lon)
    la0, lo0 = math.radians(ref[0]), math.radians(ref[1])
    v0, v = prime_v(la0), prime_v(la)
    x = (v + h) * math.cos(la) * math.cos(lo)
    y = (v + h) * math.cos(la) * math.sin(lo)
    z = (v * (1 - e2) + h) * math.sin(la)
    x0 = (v0 + ref[2]) * math.cos(la0) * math.cos(lo0)
    y0 = (v0 + ref[2]) * math.cos(la0) * math.sin(lo0)
    z0 = (v0 * (1 - e2) + ref[2]) * math.sin(la0)
    dx, dy, dz = x - x0, y - y0, z - z0
    sLa, cLa, sLo, cLo = (math.sin(la0), math.cos(la0),
                          math.sin(lo0), math.cos(lo0))
    e = -sLo * dx + cLo * dy
    n = -sLa * cLo * dx - sLa * sLo * dy + cLa * dz
    u = cLa * cLo * dx + cLa * sLo * dy + sLa * dz
    return e, n, u


def main():
    # ---------- 定位 ----------
    nav = np.genfromtxt(f"{OUT}/fgi_whu60_nav.csv", delimiter=",",
                        names=True)
    nav = np.atleast_1d(nav)
    ok = nav["bvalid"].astype(bool) & np.isfinite(nav["lat"])
    sol = nav[ok]
    enu = np.array([lla_to_enu(r["lat"], r["lon"], r["hgt"]) for r in sol])
    n_sol = len(sol)
    mean_enu = enu.mean(axis=0) if n_sol else np.full(3, np.nan)
    # 论文 RMS 用相对参考点（未去均值），STD 去均值
    rmse = np.sqrt((enu ** 2).mean(axis=0)) if n_sol else np.full(3, np.nan)
    std_enu = enu.std(axis=0) if n_sol else np.full(3, np.nan)
    h_rms = math.hypot(rmse[0], rmse[1])
    v_rms = rmse[2]
    d3_rms = math.sqrt((rmse ** 2).sum())

    # ---------- C/N0 ----------
    # 稳态口径：剔除跟踪拉入期（epoch_ms < 10000），逐星取中位数（对暂态稳健），
    # 与论文表18"仿真期平均"口径对齐。
    cn = np.genfromtxt(f"{OUT}/fgi_whu60_cn0.csv", delimiter=",", names=True)
    cn = np.atleast_1d(cn)
    cn = cn[cn["epoch_ms"] >= 10000]
    prns = sorted(set(int(p) for p in cn["prn"]))
    sv_stats = {}
    for p in prns:
        m = cn["prn"] == p
        v = cn["mean_cn0"][m]
        v = v[(v > 0) & np.isfinite(v)]
        if v.size > 10:
            sv_stats[p] = (float(np.median(v)), float(v.std()), v.size)

    # ---------- 绘图 ----------
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6))

    ax = axes[0]
    if n_sol:
        t = sol["epoch"] * 1.0  # navSolPeriod=1000ms → epoch 号即秒
        ax.plot(t, enu[:, 0], label="E", color="#1f77b4", lw=1)
        ax.plot(t, enu[:, 1], label="N", color="#2ca02c", lw=1)
        ax.plot(t, enu[:, 2], label="U", color="#d62728", lw=1)
        ax.axhline(0, color="#999999", lw=0.6)
        span = int(sol["epoch"].max() - sol["epoch"].min())
    else:
        span = 0
    ax.set_title(f"① FGI 定位 ENU 误差（{n_sol} 解 / 跨 {span}s，1 Hz）\n"
                 f"3D-RMSE {d3_rms:.2f} m（论文 2.43）", fontsize=11)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("ENU 偏差 [m]")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    ax = axes[1]
    keys = sorted(sv_stats, key=lambda p: -sv_stats[p][0])
    x = np.arange(len(keys))
    mvals = [sv_stats[p][0] for p in keys]
    svals = [sv_stats[p][1] for p in keys]
    ax.errorbar(x, mvals, yerr=svals, fmt="o", capsize=3,
                color="#1f77b4", ecolor="#9dc3e6", ms=6, lw=1)
    ax.axhline(PAPER["mean_cn0"], color="#d62728", ls="--", lw=1.2,
               label=f"论文表18均值 {PAPER['mean_cn0']}")
    ax.axhspan(PAPER["cn0_lo"], PAPER["cn0_hi"], color="#d62728", alpha=0.07,
               label="论文图31包络")
    ax.set_xticks(x)
    ax.set_xticklabels([f"G{p}" for p in keys], fontsize=9)
    ax.set_title(f"② FGI 逐星 C/N0 均值±σ（{len(keys)} 星）\n"
                 f"总均值 {np.mean(mvals):.2f} dB-Hz（论文 44.85）", fontsize=11)
    ax.set_ylabel("C/N0 [dB-Hz]")
    ax.set_ylim(36, 53)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[2]
    ax.axis("off")
    rows = [("指标", "FGI 实测", "论文表18/19", "判定")]
    def verdict(fg, pa, tol):
        return "OK" if abs(fg - pa) <= tol else "偏"
    rows.append(("水平 RMSE [m]", f"{h_rms:.2f}", f"{PAPER['h_rmse']:.2f}",
                 verdict(h_rms, PAPER["h_rmse"], 1.5)))
    rows.append(("垂直 RMSE [m]", f"{v_rms:.2f}", f"{PAPER['v_rmse']:.2f}",
                 verdict(v_rms, PAPER["v_rmse"], 2.0)))
    rows.append(("3D RMSE [m]", f"{d3_rms:.2f}", f"{PAPER['d3_rmse']:.2f}",
                 verdict(d3_rms, PAPER["d3_rmse"], 2.5)))
    rows.append(("C/N0 均值 [dB-Hz]", f"{np.mean(mvals):.2f}",
                 f"{PAPER['mean_cn0']}", verdict(np.mean(mvals), PAPER["mean_cn0"], 3)))
    rows.append(("有效解数", f"{n_sol}", f"{PAPER['n_sol']}",
                 f"窗口 {n_sol}s vs 900s"))
    tbl = ax.table(cellText=rows, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1.05, 1.7)
    for j in range(4):
        tbl[0, j].set_facecolor("#e8eef7")
        tbl[0, j].set_text_props(weight="bold")
    ax.set_title("③ 与论文基准对照（口径注：60s vs 900s、无干扰）", fontsize=11)

    fig.suptitle("FGI-GSRx 2.1.3 处理 whu afzero 60s 信号 vs 论文 §6.2/§7.4 基准",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(f"{OUT}/fgi_whu60_compare.png", dpi=150, facecolor="white")

    stats = dict(
        n_sol=int(n_sol),
        mean_enu=[round(v, 4) for v in mean_enu],
        std_enu=[round(v, 4) for v in std_enu],
        rmse_enu=[round(v, 4) for v in rmse],
        h_rmse=round(h_rms, 4), v_rmse=round(v_rms, 4), d3_rmse=round(d3_rms, 4),
        cn0_sats={f"G{p}": dict(mean=round(mvals[i], 3), std=round(svals[i], 3),
                                n=sv_stats[p][2])
                  for i, p in enumerate(keys)},
        cn0_grand_mean=round(float(np.mean(mvals)), 3) if mvals else None,
        cn0_min=round(min(mvals), 3) if mvals else None,
        cn0_max=round(max(mvals), 3) if mvals else None,
        paper=PAPER,
    )
    with open(f"{OUT}/fgi_whu60_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: stats[k] for k in
                     ('n_sol', 'h_rmse', 'v_rmse', 'd3_rmse',
                      'cn0_grand_mean', 'cn0_min', 'cn0_max')},
                     ensure_ascii=False, indent=2))
    print("saved:", f"{OUT}/fgi_whu60_compare.png")


if __name__ == "__main__":
    main()
