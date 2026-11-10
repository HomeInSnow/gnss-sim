# 单星冒烟探针：直调 _worker（G1，捕获修复后复验）
import importlib.util
import json
import sys
import time
import datetime as dt

sys.path.insert(0, ".")
from backend import config
from backend.ephem import ephemeris

spec = importlib.util.spec_from_file_location(
    "rt300", ".workbuddy/rx_realtime_300.py")
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)

outdir = config.OUT_DIR / "20261110T084902599874"
meta = json.loads((outdir / "meta.json").read_text())
cfg = meta["config"]
marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
band = meta["bands"][0]
start = dt.datetime.fromisoformat(cfg["start_utc"])
gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow0 = ephemeris.gps_week_and_sow(gps_start)

svs = [s for s in meta["provenance"]["svs"] if s["sys"] == "G"]
sv = next(s for s in svs if int(s["prn"]) == 1)
print("sv:", {k: sv.get(k) for k in ("sys", "prn", "gain_db", "if_hz")},
      " truth fd:", sv.get("carrier_doppler_hz"), flush=True)

opts = {"sample_format": meta.get("sample_format", "int8"),
        "track_s": 60.0}
t0 = time.time()
out = rt._worker((str(outdir), sv, band, marker, float(sow0), opts))
print("wall: %.1f s" % (time.time() - t0))
print("acq:", json.dumps(out.get("acq")))
print("pass1:", out.get("pass1"))
nav = out.get("nav") or {}
print("nav:", {k: nav.get(k) for k in
               ("decoded", "complete_t_s", "subframes", "pages",
                "reason_last")})
print("stats:", out.get("stats"))
bits = out.get("_bits") or {}
print("bits seconds:", len(bits),
      "sample sizes:", [len(bits.get(s, [])) for s in (0, 30, 59)])
print("skipped:", out.get("skipped"), "error:", out.get("error"))
if out.get("tb"):
    print(out["tb"])
obs = out.get("obs") or {}
ks = sorted(int(k) for k in obs)
for k in ks[:2] + ks[len(ks) // 2:len(ks) // 2 + 1] + ks[-2:]:
    o = obs[k] if k in obs else obs[str(k)]
    print(f"  k={k} chi={o['chi_chips']:.4f} err={o['err_chips']:+.6f} "
          f"fd={o['fd_hz']:+.2f} ph={o['phase_cycles']} "
          f"cn0={o['cn0_dbhz']}")
import pathlib
pathlib.Path(".workbuddy/probe_g1c.json").write_text(
    json.dumps(out, indent=1, default=float))
print("dumped probe_g1c.json")
