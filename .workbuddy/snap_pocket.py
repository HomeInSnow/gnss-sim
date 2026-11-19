# -*- coding: utf-8 -*-
"""PocketSDR WebUI 界面截图剧本（公众号文章素材）。
流程：连上回放服务 -> Input/Signal 配置页 -> Start 实时回放 ->
      Correlator（相关峰）-> Satellites（C/N0）-> Solution（定位解）。
前置：pocket_web_local.exe -web 127.0.0.1:8082 -html ../html -ini art1.ini；
      headless Edge CDP:9223。注意回放 60s 自动结束，截图须在 ~55s 内完成。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"
URL = "http://127.0.0.1:8082/"
os.makedirs(OUT, exist_ok=True)


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def open_tab(c, name):
    js = """(() => {const t=[...document.querySelectorAll('#tabbar .tab')]
        .find(x=>x.textContent.trim()===%r);
      if(!t) return 'NOTAB'; t.click(); return 'OK';})()""" % name
    v = c.eval(js)
    if v != "OK":
        raise RuntimeError("tab not found: " + name)


def main():
    c = CDP(9223, create=True)   # 独立新标签页，不与 8010 页面互抢
    c.set_viewport(1280, 900, 2)
    c.navigate(URL, 30)
    # 等 ws 连接（conn 指示灯：main.js setConn）
    c.wait_js("document.getElementById('conn').className.indexOf('conn-off')<0",
              20)
    log("ws connected:", c.eval(
        "document.getElementById('msg1').textContent"))
    time.sleep(0.8)

    # Input 页（文件/采样率/定时）
    c.eval("document.getElementById('btn-inp').click()")
    time.sleep(0.8)
    c.shot(OUT + "07_pocket_input.png", dsf=1.5)

    # Signal 页（L1CA 勾选与卫星号）
    c.eval("document.getElementById('btn-sig').click()")
    time.sleep(0.8)
    c.shot(OUT + "08_pocket_signal.png", dsf=1.5)

    # Start 实时回放
    c.eval("document.getElementById('btn-start').click()")
    t0 = time.time()
    log("start clicked")
    try:
        c.wait_js("!document.getElementById('btn-stop').disabled", 25)
    except TimeoutError:
        log("WARN: stop 未使能（可能启动慢）")
    log("receiver running at t+%.1fs" % (time.time() - t0))

    # Correlator（拉入后相关峰，约 18-20s 锁定）
    wait = 16 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    open_tab(c, "Correlator")
    time.sleep(2.0)
    c.shot(OUT + "09_corr.png", dsf=1.5)
    log("corr shot at t+%.1fs" % (time.time() - t0))

    # Satellites（C/N0 条）
    wait = 33 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    open_tab(c, "Satellites")
    time.sleep(2.0)
    c.shot(OUT + "10_sats.png", dsf=1.5)
    log("sats shot at t+%.1fs" % (time.time() - t0))

    # Log 页（$CH/$C/N0/$POS 实时流，作为处理过程留痕）
    wait = 44 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    open_tab(c, "Log")
    time.sleep(1.5)
    c.shot(OUT + "10b_logpage.png", dsf=1.5)

    # Solution（等首 FIX；回放 60s 自动结束，页面保留最后一帧）
    wait = 52 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    open_tab(c, "Solution")
    time.sleep(2.0)
    c.shot(OUT + "11_sol.png", dsf=1.5)
    log("sol shot at t+%.1fs" % (time.time() - t0))

    # 回放结束后补一张 Solution 稳定帧
    time.sleep(12)
    c.shot(OUT + "11b_sol_final.png", dsf=1.5)
    log("final done. msg1:", c.eval(
        "document.getElementById('msg1').textContent"))
    c.close()


if __name__ == "__main__":
    main()
