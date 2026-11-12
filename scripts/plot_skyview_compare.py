# -*- coding: utf-8 -*-
"""天空视图三面板对比：论文 Fig.23(b) vs 引擎实生 12 星（武大广播星历 run）。

用法: python scripts/plot_skyview_compare.py [runid]
默认 runid=20261112T081838822389（2023-09-28 23:20:00 UTC, Tampere, 60s@25M,
广播星历源=武汉大学 IGS 数据中心 FTP, 12 星含 G28）。
输出: out/skyview/sky_view_compare.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
runid = sys.argv[1] if len(sys.argv) > 1 else "20261112T081838822389"
thesis_png = ROOT / ".workbuddy" / "pdf_thesis" / "fig23b_crop.png"
out = ROOT / "out" / "skyview" / "sky_view_compare.png"
out.parent.mkdir(parents=True, exist_ok=True)

trace = json.load(open(ROOT / "out" / runid / "trace_sim.json", encoding="utf-8"))
svs = trace["svs"]
# 论文 Fig.31 图例清单（12 星）
PAPER_SVS = {"G9", "G18", "G4", "G5", "G12", "G26", "G20",
             "G11", "G31", "G28", "G25", "G29"}


def sky_axes(ax, title):
    ax.set_title(title, fontsize=11, pad=10)
    for el in (0, 30, 60):
        ax.add_patch(plt.Circle((0, 0), 1 - el / 90.0, fill=False,
                                color="#bbbbbb", lw=0.8, zorder=1))
    for az in range(0, 360, 30):
        a = np.deg2rad(az)
        # 天空图约定：圆心=天顶90°，外圈=地平0°，北在上方、方位顺时针
        ax.plot([0, np.sin(a)], [0, np.cos(a)], color="#dddddd", lw=0.6, zorder=1)
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.25, 1.25)
    ax.set_aspect("equal"); ax.axis("off")
    for az, lab in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
        a = np.deg2rad(az)
        ax.text(1.12 * np.sin(a), 1.12 * np.cos(a), lab,
                ha="center", va="center", fontsize=10, color="#555555")
    ax.text(0.02, 0.02, "90°", fontsize=7, color="#999999")


fig, axes = plt.subplots(1, 3, figsize=(16.5, 6.2))

# ① 论文 Fig.23(b) 原图裁剪
if thesis_png.exists():
    axes[0].imshow(plt.imread(str(thesis_png)), interpolation="lanczos")
    axes[0].set_title("① 论文 Fig.23(b) Skydel 仿真天空图\n(Pääkkönen 2024, p.65)",
                      fontsize=11, pad=10)
    axes[0].axis("off")
else:
    axes[0].axis("off")
    axes[0].text(0.5, 0.5, "fig23b_crop.png 缺失", ha="center")

# ② 引擎实生（本 run，12 星，全部真实生成）
sky_axes(axes[1], f"② gnss-sim 实生信号（武大广播星历，{runid}）")
rows = []
for k in sorted(svs, key=lambda s: -svs[s]["el_deg_t"][0]):
    el, az = svs[k]["el_deg_t"][0], svs[k]["az_deg_t"][0]
    r = 1 - min(max(el, 0.0), 90.0) / 90.0
    a = np.deg2rad(az)
    x, y = r * np.sin(a), r * np.cos(a)
    axes[1].scatter([x], [y], s=170, color="#1f77b4", zorder=3,
                    edgecolor="white", linewidth=1.2)
    axes[1].text(x, y, k[0] + k[1:].lstrip("0"), ha="center", va="center",
                 fontsize=7.5, color="white", zorder=4)
    rows.append((k, el, az))
axes[1].text(0, -1.18,
             "起算历元 el/az：" + "  ".join(f"{k}:{el:.0f}°/{az:.0f}°"
                                          for k, el, az in rows),
             ha="center", fontsize=6.8, color="#444444")

# ③ 逐星对比表（论文图31图例 vs 引擎实生）
ax3 = axes[2]; ax3.axis("off")
ax3.set_title("③ 卫星清单核对（论文 Fig.31 图例 vs 引擎实生）",
              fontsize=11, pad=10)
ax3.text(0.5, 0.96, "论文 12 星: 9·18·4·5·12·26·20·11·31·28·25·29",
         ha="center", fontsize=10, transform=ax3.transAxes)
gen = set(svs)
common = PAPER_SVS & gen
missing = PAPER_SVS - gen
extra = gen - PAPER_SVS
ax3.text(0.5, 0.86, f"引擎实生 {len(gen)} 星 · 完全匹配: {len(common)}/12",
         ha="center", fontsize=12, transform=ax3.transAxes, color="#1a7f37",
         weight="bold")
ax3.text(0.5, 0.74, ("缺失: 无" if not missing
                     else "缺失: " + ",".join(sorted(missing))),
         ha="center", fontsize=10, transform=ax3.transAxes)
ax3.text(0.5, 0.66, ("多出: 无" if not extra
                     else "多出: " + ",".join(sorted(extra))),
         ha="center", fontsize=10, transform=ax3.transAxes)
ax3.text(0.5, 0.46,
         "广播星历源: 武汉大学 IGS 数据中心\nftp://igs.gnsswhu.cn\n"
         "BRDC00IGS_R_20232710000_01D_MN\n(含 G28/G21, 当日 14 条完整电文)",
         ha="center", fontsize=9, transform=ax3.transAxes, color="#555555")
fig.suptitle("Skydel 论文场景天空视图 vs gnss-sim 实生信号（UTC 2023-09-28 23:20:00, "
             "Tampere 60.18°N 24.83°E）", fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(str(out), dpi=150, facecolor="white")
print("saved:", out)
print("prns:", sorted(gen), " match:", len(common), "/12")
