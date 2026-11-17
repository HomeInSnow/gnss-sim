# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdpsnap import CDP

c = CDP(9223)
js = """(() => {
  const el=document.getElementById('ch1-map');
  const ev=el._leaflet_events||{};
  const ks=Object.keys(ev);
  const k=ks.find(x=>x.startsWith('click'));
  if(!k) return 'NOCLICK keys='+ks.join(',');
  const h=ev[k];
  const ctx=h.context||h.ctx||h.fn;
  return JSON.stringify({key:k, fields:Object.keys(h),
    isMap: !!(ctx&&ctx.setView&&ctx.fire)});
})()"""
print("probe1:", c.eval(js))
# 若有 context 是 map，直接放 marker
js2 = """(() => {
  const el=document.getElementById('ch1-map');
  const ev=el._leaflet_events||{};
  const k=Object.keys(ev).find(x=>x.startsWith('click'));
  if(!k) return 'NOCLICK';
  const h=ev[k];
  let map=null;
  for (const f of ['context','ctx','_ctx']) if (h[f]&&h[f].fire) map=h[f];
  if(!map && typeof h.fn==='function' && h.fn.context && h.fn.context.fire)
    map=h.fn.context;
  if(!map) return 'NOMAP fields='+Object.keys(h).join(',');
  window.__m=map;
  map.setView(L.latLng(60.182537,24.82826), 9);
  map.fire('click',{latlng:L.latLng(60.182537,24.82826)});
  return 'FIRED';
})()"""
print("probe2:", c.eval(js2))
import time; time.sleep(0.8)
print("marker:", c.eval(
    "!!document.querySelector('#ch1-map .leaflet-marker-icon')"))
print("readout:", c.eval(
    "(document.getElementById('ch1-map')||{}).textContent"))
c.close()
