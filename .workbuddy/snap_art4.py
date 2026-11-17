# -*- coding: utf-8 -*-
"""both-off 版回放 whu60b 干净 IQ（20261113，atmo off + sv_clock on）——
文章"模型匹配后精度大幅提高"配图：Solution 页，Span=60。
前置：pocket_web_both_off.exe -web 127.0.0.1:8082 -ini art4.ini；Edge CDP:9223。
产物：img/12_sol_bothoff.png + art4.nmea。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim/output/wechat_l1ca_article/img/"
URL = "http://127.0.0.1:8082/"


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def set_span(c, want="60"):
    js = """(() => {const sels=[...document.querySelectorAll('#pages select')];
      const span=sels.find(s=>[...s.options].some(o=>o.value==='300'));
      if(!span) return 'NOSELECT';
      span.value=%r;
      span.dispatchEvent(new Event('input',{bubbles:true}));
      span.dispatchEvent(new Event('change',{bubbles:true}));
      if(span.onchange) try{span.onchange();}catch(e){}
      return span.value;})()""" % want
    for k in range(6):
        v = c.eval(js)
        log("set_span ->", v)
        if v == want:
            return True
        time.sleep(0.6)
    return False


def main():
    c = CDP(9223, create=True)
    c.set_viewport(1280, 900, 2)
    c.navigate(URL, 30)
    c.wait_js("document.getElementById('conn').className.indexOf('conn-off')<0",
              30)
    log("ws connected")
    # 先切 Solution 页并把 Span 设好，再启动回放（保证回放期数据按 60s 窗铺满）
    c.eval("""(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
        .find(x=>x.textContent.trim()==='Solution'); t.click(); return 1;})()""")
    time.sleep(0.8)
    set_span(c)
    c.eval("document.getElementById('btn-start').click()")
    t0 = time.time()
    log("start clicked")
    try:
        c.wait_js("!document.getElementById('btn-stop').disabled", 25)
    except TimeoutError:
        log("WARN: stop 未使能")
    # 回放中期再确认一次 Span（页面可能用服务端状态回写控件）
    wait = 40 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    set_span(c)
    time.sleep(8)
    c.cmd("Page.bringToFront")
    time.sleep(1.0)
    c.shot(OUT + "12_sol_bothoff.png", dsf=1.5)
    log("sol shot t+%.1fs size=%d msg1=%r" % (
        time.time() - t0, os.path.getsize(OUT + "12_sol_bothoff.png"),
        (c.eval("document.getElementById('msg1').textContent") or "")[:80]))
    # 等回放自然结束
    wait = 75 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    nmea = "D:/workbuddy/GNSSSignal/gnss-sim/output/wechat_l1ca_article/art4.nmea"
    if os.path.exists(nmea):
        with open(nmea, encoding="utf-8", errors="ignore") as f:
            gga = sum(1 for ln in f if ln.startswith("$GNGGA"))
        log("art4.nmea GGA:", gga, "size:", os.path.getsize(nmea))
    c.close()


if __name__ == "__main__":
    main()
