# -*- coding: utf-8 -*-
"""第三次重放：t+18s 重抓 Correlator（PLL 星座应干净），t+33 重抓 Satellites。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim/output/wechat_l1ca_article/img/"

c = CDP(9223, url_sub="8082")
c.cmd("Page.bringToFront")
c.set_viewport(1280, 900, 2)
time.sleep(0.5)
if c.eval("!document.getElementById('btn-start').disabled"):
    c.eval("document.getElementById('btn-start').click()")
    print("started", flush=True)
t0 = time.time()
time.sleep(3)
c.eval("""(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
  .find(x=>x.textContent.trim()==='Correlator'); t.click(); return 1;})()""")
wait = 20 - (time.time() - t0)
if wait > 0:
    time.sleep(wait)
time.sleep(1.5)
c.shot(OUT + "09_corr.png", dsf=1.5)
print("corr", os.path.getsize(OUT + "09_corr.png"), flush=True)
wait = 35 - (time.time() - t0)
if wait > 0:
    time.sleep(wait)
c.eval("""(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
  .find(x=>x.textContent.trim()==='Satellites'); t.click(); return 1;})()""")
time.sleep(1.5)
c.shot(OUT + "10_sats.png", dsf=1.5)
print("sats", os.path.getsize(OUT + "10_sats.png"), flush=True)
# Signal 页补一张（回放运行态）
time.sleep(1)
c.eval("document.getElementById('btn-sig').click()")
time.sleep(0.8)
c.shot(OUT + "08_pocket_signal.png", dsf=1.5)
print("sig", os.path.getsize(OUT + "08_pocket_signal.png"), flush=True)
c.close()
