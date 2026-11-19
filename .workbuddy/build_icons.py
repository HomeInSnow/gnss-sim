# -*- coding: utf-8 -*-
"""ImageGen 原图 -> 软件 .ico：
1) 中心裁切 3.5%；2) 右下角 AI 水印按列背景色替换清除（自适应检测）；
3) 四角连通白底洪泛转透明；4) 导出多尺寸 .ico。"""
import sys
from collections import deque
from pathlib import Path
from statistics import median

from PIL import Image

SIZES = [256, 128, 64, 48, 32, 24, 16]

JOBS = [
    ("generated-images/Flat_modern_app_icon_for_a_GNS_2026-11-19T04-10-02.png",
     "desktop/assets/app_icon_gnss_sim.png", "desktop/assets/app.ico"),
    ("generated-images/Flat_modern_app_icon_for_a_Poc_2026-11-19T04-10-29.png",
     "pocket_desktop/assets/app_icon_pocket_sdr.png",
     "pocket_desktop/assets/app.ico"),
]


def median_col_bg(px, x, ys):
    cols = [[], [], []]
    for y in ys:
        c = px[x, y]
        for i in range(3):
            cols[i].append(c[i])
    return tuple(median(v) for v in cols)


def clean_watermark(im):
    w, h = im.size
    px = im.load()
    x0, y0 = int(0.82 * w), int(0.87 * h)
    band = range(max(0, y0 - 36), max(1, y0 - 6))
    replaced = 0
    for x in range(x0, w):
        bg = median_col_bg(px, x, band)
        for y in range(y0, h):
            c = px[x, y]
            if any(abs(a - b) > 50 for a, b in zip(c, bg)):
                px[x, y] = tuple(int(v) for v in bg)
                replaced += 1
    return replaced


def flood_transparent(im):
    w, h = im.size
    rgb = im.convert("RGB")
    px = rgb.load()
    corner = px[2, 2]

    def close(c):
        return all(abs(a - b) < 40 for a, b in zip(c, corner))

    alpha = [255] * (w * h)
    q = deque()
    seeds = [(x, y) for x in range(w) for y in (0, h - 1)] + \
            [(x, y) for y in range(h) for x in (0, w - 1)]
    for x, y in seeds:
        if close(px[x, y]):
            idx = y * w + x
            if alpha[idx] == 255:
                alpha[idx] = 0
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if alpha[idx] == 255 and close(px[nx, ny]):
                    alpha[idx] = 0
                    q.append((nx, ny))
    rgba = im.convert("RGBA")
    pa = rgba.load()
    for y in range(h):
        for x in range(w):
            r, g, b, _ = pa[x, y]
            pa[x, y] = (r, g, b, alpha[y * w + x])
    return rgba


def process(src: str, png_out: str, ico_out: str):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    m = int(w * 0.035)
    im = im.crop((m, m, w - m, h - m))
    n = clean_watermark(im)
    rgba = flood_transparent(im)
    Path(png_out).parent.mkdir(parents=True, exist_ok=True)
    rgba.save(png_out)
    rgba.save(ico_out, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"ICON-OK {ico_out} watermark_px_replaced={n}")


for src, png, ico in JOBS:
    process(src, png, ico)
print("BUILD-ICONS-DONE")
