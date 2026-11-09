"""Plot sim-truth vs receiver-measured observables for one run.

Reads (or regenerates with --regen) the two unified-grid dumps
``out/<runid>/trace_sim.json`` and ``out/<runid>/trace_rx.json`` written by
backend/analysis/trace.py, and renders ``out/<runid>/trace_compare.png``:

  1 code-phase error      measured - synthesized, chips, per SV vs t
  2 pseudorange residual  measured_pr - sim truth pr, metres, per SV vs t
  3 Doppler time series   per-system best SV: measured vs geometric truth
                          and the constant the synthesizer actually injected
  4 Doppler quantisation  histogram of measured - synthesized constant
  5 acquisition metric    metric_db(t) with the SV's gain_db taper baseline
  6 strength correlation  per-SV mean metric_db vs gain_db scatter

Usage: python scripts/plot_trace.py <runid|outdir> [--epochs N] [--step S]
                                   [--regen] [--dll]

With --dll the receiver-side tracking dump (trace_dll.json, carrier-aided
DLL) is loaded/regenerated as well and a second figure trace_dll.png is
written: acquisition-vs-DLL code-phase error overlay, error histograms,
pseudorange residuals and a per-method RMS table.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import warnings

import numpy as np

# georinex/xarray emit a wall of FutureWarning per BRDC parse; irrelevant here
warnings.filterwarnings("ignore")

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import matplotlib                                                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

from backend import config                                       # noqa: E402
from backend.analysis import trace                               # noqa: E402


def _resolve_outdir(arg: str) -> pathlib.Path:
    p = pathlib.Path(arg)
    if not p.is_absolute():
        p = config.OUT_DIR / arg
    if not (p / "meta.json").exists():
        raise SystemExit(f"not a run dir (no meta.json): {p}")
    return p


def _load(p: pathlib.Path, name: str, regen, dumper):
    f = p / name
    if not f.exists() or regen:
        res = dumper(p)
        if res is None:
            raise SystemExit(f"cannot produce {name} for {p} "
                             "(non-native run or ephemeris unavailable)")
    return json.loads(f.read_text())


def _dll_figure(od: pathlib.Path, sim: dict, rx: dict, dl: dict) -> None:
    """Second figure: acquisition snapshot vs carrier-aided DLL tracking."""
    keys = sorted(set(sim["svs"]) & set(rx["svs"]) & set(dl["svs"]))
    if not keys:
        print("dll: no SV common to sim/rx/dll traces -- skipping figure")
        return
    t = dl["t_s"]
    cmap = plt.get_cmap("tab10")
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9.5))
    fig.suptitle(
        f"Acquisition snapshot vs carrier-aided DLL tracking -- run "
        f"{sim['runid']}  ({len(keys)} SVs, {len(t)} epochs @ {dl['step_s']} s)",
        fontsize=12)

    rms_a, rms_d = {}, {}

    # (a) code-phase error overlay: acq thin grey, DLL colored
    ax = axes[0][0]
    for i, k in enumerate(keys):
        ea = np.asarray(rx["svs"][k]["err_chips"][:len(t)])
        ed = np.asarray(dl["svs"][k]["err_chips"][:len(t)])
        ax.plot(t[:len(ea)], ea, lw=0.7, color="#bbb", zorder=1)
        ax.plot(t[:len(ed)], ed, lw=1.0, color=cmap(i % 10), label=k,
                zorder=2)
        rms_a[k] = float(np.sqrt(np.mean(ea ** 2)))
        rms_d[k] = float(np.sqrt(np.mean(ed ** 2)))
    ax.set_title("a) chip error vs prediction: acq (grey, per-SV coloured "
                 "= DLL)")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("chip error [chips]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=6, ncol=4, loc="best")

    # (b) error histograms on one axis
    ax = axes[0][1]
    ea_all = np.concatenate([np.asarray(rx["svs"][k]["err_chips"][:len(t)])
                             for k in keys])
    ed_all = np.concatenate([np.asarray(dl["svs"][k]["err_chips"][:len(t)])
                             for k in keys])
    bins = np.linspace(-0.15, 0.15, 121)
    ax.hist(ea_all, bins=bins, color="#999", alpha=0.75,
            label=f"acq  RMS {np.sqrt(np.mean(ea_all**2)):.4f} ch")
    ax.hist(ed_all, bins=bins, color="#c33", alpha=0.65,
            label=f"DLL  RMS {np.sqrt(np.mean(ed_all**2)):.4f} ch")
    ax.set_yscale("log")
    ax.set_title("b) error histograms (log count): grid quantization vs "
                 "continuous loop state")
    ax.set_xlabel("chip error [chips]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # (c) pseudorange residual vs sim truth
    ax = axes[1][0]
    pa_all, pd_all = [], []
    for i, k in enumerate(keys):
        simk = sim["svs"][k]
        if "pr_truth_m" not in simk:
            continue
        da = np.asarray(rx["svs"][k]["meas_pr_m"][:len(t)]) \
            - np.asarray(simk["pr_truth_m"][:len(t)])
        dd = np.asarray(dl["svs"][k]["meas_pr_m"][:len(t)]) \
            - np.asarray(simk["pr_truth_m"][:len(t)])
        ax.plot(t[:len(da)], da, lw=0.7, color="#bbb", zorder=1)
        ax.plot(t[:len(dd)], dd, lw=1.0, color=cmap(i % 10), label=k,
                zorder=2)
        pa_all.append(da)
        pd_all.append(dd)
    if pa_all:
        ax.text(0.02, 0.97,
                f"acq RMS {np.sqrt(np.mean(np.concatenate(pa_all)**2)):.2f} m"
                f"   DLL RMS {np.sqrt(np.mean(np.concatenate(pd_all)**2)):.2f} m",
                transform=ax.transAxes, va="top", fontsize=9,
                bbox=dict(fc="w", alpha=0.7, ec="#999"))
    ax.set_title("c) pseudorange residual vs sim truth (grey=acq, colour=DLL)")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("pseudorange error [m]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=6, ncol=4, loc="best")

    # (d) per-SV RMS table (acq vs DLL)
    ax = axes[1][1]
    ax.axis("off")
    rows = [[k, f"{rms_a[k]:.4f}", f"{rms_d[k]:.4f}",
             f"{rms_a[k] / max(rms_d[k], 1e-9):.1f}x"] for k in keys]
    rows.append(["MEAN", f"{np.mean(list(rms_a.values())):.4f}",
                 f"{np.mean(list(rms_d.values())):.4f}",
                 f"{np.mean(list(rms_a.values())) / max(np.mean(list(rms_d.values())), 1e-9):.1f}x"])
    tbl = ax.table(cellText=rows,
                   colLabels=["SV", "acq ch", "DLL ch", "gain"],
                   loc="center", fontsize=7)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    tbl.scale(1, 1.05)
    ax.set_title("d) per-SV chip-RMS: acquisition vs DLL")

    png = od / "trace_dll.png"
    fig.savefig(png, dpi=130, bbox_inches="tight")
    print(f"saved {png}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", help="run id under out/ (or a path to a run dir)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--regen", action="store_true",
                    help="re-dump both traces even if the JSONs exist")
    ap.add_argument("--dll", action="store_true",
                    help="also dump/plot the carrier-aided DLL tracking "
                         "receiver (trace_dll.json + trace_dll.png)")
    a = ap.parse_args()

    od = _resolve_outdir(a.run)
    sim = _load(od, "trace_sim.json", a.regen,
                lambda p: trace.dump_sim_trace(p, step_s=a.step,
                                               n_max=a.epochs))
    rx = _load(od, "trace_rx.json", a.regen,
               lambda p: trace.dump_rx_trace(p, step_s=a.step,
                                             n_max=a.epochs))
    keys = sorted(set(sim["svs"]) & set(rx["svs"]))
    if not keys:
        raise SystemExit("no SV common to both traces")
    t = rx["t_s"]
    cmap = plt.get_cmap("tab10")

    fig, axes = plt.subplots(3, 2, figsize=(14.5, 13.5))
    fig.suptitle(
        f"Sim truth vs receiver measurement -- run {sim['runid']}  "
        f"(start {sim['start_utc']}, {len(keys)} SVs, "
        f"{len(t)} epochs @ {rx['step_s']} s)", fontsize=12)

    # 1. code-phase error ---------------------------------------------------
    ax = axes[0][0]
    rms_chip = {}
    for i, k in enumerate(keys):
        e = np.asarray(rx["svs"][k]["err_chips"])
        ax.plot(t[:len(e)], e, lw=0.9, color=cmap(i % 10), label=k)
        rms_chip[k] = float(np.sqrt(np.mean(e ** 2)))
    ax.set_title("1) code-phase error: acquired - synthesized model (chips)")
    ax.set_xlabel("t from run start [s]")
    ax.set_ylabel("chip error [chips]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=6, ncol=4, loc="best")

    # 2. pseudorange residual ------------------------------------------------
    ax = axes[0][1]
    rms_pr = {}
    chip_m = {}
    for i, k in enumerate(keys):
        rxs, simk = rx["svs"][k], sim["svs"][k]
        meas = np.asarray(rxs["meas_pr_m"])
        if "pr_truth_m" in simk:
            truth = np.asarray(simk["pr_truth_m"])[:len(meas)]
            d = meas - truth
        else:                                  # constants-only fallback
            chip_m[k] = config.C / rxs["chip_hz"]
            d = np.asarray(rxs["err_chips"])[:len(meas)] * chip_m[k]
        ax.plot(t[:len(d)], d, lw=0.9, color=cmap(i % 10), label=k)
        rms_pr[k] = float(np.sqrt(np.mean(d ** 2)))
    ax.set_title("2) pseudorange residual: measured - sim truth [m]")
    ax.set_xlabel("t from run start [s]")
    ax.set_ylabel("pseudorange error [m]")
    ax.grid(alpha=0.3)

    # 3. Doppler time series, one best SV per system ------------------------
    ax = axes[1][0]
    best = {}
    for k in keys:
        s = sim["svs"][k]
        el = max(s.get("el_deg_t") or [s.get("el_deg", 0.0)])
        if s["sys"] not in best or el > best[s["sys"]][1]:
            best[s["sys"]] = (k, el)
    for i, (s, (k, el)) in enumerate(sorted(best.items())):
        rxs, simk = rx["svs"][k], sim["svs"][k]
        fdm = np.asarray(rxs["fd_meas_hz"])
        c = cmap((i + 5) % 10)
        ax.plot(t[:len(fdm)], fdm, ".", ms=4, color=c,
                label=f"{k} meas (el~{el:.0f}$^\\circ$)")
        if "fd_geo_hz" in simk:
            g = np.asarray(simk["fd_geo_hz"])[:len(fdm)]
            ax.plot(t[:len(g)], g, lw=1.2, color=c, ls="--")
        if simk.get("carrier_doppler_hz") is not None:
            ax.axhline(simk["carrier_doppler_hz"], color=c, lw=0.7, alpha=0.5)
    ax.set_title("3) Doppler: measured . vs geometric truth -- and the\n"
                 "   constant the synthesizer injected (thin horizontal)")
    ax.set_xlabel("t from run start [s]")
    ax.set_ylabel("carrier Doppler [Hz]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="best")

    # 4. Doppler quantisation histogram -------------------------------------
    ax = axes[1][1]
    resid = []
    for k in keys:
        rxs, simk = rx["svs"][k], sim["svs"][k]
        if simk.get("carrier_doppler_hz") is None:
            continue
        resid.append(np.asarray(rxs["fd_meas_hz"])
                     - simk["carrier_doppler_hz"])
    if resid:
        allr = np.concatenate(resid)
        step = rx.get("acq", {}).get("dopp_step_hz", 0.0)
        ax.hist(np.clip(allr, -2 * step, 2 * step) if step > 0 else allr,
                bins=41, color="#3b7")
        ax.set_title(f"4) Doppler error vs injected constant "
                     f"(acq bin {step:.0f} Hz)")
    else:
        ax.set_title("4) Doppler quantisation (no constants in provenance)")
    ax.set_xlabel("measured - synthesized [Hz]")
    ax.grid(alpha=0.3)

    # 5. acquisition metric vs time with gain_db baseline --------------------
    ax = axes[2][0]
    for i, k in enumerate(keys):
        rxs, simk = rx["svs"][k], sim["svs"][k]
        m = np.asarray(rxs["metric_db"])
        c = cmap(i % 10)
        ax.plot(t[:len(m)], m, lw=0.9, color=c, label=k)
        if simk.get("gain_db") is not None:
            ax.axhline(simk["gain_db"], color=c, lw=0.5, alpha=0.45)
    ax.set_title("5) strength: acquisition metric_db(t), dashed = sim "
                 "gain_db taper")
    ax.set_xlabel("t from run start [s]")
    ax.set_ylabel("metric [dB]")
    ax.grid(alpha=0.3)

    # 6. strength correlation -------------------------------------------------
    ax = axes[2][1]
    xs, ys, labs = [], [], []
    for k in keys:
        rxs, simk = rx["svs"][k], sim["svs"][k]
        if simk.get("gain_db") is None:
            continue
        xs.append(simk["gain_db"])
        ys.append(float(np.mean(rxs["metric_db"])))
        labs.append(k)
    if len(xs) >= 3:
        ax.scatter(xs, ys, s=18, color="#c33", zorder=3)
        for x, y, k in zip(xs, ys, labs):
            ax.annotate(k, (x, y), fontsize=6, xytext=(2, 2),
                        textcoords="offset points")
        r = float(np.corrcoef(xs, ys)[0, 1])
        b1, b0 = np.polyfit(xs, ys, 1)
        xx = np.linspace(min(xs), max(xs), 10)
        ax.plot(xx, b0 + b1 * xx, lw=1, color="#999")
        ax.set_title(f"6) mean metric_db vs sim gain_db   r = {r:.2f}, "
                     f"slope = {b1:.2f}")
    else:
        ax.set_title("6) strength correlation: insufficient SVs")
    ax.set_xlabel("sim gain taper [dB]")
    ax.set_ylabel("mean acquisition metric [dB]")
    ax.grid(alpha=0.3)

    # footer summary ----------------------------------------------------------
    err_m = None
    rf = od / "receiver_result.json"
    if rf.exists():
        try:
            err_m = json.loads(rf.read_text()).get("error_m")
        except (ValueError, OSError):
            pass
    worst = max(rms_chip.items(), key=lambda kv: kv[1]) if rms_chip else None
    txt = (f"chip RMS: mean {np.mean(list(rms_chip.values())):.3f}, "
           f"worst {worst[0]} {worst[1]:.3f}   |   "
           f"PR RMS: mean {np.mean(list(rms_pr.values())):.2f} m"
           + (f"   |   fix error {err_m:.2f} m" if err_m else ""))
    fig.text(0.5, 0.005, txt, ha="center", fontsize=9, color="#333")

    png = od / "trace_compare.png"
    fig.savefig(png, dpi=130, bbox_inches="tight")
    print(f"saved {png}")
    print(txt)
    for k in keys:
        print(f"  {k:>4}  chipRMS={rms_chip.get(k, float('nan')):.4f}"
              f"  prRMS={rms_pr.get(k, float('nan')):8.2f} m")

    if a.dll:
        dl = _load(od, "trace_dll.json", a.regen,
                   lambda p: trace.dump_rx_trace_dll(p, step_s=a.step,
                                                     n_max=a.epochs))
        _dll_figure(od, sim, rx, dl)


if __name__ == "__main__":
    main()
