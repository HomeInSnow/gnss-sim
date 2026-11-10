# -*- coding: utf-8 -*-
"""信号仿真精度评估报告图表生成（无大气/无卫星钟差口径，coh 跟踪）。

与 make_report_charts.py 同源，数据源换为"剥离电离层/对流层/卫星钟差注入"
的新 run：verify_sim_rx.json + tracking_fix_coh.json + trace_sim/trace_dll.json。
差异：① 每图右下角加口径声明水印；② fig03/fig09 纵轴按数据自适应；
③ fig08 标题动态化（不再硬编码 15/15）。

用法: python .workbuddy/make_report_charts_noclock.py [runid]
输出: out/<runid>/figs/fig01..fig09_*.png
"""
import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

RUN = sys.argv[1] if sys.argv and len(sys.argv) > 1 else "20261110T020937303125"
OUT = f"out/{RUN}"
FIG = f"{OUT}/figs"
os.makedirs(FIG, exist_ok=True)

CLR_G = "#d62728"   # G 红
CLR_E = "#1f77b4"   # E 蓝
CLR_OK = "#2ca02c"
CLR_BAD = "#d62728"
CLR_GRID = "#d9d9d9"
BADGE = "口径：生成侧不注入电离层/对流层/卫星钟差 · 接收侧对称不扣除（TGD/BGD 群延迟保留）· 相干 E/L + Costas PLL 跟踪"

j = json.load(open(f"{OUT}/verify_sim_rx.json", encoding="utf-8"))
ps, summ, nav = j["per_sv"], j["summary"], j["nav"]
fx = json.load(open(f"{OUT}/tracking_fix_coh.json", encoding="utf-8"))
assert fx.get("dll_mode") == "coh", "tracking_fix_coh.json 必须是 coh 口径"
meta = json.load(open(f"{OUT}/meta.json", encoding="utf-8"))
cfg = meta.get("config", {})
assert cfg.get("sv_clock") is False and cfg.get("atmosphere", {}).get(
    "ionosphere") == "off", "meta.json 应为无大气/无钟差策略"


def svs_of(sysc):
    return sorted([k for k in ps if k[0] == sysc], key=lambda k: int(k[1:]))


def save(fig, name):
    fig.tight_layout()
    fig.text(0.995, 0.005, BADGE, ha="right", va="bottom", fontsize=6,
             color="#888888")
    p = f"{FIG}/{name}"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print("wrote", p, flush=True)


def nice_ylim(vals, floor=0.75, k=1.3):
    """按数据自适应纵轴对称范围（≥floor，向上取 0.05 的整倍数）。"""
    m = max(floor, k * float(np.max(np.abs(vals))) if len(vals) else floor)
    return math.ceil(m / 0.05) * 0.05


# ---------------- fig01 总览：coh 检查项 worst/threshold 归一化 -------------
METRICS = [("code_trk_rms_ch", "码相位跟踪 RMS"), ("code_trk_max_ch", "码相位跟踪 最大"),
           ("pr_trk_rms_m", "伪距跟踪 RMS"), ("pr_trk_max_m", "伪距跟踪 最大"),
           ("fd_trk_rms_hz", "多普勒跟踪 RMS"),
           ("phase_drift_cycps", "载波相位漂移率"), ("el_max_deg", "仰角偏差 最大"),
           ("strength_slope", "强度斜率"), ("strength_r", "强度相关系数")]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
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
        elif k == "el_max_deg":
            ratio = max(m["worst"], 0.005) / m["threshold"]
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
    ax.set_title(f"{sysc} 系统 相干跟踪检查项（{summ[sysc]['n_sv']} 星）全部 PASS"
                 if all(summ[sysc].get(k, {}).get("pass", True) for k, _ in METRICS)
                 else f"{sysc} 系统 检查项概览")
    ax.grid(axis="x", color=CLR_GRID, lw=0.5)
save(fig, "fig01_overview.png")


# ---------------- fig02 码相位跟踪误差逐星（coh，去常数后 RMS）-------------
fig, axes = plt.subplots(2, 1, figsize=(9.5, 5.6))
for ax, sysc in zip(axes, ("G", "E")):
    keys = svs_of(sysc)
    x = np.arange(len(keys))
    clr = CLR_G if sysc == "G" else CLR_E
    trk = [ps[k]["code_trk"]["rms"] for k in keys]
    ax.bar(x, trk, color=clr, alpha=0.9, width=0.6)
    thr = summ[sysc]["code_trk_rms_ch"]["threshold"]
    ax.axhline(thr, color=CLR_BAD, ls="--", lw=1.0, label=f"RMS 门限 {thr:g} ch")
    mean = summ[sysc]["code_trk_rms_ch"]["mean"]
    ax.axhline(mean, color="#555", ls=":", lw=1.0, label=f"系统均值 {mean:.4f} ch")
    ax.set_xticks(x, keys, fontsize=8)
    ax.set_ylabel("ch")
    ax.set_title(f"码相位跟踪误差（测量−仿真注入，去常数）· {sysc} 系统", fontsize=10)
    ax.grid(axis="y", color=CLR_GRID, lw=0.5)
    ax.legend(fontsize=8, ncol=2)
