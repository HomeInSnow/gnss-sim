# -*- coding: utf-8 -*-
"""gnss-sim 前端界面截图剧本（公众号文章素材）。
流程：填 Tampere L1CA 场景 -> marker -> Preview geometry（星空图）
      -> Generate（进度/完成态）-> Verify Fix（内置接收机结果）。
前置：uvicorn:8010 + headless Edge CDP:9223。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

OUT = "D:/workbuddy/GNSSSignal/gnss-sim-desktop/output/wechat_l1ca_article/img/"
os.makedirs(OUT, exist_ok=True)


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""   # 可选分步: config|preview|generate|verify
    c = CDP(9223)
    c.set_viewport(1440, 950, 2)
    c.navigate("http://127.0.0.1:8010/", 40)
    c.wait_js("typeof addChannel==='function'", 20)
    time.sleep(1.5)
    if not c.eval("!!document.querySelector('.channel-card')"):
        c.eval("addChannel()")
        time.sleep(1.0)
    # leaflet 容器暗色背景（tiles 不可达时不留白块）
    c.eval("""(() => {const st=document.createElement('style');
      st.textContent='.leaflet-container{background:#20242b !important}';
      document.head.appendChild(st); return 1;})()""")
    # 填表
    c.eval("""(() => {
      const set=(id,v)=>{const e=document.getElementById(id);
        if(!e) return; e.value=v;
        e.dispatchEvent(new Event('change',{bubbles:true}));
        e.dispatchEvent(new Event('input',{bubbles:true}));};
      set('ch1-start-utc','2023-09-28T23:20');
      set('ch1-duration','60');
      set('ch1-rate','25000000');
      set('ch1-fmt','int16');
      set('ch1-rinex-path',
          'D:/workbuddy/GNSSSignal/gnss-sim-desktop/data/rinex/BRDC_2023271_whu_afzero2.rnx');
      return 1;})()""")
    # 参考点 marker：走前端自带的程序化入口（与读档场景同路径）
    mv = c.eval("""(() => {try {
      _channels.ch1.map.setLatlng(60.182537, 24.82826);
      return 'OK'; } catch(e) { return 'ERR '+e; }})()""")
    log("marker fire:", mv)
    time.sleep(1.0)
    # marker 图标兜底（unpkg 图标不可达时换成内联红点）
    c.eval("""(() => {const ic=document.querySelector('#ch1-map .leaflet-marker-icon');
      if(ic && (!ic.complete || ic.naturalWidth===0))
        ic.src='data:image/svg+xml;utf8,' + encodeURIComponent(
          '<svg xmlns="http://www.w3.org/2000/svg" width="26" height="42">' +
          '<path d="M13 1C6.4 1 1 6.3 1 12.9c0 9.2 12 28.1 12 28.1s12-18.9 ' +
          '12-28.1C25 6.3 19.6 1 13 1z" fill="%23e03131" stroke="white" ' +
          'stroke-width="1.6"/><circle cx="13" cy="13" r="4.5" fill="white"/></svg>');
      return 1;})()""")
    log("RX readout:", c.eval(
        "(document.querySelector('#ch1-map')||{}).textContent"))
    if only in ("", "config"):
        c.shot(OUT + "01_sim_config.png",
               clip=c.rect_of("#channel-list .channel-card"), dsf=1.5)

    # Preview geometry -> 星空图 + 卫星表
    if only in ("", "preview"):
        c.click("#ch1-btn-preview")
        c.wait_js("document.querySelectorAll('#ch1-sat-table tr').length>1",
                  90)
        log("sat rows:", c.eval(
            "document.querySelectorAll('#ch1-sat-table tr').length"))
        c.eval("""(() => {[...document.querySelectorAll(
          '#channel-list .tab-btn')].find(b=>b.textContent=='Satellites')
          .click(); return 1;})()""")
        time.sleep(0.8)
        c.shot(OUT + "02_satellites.png",
               clip=c.rect_of("#channel-list .channel-card"), dsf=1.5)

    # Generate
    if only in ("", "generate"):
        c.click("#ch1-btn-generate")
        log("generate clicked")
        # 抓进度条画面（轮询 progress 中段值）
        deadline = time.time() + 900
        shot_prog = False
        while time.time() < deadline:
            pr = c.eval("document.getElementById('ch1-gen-progress').value")
            warn = c.eval("(document.getElementById('ch1-warnings')||{}).textContent")
            if pr and pr >= 0.02 and not shot_prog:
                c.shot(OUT + "03_generating.png",
                       clip=c.rect_of("#channel-list .channel-card"), dsf=1.2)
                shot_prog = True
            if pr and pr >= 0.999:
                break
            if warn and ("error" in warn.lower() or "failed" in warn.lower()):
                log("generate FAILED:", warn[:300])
                sys.exit(1)
            time.sleep(2.0)
        else:
            log("generate timeout"); sys.exit(1)
        time.sleep(1.5)
        log("done. warnings:",
            (c.eval("(document.getElementById('ch1-warnings')||{}).textContent") or "")[:200])
        c.shot(OUT + "04_generated.png",
               clip=c.rect_of("#channel-list .channel-card"), dsf=1.5)

    # Verify Fix
    if only in ("", "verify"):
        c.click("#ch1-btn-receiver")
        log("verify clicked")
        deadline = time.time() + 1800
        while time.time() < deadline:
            txt = c.eval("(document.getElementById('ch1-rx-result')||{}).textContent") or ""
            if "Fix:" in txt or "failed" in txt.lower():
                break
            time.sleep(5.0)
        txt = c.eval("(document.getElementById('ch1-rx-result')||{}).textContent") or ""
        log("rx-result:", txt.replace("\n", " | ")[:400])
        time.sleep(0.8)
        c.shot(OUT + "05_verify.png",
               clip=c.rect_of("#channel-list .channel-card"), dsf=1.5)
        # Log 页（操作留痕）
        c.eval("""(() => {document.querySelector('.side-icon[data-page="log"]')
          .click(); return 1;})()""")
        time.sleep(0.6)
        c.shot(OUT + "06_logpage.png",
               clip=c.rect_of("#page-log"), dsf=1.5)
    c.close()
    log("ALL DONE")


if __name__ == "__main__":
    main()
