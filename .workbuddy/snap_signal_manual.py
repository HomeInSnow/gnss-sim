# -*- coding: utf-8 -*-
"""Signal 页按真实用户路径操作后截图 08：
（receiver 停止后）Unset All -> 勾 L1CA -> Satellite No=12星 -> Apply -> 截图。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"
SAT = "4,5,9,11,12,18,20,25,26,28,29,31"

c = CDP(9223, url_sub="8082")
c.cmd("Page.bringToFront")
c.set_viewport(1280, 900, 2)
time.sleep(0.4)
# 确认 receiver 已停止（可编辑）
if c.eval("!document.getElementById('btn-stop').disabled"):
    c.eval("document.getElementById('btn-stop').click()")
    time.sleep(1.5)
print("editable:", c.eval("document.getElementById('sg-apply') ? "
      "!document.getElementById('sg-apply').disabled : 'NOPAGE'"))
c.eval("document.getElementById('btn-sig').click()")
time.sleep(0.8)
# Unset All
c.eval("document.getElementById('sg-none').click()")
time.sleep(0.3)
# 勾 GPS 系统 + L1CA 信号 + 卫星号
r = c.eval("""(() => {
  const sec = document.querySelector('.sig-sec[data-sys="GPS"]');
  const sys = sec.querySelector('.sg-sys');
  if (!sys.checked) sys.click();
  let l1 = null;
  sec.querySelectorAll('.sg-sig').forEach(e => {
    if (e.nextSibling && /L1CA/.test(e.parentElement.textContent)) l1 = e; });
  const sigs = [...sec.querySelectorAll('.sg-sig')].filter(e =>
    /L1CA/.test(e.parentElement.textContent));
  if (!sigs.length) return 'NOL1CA';
  for (const e of sigs) if (!e.checked) e.click();
  const prn = sec.querySelector('.sg-prn');
  prn.value = %r;
  prn.dispatchEvent(new Event('change', {bubbles: true}));
  return 'OK ' + sigs.length + ' chk=' + sigs.map(e=>e.checked).join(',');
})()""" % SAT)
print("l1ca:", r)
time.sleep(0.4)
c.eval("document.getElementById('sg-apply').click()")
print("applied, server ack wait...")
time.sleep(1.2)
# 复核页面状态 + 服务端广播
print("cfg_ena/apply disabled:", c.eval(
    "document.getElementById('sg-apply').disabled"))
c.shot(OUT + "08_pocket_signal.png", dsf=1.5)
print("size:", os.path.getsize(OUT + "08_pocket_signal.png"))
