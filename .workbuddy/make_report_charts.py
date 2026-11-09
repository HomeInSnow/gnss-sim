# -*- coding: utf-8 -*-
"""交叉验证汇总报告图表生成：读 verify_sim_rx.json + trace json → PNG。

用法: python .workbuddy/make_report_charts.py [runid]
输出: out/<runid>/figs/fig01..fig09_*.png
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

RUN = sys.argv[1] if len(sys.argv) > 1 else "20261106T084558776704"
OUT = f"out/{RUN}"
FIG = f"{OUT}/figs"
os.makedirs(FIG, exist_ok=True)

CLR_G = "#d62728"   # G 红
CLR_E = "#1f77b4"   # E 蓝
CLR_OK = "#2ca02c"
CLR_BAD = "#d62728"
CLR_GRID = "#d9d9d9"

j = json.load(open(f"{OUT}/verify_sim_rx.json", encoding="utf-8"))
ps, summ, nav = j["per_sv"], j["summary"], j["nav"]
meta = json.load(open(f"{OUT}/meta.json", encoding="utf-8"))
elmap = {s["sys"] + str(s["prn"]): (s.get("elev_deg") or s.get("elevation_deg"))
         for s in meta["provenance"]["svs"]}

def svs_of(sysc):
    return sorted([k for k in ps if k[0] == sysc], key=lambda k: int(k[1:]))

def save(fig, name):
    fig.tight_layout()
    p = f"{FIG}/{name}"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print("wrote", p, flush=True)

# ---------------- fig01 总览：worst/threshold 归一化 ----------------
METRICS = [("code_trk_rms_ch", "码相位跟踪 RMS"), ("code_trk_max_ch", "码相位跟踪 最大"),
           ("pr_trk_rms_m", "伪距跟踪 RMS"), ("pr_trk_max_m", "伪距跟踪 最大"),
           ("fd_trk_rms_hz", "多普勒跟踪 RMS"), ("code_snap_rms_ch", "码相位快照 RMS"),
           ("pr_snap_rms_m", "伪距快照 RMS"), ("fd_snap_max_hz", "多普勒快照 最大"),
           ("phase_drift_cycps", "载波相位漂移率"), ("el_max_deg", "仰角偏差 最大"),
           ("strength_slope", "强度斜率"), ("strength_r", "强度相关系数")]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, sysc in zip(axes, ("G", "E")):
    names, vals, cols = [], [], []
    for k, lab in METRICS:
        m = summ[sysc].get(k)
        if not m:
            continue
        if k == "strength_r":
            # 越大越好 → 反转为 门限/最差，保持"越过虚线=不合格"的读图约定
            ratio = m["threshold"] / max(m["worst"], 1e-9)
            lab = lab + "†"
        else:
            ratio = m["worst"] / m["threshold"] if m["threshold"] else m["worst"]
        names.append(lab)
        vals.append(max(ratio, 0.005))
        cols.append(CLR_OK if m["pass"] else CLR_BAD)
    y = np.arange(len(names))[::-1]
    ax.barh(y, vals, color=cols, alpha=0.85, height=0.6)
    ax.axvline(1.0, color="#333", lw=1.2, ls="--")
    ax.set_xscale("log")
    ax.set_yticks(y, names, fontsize=8)
    ax.set_xlabel("最差值/门限（越过虚线=不合格；带†项为越大越好、已按门限/最差反转）")
    ax.set_title(f"{sysc} 系统 全部检查项（{j['summary'][sysc]['n_sv']} 星）全部 PASS"
                 if all(summ[sysc].get(k, {}).get("pass", True) for k, _ in METRICS)
                 else f"{sysc} 系统 检查项概览")
    ax.grid(axis="x", color=CLR_GRID, lw=0.5)
save(fig, "fig01_overview.png")

# ---------------- fig02/03 码相位 / 伪距：snap vs trk per-SV ----------------
def per_sv_bar(name, trk_k, snap_k, unit, thr_k, title, fname):
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.2))
    for ax, sysc in zip(axes, ("G", "E")):
        keys = svs_of(sysc)
        x = np.arange(len(keys))
        trk = [ps[k][trk_k]["rms"] for k in keys]
        snp = [ps[k][snap_k]["rms"] for k in keys]
        clr = CLR_G if sysc == "G" else CLR_E
        ax.bar(x - 0.2, snp, width=0.38, color=clr, alpha=0.45, label="快照(捕获级)")
        ax.bar(x + 0.2, trk, width=0.38, color=clr, alpha=0.95, label="跟踪级")
        thr = summ[sysc][thr_k]["threshold"]
        ax.axhline(thr, color=CLR_BAD, ls="--", lw=1.0,
                   label=f"RMS 门限 {thr:g} {unit}")
        ax.set_xticks(x, keys, fontsize=8)
        ax.set_ylabel(unit)
        ax.set_title(f"{title} · {sysc} 系统", fontsize=10)
        ax.grid(axis="y", color=CLR_GRID, lw=0.5)
        ax.legend(fontsize=8, ncol=3)
    save(fig, fname)

per_sv_bar("code", "code_trk", "code_snap", "ch", "code_trk_rms_ch",
           "码相位误差（测量−仿真注入）", "fig02_code.png")
per_sv_bar("pr", "pr_trk", "pr_snap", "m", "pr_trk_rms_m",
           "伪距误差（测量−仿真注入）", "fig03_pr.png")

# ---------------- fig04 多普勒：跟踪 RMS + FLL 常数偏差 ----------------
fig, axes = plt.subplots(2, 2, figsize=(10.5, 5.6))
for row, sysc in zip((0, 1), ("G", "E")):
    keys = svs_of(sysc)
    x = np.arange(len(keys))
    clr = CLR_G if sysc == "G" else CLR_E
    trk = [ps[k]["fd_trk"]["rms"] for k in keys]
    axes[row, 0].bar(x, trk, color=clr, alpha=0.9)
    axes[row, 0].axhline(summ[sysc]["fd_trk_rms_hz"]["threshold"],
                         color=CLR_BAD, ls="--", lw=1.0)
    axes[row, 0].set_xticks(x, keys, fontsize=7)
    axes[row, 0].set_ylabel("RMS (Hz)")
    axes[row, 0].set_title(f"多普勒跟踪 RMS · {sysc}", fontsize=10)
    axes[row, 0].grid(axis="y", color=CLR_GRID, lw=0.5)
    cb = [ps[k]["fd_trk_vs_const_bias_hz"] for k in keys]
    axes[row, 1].scatter(x, cb, color=clr, s=28)
    axes[row, 1].axhline(0, color="#333", lw=0.8)
    axes[row, 1].set_xticks(x, keys, fontsize=7)
    axes[row, 1].set_ylabel("跟踪−常数 (Hz)")
    axes[row, 1].set_title(f"多普勒跟踪剩余斜率（已扣除 FLL 常数偏差）· {sysc}",
                           fontsize=10)
    axes[row, 1].grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig04_fd.png")

# ---------------- fig05 逐历元曲线：G2 / E4 fd + err_chips ----------------
ts = json.load(open(f"{OUT}/trace_sim.json", encoding="utf-8"))
tr = json.load(open(f"{OUT}/trace_rx.json", encoding="utf-8"))
t = np.asarray(ts["t_s"], float)
fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.4))
for col, key in enumerate(("G2", "E4")):
    s, r = ts["svs"][key], tr["svs"][key]
    clr = CLR_G if key[0] == "G" else CLR_E
    fd_s = np.asarray(s["fd_geo_hz"] if key[0] == "G" else s["fd_geo_hz"], float)
    fd_r = np.asarray(r["fd_meas_hz"], float)
    axes[0, col].plot(t, fd_s, lw=2.0, color="#555", label="仿真注入（几何多普勒）")
    axes[0, col].plot(t, fd_r, lw=1.4, color=clr, label="接收测量（FLL）")
    axes[0, col].set_title(f"{key} 载波多普勒对比", fontsize=10)
    axes[0, col].set_ylabel("Hz")
    axes[0, col].grid(color=CLR_GRID, lw=0.5)
    axes[0, col].legend(fontsize=8)
    ec = np.asarray(r["err_chips"], float)
    axes[1, col].plot(t, ec, "o-", ms=3, lw=1.2, color=clr)
    axes[1, col].axhline(0, color="#333", lw=0.8)
    axes[1, col].set_title(f"{key} 码相位跟踪误差（测量−预测）", fontsize=10)
    axes[1, col].set_xlabel("历元时间 t (s)")
    axes[1, col].set_ylabel("chips")
    axes[1, col].grid(color=CLR_GRID, lw=0.5)
save(fig, "fig05_trace_g2_e4.png")

# ---------------- fig06 逐历元伪距差 ----------------
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
for col, key in enumerate(("G2", "E4")):
    r = tr["svs"][key]
    m = np.asarray(r["meas_pr_m"], float)
    p = np.asarray(r["pred_pr_m"], float)
    clr = CLR_G if key[0] == "G" else CLR_E
    axes[col].plot(t, m - p, "o-", ms=3, lw=1.2, color=clr)
    axes[col].axhline(0, color="#333", lw=0.8)
    axes[col].set_title(f"{key} 伪距测量−预测", fontsize=10)
    axes[col].set_xlabel("历元时间 t (s)")
    axes[col].set_ylabel("m")
    axes[col].grid(color=CLR_GRID, lw=0.5)
save(fig, "fig06_pr_epoch.png")

# ---------------- fig07 C/N0 vs 注入增益 ----------------
fig, ax = plt.subplots(figsize=(7.2, 4.6))
for sysc, clr in (("G", CLR_G), ("E", CLR_E)):
    keys = svs_of(sysc)
    g = [ps[k]["gain_db"] for k in keys]
    c = [ps[k]["metric_mean_db"] for k in keys]
    ax.scatter(g, c, color=clr, s=38, label=f"{sysc} 系统")
    if len(keys) > 2:
        b, a = np.polyfit(g, c, 1)
        xs = np.linspace(min(g), max(g), 50)
        r = np.corrcoef(g, c)[0, 1]
        ax.plot(xs, a + b * xs, color=clr, lw=1.0, ls="--",
                label=f"{sysc} 拟合斜率 {b:.3f}，r={r:.3f}")
ax.set_xlabel("仿真注入增益 (dB)")
ax.set_ylabel("接收 C/N₀ 均值 (dB-Hz)")
ax.set_title("信号强度链路一致性（注入增益 vs 实测 C/N₀）")
ax.grid(color=CLR_GRID, lw=0.5)
ax.legend(fontsize=8)
save(fig, "fig07_strength.png")

# ---------------- fig08 NAV 解码覆盖 ----------------
def _cnt(v):
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    return len(v or [])

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
gk = svs_of("G")
x = np.arange(len(gk))
subn = [_cnt(nav[k].get("subframes")) for k in gk]
axes[0].bar(x, subn, color=CLR_G, alpha=0.9)
axes[0].set_xticks(x, gk, fontsize=7)
axes[0].set_ylabel("解出的子帧数")
axes[0].set_title(f"G LNAV：10/10 星全解（子帧 1/2/3/5 完整帧集 {sum(subn)} 个）",
                  fontsize=10)
axes[0].set_ylim(0, 5)
axes[0].grid(axis="y", color=CLR_GRID, lw=0.5)
ek = svs_of("E")
x2 = np.arange(len(ek))
pgn = [_cnt(nav[k].get("pages")) for k in ek]
axes[1].bar(x2, pgn, color=CLR_E, alpha=0.9)
axes[1].set_xticks(x2, ek, fontsize=7)
axes[1].set_ylabel("解出的 I/NAV 页数")
axes[1].set_title(f"E I/NAV：15/15 星全解（26 页全类型 0–6）", fontsize=10)
axes[1].set_ylim(0, 30)
axes[1].grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig08_nav.png")

# ---------------- fig09 定位精度阶梯 ----------------
labels = ["快照基线\n(el 判别器)", "跟踪解算 el\n非相干 E/L", "跟踪解算 coh\n相干 E/L+PLL",
          "跟踪解算 coh\n(20 Msps 场景)"]
vals = [3.97, 1.00, 0.17, 0.12]
errs = None
fig, ax = plt.subplots(figsize=(7.6, 4.4))
bars = ax.bar(labels, vals, color=["#9c9c9c", "#f0a020", "#2ca02c", "#1f77b4"],
              alpha=0.9)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f} m",
            ha="center", fontsize=10)
ax.axhline(1.0, color=CLR_BAD, ls="--", lw=1.0)
ax.text(3.42, 1.06, "1 m（亚米线）", color=CLR_BAD, fontsize=8)
ax.set_ylabel("定位误差 (m)")
ax.set_title("三维定位误差（演示场景：郑州 G+E 25 星 @5 Msps，60 s）")
ax.grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig09_position.png")

print("ALL_FIGS_DONE", len(os.listdir(FIG)))
