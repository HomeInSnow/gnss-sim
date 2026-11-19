# -*- coding: utf-8 -*-
"""组装论文中文译本：sections/*.html + figs/cand/*.png(base64) → 单一 HTML"""
import re, base64, pathlib, sys

ROOT = pathlib.Path(r"D:\workbuddy\GNSSSignal\gnss-sim-desktop")
SEC = ROOT / r"output\fgi-gsrx\thesis_cn\sections"
FIGS = ROOT / r".workbuddy\thesis_work\figs\cand"
OUT = ROOT / r"output\fgi-gsrx\thesis_cn\thesis_cn.html"

CSS = """
<style>
body { font-family: "Source Han Serif SC","Noto Serif CJK SC","SimSun",serif; font-size: 11pt; line-height: 1.6; color: #000; }
h1.ch { font-family: "Source Han Sans SC","Noto Sans CJK SC","SimHei",sans-serif; font-size: 16pt; text-align: center; margin: 28pt 0 14pt; }
h2 { font-family: "Source Han Sans SC","Noto Sans CJK SC","SimHei",sans-serif; font-size: 13pt; margin: 16pt 0 8pt; }
h3 { font-family: "Source Han Sans SC","Noto Sans CJK SC","SimHei",sans-serif; font-size: 12pt; margin: 12pt 0 6pt; }
p { margin: 6pt 0; text-align: justify; }
ul { margin: 6pt 0 6pt 18pt; padding: 0; }
li { margin: 4pt 0; text-align: justify; }
.title-page h1 { font-size: 20pt; text-align: center; margin: 30pt 0 6pt; }
.title-page h2 { font-size: 13pt; text-align: center; font-weight: normal; margin: 2pt 0 14pt; }
.title-page p, .title-page div { text-align: center; }
.fig { text-align: center; margin: 12pt 0; }
.fig img { max-width: 88%; }
.figcap { font-size: 9.5pt; text-align: center; margin-top: 4pt; color: #222; }
.eqd { text-align: center; margin: 8pt 0; font-family: "Times New Roman","Cambria Math",serif; }
.eq { font-family: "Times New Roman","Cambria Math",serif; }
.eqd .eq { font-size: 11.5pt; }
.eqnum { float: right; font-family: "Times New Roman",serif; }
table { border-collapse: collapse; margin: 10pt auto; font-size: 9.5pt; }
caption { font-size: 9.5pt; margin-bottom: 4pt; }
th, td { border: 1px solid #444; padding: 3pt 6pt; text-align: center; }
th { background: #f0f0f0; }
.abbr td, .abbr th { text-align: left; }
.abbr { width: 94%; }
.alg { border: 1px solid #666; padding: 8pt 10pt; margin: 10pt 0; font-size: 10pt; }
.algtitle { font-weight: bold; text-align: center; }
.alg pre { font-family: "Consolas","Courier New",monospace; font-size: 9pt; white-space: pre-wrap; margin: 4pt 0; text-align: left; }
.refs li { font-size: 9.5pt; text-align: left; }
.transnote { font-size: 9.5pt; color: #444; }
.abstract p { text-indent: 2em; }
</style>
"""

ORDER = ["s00-front.html", "s01-intro.html", "s02-gnss.html", "s03-ch3.html",
         "s04-ch4.html", "s05-ch5.html", "s06-ch6.html", "s07-ch7.html",
         "s08-ch89.html", "s09-refs.html"]

def fig_b64(n):
    p = FIGS / f"fig-{n:02d}.png"
    return base64.b64encode(p.read_bytes()).decode()

parts = []
missing = []
for f in ORDER:
    txt = (SEC / f).read_text(encoding="utf-8")
    for m in re.findall(r"\{\{FIG:(\d+)\}\}", txt):
        n = int(m)
        try:
            img = f'<img src="data:image/png;base64,{fig_b64(n)}" alt="图 {n}"/>'
        except FileNotFoundError:
            missing.append((f, n)); img = ""
        txt = txt.replace("{{FIG:%d}}" % n, img)
    parts.append(txt)
if missing:
    print("MISSING FIGS:", missing); sys.exit(1)

left = re.findall(r"\{\{FIG:\d+\}\}", "\n".join(parts))
assert not left, left
html_doc = ("<!DOCTYPE html><html><head><meta charset='utf-8'/><title>"
            "GPS L1C 信号在软件定义 GNSS 接收机中的实现（中文译本）</title>"
            + CSS + "</head><body>\n" + "\n".join(parts) + "\n</body></html>")
OUT.write_text(html_doc, encoding="utf-8")
print("assembled:", OUT, OUT.stat().st_size, "bytes")
