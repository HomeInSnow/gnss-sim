# -*- coding: utf-8 -*-
"""补拍 Verify Fix：复用 8010 页面（done 事件此时已落定 lastOutdir），
点击 Verify Fix -> 等待 rx-result 出 Fix -> Status tab 补拍 04/05。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"
RUN = "20261117T150257152117"


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    c = CDP(9223, url_sub="8010")
    c.set_viewport(1440, 950, 2)
    lo = c.eval("(_channels.ch1||{}).lastOutdir")
    log("lastOutdir:", lo)
    if not lo:
        # done 消息若曾丢失，按服务端实际产物手工挂接（meta/文件均在盘上核实过）
        if os.path.exists("out/%s/receiver_result.json" % RUN):
            log("result already on disk:", RUN)
        c.eval("_channels.ch1.lastOutdir=%r" % RUN)
        log("set lastOutdir manually ->", RUN)
    c.click("#ch1-btn-receiver")
    t0 = time.time()
    # 确认 fetch 真的发出：rx-result 应变为 Running...（或旧 hint 说明仍无 outdir）
    time.sleep(1.0)
    txt = c.eval("document.getElementById('ch1-rx-result').textContent") or ""
    log("rx-result after click:", txt.replace("\n", " | ")[:160])
    if "No generated scenario" in txt:
        sys.exit("STILL no outdir -- abort")
    deadline = time.time() + 45 * 60
    while time.time() < deadline:
        txt = c.eval("document.getElementById('ch1-rx-result').textContent") or ""
        if "Fix:" in txt or "failed" in txt.lower():
            break
        time.sleep(10.0)
    dt = time.time() - t0
    txt = c.eval("document.getElementById('ch1-rx-result').textContent") or ""
    log("waited %.1f min. rx-result:" % (dt / 60), txt.replace("\n", " | ")[:500])
    # Status tab（生成态图表+功率表）与整卡补拍
    c.eval("""(() => {[...document.querySelectorAll('#channel-list .tab-btn')]
      .find(b=>b.textContent=='Status').click(); return 1;})()""")
    time.sleep(1.0)
    c.shot(OUT + "04_generated.png", clip=c.rect_of("#channel-list .channel-card"),
           dsf=1.5)
    time.sleep(0.5)
    c.shot(OUT + "05_verify.png", clip=c.rect_of("#channel-list .channel-card"),
           dsf=1.5)
    c.close()
    log("verify capture done")


if __name__ == "__main__":
    main()
