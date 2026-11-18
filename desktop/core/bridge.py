# -*- coding: utf-8 -*-
"""services 桥接层：桌面 UI 直调 backend 内核，无 HTTP、无端口。

复用策略（M0 定案）：不复制、不重写任何生成/验证逻辑——直接调用 backend.app
的同步处理函数本体（FastAPI 装饰器返回原函数）：
  * preview / run_receiver / iqplot / correlation / lnav 为纯函数，直接转调；
  * generate 内部自建 worker 线程 + 进度队列，返回 StreamingResponse(SSE)，
    这里在私有事件循环里消费其 body_iterator，把 progress/error/done 翻译成
    回调/返回值——生成路径与 Web 端执行的是同一份代码；
  * 停止生成 = backend.generator.stop_active_generation()（与 /api/generate/stop 同一入口）；
  * 场景库复用 backend.store.scenario_lib（与 Web 互通）。
铁律入口（align_for_run / at_gps / meta 注入策略门控）全部位于被复用代码内部，
桌面层不做任何补偿性修改。
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import pathlib
import sys
import os
import threading

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ.setdefault("ALLOW_TX", "0")          # 桌面版永不触碰发射链

_init_lock = threading.Lock()
_web = None


def web():
    """懒加载 backend.app（首次 ~2s：numpy/FastAPI 导入）。"""
    global _web
    with _init_lock:
        if _web is None:
            import backend.app as w
            _web = w
    return _web


# ── numpy 安全序列化（FastAPI 内部有 jsonable 编码器；进程内直调需自备）──
def _jsonable(x):
    import numpy as np
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, pathlib.PurePath):
        return str(x)
    if isinstance(x, (dt.datetime, dt.date)):
        return x.isoformat()
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


class BridgeError(RuntimeError):
    """携带 HTTP 语义（status/detail）的桥接异常。"""

    def __init__(self, status, detail):
        super().__init__(f"[{status}] {detail}")
        self.status, self.detail = status, str(detail)


def _call(fn, *a, **kw):
    try:
        return _jsonable(fn(*a, **kw))
    except Exception as e:                       # noqa: BLE001
        from fastapi import HTTPException
        if isinstance(e, HTTPException):
            raise BridgeError(e.status_code, e.detail) from e
        raise


# ── 预览 ────────────────────────────────────────────────────────────
def preview(body: dict) -> dict:
    return _call(web().preview, dict(body))


# ── 生成 ────────────────────────────────────────────────────────────
def generate(body: dict, progress_cb=None, stop_flag=None) -> dict:
    """跑完一次生成。progress_cb(frac)；stop_flag()→True 时请求停止。返回 done 载荷。"""
    resp = _call(web().generate, dict(body))
    out: dict = {}

    async def drain():
        async for chunk in resp.body_iterator:
            s = chunk.decode() if isinstance(chunk, (bytes, bytearray)) else str(chunk)
            if not s.startswith("data:"):
                continue
            d = json.loads(s[5:].strip())
            if "progress" in d:
                if progress_cb:
                    progress_cb(d["progress"])
                if stop_flag and stop_flag():
                    stop()
            elif "error" in d:
                out["error"] = d["error"]
            elif "done" in d:
                out["done"] = d["done"]

    asyncio.run(drain())
    if "error" in out:
        raise BridgeError(500, out["error"])
    if "done" not in out:
        raise BridgeError(500, "生成意外结束（无 done 事件）")
    return out["done"]


def stop() -> bool:
    from backend import generator as bgen
    return bool(bgen.stop_active_generation())


# ── 内置接收机验证 ──────────────────────────────────────────────────
def receiver(outdir: str, marker: dict | None = None, trace: bool = True,
             tracking: bool = False, dll_mode: str = "coh",
             track_s: float | None = None,
             min_metric_db: float | None = None) -> dict:
    body: dict = {"outdir": outdir, "trace": bool(trace)}
    if marker:
        body["marker"] = marker
    if tracking:
        body["tracking"] = True
        body["dll_mode"] = dll_mode
        if track_s is not None:
            body["track_s"] = float(track_s)
        if min_metric_db is not None:
            body["min_metric_db"] = float(min_metric_db)
    return _call(web().run_receiver, body)


# ── IQ 图谱（M2 用）────────────────────────────────────────────────
def iqplot(outdir: str, n: int = 2000, offset: int = 0) -> dict:
    return _call(web().iqplot, outdir, n, offset)


def correlation(outdir: str, prn: int) -> dict:
    return _call(web().correlation, outdir, int(prn))


def lnav(prn: int, outdir: str) -> dict:
    return _call(web().lnav, int(prn), outdir)


# ── 历史（out/ 扫描）───────────────────────────────────────────────
def list_runs(limit: int = 80) -> list[dict]:
    from backend import config as bconfig
    base = bconfig.OUT_DIR
    runs = []
    if base.exists():
        for p in sorted((d for d in base.iterdir() if d.is_dir()),
                        key=lambda d: d.name, reverse=True):
            info: dict = {"outdir": p.name, "path": str(p), "size_bytes": 0,
                         "meta": False}
            m = p / "meta.json"
            if m.exists():
                try:
                    meta = json.loads(m.read_text(encoding="utf-8"))
                    cfg = meta.get("config", {})
                    prov = meta.get("provenance", {})
                    info.update(meta=True,
                                size_bytes=(p / "gpssim.bin").stat().st_size
                                if (p / "gpssim.bin").exists() else 0,
                                lat=cfg.get("lat"), lon=cfg.get("lon"),
                                alt=cfg.get("alt"),
                                start_utc=cfg.get("start_utc"),
                                duration_s=cfg.get("duration_s"),
                                sample_rate=meta.get("sample_rate"),
                                sample_format=meta.get("sample_format"),
                                systems=prov.get("systems")
                                or cfg.get("systems") or ["G"],
                                engine=prov.get("engine"),
                                atmosphere=cfg.get("atmosphere"))
                except Exception:                # noqa: BLE001 - 损坏 meta 不致命
                    pass
            rr = p / "receiver_result.json"
            if rr.exists():
                try:
                    r = json.loads(rr.read_text(encoding="utf-8"))
                    info["error_m"] = r.get("error_m")
                except Exception:                # noqa: BLE001
                    pass
            runs.append(info)
            if len(runs) >= limit:
                break
    return runs


# ── 场景库（复用 backend.store，与 Web 互通）──────────────────────
def scenario_save(name: str, params: dict) -> None:
    from backend.store import scenario_lib
    _call(scenario_lib.save, name, params)


def scenario_list() -> list[str]:
    from backend.store import scenario_lib
    return list(_call(scenario_lib.list_names) or [])


def scenario_load(name: str) -> dict:
    from backend.store import scenario_lib
    return _call(scenario_lib.load, name)
