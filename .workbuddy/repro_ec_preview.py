# -*- coding: utf-8 -*-
"""复刻：E+C+G 预览（AUTO 星历、当前时刻），断网桩强制走缓存 fallback。"""
import sys
import datetime as dt

sys.path.insert(0, ".")
import urllib.request  # noqa: E402
import requests  # noqa: E402


class _NetDown(Exception):
    pass


def _blocked(*a, **k):
    raise _NetDown("network stubbed")


urllib.request.urlopen = _blocked        # type: ignore
requests.get = _blocked                  # type: ignore

from backend.ephem import ephemeris  # noqa: E402,F401
from desktop.core import bridge       # noqa: E402

body = {
    "start_utc": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "lat": 60.182537, "lon": 24.82826, "alt": 47.248,
    "duration_s": 60, "sample_rate": "auto", "sample_format": "int8",
    "rinex_path": "AUTO", "ephemeris_mode": "broadcast",
    "systems": ["G", "E", "C"], "bands": [], "engine": "native",
}
print("REPRO start_utc =", body["start_utc"], flush=True)
try:
    res = bridge.preview(body)
except Exception as e:  # noqa: BLE001
    print("REPRO-RAISED:", type(e).__name__, str(e)[:400], flush=True)
    sys.exit(0)
sats = res.get("satellites", [])
by: dict = {}
for s in sats:
    by.setdefault(s.get("sys"), []).append(s.get("prn"))
print("REPRO n_sats", len(sats),
      {k: len(v) for k, v in sorted(by.items())}, flush=True)
print("REPRO dop", {k: (round(v, 2) if isinstance(v, float) else v)
                    for k, v in res.get("dop", {}).items()}, flush=True)
for w in res.get("warnings", []):
    print("REPRO WARN:", w, flush=True)
sys.exit(0)
