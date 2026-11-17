# -*- coding: utf-8 -*-
"""公众号文章 md -> HTML（图片 base64 内联），供 convert_doc.py 转 docx。

忠实转换，不改写内容：标题/引言块/列表/表格/图片/粗体/行内代码/链接/hr。
图片 src 一律转 dataURI（经验证 convert_doc 仅真正内嵌 base64 图）。
用法: python md2html_article.py
"""
import base64
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "output", "wechat_l1ca_article")
MD = os.path.join(ART, "article_l1ca.md")
OUT = os.path.join(ART, "article_l1ca.inlined.html")

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s):
    """行内元素：先转义，再按 代码->粗体->斜体->链接 顺序还原。"""
    s = esc(s)
    # 行内代码
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # 粗体
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    # 链接（URL 里可能含 / 与 -，不匹配 * 即可）
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               r'<a href="\2">\1</a>', s)
    return s


def img_tag(rel, alt):
    p = os.path.join(ART, rel.replace("/", os.sep))
    ext = os.path.splitext(p)[1].lower()
    with open(p, "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return ('<p class="fig" style="text-align:center">'
            f'<img src="data:{MIME[ext]};base64,{b}" width="580" alt="{esc(alt)}"></p>'
            f'<p class="figcap" style="text-align:center">{esc(alt)}</p>')


def md_to_html(md):
    lines = md.split("\n")
    out = []
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        # 图片行
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m:
            out.append(img_tag(m.group(2), m.group(1)))
            i += 1
            continue
        # 表格块
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^:?-{3,}", cells[0].replace(" ", "")):
                    rows.append(cells)
                i += 1
            out.append('<table border="1" cellspacing="0" cellpadding="6" '
                       'style="border-collapse:collapse;width:100%">')
            for r, cells in enumerate(rows):
                tag = "th" if r == 0 else "td"
                out.append("<tr>" + "".join(
                    f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            out.append("</table>")
            continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue
        # 引用块
        if s.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote><p>" + "<br>".join(quote) + "</p></blockquote>")
            continue
        # 有序列表
        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(inline(re.sub(r"^\d+\.\s+", "", lines[i].strip())))
                i += 1
            out.append("<ol>" + "".join(f"<li>{t}</li>" for t in items) + "</ol>")
            continue
        # 无序列表
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(inline(lines[i].strip()[2:]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{t}</li>" for t in items) + "</ul>")
            continue
        # 分隔线
        if s == "---":
            out.append("<hr>")
            i += 1
            continue
        # 普通段落（斜体段整体 *...* 包裹时转 em）
        segs = [ln.strip() for ln in lines[i:i + 1]]
        para = []
        while i < n and lines[i].strip() and not re.match(
                r"^(\||#{1,4}\s|>|-\s|\d+\.\s|!\[|---$)", lines[i].strip()):
            t = lines[i].strip()
            mt = re.match(r"^\*([^*].*?)\*$", t)
            if mt:
                para.append("<em>" + inline(mt.group(1)) + "</em>")
            else:
                para.append(inline(t))
            i += 1
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
        else:
            i += 1
    return "\n".join(out)


CSS = """
body{font-family:'Microsoft YaHei','PingFang SC',serif;font-size:15px;line-height:1.75;color:#222;max-width:720px;margin:0 auto;padding:24px}
h1{font-size:24px;line-height:1.4}
h2{font-size:20px;border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:32px}
h3{font-size:17px;margin-top:24px}
blockquote{margin:12px 0;padding:10px 16px;background:#f7f7f7;border-left:4px solid #4a90d9;color:#555}
code{font-family:Consolas,monospace;background:#f2f2f2;padding:1px 5px;font-size:13px}
table{font-size:14px;margin:12px 0}
th{background:#f0f4f8}
hr{border:none;border-top:1px solid #ddd;margin:28px 0}
p{margin:12px 0}
p.fig{margin:16px 0 4px}
p.figcap{margin:0 0 16px;color:#888;font-size:13px}
a{color:#4a90d9;text-decoration:none}
"""


def main():
    with open(MD, encoding="utf-8") as f:
        md = f.read()
    body = md_to_html(md)
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>\n{body}\n</body></html>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    nimg = html.count("data:image/")
    print(f"OK {OUT} bytes={os.path.getsize(OUT)} images={nimg}")
    if nimg != 13:
        print("WARN: expected 13 inlined images", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
