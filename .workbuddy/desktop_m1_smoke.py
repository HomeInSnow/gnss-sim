# -*- coding: utf-8 -*-
"""M1 验收冒烟：桌面桥接路径 preview → generate → receiver，落盘 body 供 Web 侧对表。

用法：
    .venv/Scripts/python.exe .workbuddy/desktop_m1_smoke.py desktop   # 桥接侧
    .venv/Scripts/python.exe .workbuddy/desktop_m1_smoke.py web <outdir>  # 仅算 sha256
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BODY_FILE = ROOT / ".workbuddy" / "m1_body.json"


def make_task():
    from desktop.core.model import SimTask
    t = SimTask(name="M1冒烟", start_utc="2023-09-28T23:20:00",
                duration_s=10, sample_rate=2500000.0, sample_format="int8",
                rinex_path="AUTO", systems=["G"], bands=[],
                sv_clock=True)
    return t


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def run_desktop():
    from desktop.core import bridge
    t = make_task()
    body = t.generate_body()
    BODY_FILE.write_text(json.dumps(body, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print("BODY-SAVED", BODY_FILE)

    t0 = time.time()
    pv = bridge.preview(t.preview_body())
    sats = pv.get("satellites", [])
    print(f"PREVIEW ok sats={len(sats)} pdop={pv.get('dop', {}).get('pdop')}"
          f" warns={pv.get('warnings')}")
    assert len(sats) >= 4, "可见星不足"

    n = [0]

    def prog(f):
        n[0] += 1
        if n[0] % 10 == 0:
            print(f"  progress {f:.2f}")
    done = bridge.generate(body, progress_cb=prog)
    outdir = done["outdir"]
    print(f"GENERATE ok outdir={outdir} size={done.get('size_bytes')}"
          f" 用时 {time.time() - t0:.1f}s")
    gp = ROOT / "out" / outdir / "gpssim.bin"
    digest = sha256(gp)
    print(f"SHA256 {digest}")
    (ROOT / ".workbuddy" / "m1_sha_desktop.txt").write_text(digest)

    res = bridge.receiver(outdir, marker={"lat": t.lat, "lon": t.lon,
                                          "alt": t.alt}, trace=False)
    if "error" in res:
        print("RECEIVER-ERROR", res["error"])
        sys.exit(2)
    print(f"RECEIVER ok error_m={res.get('error_m'):.3f}"
          f" pdop={res.get('pdop'):.2f} sats={len(res.get('prns_used', []))}"
          f" llh={[round(x, 6) for x in res.get('llh', [])]}")
    print("OUTDIR", outdir)
    print("SMOKE-PASS")


def hash_outdir(outdir: str):
    gp = ROOT / "out" / outdir / "gpssim.bin"
    print(f"SHA256 {sha256(gp)}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "desktop"
    if mode == "desktop":
        run_desktop()
    elif mode == "web":
        hash_outdir(sys.argv[2])
