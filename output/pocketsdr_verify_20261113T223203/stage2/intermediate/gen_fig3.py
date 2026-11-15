# -*- coding: utf-8 -*-
"""图3：PVT 配置三态 3D 误差对比（数值全部抄录自 results.md 三态表，无新增数值）。"""
import base64, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))

labels = ["基线\n(大气开+钟差开)", "场景匹配版\n(大气关+钟差留)", "错关钟差对照\n(大气关+钟差关)"]
d3 = [11.41, 0.22, 4.65]
subs = ["N −1.46 E +0.10 U −11.31", "N −0.00 E −0.09 U +0.20", "N +3.16 E +2.41 U +2.37"]
colors = ["#C62828", "#2E7D32", "#EF6C00"]

fig, ax = plt.subplots(figsize=(6.6, 3.0), dpi=150)
x = range(3)
ax.bar(x, d3, color=colors, width=0.55)
for i, v in enumerate(d3):
    ax.text(i, v + 0.28, f"{v:.2f} m", ha="center", fontsize=10,
            color="#212121", fontweight="bold")
    ax.text(i, -0.85, subs[i], ha="center", fontsize=7, color="#616161")
ax.axhline(1.0, color="#9E9E9E", lw=0.8, ls=":")
ax.text(2.42, 1.12, "1 m", fontsize=7, color="#9E9E9E", ha="right")
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("3D 误差（m，末 10 历元均值 vs 真值）", fontsize=9)
ax.set_ylim(-1.6, 13.2)
ax.tick_params(axis="y", labelsize=8)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
p = os.path.join(HERE, "fig_pvt3.png")
fig.savefig(p, facecolor="white", bbox_inches="tight")
plt.close(fig)

with open(p, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")
with open(os.path.join(HERE, "fig3.b64"), "w") as f:
    f.write(b64)
print("fig3.b64", len(b64), "chars")
