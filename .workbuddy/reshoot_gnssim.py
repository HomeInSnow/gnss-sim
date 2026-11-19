# -*- coding: utf-8 -*-
"""04/05 特写裁剪：04=Status tab 验证区，05=Verify 按钮+结果文字。全卡版另存 04x/05x。"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"


def rect_json(c, js):
    return json.loads(c.eval(js))


def clip_of(r, pad=10):
    return {"x": max(0, r["x"] - pad), "y": max(0, r["y"] - pad),
            "width": r["w"] + 2 * pad, "height": r["h"] + 2 * pad}


c = CDP(9223, url_sub="8010")
c.cmd("Page.bringToFront")
c.set_viewport(1440, 950, 2)
time.sleep(0.5)

# 全卡版留档
shutil.copy(OUT + "05_verify.png", OUT + "04x_full_card.png")

# 05 特写：按钮行 + rx-result
r = rect_json(c, """(() => {const a=document.querySelector('#ch1 .channel-actions');
  const x=document.getElementById('ch1-rx-result');
  a.scrollIntoView({block:'start'}); window.scrollBy(0,-8);
  const ra=a.getBoundingClientRect(), rx=x.getBoundingClientRect();
  return JSON.stringify({x:ra.x, y:ra.y+window.scrollY,
    w:ra.width, h:(rx.bottom-ra.top)});})()""")
time.sleep(0.3)
c.shot(OUT + "05_verify.png", clip=clip_of(r), dsf=1.6)

# 04 特写：Status tab（inspect+svpower+acquisition 至 C/N0 前）
r = rect_json(c, """(() => {const t=document.querySelector(
  '#ch1 .tab-content[data-tab="status"]'); t.scrollIntoView({block:'start'});
  window.scrollBy(0,-8);
  const b=t.getBoundingClientRect();
  // 截到 acquisition metric canvas 底部
  const cv=document.getElementById('ch1-iq-correlation');
  let h=b.height;
  if (cv){const cb=cv.getBoundingClientRect();
    h=Math.min(b.height, cb.bottom-b.top);}
  return JSON.stringify({x:b.x, y:b.y+window.scrollY, w:b.width, h:h});})()""")
time.sleep(0.3)
c.shot(OUT + "04_generated.png", clip=clip_of(r), dsf=1.6)
print("sizes:", os.path.getsize(OUT + "04_generated.png"),
      os.path.getsize(OUT + "05_verify.png"))
