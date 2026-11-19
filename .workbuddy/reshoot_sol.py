# -*- coding: utf-8 -*-
"""Sol 页补拍：Span 调小让 41 个 FIX 轨迹铺满图区。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"

c = CDP(9223, url_sub="8082")
c.cmd("Page.bringToFront")
c.set_viewport(1280, 900, 2)
time.sleep(0.5)
# 打开 Sol 页
c.eval("""(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
  .find(x=>x.textContent.trim()==='Solution'); t.click(); return 1;})()""")
time.sleep(0.6)
opts = c.eval("""(() => {const sels=[...document.querySelectorAll(
  '#pages select')];
  const span=sels.find(s=>[...s.options].some(o=>o.value=='300'));
  if(!span) return 'NOSPAN opts='+sels.map(s=>[...s.options].map(o=>o.value)
    .join('/')).join(';');
  return [...span.options].map(o=>o.value).join(',');})()""")
print("span options:", opts)
target = "60" if "60" in opts.split(",") else ("30" if "30" in opts.split(",")
                                               else None)
if target:
    c.eval("""(() => {const sels=[...document.querySelectorAll('#pages select')];
      const span=sels.find(s=>[...s.options].some(o=>o.value===%r));
      span.value=%r; span.dispatchEvent(new Event('change')); return 1;})()"""
           % (target, target))
    time.sleep(1.2)
c.shot(OUT + "11_sol.png", dsf=1.5)
print("size:", os.path.getsize(OUT + "11_sol.png"))
