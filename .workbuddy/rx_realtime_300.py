r"""真实接收机工作方式 300 s 验证（run 20261110T084902599874，无大气无钟差口径）。

流程（每星一个 worker，multiprocessing 并行）：
  1) 两段式捕获：全频带粗捕获（±5 kHz/200 Hz）→ 预移频精捕获（±250/25 Hz），
     种子落入 FLL ±25 Hz 无模糊窗（不使用生成侧真值）。
  2) pass1 自辅助跟踪 300 s（coh 模式，无 fd_fn：PLL 频率积分器驱动 NCO，
     等价真实接收机冷启动自主跟踪）→ 为电文解调提供逐时刻 chi/fd 种子。
  3) 电文解调：G LNAV 滑窗 13 s（tracked 种子，600 bit/窗，至子帧 {1,2,3} 齐）；
     E1B I/NAV 递增窗 30 s 分块 → decode_messages → reconstruct_ephemeris。
     记录每星"电文解析完整时刻" complete_t。
  4) 每秒 bit 流 hex：G 用 4× 抽取 IQ 的 30 s 分块 demod_nav_bits（1500 bit/块），
     按标称 20 ms bit 栅格分入秒桶；E 复用 I/NAV 分块的符号流按 4 ms 栅格分桶。
  5) pass2 正式跟踪 300 s：fd_fn 用【接收机自解星历】的几何多普勒 0.25 s 栅格
     （与既有验证配方一致）+ C/N0 矩法估计（tracker.cn0_est）。
  6) 逐秒观测（k=1..300）：锚定伪距（pred 用自解星历）、连续载波相位（cycles）、
     多普勒（Hz）、C/N0（dB-Hz，秒桶 k−1）。
  7) 电文全集完整（所有可用星 complete_t 最大值）后逐秒瞬时 LS 定位（不平均）,
     卫星位置/预测全部来自自解星历；TGD/BGD 保留（sv_clock=False 口径）。
  8) 落盘：RINEX 3.04 OBS（G: C1C/L1C/D1C/S1C；E: C1B/L1B/D1B/S1B）、
     RINEX 3.04 NAV（G+E 自解星历，写后用 georinex 回读抽查）、
     navbits_300.txt（每秒 hex 比特流）、rx_rt_300.json（全部中间量）。

Usage: python .workbuddy/rx_realtime_300.py [runid] [--workers 6]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import sys
import time as _ptime
import warnings

import numpy as np

warnings.filterwarnings("ignore")
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from backend import config, geometry                              # noqa: E402
from backend.ephem import ephemeris                               # noqa: E402

TRACK_S = 300.0
LOG_P = 0.05
DLL_BW = 0.5
MIN_METRIC_DB = 15.0


def _p(*a, **k):                                    # progress print
    print(f"[{_ptime.strftime('%H:%M:%S')}]", *a, flush=True)


# ===================================================================== #
# worker：单星完整流程（top-level，Windows spawn 可 pickle）              #
# ===================================================================== #
def _worker(arg):
    (outdir_s, sv, band, approx_llh, gps_sow0, opts) = arg
    from backend import inspector
    from backend.analysis.l1_acquire import acquire_l1
    from backend.analysis.tracker import SVTracker
    from backend.synth import signals

    outdir = pathlib.Path(outdir_s)
    sysc, prn = sv["sys"], int(sv["prn"])
    key = f"{sysc}{prn}"
    fs = float(band["fs"])
    fmt = opts["sample_format"]
    bf = outdir / band["file"]
    if_hz = float(sv.get("if_hz") or 0.0)
    signame = "GPS_L1CA" if sysc == "G" else "GAL_E1"
    sig = signals.SIGNALS[signame]
    chip_hz, L = float(sig.chip_rate_hz), int(sig.code_len)
    m_per_chip = config.C / chip_hz
    tv = _ptime.time()
    TS = float(opts.get("track_s", TRACK_S))
    out: dict = {"key": key, "sys": sysc, "prn": prn, "if_hz": if_hz,
                 "gain_db": sv.get("gain_db")}

    def rd(t0: float, ns: int) -> np.ndarray:
        # file-tail windows (t_end=TS hits EOF mid-window) come back short-
        # read from np.fromfile; pad with zeros so reshape/broadcast in the
        # tracker see the full window. All OBS epochs (t <= TS) stay clean.
        arr = inspector.read_iq(bf, fmt, max_samples=ns,
                               offset_samples=int(round(t0 * fs)))
        if arr.size < ns:
            arr = np.pad(arr, (0, ns - arr.size))
        return arr

    _wc: dict = {}

    def get_window(t0: float, ns: int) -> np.ndarray:
        k = (int(round(t0 * fs)), ns)
        hit = _wc.get(k)
        if hit is None:
            hit = rd(t0, ns)
            if len(_wc) > 250:
                _wc.clear()
            _wc[k] = hit
        return hit

    def _idx(t: float) -> int:                      # nearest 0.05 s log idx
        return int(np.clip(round(t / LOG_P), 0, round(TS / LOG_P)))

    try:
        # ---------------- 1) 两段式捕获 ----------------------------------
        # 粗捕获 50 ms 非相干（±5k/200），精捕获以粗值预移频后 150 ms
        # 非相干 + 10 Hz 细栅：残差 ≤±5 Hz，落进 coh-PLL ±100 Hz 无模糊窗。
        # （4 ms 短积分曾在 15.5 dB 星上出现过 218 Hz 错峰，勿再缩短。）
        npp = int(round(fs * L / chip_hz))
        nc_c, nc_f = 50, 150
        iq_c = rd(0.0, npp * nc_c + 16)
        tt0 = np.arange(len(iq_c)) / fs
        acq1 = acquire_l1(iq_c, fs, sysc, prn, centre_offset_hz=if_hz,
                          nperiods=nc_c)
        seg1 = iq_c * np.exp(-2j * np.pi * acq1["doppler_hz"] * tt0)
        acq2 = acquire_l1(seg1[:npp * nc_f + 16], fs, sysc, prn,
                          centre_offset_hz=if_hz,
                          dopp_hz=300.0, dopp_step_hz=10.0, nperiods=nc_f)
        out["acq"] = {"coarse": {"fd": acq1["doppler_hz"],
                                 "chi": acq1["code_phase_chips"],
                                 "metric_db": acq1["metric_db"]},
                      "fine": {"fd": acq2["doppler_hz"],
                               "chi": acq2["code_phase_chips"],
                               "metric_db": acq2["metric_db"]}}
        fd_seed = float(acq1["doppler_hz"]) + float(acq2["doppler_hz"])
        chi_seed = float(acq2["code_phase_chips"])
        if acq2["metric_db"] < MIN_METRIC_DB:
            out["skipped"] = f"weak ({acq2['metric_db']:.1f} dB)"
            _p(f"  {key}: SKIP {out['skipped']}")
            return out

        # ---------------- 2) pass1 自辅助 300 s --------------------------
        trk1 = SVTracker(get_window, fs, sysc, prn, chip_hz=chip_hz,
                         code_len=L, carrier_hz=float(sig.carrier_hz),
                         if_hz=if_hz, fd0=fd_seed, chi0=chi_seed,
                         boc=(sig.boc is not None), mode="coh",
                         dll_bw_hz=DLL_BW, cn0_est=False, fd_fn=None)
        trk1.run(t_end=TS + 1e-6, log_period_s=LOG_P)
        chi1 = np.asarray(trk1.chi_log, float)
        fd1 = np.asarray(trk1.fd_log, float)
        out["pass1"] = {"n_log": int(len(trk1.t_log)),
                        "n_dropped": int(trk1.n_dropped),
                        "fd_end_hz": float(trk1.fd),
                        "pll_off_end_hz": float(trk1._pll_off)}
        _p(f"  {key}: pass1 done {trk1.fd:+.1f}Hz "
           f"({int(trk1.n_dropped)} drop)")

        # ---------------- 3) 电文解调 ------------------------------------
        from backend.analysis import lnav_decode, inav_decode
        fields, complete_t, nav_info = None, None, {}
        approx_rx = np.array(geometry.llh_to_ecef(*approx_llh))
        if sysc == "G":
            sfs: dict[int, list] = {}
            done_at = None
            for t_a in range(21, max(2, min(281, int(TS))), 5):
                _p(f"    {key} G-decode win t_a={t_a} sfs={sorted(sfs)}")
                iq = rd(float(t_a), int(13 * fs))
                bits = lnav_decode.demod_nav_bits(
                    iq, fs, prn, float(chi1[_idx(t_a)]), float(fd1[_idx(t_a)]),
                    n_bits=600, rate_span=4.0)
                if len(bits) >= 600:
                    for h in lnav_decode.find_frame(bits):
                        sfs.setdefault(int(h["subframe_id"]), h["words"])
                iq = None
                if {1, 2, 3} <= set(sfs):
                    done_at = t_a
                    break
            nav_info["subframes"] = sorted(sfs)
            if done_at is not None:
                fields = lnav_decode.decode_ephemeris(sfs)
                # decode_ephemeris 不带 prn/system；从星上下文盖入（RINEX
                # NAV 行与 state_fn_for 分派都需要）。LNAV WN 只有 10 bit
                # （如 391）；RINEX NAV epoch 需完整周，也从 run 上下文盖
                # （Kepler 传播用绝对 t，不受此字段影响）。
                fields["prn"] = prn
                fields["system"] = "G"
                fields["gps_week"] = int(opts.get("gps_week")
                                         or fields.get("gps_week") or 0)
                complete_t = float(done_at + 13)
        else:
            chunks: list[np.ndarray] = []
            for W in list(range(60, int(TS) + 1, 30)) or [max(60, int(TS))]:
                while len(chunks) * 30 < W:
                    c0 = len(chunks) * 30
                    iq = rd(float(c0), int(30 * fs))
                    if c0 == 0:
                        ch, fdch = chi_seed, fd_seed
                    else:
                        ch, fdch = float(chi1[_idx(c0)]), float(fd1[_idx(c0)])
                    _p(f"    {key} E-chunk c0={c0} W={W} seed=({ch:.2f}ch,"
                       f"{fdch:+.1f}Hz)")
                    sy = inav_decode.demod_symbols_e1b(
                        iq, fs, prn, centre_offset_hz=if_hz,
                        dopp_hz=fdch, code_phase_chips=ch)
                    chunks.append(np.asarray(sy, np.int8))
                    iq = None
                try:
                    msgs = inav_decode.decode_messages(
                        np.concatenate(chunks).tolist())
                    fields = inav_decode.reconstruct_ephemeris(msgs)
                    nav_info["pages"] = len(msgs)
                    complete_t = float(W)
                    break
                except ValueError as exc:
                    nav_info["reason_last"] = str(exc)
            nav_info["chunks"] = [int(c.size) for c in chunks]

        out["nav"] = {"decoded": fields is not None,
                      "complete_t_s": complete_t, **nav_info}
        if fields is None:
            # 电文不全：保留 pass1 观测（伪距以 pass1 chi 对 BRDC 预测锚定意义
            # 不强），从定位集中剔除；报告单列。
            out["skipped"] = "nav incomplete"
            _p(f"  {key}: NAV FAIL {nav_info.get('reason_last', '')}")
            return out
        _p(f"  {key}: nav OK complete_t={complete_t}s")

        # ---------------- 4) 每秒 bit 流（hex 源） ------------------------
        # G: 4× 抽取 30 s 分块 demod_nav_bits（快速通道），bit 按标称 20 ms
        #    栅格分桶（chunk 内对齐 ≤19 ms 的不确定度只影响秒界 1 bit）；
        # E: 与解码同款快速通道全程 30 s 分块 demod_symbols_e1b（pass1 块首
        #    态为种子），符号按标称 4 ms 栅格分桶——解码 chunk 只到 complete_t
        #    为止（~60 s），复用它会留下 60 s 后的空洞，必须全程独立提取。
        bits_by_sec: dict[int, list[int]] = {}
        if sysc == "G":
            for c0 in range(0, int(TS), 30):
                # 预分配 + 逐片填充（4× 抽取），避免 4 片同驻 + concatenate 双拷贝
                n_e = int(7.5 * fs) // 4
                iq_s = np.empty(n_e * 4, np.complex64)
                for i in range(4):
                    p = rd(c0 + i * 7.5, int(7.5 * fs))[::4]
                    iq_s[i * n_e:i * n_e + len(p)] = p[:n_e]
                    del p
                ch, fdch = float(chi1[_idx(c0)]), float(fd1[_idx(c0)])
                bits = lnav_decode.demod_nav_bits(
                    iq_s, fs / 4.0, prn, ch, fdch, n_bits=1500,
                    rate_span=4.0)
                for b, v in enumerate(bits.tolist()):
                    sec = c0 + int((0.02 * b + 0.01) // 1.0)
                    if 0 <= sec < int(TS):
                        bits_by_sec.setdefault(sec, []).append(int(v))
        else:
            # 全程符号快速通道：30 s 分块，块首用 pass1 态做种子，与解码
            # 同款 demod_symbols_e1b 配方；符号按标称 4 ms 栅格分桶（块界
            # ≤4 ms 对齐不确定度只影响秒界 1 符号）。
            for c0 in range(0, int(TS), 30):
                if c0 == 0:
                    ch, fdch = chi_seed, fd_seed
                else:
                    ch, fdch = float(chi1[_idx(c0)]), float(fd1[_idx(c0)])
                iq = rd(float(c0), int(min(30, TS - c0) * fs))
                sy = inav_decode.demod_symbols_e1b(
                    iq, fs, prn, centre_offset_hz=if_hz,
                    dopp_hz=fdch, code_phase_chips=ch)
                for j, v in enumerate(np.asarray(sy, np.int8).tolist()):
                    sec = c0 + int((0.004 * j + 0.002) // 1.0)
                    if 0 <= sec < int(TS):
                        bits_by_sec.setdefault(sec, []).append(int(v))
                iq = None
        out["bits_sec_n"] = {s: len(v) for s, v in sorted(bits_by_sec.items())}

        # ---------------- 5) 预测栅格（自解星历） ------------------------
        svb = geometry.group_delay_bias_s(sysc, "L1", fields)
        state = geometry.state_fn_for(fields)
        t_g = np.arange(0.0, TS + 0.51, 0.25)
        fd_g = np.empty(t_g.size)
        pr_g = np.empty(t_g.size)
        for i, tk in enumerate(t_g):
            o = geometry.observables(state, approx_rx, gps_sow0 + float(tk),
                                     signal=sig, sv_clock_bias_s=svb,
                                     sv_clock=False)
            fd_g[i] = o["carrier_doppler_hz"]
            pr_g[i] = o["pseudorange_m"]
        el_fix = geometry.observables(state, approx_rx,
                                       gps_sow0 + TS, signal=sig,
                                       sv_clock_bias_s=svb,
                                       sv_clock=False)["el_deg"]

        # ---------------- 6) pass2 正式跟踪 + C/N0 -----------------------
        trk2 = SVTracker(get_window, fs, sysc, prn, chip_hz=chip_hz,
                         code_len=L, carrier_hz=float(sig.carrier_hz),
                         if_hz=if_hz, fd0=fd_seed, chi0=chi_seed,
                         boc=(sig.boc is not None), mode="coh",
                         dll_bw_hz=DLL_BW, cn0_est=True,
                         fd_fn=lambda t: float(np.interp(t, t_g, fd_g)))
        trk2.run(t_end=TS + 1e-6, log_period_s=LOG_P)

        obs: dict[int, dict] = {}
        for k in range(1, int(TS) + 1):
            m = trk2.measure(float(k))
            if not m:
                continue
            pred_pr = float(np.interp(k, t_g, pr_g))
            pp = pred_pr / config.C * chip_hz
            err = ((m["chi_chips"] - pp + L / 2.0) % L) - L / 2.0
            meas_pr = pred_pr + err * m_per_chip
            obs[k] = {"chi_chips": m["chi_chips"], "err_chips": err,
                      "fd_hz": m["doppler_hz"],
                      "phase_cycles": m.get("carrier_phase_cycles"),
                      "cn0_dbhz": trk2.cn0_dbhz(k - 1),
                      "pred_pr_m": pred_pr,
                      "meas_pr_m": meas_pr,
                      "corr_pr_m": meas_pr + config.C * svb}
        # 会话统计（t>=1 s）：err 中值 / chi 去趋势抖动 / 相位去趋势抖动+漂移
        tl = np.asarray(trk2.t_log, float)
        es = np.array([o["err_chips"] for o in obs.values()], float)
        stats = {"err_med_ch": float(np.median(es)) if es.size else None,
                 "err_rms_ch": (float(np.sqrt(np.mean((es - np.median(es))
                                                      ** 2)))
                                if es.size else None)}
        sel = tl >= 1.0
        cl = np.unwrap(np.asarray(trk2.chi_log, float), period=float(L))
        if sel.sum() >= 8:
            pf = np.polyfit(tl[sel], cl[sel], 1)
            r = cl[sel] - np.polyval(pf, tl[sel])
            stats["chip_rms_ch"] = float(np.sqrt(np.mean(r * r)))
        if trk2.phase_log:
            # 锚定残差（demo 口径）：引擎相位=geo（本 run 无大气/钟差），
            # 锁定时 φ ≈ ρ/λ + N → φ + pr_g/λ 应近常数；先锚定再去趋势，
            # drift 才是真实残余（demo：E 0.05~0.13 cyc/s），raw NCO 斜坡
            # （≈fd）只进 RINEX L1C（真实接收机报告即累积周数）。
            lam = config.C / float(sig.carrier_hz)
            # unwrap AFTER anchoring (l1_fix L488 recipe): unwrapping the
            # raw NCO series first would wrap at 2π and destroy the ~fd
            # ramp (observed: slope 1166 → 35 cyc/s square-wave artifact).
            raw = np.asarray(trk2.phase_log, float)
            ph = np.unwrap(raw + np.interp(tl, t_g, pr_g) / lam)
            if sel.sum() >= 16:
                pf = np.polyfit(tl[sel], ph[sel], 1)
                stats["phase_drift_cycps"] = float(pf[0])
                stats["phase_rms_cycles"] = float(np.sqrt(np.mean(
                    (ph[sel] - np.polyval(pf, tl[sel])) ** 2)))
        secs = _ptime.time() - tv
        out.update({"stats": stats, "el_fix_deg": el_fix, "svb_s": svb,
                    "obs": obs, "fields": fields,
                    "n_dropped2": int(trk2.n_dropped),
                    "_bits": bits_by_sec,
                    "secs": secs})
        em = stats["err_med_ch"]
        _p(f"  {key}: pass2 OK err_med="
           f"{'--' if em is None else format(em, '+.5f')}ch ({secs:.0f}s)")
        return out
    except Exception as exc:                          # noqa: BLE001
        import traceback
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["tb"] = traceback.format_exc()[-1500:]
        _p(f"  {key}: ERROR {out['error']}")
        return out


# ===================================================================== #
# RINEX 3.04 writers                                                     #
# ===================================================================== #
def _f20(v) -> str:
    # RINEX 3 nav numeric fields are right-aligned 19-char slots when the
    # epoch line starts its clock fields at column 23 and continuation
    # lines start at column 4 (both give (80-start)/4 = 19): georinex/nav3
    # slices raw at FIXED width LF=19 (nav3.py L17), so width must be 19 —
    # 20 desynchronises every slice and yields all-NaN rows.
    return f"{float(v or 0.0):19.12E}"


def _nav_epoch_line(sysc: str, prn: int, when: dt.datetime) -> str:
    # RINEX 3.04 epoch line, as georinex/nav3._time parses it: year is
    # FOUR digits (ln[4:8]); month [9:11] day [12:14] hour [15:17]
    # minute [18:20] second [21:23]; the three clock fields start at
    # column 23 (raw = line[23:80]). Verified against BRDC_2026283.rnx
    # ("G01 2026 10 10 04 00 00 1.53...E-04...").
    return (f"{sysc}{prn:02d} {when.year:04d} {when.month:02d} "
            f"{when.day:02d} {when.hour:02d} {when.minute:02d} "
            f"{when.second:02d}")


def rinex3_nav(svs_nav: list[tuple[str, dict]]) -> str:
    """svs_nav: [(sysc, decoded_fields)] — 与 georinex nav3 字段布局逐位对应
    （写后可用 georinex 回读校验）。"""
    hdr = [
        "     3.04           N: GNSS NAV DATA    G:E:GNSS   RINEX VERSION / TYPE",
        f"rx_realtime_300     GNSS-SIM            "
        f"{dt.datetime.utcnow():%Y%m%d %H%M%S UTC} PGM / RUN BY / DATE",
        "    Self-decoded (receiver-side) broadcast ephemeris, demodulated"   .ljust(60)
        + "COMMENT",
        "    from the 300 s IQ capture; G=LNAV sf1-3, E=I/NAV wt1-4."        .ljust(60)
        + "COMMENT",
        "                                                        END OF HEADER",
    ]
    lines = list(hdr)
    for sysc, rec in svs_nav:
        prn = int(rec["prn"])
        if sysc == "G":
            week = int(rec.get("gps_week", 0))
            when = (ephemeris._GPS_EPOCH
                    + dt.timedelta(weeks=week, seconds=rec.get("toc", 0.0)))
            lines.append(_nav_epoch_line("G", prn, when)
                         + _f20(rec.get("af0")) + _f20(rec.get("af1"))
                         + _f20(rec.get("af2")))
            lines.append("    " + _f20(rec.get("iode")) + _f20(rec.get("crs"))
                         + _f20(rec.get("delta_n")) + _f20(rec.get("m0")))
            lines.append("    " + _f20(rec.get("cuc")) + _f20(rec.get("e"))
                         + _f20(rec.get("cus")) + _f20(rec.get("sqrtA")))
            lines.append("    " + _f20(rec.get("toe")) + _f20(rec.get("cic"))
                         + _f20(rec.get("omega0")) + _f20(rec.get("cis")))
            lines.append("    " + _f20(rec.get("i0")) + _f20(rec.get("crc"))
                         + _f20(rec.get("omega")) + _f20(rec.get("omega_dot")))
            lines.append("    " + _f20(rec.get("idot"))
                         + _f20(rec.get("codes_l2", 0)) + _f20(week)
                         + _f20(0))
            lines.append("    " + _f20(0) + _f20(rec.get("health", 0))
                         + _f20(rec.get("tgd")) + _f20(rec.get("iodc")))
            lines.append("    " + _f20(0) + _f20(2.0) + _f20(0) + _f20(0))
        else:
            wkg = int(rec.get("gal_week", 0))
            # GST week 0 = 1999-08-22 00:00 UTC (GPS-13 s 差忽略，仅报头展示用)
            when = (dt.datetime(1999, 8, 22)
                    + dt.timedelta(weeks=wkg, seconds=rec.get("toc", 0.0)))
            lines.append(_nav_epoch_line("E", prn, when)
                         + _f20(rec.get("af0")) + _f20(rec.get("af1"))
                         + _f20(rec.get("af2")))
            lines.append("    " + _f20(rec.get("iodnav"))
                         + _f20(rec.get("crs")) + _f20(rec.get("delta_n"))
                         + _f20(rec.get("m0")))
            lines.append("    " + _f20(rec.get("cuc")) + _f20(rec.get("e"))
                         + _f20(rec.get("cus")) + _f20(rec.get("sqrtA")))
            lines.append("    " + _f20(rec.get("toe")) + _f20(rec.get("cic"))
                         + _f20(rec.get("omega0")) + _f20(rec.get("cis")))
            lines.append("    " + _f20(rec.get("i0")) + _f20(rec.get("crc"))
                         + _f20(rec.get("omega")) + _f20(rec.get("omega_dot")))
            lines.append("    " + _f20(rec.get("idot")) + _f20(3)
                         + _f20(wkg) + _f20(0))
            lines.append("    " + _f20(rec.get("sisa", 0)) + _f20(0)
                         + _f20(rec.get("tgd_e5a")) + _f20(rec.get("tgd")))
            lines.append("    " + _f20(0) + _f20(0) + _f20(0) + _f20(0))
    return "\n".join(lines) + "\n"


def _obs14(v, lli="   ", ssi="1") -> str:
    if v is None or not np.isfinite(float(v)):
        return " " * 14 + "   " + " "
    return f"{float(v):14.3f}{lli}{ssi}"


def rinex3_obs(runid: str, first_obs: dt.datetime, rows: list[dict]) -> str:
    """rows: [{k_sow, date, svs:{key:{'C1C','L1C','D1C','S1C'}}}]"""
    hdr = [
        "     3.04           OBSERVATION DATA    G             RINEX VERSION / TYPE",
        f"rx_realtime_300     GNSS-SIM            "
        f"{dt.datetime.utcnow():%Y%m%d %H%M%S UTC} PGM / RUN BY / DATE",
        ("    C1C/C1B = anchored pseudorange [m] incl. broadcast TGD/BGD;"
         ).ljust(60) + "COMMENT",
        ("    L1C/L1B = tracked NCO carrier phase [cycles, continuous];"
         ).ljust(60) + "COMMENT",
        ("    D1C/D1B = tracked carrier Doppler [Hz]; S1C/S1B = C/N0"
         " [dB-Hz, moment est.]."  ).ljust(60) + "COMMENT",
        ("    Run " + runid + ", no-atmosphere / no-sv-clock policy;"
         " SSI=1 = tracking+nav-locked.").ljust(60) + "COMMENT",
        "    1.0000                                              INTERVAL",
        "G     4 C1C L1C D1C S1C                                   SYS / # / OBS TYPES",
        "E     4 C1B L1B D1B S1B                                   SYS / # / OBS TYPES",
        f"{first_obs.year:4d} {first_obs.month:2d} {first_obs.day:2d} "
        f"{first_obs.hour:2d} {first_obs.minute:2d} "
        f"{first_obs.second + first_obs.microsecond / 1e6:9.6f}"
        "     GPS                                        TIME OF FIRST OBS",
        "                                                        END OF HEADER",
    ]
    lines = list(hdr)
    for r in rows:
        d = r["date"]
        svs = r["svs"]
        # RINEX 3.04 epoch header: "> " I4 1X I2 1X I2 1X I2 1X I2 1X F11.7
        # 3X I1(obs sys=0) I3(num) -- minute and second must be space-split.
        lines.append(f"> {d.year:04d} {d.month:02d} {d.day:02d} {d.hour:02d} "
                     f"{d.minute:02d} {d.second + d.microsecond / 1e6:10.7f}"
                     f"   0{len(svs):3d}")
        for key in sorted(svs):
            o = svs[key]
            lines.append(f"{key:<3}" + _obs14(o["C1C"]) + _obs14(o["L1C"])
                         + _obs14(o["D1C"]) + _obs14(o["S1C"]))
    return "\n".join(lines) + "\n"


def bits_hex_file(runid: str, svs_out: list[dict]) -> str:
    lines = [
        f"# run {runid} — 每秒解调电文比特流（hex ASCII）",
        "# 列: 秒(从0) SV 系统 PRN 类型 比特数 16进制比特流",
        "# G: LNAV 50 bps → 标称 50 bit/秒（4x 抽取快通道，bit 按标称 20 ms",
        "#    栅格分桶，秒界 bit 至多偏移 1）",
        "# E: I/NAV 250 sym/s → 标称 250 符号/秒（复用解码分块符号流，",
        "#    4 ms 符号栅格，块界至多偏移 1 符号）",
    ]
    return lines


def bits_hex_rows(svs_out: list[dict], bit_payload: dict) -> list[str]:
    lines = []
    for so in svs_out:
        kind = "navbits" if so["sys"] == "G" else "inav_syms"
        for sec, bits in sorted((bit_payload.get(so["key"]) or {}).items()):
            n = len(bits)
            pad = (-n) % 4
            v = int("".join(str(b) for b in bits) + "0" * pad or "0", 2)
            hexs = format(v, f"0{(n + pad) // 4}X") if n else ""
            lines.append(f"{sec:4d} {so['key']:<4} {so['sys']} "
                         f"{so['prn']:2d} {kind:9s} {n:4d} {hexs}")
    return lines


# ===================================================================== #
# ENU + main                                                             #
# ===================================================================== #
def ecef_to_enu(d_ecef, lat_deg: float, lon_deg: float) -> tuple:
    p, l = math.radians(lat_deg), math.radians(lon_deg)
    sp, cp, sl, cl = math.sin(p), math.cos(p), math.sin(l), math.cos(l)
    e = -sl * d_ecef[0] + cl * d_ecef[1]
    n = -sp * cl * d_ecef[0] - sp * sl * d_ecef[1] + cp * d_ecef[2]
    u = cp * cl * d_ecef[0] + cp * sl * d_ecef[1] + sp * d_ecef[2]
    return e, n, u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runid", nargs="?", default="20261110T084902599874")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--track-s", type=float, default=TRACK_S,
                    help="session length (smoke: 60)")
    ap.add_argument("--limit", type=int, default=0,
                    help="smoke: max SVs (G-first, half E)")
    ap.add_argument("--no-sim-trace", dest="sim_trace", action="store_false")
    ap.add_argument("--sim-trace", dest="sim_trace", action="store_true",
                    default=True,
                    help="also dump trace_sim.json @epochs (task #36)")
    a = ap.parse_args()
    TS = float(a.track_s)

    import multiprocessing as mp

    outdir = (config.OUT_DIR / a.runid
              if not pathlib.Path(a.runid).is_absolute()
              else pathlib.Path(a.runid))
    meta = json.loads((outdir / "meta.json").read_text())
    cfg = meta["config"]
    marker = (float(cfg["lat"]), float(cfg["lon"]), float(cfg["alt"]))
    start = dt.datetime.fromisoformat(cfg["start_utc"])
    gps_start = start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
    week, sow0 = ephemeris.gps_week_and_sow(gps_start)
    band = meta["bands"][0]
    opts = {"sample_format": meta.get("sample_format", "int8"),
            "track_s": TS, "gps_week": week}
    svs = [s for s in meta["provenance"]["svs"] if s["sys"] in ("G", "E")]
    if a.limit:
        gs = [s for s in svs if s["sys"] == "G"][:a.limit - a.limit // 2]
        es = [s for s in svs if s["sys"] == "E"][:a.limit // 2]
        svs = gs + es
    _p(f"run {outdir.name}  {len(svs)} SVs  fs={band['fs']}  "
       f"marker={marker}  gps_week={week} sow0={sow0:.1f}")

    t0 = _ptime.time()
    args = [(str(outdir), s, band, marker, float(sow0), opts) for s in svs]
    with mp.Pool(processes=a.workers) as pool:
        svs_out = pool.map(_worker, args, chunksize=1)
    _p(f"workers done in {(_ptime.time() - t0) / 60:.1f} min")

    # ---- 比特流 payload（worker 里 bits_by_sec 在 obs 同级键上） ----
    # worker 返回时把 bits_by_sec 挂在 _bits（dict[int,list]）
    bit_payload = {so["key"]: so.pop("_bits", {}) for so in svs_out}
    # 说明：worker 内 bits_by_sec 已改名挂 _bits
    for so in svs_out:
        so.setdefault("_bits", {})

    usable = [so for so in svs_out
              if so.get("fields") and so.get("obs")]
    failed = [so for so in svs_out if so not in usable]
    dec_ok = [so for so in usable if so["nav"]["decoded"]]
    if len(usable) < 4:
        _p(f"FATAL: only {len(usable)} usable SVs -- abort")
        for so in failed:
            _p("  fail:", so.get("key"), so.get("skipped"), so.get("error"))
        sys.exit(2)
    t_full = max(so["nav"]["complete_t_s"] for so in usable)

    # ---- 逐秒 LS（自解星历），不平均 ----
    from backend.analysis.receiver import _ecef_to_llh, solve_position
    approx_rx = np.array(geometry.llh_to_ecef(*marker))
    marker_ecef = approx_rx
    states, svbs = {}, {}
    for so in usable:
        states[so["key"]] = geometry.state_fn_for(so["fields"])
        svbs[so["key"]] = geometry.group_delay_bias_s(
            so["sys"], "L1", so["fields"])
    fix_rows = []
    k_first = max(1, int(math.ceil(t_full)))
    for k in range(k_first, int(TS) + 1):
        prs, poss = {}, {}
        for so in usable:
            o = (so["obs"] or {}).get(str(k)) or (so["obs"] or {}).get(k)
            if o is None:
                continue
            prs[so["key"]] = o["corr_pr_m"]
            pos, _v, _t, _c = geometry.solve_transmit_time(
                states[so["key"]], approx_rx, float(sow0) + k)
            poss[so["key"]] = pos
        if len(prs) < 4:
            continue
        sol = solve_position(prs, poss, x0=[*approx_rx, 0.0])
        lat, lon, h = _ecef_to_llh(*sol["ecef"])
        ents = [{"_los": ((poss[kk] - np.array(sol["ecef"]))
                          / np.linalg.norm(poss[kk] - np.array(sol["ecef"])))
                 .tolist()} for kk in sorted(prs)]
        pdop = geometry.dop(ents, sol["ecef"])["pdop"]
        e, n, u = ecef_to_enu(np.array(sol["ecef"]) - marker_ecef,
                              marker[0], marker[1])
        d = gps_start + dt.timedelta(seconds=k - 1)     # 文件秒 k ↔ 采集第 k 秒
        fix_rows.append({
            "t_s": k, "date": d.isoformat(),
            "ecef": sol["ecef"], "llh": [lat, lon, h],
            "enu_m": [e, n, u], "err_h_m": math.hypot(e, n),
            "err_3d_m": float(np.linalg.norm(np.array(sol["ecef"])
                                             - marker_ecef)),
            "clock_bias_s": sol["clock_bias_s"], "pdop": pdop,
            "residual_rms_m": sol["residual_rms_m"], "nsat": len(prs)})
    _p(f"LS done: {len(fix_rows)} epochs from t={k_first}s")

    errs = np.array([r["err_3d_m"] for r in fix_rows])
    summary = {
        "t_full_s": t_full, "fix_first_t_s": k_first, "n_fix": len(fix_rows),
        "err_3d_rms_m": float(np.sqrt(np.mean(errs ** 2))) if errs.size else None,
        "err_3d_med_m": float(np.median(errs)) if errs.size else None,
        "err_3d_p95_m": float(np.percentile(errs, 95)) if errs.size else None,
        "err_h_rms_m": (float(np.sqrt(np.mean(
            np.array([r["err_h_m"] ** 2 for r in fix_rows]))))
            if fix_rows else None),
        "pdop_mean": float(np.mean([r["pdop"] for r in fix_rows]))
        if fix_rows else None,
        "n_usable": len(usable), "n_failed": [
            {k: so.get(k) for k in ("key", "skipped", "error")}
            for so in failed],
        "nsys": {"G": sum(1 for s in usable if s["sys"] == "G"),
                 "E": sum(1 for s in usable if s["sys"] == "E")},
    }

    # ---- RINEX OBS 行（全部 300 历元，1 Hz） ----
    obs_rows = []
    for k in range(1, int(TS) + 1):
        d = gps_start + dt.timedelta(seconds=k - 1)
        s_d = {}
        for so in usable:
            o = (so["obs"] or {}).get(str(k)) or (so["obs"] or {}).get(k)
            if o is None:
                continue
            s_d[so["key"]] = {"C1C": o["corr_pr_m"],
                              "L1C": o["phase_cycles"],
                              "D1C": o["fd_hz"], "S1C": o["cn0_dbhz"]}
        if s_d:
            obs_rows.append({"k_sow": k, "date": d, "svs": s_d})
    (outdir / "rx_rt_300.304o").write_text(
        rinex3_obs(outdir.name, obs_rows[0]["date"], obs_rows))
    (outdir / "rx_rt_300.304n").write_text(
        rinex3_nav([(so["sys"], so["fields"]) for so in dec_ok]))
    (outdir / "navbits_300.txt").write_text(
        "\n".join(bits_hex_file(outdir.name, usable)
                  + bits_hex_rows(usable, bit_payload)) + "\n")

    # georinex 回读抽查 NAV（sv 坐标 = "G01"/"E04"；sqrtA 逐星比对）
    nav_rt = "skip"
    try:
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            import georinex
            ds = georinex.load(outdir / "rx_rt_300.304n")
        bad = []
        have = {str(s) for s in ds.coords["sv"].values}
        for so in dec_ok:
            # georinex pads SV names to 3 chars ("G01"/"E04"), our key is
            # "G1"/"E4" (matches our OBS file, which uses the same key).
            name = f"{so['sys']}{int(so['prn']):02d}"
            if name not in have:
                bad.append(so["key"] + ":missing")
                continue
            # G/E epoch times differ → merge pads the other system's time
            # rows with NaN; take the finite row(s), not isel(time=0).
            arr = np.asarray(ds["sqrtA"].sel(sv=name).values, float)
            arr = arr[np.isfinite(arr)]
            if arr.size == 0:
                bad.append(so["key"] + ":empty")
                continue
            v = float(arr[0])
            if abs(v - float(so["fields"]["sqrtA"])) > 1e-3:
                bad.append(so["key"])
        nav_rt = "ok" if not bad else f"mismatch:{bad}"
    except Exception as exc:                            # noqa: BLE001
        nav_rt = f"readback-fail: {exc}"

    # ---- json ----
    doc = {
        "kind": "rx_realtime_300", "runid": outdir.name,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(
            timespec="seconds"),
        "policy": {"atmosphere": "off", "sv_clock": False,
                   "ephemeris_source": "receiver-decoded (LNAV/I/NAV)",
                   "track_s": TS, "dll_bw_hz": DLL_BW,
                   "mode": "coh", "ls_averaging": "none (instantaneous)"},
        "marker_llh": list(marker), "gps_week": week, "sow0": float(sow0),
        "svs": [{k: so.get(k) for k in
                 ("key", "sys", "prn", "gain_db", "acq", "pass1", "nav",
                  "stats", "el_fix_deg", "svb_s", "n_dropped2", "skipped",
                  "error", "tb", "secs")}
                | {"obs": so.get("obs")} for so in svs_out],
        "fixes": fix_rows, "summary": summary, "nav_rinex_readback": nav_rt,
        "outputs": ["rx_rt_300.304o", "rx_rt_300.304n", "navbits_300.txt",
                    "rx_rt_300.json"],
    }
    # worker 里 bits_by_sec 已改名挂 _bits；obs 的 int key 转 json 字符串
    (outdir / "rx_rt_300.json").write_text(
        json.dumps(doc, indent=1, default=float))

    # ---- task #36: 300 历元仿真真值 trace ----
    if a.sim_trace:
        from backend.analysis import trace as _tr
        rp = cfg.get("rinex_path")
        eph = ephemeris.parse_rinex_multi(
            rp, tuple({s["sys"] for s in svs}),
            at_gps=gps_start if meta["provenance"].get("engine") == "native"
            else None)
        eph = ephemeris.align_for_run(eph, week, sow0,
                                      meta["provenance"].get("engine"))
        _tr.dump_sim_trace(outdir, eph=eph, step_s=1.0, n_max=300)
        _p("trace_sim.json @300 epochs dumped")

    _p(f"T_full={t_full}s  first fix t={k_first}s  n_fix={len(fix_rows)}")
    _p(f"err3d: rms={summary['err_3d_rms_m']} med={summary['err_3d_med_m']}"
       f" p95={summary['err_3d_p95_m']}  PDOP~{summary['pdop_mean']}")
    _p(f"nav readback: {nav_rt}   usable={len(usable)} "
       f"(G{summary['nsys']['G']}/E{summary['nsys']['E']})")


if __name__ == "__main__":
    main()
