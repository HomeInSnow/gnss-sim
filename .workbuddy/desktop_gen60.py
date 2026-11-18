# -*- coding: utf-8 -*-
"""桌面新程序生成 60s 无大气场景（PocketSDR 互验用）。

链路：desktop.core.bridge（与已打包 exe 逐位等价的桌面内核）
body：.workbuddy/gen_whu_afz2_60s.json（与 11-13 文章轮 whu60b 同参数，
seed 2281271 → IQ 应与历史文章场景统计同口径）
产物：out/<runid>/ + gpssim.bin sha256 + 内置快照解算基线。
"""
import hashlib
import json
import sys

sys.path.insert(0, ".")
from desktop.core import bridge  # noqa: E402


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    body = json.load(open(".workbuddy/gen_whu_afz2_60s.json", encoding="utf-8"))
    cfg = body.get("config", body)
    print(f"[gen] start={cfg['start_utc']} dur={cfg['duration_s']}s "
          f"fs={cfg['sample_rate']} fmt={cfg['sample_format']} "
          f"atmo={cfg['atmosphere']} sv_clock={cfg['sv_clock']}", flush=True)
    done = bridge.generate(body)
    outdir = done["outdir"]
    print(f"[gen] DONE outdir={outdir}", flush=True)
    import backend.config as bc
    import pathlib
    run = pathlib.Path(bc.OUT_DIR) / outdir
    iq = run / "gpssim.bin"
    if not iq.exists():
        iq = next(run.glob("*.bin"))
    print(f"[sha] {iq.name} = {sha256_file(iq)} ({iq.stat().st_size:,} B)", flush=True)
    mk = {"lat": cfg["lat"], "lon": cfg["lon"], "alt": cfg["alt"]}
    res = bridge.receiver(outdir, marker=mk, trace=False)
    keep = {k: res.get(k) for k in ("error_m", "pdop", "residual_rms_m",
                                    "prns_used", "clock_bias_s")}
    print("[snap] " + json.dumps(keep), flush=True)
    print("OUTDIR=" + outdir, flush=True)


if __name__ == "__main__":
    main()
