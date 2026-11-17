# -*- coding: utf-8 -*-
"""救援 out/20261117T022846863288（900 s 场景，引擎段完整落盘 90 GB 原始 IQ，
AWGN 后处理在写 .tmp 副本时磁盘打满而中止——原文件未被破坏、只差加噪）。

用 postproc.apply_impairments(inplace=True) 对现有文件逐块原地加噪
（同 seed=20261117，与重跑链路逐比特一致的噪声序列生成方式），
再以冒烟 run 20261117T022149933828 的引擎产出 meta 为底补写 meta.json
（同场景/同 start/同 seed，仅 duration、total_samples、created、加噪报告不同）。
"""
import datetime as dt
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, ".")

from backend.models import impairments as imp_mod   # noqa: E402
from backend.synth import postproc                  # noqa: E402

OUT = pathlib.Path("out/20261117T022846863288")
SMOKE_META = pathlib.Path("out/20261117T022149933828/meta.json")
IQ = OUT / "gpssim.bin"
FS = 25_000_000.0
QUANT = 2                     # bands._QUANT["int16"]
DURATION_S = 900
TOTAL_SAMPLES = 22_500_000_000

want = TOTAL_SAMPLES * 4      # int16 I+Q = 4 B/sample
size = IQ.stat().st_size
assert size == want, f"IQ size {size} != {want}"
assert not (OUT / "meta.json").exists(), "meta exists: already rescued?"
assert not (OUT / "gpssim.bin.tmp").exists(), "stray tmp present"

cfg = imp_mod.ImpairmentConfig.from_dict(
    {"enabled_flag": True, "snr_db": -18.33, "seed": 20261117})


def sample_power(path, off, n):
    """Mean |x|^2 over n complex samples at byte offset off (int16 IQ)."""
    a = np.fromfile(path, dtype=np.int16, count=2 * n, offset=off)
    x = a[0::2] + 1j * a[1::2]
    return float(np.mean(np.abs(x) ** 2, dtype=np.float64))


HEAD, TAIL = 4_000_000, 4_000_000
p0h = sample_power(IQ, 0, HEAD)
p0t = sample_power(IQ, (TOTAL_SAMPLES - TAIL) * 4, TAIL)
print(f"pre-noise  head P={p0h:.1f}  tail P={p0t:.1f}", flush=True)

t0 = time.time()
rep = postproc.apply_impairments(IQ, FS, QUANT, cfg, band_idx=0, inplace=True)
print(f"inplace impairments done in {time.time()-t0:.0f}s: {rep}", flush=True)

p1h = sample_power(IQ, 0, HEAD)
p1t = sample_power(IQ, (TOTAL_SAMPLES - TAIL) * 4, TAIL)
npow = rep["noise_power"]
print(f"post-noise head P={p1h:.1f} (dP={p1h-p0h:.1f})  "
      f"tail P={p1t:.1f} (dP={p1t-p0t:.1f})  target noise_power={npow:.1f}",
      flush=True)
assert abs((p1h - p0h) - npow) / npow < 0.10, "head power step off"
assert abs((p1t - p0t) - npow) / npow < 0.10, "tail power step off"

meta = json.loads(SMOKE_META.read_text())
meta["created_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
meta["total_samples"] = TOTAL_SAMPLES
meta["config"]["duration_s"] = DURATION_S
meta["provenance"]["impairments"] = {"L1": rep}
meta["rescue_note"] = (
    "IQ synthesized by native engine run 20261117T022846863288; the original "
    "AWGN postproc pass aborted on ENOSPC while writing the .tmp copy, so "
    "noise was re-applied in place (apply_impairments inplace=True, same "
    "cfg/seed) on the untouched engine output. Meta cloned from smoke run "
    "20261117T022149933828 (same scenario/start/seed) with duration/samples/"
    "impairments report updated.")
(OUT / "meta.json").write_text(json.dumps(meta, indent=2))
print(f"DONE meta written, measured_snr_db={rep['measured_snr_db']}", flush=True)