save(fig, "fig02_code.png")


# ---------------- fig03 逐星伪距误差（coh 跟踪解算 LS 测量列）--------------
fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.0))
fsv = fx["per_sv"]
all_err = [fsv[k]["err_avg_m"] for k in fsv if fsv[k].get("err_avg_m") is not None]
ylim3 = nice_ylim(all_err)
for ax, sysc in zip(axes, ("G", "E")):
    keys = svs_of(sysc)
    x = np.arange(len(keys))
    clr = CLR_G if sysc == "G" else CLR_E
    vals = [fsv[k]["err_avg_m"] for k in keys]
    ax.bar(x, vals, color=clr, alpha=0.9, width=0.6)
    for lim in (0.2, -0.2):
        ax.axhline(lim, color="#333", ls="--", lw=1.0)
    e_ = np.array(vals)
    rms = float(np.sqrt(np.mean(e_ ** 2)))
    ax.set_xticks(x, keys, fontsize=8)
    ax.set_ylabel("m")
    ax.set_ylim(-ylim3, ylim3)
    ax.text(0.02, 0.86, f"RMS {rms:.3f} m　均值|·| {np.mean(np.abs(e_)):.3f} m　"
                        f"最差 {np.max(np.abs(e_)):.3f} m",
            transform=ax.transAxes, fontsize=9,
            bbox=dict(fc="white", ec="#bbb", alpha=0.85))
    ax.set_title(f"逐星伪距误差（会话中值 → LS 测量，虚线 ±0.2 m）· {sysc} 系统",
                 fontsize=10)
    ax.grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig03_pr.png")

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
    axes[row, 1].set_title(f"多普勒跟踪剩余（已扣除 FLL 常数偏差）· {sysc}",
                           fontsize=10)
    axes[row, 1].grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig04_fd.png")

# ---------------- fig05 逐历元曲线（coh 会话）：G2 / E4 fd + 码相位 ------
ts = json.load(open(f"{OUT}/trace_sim.json", encoding="utf-8"))
td = json.load(open(f"{OUT}/trace_dll.json", encoding="utf-8"))
t = np.asarray(ts["t_s"], float)
fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.4))
for col, key in enumerate(("G2", "E4")):
    s, d = ts["svs"][key], td["svs"][key]
    clr = CLR_G if key[0] == "G" else CLR_E
    fd_s = np.asarray(s["fd_geo_hz"], float)
    fd_r = np.asarray(d["fd_meas_hz"], float)
    axes[0, col].plot(t, fd_s, lw=2.0, color="#555", label="仿真注入（几何多普勒）")
    axes[0, col].plot(t, fd_r, lw=1.4, color=clr, label="跟踪环路（PLL/FLL）")
    axes[0, col].set_title(f"{key} 载波多普勒对比（相干跟踪）", fontsize=10)
    axes[0, col].set_ylabel("Hz")
    axes[0, col].grid(color=CLR_GRID, lw=0.5)
    axes[0, col].legend(fontsize=8)
    chip_hz = float(d["chip_hz"])
    code_len = float(d["code_len"])
    chi = np.asarray(d["chi_chips"], float)
    truth_pr = np.asarray(s["pr_truth_m"], float)
    truth_ch = np.mod(truth_pr / 299792458.0 * chip_hz, code_len)
    e = (chi - truth_ch + code_len / 2) % code_len - code_len / 2
    e = e - np.median(e)          # 每星常数=捕获牵引偏置，另行审计
    axes[1, col].plot(t, e, "o-", ms=3, lw=1.2, color=clr)
    axes[1, col].axhline(0, color="#333", lw=0.8)
    axes[1, col].axhline(0.02, color=CLR_BAD, ls="--", lw=0.8)
    axes[1, col].axhline(-0.02, color=CLR_BAD, ls="--", lw=0.8)
    axes[1, col].set_title(f"{key} 码相位跟踪误差（去常数，虚线±0.02 ch门限）",
                           fontsize=10)
    axes[1, col].set_xlabel("历元时间 t (s)")
    axes[1, col].set_ylabel("chips")
    axes[1, col].grid(color=CLR_GRID, lw=0.5)
save(fig, "fig05_trace_g2_e4.png")

