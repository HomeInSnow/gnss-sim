# -*- coding: utf-8 -*-
"""公众号 v3：md → 与 v2 同款模板的 inlined.html（图片 base64 内联）。

用法：.venv/Scripts/python.exe .workbuddy/article_build_v3.py <md路径> <out html路径>
覆盖子集：h1/h2、blockquote、pipe 表格、有序/无序列表、hr、段落、
**bold**、`code`、*em*、![cap](src)（相对 md 目录解析，base64 内联）。
"""
import base64
import re
import sys
from pathlib import Path

CSS = """body{font-family:'Microsoft YaHei','PingFang SC',serif;font-size:15px;line-height:1.75;color:#222;max-width:720px;margin:0 auto;padding:24px}
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
a{color:#4a90d9;text-decoration:none}"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s, md_dir):
    s = esc(s)
    m = re.match(r"^!\[(.*)\]\((.+)\)$", s.strip())
    if m:
        cap, src = m.groups()
        p = (md_dir / src).resolve()
        b64 = base64.b64encode(p.read_bytes()).decode()
        return (f'<p class="fig"><img src="data:image/png;base64,{b64}" '
                f'style="max-width:100%"></p>'
                + (f'<p class="figcap">{cap}</p>' if cap else ""))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    # 先做成 md 链接并用占位符保护，再给裸 URL 自动加链，最后还原
    keep = []

    def _stash(frag):
        keep.append(frag)
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               lambda mm: _stash(f'<a href="{mm.group(2)}">{mm.group(1)}</a>'),
               s)
    s = re.sub(r"(https?://[A-Za-z0-9;/?:@&=+$_.~#%-]+)",
               lambda mm: _stash(
                   '<a href="{0}">{0}</a>'.format(
                       mm.group(1).rstrip(".,;:%)")) ),
               s)
    s = re.sub(r"\x00(\d+)\x00", lambda mm: keep[int(mm.group(1))], s)
    return s


def convert(md_text, md_dir):
    out, lines, i = [], md_text.splitlines(), 0
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        ln = lines[i]
        if re.match(r"^\s*\|", ln):                      # pipe 表格
            close_lists()
            rows = []
            while i < len(lines) and re.match(r"^\s*\|", lines[i]):
                cells = [c.strip() for c in
                         re.split(r"\|", lines[i].strip().strip("|"))]
                if not re.match(r"^:?-{2,}", cells[0].replace(" ", "") or "---"):
                    rows.append(cells)
                i += 1
            out.append("<table>")
            for r, cells in enumerate(rows):
                tag = "th" if r == 0 else "td"
                out.append("<tr>" + "".join(
                    f"<{tag}>{inline(c, md_dir)}</{tag}>" for c in cells)
                    + "</tr>")
            out.append("</table>")
            continue
        if ln.startswith("# "):
            close_lists()
            out.append(f"<h1>{inline(ln[2:], md_dir)}</h1>")
        elif ln.startswith("## "):
            close_lists()
            out.append(f"<h2>{inline(ln[3:], md_dir)}</h2>")
        elif ln.startswith("### "):
            close_lists()
            out.append(f"<h3>{inline(ln[4:], md_dir)}</h3>")
        elif ln.startswith("> "):
            close_lists()
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(inline(lines[i][2:], md_dir))
                i += 1
            out.append("<blockquote><p>" + "<br>".join(buf) + "</p></blockquote>")
            continue
        elif re.match(r"^---+$", ln.strip()):
            close_lists()
            out.append("<hr>")
        elif re.match(r"^\s*!\[", ln.strip()):
            close_lists()
            out.append(inline(ln.strip(), md_dir))
        elif re.match(r"^\s*- ", ln):
            if not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(ln.strip()[2:], md_dir)}</li>")
        elif re.match(r"^\s*\d+\. ", ln):
            if not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            out.append("<li>" + inline(
                re.sub(r"^\s*\d+\. ", "", ln), md_dir) + "</li>")
        elif ln.strip() == "":
            pass
        else:                                            # 段落（并入相邻行）
            close_lists()
            buf = [ln]
            while (i + 1 < len(lines) and lines[i + 1].strip()
                   and not re.match(r"^(#|>|\||---|\s*- |\s*\d+\. |!\[)",
                                    lines[i + 1])):
                i += 1
                buf.append(lines[i])
            out.append("<p>" + inline(" ".join(buf), md_dir) + "</p>")
        i += 1
    close_lists()
    return "\n".join(out)


def main():
    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    body = convert(md_path.read_text(encoding="utf-8"), md_path.parent)
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>\n{CSS}</style></head><body>\n{body}\n</body></html>")
    out_path.write_text(html, encoding="utf-8")
    print("BUILD-OK", out_path, len(html), "chars")


main()
