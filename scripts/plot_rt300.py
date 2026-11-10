"""Real-receiver 300 s run: per-second simulation-vs-receiver analysis plots.

Reads ``out/<runid>/rx_rt_300.json`` (written by
.workbuddy/rx_realtime_300.py) plus ``out/<runid>/trace_sim.json``
(sim-side truth, 1 Hz grid) and ``meta.json`` (per-SV injected gain), and
renders ``out/<runid>/rt300_analysis.png`` with eight panels:

  A per-SV pseudorange error      corr_pr_m(rx, self-decoded eph)
                                  - pr_truth_m(sim), metres, all SVs vs t
  B pseudorange error histogram   pooled |err|, metres
  C per-SV code error             err_chips per SV vs t (wrapped, ch)
  D anchored carrier phase        wrap(phi + pr/lambda) - mean, cycles, top SVs
  E Doppler                       best SV per system: measured vs sim truth
  F C/N0 estimate vs gain_db      per-SV mean cn0_dbhz vs meta gain_db
  G per-second fix                ENU error vs t + PDOP + TTFF markers
  H bit stream fill               per-SV seconds with nominal bit count

Usage: python scripts/plot_rt300.py <runid|outdir>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import matplotlib                                                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

from backend import config, geometry                             # noqa: E402

C_LIGHT = 299792458.0
L1_HZ = 1575_420_000.0
COL = {"G": "#1f77b4", "E": "#d62728"}


def _resolve_outdir(arg: str) -> pathlib.Path:
    p = pathlib.Path(arg)
    if not p.is_absolute():
        p = config.OUT_DIR / arg
    for f in ("meta.json", "rx_rt_300.json", "trace_sim.json"):
        if not (p / f).exists():
            raise SystemExit(f"missing {f} in {p}")
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runid")
    a = ap.parse_args()
    out = _resolve_outdir(a.runid)
    doc = json.loads((out / "rx_rt_300.json").read_text())
    sim = json.loads((out / "trace_sim.json").read_text())
    meta = json.loads((out / "meta.json").read_text())
    gain_db = {f"{s['sys']}{s['prn']}": s.get("gain_db")
               for s in meta["provenance"]["svs"]}

    svs = {s["key"]: s for s in doc["svs"] if s.get("obs")}
    t_sim = sim["t_s"]                      # 0..299 @1 Hz
    lam = C_LIGHT / L1_HZ
    n_ok = len(svs)
    fig, ax = plt.subplots(4, 2, figsize=(14, 17))
    fig.suptitle(f"Real-receiver 300 s analysis - run {out.name}  "
                 f"({n_ok} SVs, coh tracking, self-decoded nav)",
                 fontsize=13)

    # ---- A pseudorange error vs sim truth -----------------------------
    A = ax[0][0]
    for key, so in svs.items():
        st = sim["svs"].get(key, {})
        truth = st.get("pr_truth_m")
        obs = so["obs"]
        ts, es = [], []
        for k_s, o in sorted(((int(k), v) for k, v in obs.items())):
            if not truth or k_s >= len(truth):
                continue
            # rx obs k is measured/logged at t = k s; sim t_s[k] = k too
            # (both sides use receive time sow0 + k) -> same index.
            ts.append(k_s)
            es.append(o["corr_pr_m"] - truth[k_s])
        A.plot(ts, es, lw=0.8, color=COL[so["sys"]],
               label=f"{key} el{so.get('el_fix_deg', 0):.0f}deg")
    A.set_title("A  pseudorange error  corr_pr(rx self-decoded) - pr_truth(sim)  [m]")
    A.set_xlabel("t [s]")
    A.grid(alpha=0.3)

    # ---- B pooled histogram ---------------------------------------------
    B = ax[0][1]
    pool = [(o["corr_pr_m"] - sim["svs"][k]["pr_truth_m"][int(k_s)])
            for k, so in svs.items() for k_s, o in so["obs"].items()
            if sim["svs"].get(k, {}).get("pr_truth_m")
            and int(k_s) < len(sim["svs"][k]["pr_truth_m"])]
    B.hist(pool, bins=120)
    B.set_title(f"B  pooled PR error histogram  (n={len(pool)}, "
                f"RMS={np.sqrt(np.mean(np.square(pool))):.2f} m)")
    B.set_xlabel("error [m]")

    # ---- C code error chips ---------------------------------------------
    Cax = ax[1][0]
    for key, so in svs.items():
        ts = [int(k) for k in so["obs"]]
        es = [o["err_chips"] for o in so["obs"].values()]
        Cax.plot(ts, es, lw=0.7, color=COL[so["sys"]])
    Cax.set_title("C  per-SV code discriminator error (wrapped)  [chips]")
    Cax.set_xlabel("t [s]")
    Cax.grid(alpha=0.3)

    # ---- D anchored phase residual ---------------------------------------
    D = ax[1][1]
    for key, so in sorted(svs.items(),
                          key=lambda kv: -abs(kv[1].get("gain_db") or -99))[:8]:
        obs = so["obs"]
        ts, ph = [], []
        for k_s, o in sorted(((int(k), v) for k, v in obs.items())):
            if o.get("phase_cycles") is None:
                continue
            ts.append(k_s)
            ph.append(o["phase_cycles"] + o["pred_pr_m"] / lam)
        if ts:
            ph = np.unwrap(np.asarray(ph))
            D.plot(ts, ph - np.mean(ph), lw=0.8, color=COL[so["sys"]],
                   label=key)
    D.set_title("D  anchored phase wrap(phi+pr/lambda)-mean  [cycles] "
                "(8 strongest)")
    D.set_xlabel("t [s]")
    D.grid(alpha=0.3)
    D.legend(fontsize=7, ncol=2)

    # ---- E Doppler ---------------------------------------------------------
    E = ax[2][0]
    for sysc in ("G", "E"):
        cand = [so for k, so in svs.items() if so["sys"] == sysc]
        if not cand:
            continue
        best = max(cand, key=lambda s: s.get("gain_db") or -99)
        st = sim["svs"].get(best["key"], {})
        fd_truth = st.get("fd_geo_hz")
        ts = [int(k) for k in best["obs"]]
        E.plot(ts, [o["fd_hz"] for o in best["obs"].values()], lw=0.9,
               color=COL[sysc], label=f"{best['key']} measured")
        if fd_truth:
            E.plot(t_sim[:len(fd_truth)], fd_truth, lw=0.9, ls="--",
                   color="k", label=f"{best['key']} sim truth")
    E.set_title("E  Doppler: strongest SV per system vs sim truth")
    E.set_xlabel("t [s]")
    E.legend(fontsize=8)
    E.grid(alpha=0.3)

    # ---- F C/N0 vs gain_db --------------------------------------------------
    F = ax[2][1]
    xs, ys, cc = [], [], []
    for key, so in svs.items():
        vals = [o["cn0_dbhz"] for o in so["obs"].values()
                if o.get("cn0_dbhz") is not None]
        if vals:
            xs.append(gain_db.get(key, -99))
            ys.append(float(np.median(vals)))
            cc.append(COL[so["sys"]])
    F.scatter(xs, ys, c=cc, s=26)
    for x, y, key in zip(xs, ys, sorted(svs)):
        F.annotate(key, (x, y), fontsize=6, xytext=(2, 2),
                   textcoords="offset points")
    F.set_title("F  per-SV median C/N0 (moment est.) vs injected gain_db")
    F.set_xlabel("gain_db")
    F.set_ylabel("C/N0 [dB-Hz]")
    F.grid(alpha=0.3)

    # ---- G fix -------------------------------------------------------------
    G = ax[3][0]
    fx = doc.get("fixes") or []
    if fx:
        ts = [r["t_s"] for r in fx]
        G.plot(ts, [r["err_h_m"] for r in fx], lw=1.0,
               label="horizontal err [m]")
        G.plot(ts, [r["err_3d_m"] for r in fx], lw=1.0,
               label="3D err [m]")
        G2b = G.twinx()
        G2b.plot(ts, [r["pdop"] for r in fx], lw=0.8, ls="--",
                 color="gray", label="PDOP")
        t_full = doc["summary"]["t_full_s"]
        k_first = doc["summary"]["fix_first_t_s"]
        G.axvline(t_full, color="purple", ls=":",
                  label=f"T_full = {t_full:.0f} s")
        G.axvline(k_first, color="green", ls=":",
                  label=f"first fix t = {k_first} s")
        s = doc["summary"]
        G.set_title(f"G  per-second fix (no averaging)  rms3d="
                    f"{s['err_3d_rms_m']:.2f} m  med={s['err_3d_med_m']:.2f} m"
                    f"  PDOP~{s['pdop_mean']:.2f}  n={s['n_fix']}")
    G.set_xlabel("t [s]")
    G.legend(fontsize=8, loc="upper right")
    G.grid(alpha=0.3)

    # ---- H bit stream fill ---------------------------------------------------
    H = ax[3][1]
    ns = doc["summary"]["n_usable"]
    H.text(0.05, 0.85,
           f"nav bits file rows: {(out / 'navbits_300.txt').exists()}\n"
           f"usable SVs: {ns}  (G {doc['summary']['nsys']['G']} / "
           f"E {doc['summary']['nsys']['E']})\n"
           f"T_full = {doc['summary']['t_full_s']:.0f} s\n"
           f"RINEX obs/nav readback: {doc.get('nav_rinex_readback')}",
           fontsize=9, family="monospace",
           transform=H.transAxes)
    H.set_title("H  bit stream / output summary")

    fig.tight_layout(rect=(0, 0, 1, 0.985))
    png = out / "rt300_analysis.png"
    fig.savefig(png, dpi=130)
    print(f"wrote {png}")


if __name__ == "__main__":
    main()
