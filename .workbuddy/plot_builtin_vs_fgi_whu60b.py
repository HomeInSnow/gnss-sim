# -*- coding: utf-8 -*-
"""内置跟踪解 vs FGI-GSRx 全量对比图（任务⑧改正后场景 whu60b）。

用法: python plot_builtin_vs_fgi_whu60b.py [fgi_prefix] [trk_json_stem]
默认 fgi_prefix=fgi_whu60b, trk_json_stem=trk_20261113T033315803665_coh
输出（out/fgi/）：cmp_whu60b_enu_ts.png / cmp_whu60b_errbar.png / cmp_whu60b_cn0.png
"""
import json, csv, pathlib, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = pathlib.Path("D:/workbuddy/GNSSSignal/gnss-sim")
FGI = ROOT / "out" / "figi_placeholder" if False else ROOT / "out" / "fgi"
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "fgi_whu60b"
STEM = sys.argv[2] if len(sys.argv) > 2 else "trk_20261113T033315803665_coh"
TAG = PREFIX.replace("fgi_", "")

stats = json.loads((FGI / f"{PREFIX}_stats.json").read_text())
trk = json.loads((pathlib.Path(__file__).with_name(f"{STEM}.json")).read_text())
marker = tuple(trk["marker"])

import importlib
geometry = importlib.import_module("backend.geometry")
sys.path.insert(0, str(ROOT))

def enu(llh, ecef):
    ref = np.array(geometry.llh_to_ecef(*llh))
    lat, lon = np.radians(llh[0]), np.radians(llh[1])
    R = np.array([[-np.sin(lon), np.cos(lon), 0],
                  [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)],
                  [np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]])
    return R @ (np.asarray(ecef) - ref)

rows = [r for r in csv.DictReader(open(FGI / f"{PREFIX}_nav.csv"))
        if int(r["bvalid"]) == 1]
ep = np.array([int(r["epoch"]) for r in rows], float)
ecef = np.array([[float(r["x"]), float(r["y"]), float(r["z"])] for r in rows])
enu_fgi = np.stack([enu(marker, e) for e in ecef])
trk_e = enu(marker, trk["tracked"]["ecef"])

# ---- 图 A: FGI ENU 时序 + 内置单点参考线
fig, axes = plt.subplots(3, 1, figsize=(8.6, 6.4), sharex=True)
for ax, k, lab in zip(axes, range(3), ("E", "N", "U")):
    ax.plot(ep, enu_fgi[:, k], "o-", ms=4, lw=1, color="#1f77b4",
            label=f"FGI-GSRx（{len(rows)} 有效解）")
    ax.axhline(trk_e[k], color="#d62728", lw=1.6, ls="--",
               label=f"内置跟踪解 {trk_e[k]:+.2f} m")
    ax.axhline(stats["paper"]["mean_enu"][k], color="#7f7f7f", lw=1.0, ls=":",
               label=f"论文均值 {stats['paper']['mean_enu'][k]:+.2f} m")
    ax.set_ylabel(f"{lab} 误差 (m)")
    ax.grid(alpha=.3); ax.legend(fontsize=8, loc="upper right")
axes[-1].set_xlabel("FGI 历元号（≈s，5 s 跟踪预热后起算）")
axes[0].set_title(f"内置跟踪解 vs FGI-GSRx 全量 ENU 误差（改正后 whu60b：sv_clock=true + 线性区，Tampere 60 s）")
fig.tight_layout(); fig.savefig(FGI / f"cmp_{TAG}_enu_ts.png", dpi=140); plt.close(fig)

# ---- 图 B: 误差指标条形对比
h_fgi, v_fgi, d3_fgi = stats["h_rmse"], stats["v_rmse"], stats["d3_rmse"]
trk_h = float(np.hypot(trk_e[0], trk_e[1])); trk_v = float(abs(trk_e[2])); trk_d3 = float(np.linalg.norm(trk_e))
base_e = trk["baseline"]["error_m"]
labels = ["水平误差 (m)", "垂直误差 (m)", "3D 误差 (m)"]
x = np.arange(3); w = 0.27
fig, ax = plt.subplots(figsize=(8.6, 4.0))
b1 = ax.bar(x - w, [trk_h, trk_v, trk_d3], w, label=f"内置跟踪解（coh, {trk['track_s']:.0f} s 会话）", color="#d62728")
b2 = ax.bar(x, [h_fgi, v_fgi, d3_fgi], w, label="FGI-GSRx 全量（RMSE）", color="#1f77b4")
b3 = ax.bar(x + w, [stats["paper"]["h_rmse"], stats["paper"]["v_rmse"], stats["paper"]["d3_rmse"]], w,
            label="论文表 19（RMSE，含大气/干扰）", color="#7f7f7f")
for bs in (b1, b2, b3):
    for b in bs:
        ax.annotate(f"{b.get_height():.2f}", (b.get_x()+b.get_width()/2, b.get_height()),
                    ha="center", va="bottom", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_yscale("log")
ax.set_ylim(0.05, 10); ax.grid(axis="y", alpha=.3, which="both")
ax.set_title(f"误差指标对比（改正后场景；内置快照基线 3D={base_e:.2f} m 仅作参考）")
ax.legend(fontsize=9, loc="upper left")
fig.tight_layout(); fig.savefig(FGI / f"cmp_{TAG}_errbar.png", dpi=140); plt.close(fig)

# ---- 图 C: 逐星 C/N0
sats = stats["cn0_sats"]
prns = sorted(sats, key=lambda k: -sats[k]["mean"])
mean = np.array([sats[p]["mean"] for p in prns])
std = np.array([sats[p]["std"] for p in prns])
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ax.bar(range(len(prns)), mean, yerr=std, capsize=3, color="#2ca02c", alpha=.85)
ax.axhline(44.86, color="#d62728", lw=1.5, ls="--", label="引擎名义注入 44.86 dB-Hz（解析）")
ax.axhline(stats["paper"]["mean_cn0"], color="#7f7f7f", lw=1.2, ls=":",
           label="论文均值 44.85（同一 FGI 估计器读数）")
ax.set_xticks(range(len(prns))); ax.set_xticklabels(prns, fontsize=8)
ax.set_ylabel("C/N$_0$ (dB-Hz)"); ax.set_ylim(30, 50)
ax.set_title(f"FGI 逐星 C/N$_0$（改正后 whu60b，总均值 {stats['cn0_grand_mean']:.2f}，n={list(sats.values())[0]['n']}/星）")
ax.grid(axis="y", alpha=.3); ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(FGI / f"cmp_{TAG}_cn0.png", dpi=140); plt.close(fig)

print("built:", {"enu": list(map(float, trk_e)), "err_m": trk["tracked"]["error_m"],
                 "h": trk_h, "v": trk_v, "d3": trk_d3,
                 "pdop": trk["tracked"].get("pdop"), "baseline_d3": base_e,
                 "n_sv": len(trk["tracked"]["prns_used"])})
print("fgi  :", {"h": h_fgi, "v": v_fgi, "d3": d3_fgi, "cn0": stats["cn0_grand_mean"],
                "mean_enu": stats["mean_enu"]})
print("pngs -> ", *[str(FGI / f"cmp_{TAG}_{s}.png") for s in ("enu_ts","errbar","cn0")])
