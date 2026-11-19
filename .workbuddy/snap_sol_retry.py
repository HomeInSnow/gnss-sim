# -*- coding: utf-8 -*-
"""重放一次，回放中把 Solution 页 Span 调到 60s 抓完整 FIX 轨迹。"""
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
st = c.eval("({s:!document.getElementById('btn-start').disabled, st:!document.getElementById('btn-stop').disabled})")
print("btn state:", st)
if st["s"]:
    c.eval("document.getElementById('btn-start').click()")
    print("started")
t0 = time.time()
# 回放中打开 Solution 页并把 Span 设为 60
time.sleep(3)
c.eval("""(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
  .find(x=>x.textContent.trim()==='Solution'); t.click(); return 1;})()""")
time.sleep(0.8)
ok = c.eval("""(() => {const sels=[...document.querySelectorAll('#pages select')];
  const span=sels.find(s=>[...s.options].every(o=>['60','120','300','900','1800','3600']
    .includes(o.value)) && s.options.length>=5);
  if(!span) return 'NOSPAN';
  span.value='60';
  span.dispatchEvent(new Event('change',{bubbles:true}));
  return 'SET60:'+span.value;})()""")
print("span:", ok)
# 等到回放后段（FIX 铺满）
wait = 53 - (time.time() - t0)
if wait > 0:
    time.sleep(wait)
time.sleep(2.0)
c.shot(OUT + "11_sol.png", dsf=1.5)
print("size:", os.path.getsize(OUT + "11_sol.png"))
# 回放自然结束后补 stop
time.sleep(8)
c.close()