# ---------------- fig06 逐历元伪距抖动（coh 会话，去常数）----------------
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
for col, key in enumerate(("G2", "E4")):
    s, d = ts["svs"][key], td["svs"][key]
    m = np.asarray(d["meas_pr_m"], float)
    p = np.asarray(s["pr_truth_m"], float)
    e = m - p
    e = e - np.median(e)
    clr = CLR_G if key[0] == "G" else CLR_E
    axes[col].plot(t, e, "o-", ms=3, lw=1.2, color=clr)
    axes[col].axhline(0, color="#333", lw=0.8)
    axes[col].set_title(f"{key} 伪距抖动（测量−仿真真值，去常数）", fontsize=10)
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
ax.set_ylabel("接收 C/N0 均值 (dB-Hz)")
ax.set_title("信号强度链路一致性（注入增益 vs 实测 C/N0）")
ax.grid(color=CLR_GRID, lw=0.5)
ax.legend(fontsize=8)
save(fig, "fig07_strength.png")

# ---------------- fig08 NAV 解码覆盖（标题动态）----------------
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
gnav = summ["G"]["nav"]
axes[0].set_title(f"G LNAV：{gnav['decoded']}/{gnav['of']}"
                  f" 星全解（子帧 1/2/3/5 完整帧集）", fontsize=10)
axes[0].set_ylim(0, 5)
axes[0].grid(axis="y", color=CLR_GRID, lw=0.5)
ek = svs_of("E")
x2 = np.arange(len(ek))
pgn = [_cnt(nav[k].get("pages")) for k in ek]
axes[1].bar(x2, pgn, color=CLR_E, alpha=0.9)
axes[1].set_xticks(x2, ek, fontsize=7)
axes[1].set_ylabel("解出的 I/NAV 页数")
enav = summ["E"]["nav"]
maxpg = int(np.nanmax(np.array(pgn, float))) if pgn else 0
axes[1].set_title(f"E I/NAV：{enav['decoded']}/{enav['of']} 星全解"
                  f"（单星最多 {maxpg} 页）", fontsize=10)
axes[1].set_ylim(0, 30)
axes[1].grid(axis="y", color=CLR_GRID, lw=0.5)
save(fig, "fig08_nav.png")

# ---------------- fig09 coh 跟踪解算定位结果 ----------------
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2),
                         gridspec_kw={"width_ratios": [1, 1.4]})
e_, n_, u_ = fx["enu_m"]
labels = ["东 E", "北 N", "天 U"]
vals = [e_, n_, u_]
ylim9 = nice_ylim(vals, floor=0.2, k=1.35)
bars = axes[0].bar(labels, vals, color=["#f0a020", "#2ca02c", "#1f77b4"],
                  alpha=0.9, width=0.55)
for b, v in zip(bars, vals):
    axes[0].text(b.get_x() + b.get_width() / 2, v + (0.006 if v >= 0 else -0.016),
                 f"{v:+.3f} m", ha="center", fontsize=9)
axes[0].axhline(0, color="#333", lw=0.8)
axes[0].set_ylim(-ylim9, ylim9)
axes[0].set_ylabel("定位误差分量 (m)")
axes[0].set_title(f"定位误差 ENU 分量\n三维 {fx['error_m']:.3f} m · PDOP "
                  f"{fx['pdop']:.2f} · 残差RMS {fx['residual_rms_m']:.3f} m · "
                  f"{fx['n_sv']} 星", fontsize=10)
axes[0].grid(axis="y", color=CLR_GRID, lw=0.5)

ax = axes[1]
pts_all = []
for sysc, clr in (("G", CLR_G), ("E", CLR_E)):
    pts = [(fsv[k]["el_deg"], fsv[k]["err_avg_m"]) for k in svs_of(sysc)
           if fsv[k].get("err_avg_m") is not None]
    el_, er_ = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    pts_all.append(er_)
    ax.scatter(el_, er_, color=clr, s=38,
               label=f"{sysc} RMS {np.sqrt(np.mean(er_**2)):.3f} m")
for lim in (0.2, -0.2):
    ax.axhline(lim, color="#333", ls="--", lw=1.0)
ax.axhline(0, color="#999", lw=0.6)
ax.set_ylim(-nice_ylim(np.concatenate(pts_all)), nice_ylim(np.concatenate(pts_all)))
ax.set_xlabel("卫星仰角 (°)")
ax.set_ylabel("伪距误差 (m)")
ax.set_title("逐星伪距误差（会话中值）vs 仰角（虚线 ±0.2 m 参考）", fontsize=10)
ax.grid(color=CLR_GRID, lw=0.5)
ax.legend(fontsize=8)
save(fig, "fig09_position.png")

print("ALL_FIGS_DONE", len(os.listdir(FIG)))
