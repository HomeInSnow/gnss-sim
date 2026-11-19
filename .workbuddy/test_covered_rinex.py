"""回归：AUTO 星历源星座覆盖感知（E/C 预览缺星 bug 的修复验证）。

覆盖三层：
  1) covered_systems / _covered_systems_text 对真实缓存文件的判定
  2) _download(want_systems=...) 跳过覆盖不足的镜像、无覆盖时降级保底
  3) get_ephemeris/cached_rinex_path 对旧的不覆盖缓存强制补下载、失败保留旧档
"""
import gzip
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.ephem import ephemeris as ep  # noqa: E402

HDR = "     3.04           N: GNSS NAV DATA    M: MIXED            RINEX VERSION / TYPE\n"


def rec(sysc, prn, y=2026):
    return (f"{sysc}{prn:02d} {y} 09 30 05 00 00"
            " -3.903123456789e-02  0.000e+00  0.000e+00\n")


GPS_ONLY = HDR + rec("G", 1) + rec("G", 2)
MULTI = HDR + rec("G", 1) + rec("E", 3) + rec("C", 6) + rec("R", 4)

fails = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


# ── 1) covered_systems 判定 ────────────────────────────────────────────
check("text gps-only", ep._covered_systems_text(GPS_ONLY) == {"G"})
check("text multi", ep._covered_systems_text(MULTI) == {"G", "E", "C", "R"})
real = Path("data/rinex/BRDC_2026274.rnx")
if real.is_file():
    cov = ep.covered_systems(real)
    check(f"real cache covers GEC {{C,E,G}} <= {sorted(cov)}",
          {"C", "E", "G"} <= cov)

# ── 2) _download 覆盖感知 ──────────────────────────────────────────────
import tempfile  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="rinex_cov_"))
(tmp / "rinex").mkdir(parents=True, exist_ok=True)
config.DATA_DIR = tmp

CONTENT = {"gps": gzip.compress(GPS_ONLY.encode("latin-1")),
           "multi": gzip.compress(MULTI.encode("latin-1"))}


class FakeResp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def install(mirrors):
    config.RINEX_MIRRORS = [f"https://x/{k}.gz" for k in mirrors]

    def fake_get(url, timeout=None):
        return FakeResp(CONTENT[url.rsplit("/", 1)[1][:-3]])

    ep.requests.get = fake_get


import datetime as dt  # noqa: E402

D = dt.date(2026, 9, 30)

install(["gps", "multi"])
p = ep._download(D)
check("no-want picks first mirror", p is not None and p.read_bytes()
      == gzip.decompress(CONTENT["gps"]))

# 清缓存后带 want 再下：应跳过 GPS-only 拿 multi
p.unlink()
p = ep._download(D, ("G", "E", "C"))
check("want=GEC skips gps-only mirror", p is not None
      and ep.covered_systems(p) >= {"G", "E", "C"})

# 全部镜像都不覆盖：降级保底第一份合法内容
install(["gps", "gps"])
p.unlink()
p = ep._download(D, ("G", "E", "C"))
check("all-short degrades to first valid", p is not None
      and ep.covered_systems(p) == {"G"})

# ── 3) get_ephemeris 覆盖不足强制补下载 ────────────────────────────────
install(["gps", "multi"])
p.unlink()
p.write_bytes(gzip.decompress(CONTENT["gps"]))  # 旧的不覆盖缓存
import os  # noqa: E402
os.utime(p, (time.time() - 3600, ) * 2)         # 装作 1 小时前下的（>600s）
try:
    ep.get_ephemeris(D, want_systems=("G", "E", "C"))
except ep.EphemerisUnavailable:
    pass  # parse_rinex 是 GPS-only 解析，MULTI 里 G01 可解析；不关心返回值
check("coverage-short cache re-downloaded",
      ep.covered_systems(p) >= {"G", "E", "C"})

# 下载全失败时保留旧缓存（不抛"all mirrors failed"、旧档不丢）
install([])
p2 = Path(ep._cache_path(D))
p2.unlink()
p2.write_bytes(gzip.decompress(CONTENT["gps"]))
os.utime(p2, (time.time() - 3600, ) * 2)
try:
    ep.get_ephemeris(D, want_systems=("G", "E", "C"))
except ep.EphemerisUnavailable as e:
    # 合成记录字段太短 georinex 解析不了属预期；关键是失败原因必须是解析层
    # 而不是"all mirrors failed"，且旧档保留（见下一条断言）
    check("download-fail keeps old cache (not 'all mirrors failed')",
          "all mirrors failed" not in str(e))
check("old cache kept when mirrors fail",
      p2.exists() and ep.covered_systems(p2) == {"G"})

print("RESULT:", "ALL-PASS" if not fails else f"FAIL x{len(fails)} {fails}")
sys.exit(1 if fails else 0)
