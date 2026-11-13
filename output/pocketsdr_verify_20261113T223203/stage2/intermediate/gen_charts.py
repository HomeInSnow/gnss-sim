# -*- coding: utf-8 -*-
"""按 materials_digest.md 中抄录的数字生成报告两张图（无新增数值）。"""
import base64, io, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 图1：A/B 垂直误差对比（数据源：附录 B A/B 表） ----
labels = ["基线\nBRDC+SAAS", "仅电离层关\nIONOOPT_OFF", "仅对流层关\nTROPOPT_OFF", "双关闭\nOFF+OFF"]
vals = [-11.45, -8.79, -2.91, 0.06]
colors = ["#C62828", "#E57373", "#EF9A9A", "#2E7D32"]

fig, ax = plt.subplots(figsize=(6.6, 2.9), dpi=150)
y = range(len(vals))
ax.barh(y, vals, color=colors, height=0.62)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=9)
ax.axvline(0, color="#424242", lw=0.8)
for i, v in enumerate(vals):
    off = -0.55 if v < 0 else 0.15
    ha = "right" if v < 0 else "left"
    ax.text(v + off, i, f"{v:+.2f} m", va="center", ha=ha, fontsize=9,
            color="#212121", fontweight="bold")
ax.set_xlabel("垂直误差（椭高 − 真值 47.248 m，单位 m）", fontsize=9)
ax.set_xlim(-13, 2.5)
ax.tick_params(axis="x", labelsize=8)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.invert_yaxis()
fig.tight_layout()
p1 = os.path.join(HERE, "fig_ab_vertical.png")
fig.savefig(p1, facecolor="white", bbox_inches="tight")
plt.close(fig)

# ---- 图2：逐星 C/N0（数据源：附录 A 逐星表） ----
prns = ["G4", "G5", "G9", "G11", "G12", "G18", "G20", "G25", "G26", "G28", "G29", "G31"]
cn0 = [39.8, 40.9, 38.9, 42.1, 40.2, 40.0, 42.8, 45.1, 43.2, 45.1, 45.9, 43.8]

fig, ax = plt.subplots(figsize=(6.6, 2.7), dpi=150)
ax.bar(prns, cn0, color="#1565C0", width=0.62)
ax.axhline(42.0, color="#2E7D32", lw=1.2, ls="--")
ax.axhline(41.676, color="#EF6C00", lw=1.2, ls=":")
ax.text(11.55, 42.05, "PocketSDR 均值 42.0", fontsize=7.5, color="#2E7D32", ha="right")
ax.text(11.55, 40.95, "FGI-GSRx 均值 41.676", fontsize=7.5, color="#EF6C00", ha="right")
for i, v in enumerate(cn0):
    ax.text(i, v + 0.25, f"{v:.1f}", ha="center", fontsize=7, color="#212121")
ax.set_ylabel("C/N0（dB-Hz）", fontsize=9)
ax.set_ylim(36, 47.5)
ax.tick_params(axis="x", labelsize=8); ax.tick_params(axis="y", labelsize=8)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
p2 = os.path.join(HERE, "fig_cn0.png")
fig.savefig(p2, facecolor="white", bbox_inches="tight")
plt.close(fig)

for src, dst in [(p1, "fig1.b64"), (p2, "fig2.b64")]:
    with open(src, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    with open(os.path.join(HERE, dst), "w") as f:
        f.write(b64)
    print(dst, len(b64), "chars")
print("OK")
