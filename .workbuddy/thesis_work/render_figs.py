# -*- coding: utf-8 -*-
"""Render thesis pages & crop figure regions: caption-anchored top search."""
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
import os, re, math

PDF = r"D:/workbuddy/GNSSSignal/gnss-sim-desktop/FGI-GSRx-2.1.3/Documentation/masters_thesis_paakkonen_2024.pdf"
W = r"D:/workbuddy/GNSSSignal/gnss-sim-desktop/.workbuddy/thesis_work"
os.makedirs(W + r"\figs\cand", exist_ok=True)

# figure -> page map (PDF file page numbers, from thesis.md page comments)
FIGS = {1:10, 2:13, 3:15, 4:16, 5:16, 6:29, 7:30, 8:32, 9:34, 10:35, 11:36, 12:38,
        13:41, 14:45, 15:48, 16:49, 17:50, 18:50, 19:51, 20:54, 21:57, 22:58,
        23:65, 24:67, 25:67, 26:69, 27:70, 28:71, 29:73, 30:75, 31:91}
# manual top anchors (search a text line near the top edge of the figure)
ANCHORS = {12: ("AWGN", 16), 20: ("Normalized", 6),
           1: ("Space segment", 4), 4: ("BPSK(1)", 14),
           6: ("IF in", 16), 8: ("True negative", 12)}

SCALE = 200 / 72
doc = pdfium.PdfDocument(PDF)
print("total pages:", len(doc))


def caption_rect(pg, needle):
    tp = pg.get_textpage()
    searcher = tp.search(needle)
    hit = searcher.get_next()
    if hit is None:
        return None
    idx, ln = hit
    l = b = 1e9
    r_ = t = -1e9
    for i in range(idx, idx + ln):
        bl, bb, br, bt = tp.get_charbox(i)
        l = min(l, bl); b = min(b, bb); r_ = max(r_, br); t = max(t, bt)
    return (l, b, r_, t)


def get_lines(pg):
    """Group chars into lines: [(ybot, ytop, x0, x1, ncount, text), ...]."""
    tp = pg.get_textpage()
    n = tp.count_chars()
    chars = []
    for i in range(n):
        l, b, r, t = tp.get_charbox(i)
        if l > r:
            continue
        chars.append((b, t, l, r))
    chars.sort(key=lambda c: (c[0] + c[1]) / 2.0)
    lines, cur, cur_y = [], None, None
    for b, t, l, r in chars:
        yc = (b + t) / 2.0
        if cur is None or abs(yc - cur_y) > 3.5:
            if cur is not None:
                lines.append(cur)
            cur = [b, t, l, r, 1]
            cur_y = yc
        else:
            cur[0] = min(cur[0], b); cur[1] = max(cur[1], t)
            cur[2] = min(cur[2], l); cur[3] = max(cur[3], r); cur[4] += 1
    if cur is not None:
        lines.append(cur)
    for ln in lines:
        try:
            ln.append(tp.get_text_bounded(ln[2] - 1, ln[0] - 1, ln[3] + 1, ln[1] + 1) or "")
        except Exception:
            ln.append("")
    return lines


DIGITY = re.compile(r"^[\d\s.,\-–+x×:;%()′'‘’]+$")


def crop_fig(fig_no, page_no):
    pg = doc[page_no - 1]
    H = pg.get_height(); Wd = pg.get_width()
    r = caption_rect(pg, f"Figure {fig_no}:") or caption_rect(pg, f"Figure {fig_no}")
    if r is None:
        print(f"fig {fig_no}: caption not found on p{page_no}")
        return False
    top_of_cap = r[3]
    lines = get_lines(pg)
    top_y = None
    anchor = ANCHORS.get(fig_no)
    if anchor:
        needle, pad = anchor
        cand = [ln for ln in lines if needle in ln[5] and ln[0] > top_of_cap + 5]
        if cand:
            top_y = max(ln[1] for ln in cand) + pad
    if top_y is None:
        top_y = H - 30
        cands = []
        for ln in lines:
            y0, y1, x0, x1, cnt, txt = ln
            if y0 <= top_of_cap + 1:
                continue
            t = txt.strip()
            if not t or DIGITY.match(t):
                continue
            span = (x1 - x0) / Wd
            alpha = sum(1 for c in t if c.isalpha())
            body = ((cnt > 55 and span > 0.60) or cnt > 100
                    or t.startswith("Figure") or t.startswith("Table")
                    or (x0 < 80 and alpha >= 20 and alpha > 0.4 * cnt))
            if body:
                cands.append(y0)
        if cands:
            top_y = min(cands) - 4
    # caption bottom: walk contiguous lines below caption first line
    cap_y1 = r[3]
    below = sorted([ln for ln in lines if ln[1] <= cap_y1 + 1 and ln[0] > 20],
                   key=lambda l: -l[1])
    bot_y = cap_y1 + 2
    prev_bot = cap_y1
    for ln in below:
        y0, y1, x0, x1, cnt, txt = ln
        if not txt.strip():
            break
        if prev_bot - y1 > 6.5:
            break
        bot_y = y0 - 2
        prev_bot = y0
    if fig_no in (16,):
        pass  # caption inline with figure tick row keeps caption content
    # drop stray page-number line at crop top
    topmost = [ln for ln in lines if ln[1] >= top_y - 2 and ln[0] <= top_y + 14
               and ln[5].strip().isdigit() and ln[4] <= 3]
    for ln in topmost:
        top_y = min(top_y, ln[0] - 3)
    if top_y - bot_y < 25:
        top_y = bot_y + 120
    left = int(55 * SCALE); right = int((Wd - 55) * SCALE)
    py_top = int((H - top_y) * SCALE); py_bot = int((H - bot_y) * SCALE)
    img = pg.render(scale=SCALE).to_pil()
    crop = img.crop((left, max(py_top, 0), right, min(py_bot, img.height)))
    import numpy as np
    a = np.asarray(crop.convert("L"))
    rows = (a < 245).any(axis=1); cols = (a < 245).any(axis=0)
    if rows.any():
        r0, r1 = rows.argmax(), len(rows) - rows[::-1].argmax()
        c0, c1 = cols.argmax(), len(cols) - cols[::-1].argmax()
        crop = crop.crop((max(c0 - 8, 0), max(r0 - 8, 0), min(c1 + 8, crop.width), min(r1 + 8, crop.height)))
    crop.save(W + rf"\figs\cand\fig-{fig_no:02d}.png")
    print(f"fig {fig_no}: p{page_no} crop {crop.size}")
    return True


done = []
for f, p in FIGS.items():
    try:
        if crop_fig(f, p):
            done.append(f)
    except Exception as e:
        print(f"fig {f} FAILED: {e}")

# contact sheets
tiles = []
for f in done:
    im = Image.open(W + rf"\figs\cand\fig-{f:02d}.png").convert("RGB")
    im.thumbnail((400, 560))
    tile = Image.new("RGB", (420, 600), "white")
    tile.paste(im, (10, 30))
    ImageDraw.Draw(tile).text((10, 6), f"fig {f}", fill="black")
    tiles.append(tile)
cols, per = 3, 9
for si in range(0, math.ceil(len(tiles) / per)):
    batch = tiles[si * per:(si + 1) * per]
    rws = math.ceil(len(batch) / cols)
    sheet = Image.new("RGB", (cols * 420, rws * 600), "white")
    for i, t in enumerate(batch):
        sheet.paste(t, ((i % cols) * 420, (i // cols) * 600))
    sheet.save(W + rf"\figs\contact-{si + 1}.png")
print("sheets:", math.ceil(len(tiles) / per))
print("OK")
