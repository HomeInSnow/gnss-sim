# -*- coding: utf-8 -*-
"""桌面版任务模型：全部配置参数 + 与 Web /api/generate 载荷逐字段对齐的请求体装配。

单一事实来源：本文件的 build_*_body() 是桌面版唯一构造生成/预览请求的地方，
字段语义严格镜像 frontend/js/channels.js 的 _impairmentsBody / _channelModelsBody
/ _engineBody / _osnmaBody 与 btn-preview / btn-generate 装配（已逐段核对）。
差异仅两处（有意为之，均已记录）：
  1. Web 版两处硬编码 alt=100（地图 marker 高程）→ 桌面版统一用任务 alt（真值自洽，
     Verify Fix 的 3D 误差不再掺入 marker 高度差）；
  2. Web 的 -fmt 与 quant 两个量化控件 → 桌面合并为 sample_format 一个控件。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

SYSTEMS = ["G", "R", "E", "C", "J", "S", "I"]
BANDS = ["L1", "L2", "L5"]

# 与 channels.js IMP_PRESETS 一致
IMP_PRESETS: dict[str, dict[str, float]] = {
    "bench": {"seed": 0, "cfo": 0, "ppm": 0.0, "phn": 0.2, "gain": 0.1,
              "iqphase": 0.5, "dci": 0.001, "dcq": 0.001, "snr": 40,
              "clip": 0, "bits": 12},
    "field": {"seed": 7, "cfo": 250, "ppm": 1.0, "phn": 1.5, "gain": 0.3,
              "iqphase": 1.5, "dci": 0.008, "dcq": 0.008, "snr": 12,
              "clip": 0.02, "bits": 10},
    "urban": {"seed": 13, "cfo": 600, "ppm": 2.5, "phn": 3.0, "gain": 0.6,
              "iqphase": 3.0, "dci": 0.02, "dcq": 0.02, "snr": 4,
              "clip": 0.05, "bits": 8},
}
# 与 channels.js MDL_PRESETS 一致
MDL_PRESETS: dict[str, dict[str, Any]] = {
    "open-sky": {"iono": "klobuchar", "tropo": "saastamoinen", "rxclk": "poly",
                 "rxclk_bias": 1e-7, "rxclk_drift": 1e-9, "rxclk_driftrate": 0,
                 "rxclk_sawamp": 0, "rxclk_sawper": 0, "mp": "off",
                 "mp1_delay": 0, "mp1_amp": 0, "mp1_phase": 3.14159,
                 "mp2_delay": 0, "mp2_amp": 0, "mp2_phase": 3.14159},
    "urban-canyon": {"iono": "klobuchar", "tropo": "saastamoinen", "rxclk": "poly",
                     "rxclk_bias": 5e-7, "rxclk_drift": 2e-9,
                     "rxclk_driftrate": 1e-12, "rxclk_sawamp": 5e-9,
                     "rxclk_sawper": 1.0, "mp": "specular",
                     "mp1_delay": 15, "mp1_amp": 0.5, "mp1_phase": 3.14159,
                     "mp2_delay": 45, "mp2_amp": 0.3, "mp2_phase": 3.14159},
    "foliage-weak": {"iono": "klobuchar", "tropo": "saastamoinen", "rxclk": "poly",
                     "rxclk_bias": 2e-7, "rxclk_drift": 5e-9,
                     "rxclk_driftrate": 0, "rxclk_sawamp": 0, "rxclk_sawper": 0,
                     "mp": "specular", "mp1_delay": 8, "mp1_amp": 0.35,
                     "mp1_phase": 3.14159, "mp2_delay": 0, "mp2_amp": 0,
                     "mp2_phase": 3.14159},
}


@dataclass
class SimTask:
    """一个仿真任务（= Web 的一张通道卡片去掉硬件部分）。"""
    name: str = "未命名场景"
    # ── 定时与输出 ──
    start_utc: str = "2023-09-28T23:20:00"        # 'YYYY-MM-DDTHH:MM[:SS]'
    duration_s: int = 60
    sample_rate: Any = "auto"                     # "auto" 或 Hz 数值
    sample_format: str = "int16"                  # int16 / int8 / int12（合并自 fmt+quant）
    # ── 星历 ──
    rinex_path: str = "AUTO"
    ephemeris_mode: str = "broadcast"             # broadcast / precise
    sp3_path: str = ""
    # ── 星座与频段 ──
    systems: list[str] = field(default_factory=lambda: ["G"])
    bands: list[str] = field(default_factory=list)   # 空=各系统本征频段
    osnma_enabled: bool = False
    osnma_nmas: int = 2
    # ── 传播模型 ──
    mdl_preset: str = "manual"
    iono: str = "off"
    tropo: str = "off"
    rxclk: str = "off"
    rxclk_bias: float = 0.0
    rxclk_drift: float = 0.0
    rxclk_driftrate: float = 0.0
    rxclk_sawamp: float = 0.0
    rxclk_sawper: float = 0.0
    mp: str = "off"
    mp1_delay: float = 0.0
    mp1_amp: float = 0.0
    mp1_phase: float = 3.14159
    mp2_delay: float = 0.0
    mp2_amp: float = 0.0
    mp2_phase: float = 3.14159
    models_to_iq: bool = False
    # ── RF 损伤 ──
    imp_enabled: bool = False
    imp_preset: str = "manual"
    imp_seed: float = 0
    imp_cfo: float = 0
    imp_ppm: float = 0
    imp_phn: float = 0
    imp_gain: float = 0
    imp_iqphase: float = 0
    imp_dci: float = 0
    imp_dcq: float = 0
    imp_snr: str = ""                             # 空串 = 不设置 snr_db
    imp_clip: float = 0
    imp_bits: float = 0
    # ── 信道衰落 ──
    fade_model: str = "off"                       # off / seeded / keyed
    fade_env: str = "suburban"
    fade_speed: str = ""                          # 空 = auto(route)
    fade_seed: float = 1
    fade_key: str = ""
    fade_record_key: bool = False
    # ── 卫星钟差（Web 版不暴露、服务端默认 True；桌面显式暴露）──
    sv_clock: bool = True
    # ── 位置 ──
    lat: float = 60.182537
    lon: float = 24.82826
    alt: float = 47.248
    route: list | None = None                     # 轨迹 [[lat,lon,alt],...]（M3）
    # ── 最近产物（运行时回填，不入库场景）──
    last_outdir: str = ""
    last_preview: dict = field(default_factory=dict, repr=False)

    # ══ 与 channels.js 对齐的请求体装配 ══════════════════════════
    def _models_part(self) -> dict:
        """镜像 _channelModelsBody()：全部 off 时返回 {}。"""
        out: dict[str, Any] = {}
        if self.iono != "off" or self.tropo != "off":
            out["atmosphere"] = {"ionosphere": self.iono, "troposphere": self.tropo}
        if self.rxclk == "poly":
            out["receiver_clock"] = {
                "model": "poly", "bias_s": self.rxclk_bias,
                "drift_s_per_s": self.rxclk_drift,
                "drift_rate_s_per_s2": self.rxclk_driftrate,
                "sawtooth_amp_s": self.rxclk_sawamp,
                "sawtooth_period_s": self.rxclk_sawper}
        if self.mp == "specular":
            refs = []
            for k in ("mp1", "mp2"):
                amp = getattr(self, f"{k}_amp")
                if amp and amp > 0:
                    refs.append({"excess_delay_m": getattr(self, f"{k}_delay"),
                                 "amplitude": amp,
                                 "phase_rad": getattr(self, f"{k}_phase")})
            if refs:
                out["multipath"] = {"model": "specular", "reflections": refs}
        if out:
            out["models_to_iq"] = bool(self.models_to_iq)
        return out

    def _impairments_part(self) -> dict | None:
        """镜像 _impairmentsBody()：未启用返回 None。"""
        if not self.imp_enabled:
            return None
        imp = {"enabled_flag": True, "seed": int(self.imp_seed),
               "cfo_hz": self.imp_cfo, "sample_rate_ppm": self.imp_ppm,
               "phase_noise_deg_rms": self.imp_phn, "iq_gain_db": self.imp_gain,
               "iq_phase_deg": self.imp_iqphase, "dc_i": self.imp_dci,
               "dc_q": self.imp_dcq, "clip_fraction": self.imp_clip,
               "quant_bits": int(self.imp_bits)}
        snr = str(self.imp_snr).strip()
        if snr != "":
            imp["snr_db"] = float(snr)
        return imp

    def _fading_part(self) -> dict | None:
        """镜像 _engineBody() 的 fading 段。"""
        if self.fade_model in ("", "off"):
            return None
        f = {"model": self.fade_model, "environment": self.fade_env}
        spd = str(self.fade_speed).strip()
        if spd != "":
            f["speed_mps"] = float(spd)
        if self.fade_model == "keyed":
            if self.fade_key.strip():
                f["key"] = self.fade_key.strip()
            if self.fade_record_key:
                f["record_key"] = True
        else:
            f["seed"] = int(self.fade_seed)
        return f

    def _start_str(self) -> str:
        s = self.start_utc.strip().replace(" ", "T")
        if s.count(":") == 1:                     # datetime-local 无秒 → 补 :00
            s += ":00"
        return s

    def preview_body(self) -> dict:
        """镜像 btn-preview 的 /api/preview 请求体。"""
        b = {"lat": self.lat, "lon": self.lon, "alt": self.alt,
             "start_utc": self._start_str(),
             "rinex_path": self.rinex_path.strip() or "AUTO",
             "ephemeris_mode": self.ephemeris_mode,
             "systems": [s for s in SYSTEMS if s in self.systems]}
        b.update(self._models_part())
        if self.ephemeris_mode == "precise" and self.sp3_path.strip():
            b["sp3_path"] = self.sp3_path.strip()
        return b

    def generate_body(self) -> dict:
        """镜像 btn-generate 的 /api/generate 请求体（硬件字段天然缺席）。"""
        b: dict[str, Any] = {
            "rinex_path": self.rinex_path.strip() or "AUTO",
            "lat": self.lat, "lon": self.lon, "alt": self.alt,
            "start_utc": self._start_str(),
            "duration_s": int(self.duration_s),
            "sample_rate": self.sample_rate,
            "sample_format": self.sample_format,
            "ephemeris_mode": self.ephemeris_mode,
            "sv_clock": bool(self.sv_clock),
        }
        if self.route:
            b["route"] = self.route
        imp = self._impairments_part()
        if imp:
            b["impairments"] = imp
            b["random_seed"] = imp["seed"]
        b.update(self._models_part())
        b["engine"] = "native"
        if self.systems:
            b["systems"] = [s for s in SYSTEMS if s in self.systems]
        if self.bands:
            b["bands"] = [x for x in BANDS if x in self.bands]
        fd = self._fading_part()
        if fd:
            b["fading"] = fd
        if self.osnma_enabled:
            b["osnma"] = {"nmas": int(self.osnma_nmas)}
        if self.ephemeris_mode == "precise" and self.sp3_path.strip():
            b["sp3_path"] = self.sp3_path.strip()
        return b

    # ══ 场景库（与 Web /api/scenario 同一存储，可互通）════════════
    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("last_preview", None)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SimTask":
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**keep)
