"""Backfill full-length E-side I/NAV symbol rows into navbits_300.txt.

The 300 s full run recorded E symbol rows only for the decode chunks
(~0..59 s). This regenerates 0..299 s per E SV with the same
demod_symbols_e1b recipe the decoder uses, seeded from the pass2 1 Hz
track state in rx_rt_300.json (chi/fd booked AT the epoch), then rewrites
the file keeping the (already good) G rows and the header comments.

Usage: python .workbuddy/fix_e_bits.py <runid>
"""
import importlib.util
import json
import multiprocessing as mp
import pathlib
import sys

sys.path.insert(0, ".")

spec = importlib.util.spec_from_file_location(
    "rt300", ".workbuddy/rx_realtime_300.py")
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)


def _e_chunk(arg):
    import numpy as np
    (outdir_s, so) = arg
    from backend.analysis import inav_decode
    outdir = pathlib.Path(outdir_s)
    import json as _json
    from backend import inspector
    meta = _json.loads((outdir / "meta.json").read_text())
    band = meta["bands"][0]
    fs = float(band["fs"])
    bf = outdir / band["file"]
    fmt = meta.get("sample_format", "int8")
    prn = int(so["prn"])
    if_hz = 0.0
    obs = {int(k): v for k, v in so["obs"].items()}
    acq = so["acq"]
    fd_seed = float(acq["coarse"]["fd"]) + float(acq["fine"]["fd"])
    chi_seed = float(acq["fine"]["chi"])
    TS = int(rt.TRACK_S) if hasattr(rt, "TRACK_S") else 300
    bits_by_sec: dict[int, list[int]] = {}
    for c0 in range(0, TS, 30):
        if c0 == 0:
            ch, fdch = chi_seed, fd_seed
        else:
            o = obs.get(c0) or obs.get(c0 - 1) or obs.get(c0 + 1)
            ch, fdch = float(o["chi_chips"]), float(o["fd_hz"])
        iq = inspector.read_iq(bf, fmt, max_samples=int(min(30, TS - c0) * fs),
                              offset_samples=int(round(c0 * fs)))
        want = int(min(30, TS - c0) * fs)
        if iq.size < want:
            iq = np.pad(iq, (0, want - iq.size))
        sy = inav_decode.demod_symbols_e1b(
            iq, fs, prn, centre_offset_hz=if_hz,
            dopp_hz=fdch, code_phase_chips=ch)
        for j, v in enumerate(np.asarray(sy, np.int8).tolist()):
            sec = c0 + int((0.004 * j + 0.002) // 1.0)
            if 0 <= sec < TS:
                bits_by_sec.setdefault(sec, []).append(int(v))
        iq = None
    return so["key"], {int(s): list(b) for s, b in bits_by_sec.items()}


def main():
    runid = sys.argv[1]
    from backend import config
    outdir = config.OUT_DIR / runid
    doc = json.loads((outdir / "rx_rt_300.json").read_text())
    e_svs = [s for s in doc["svs"] if s["sys"] == "E" and s.get("obs")]
    args = [(str(outdir), so) for so in e_svs]
    with mp.Pool(processes=4) as pool:
        payload = dict(pool.map(_e_chunk, args))
    # E rows via the production formatter
    e_lines = rt.bits_hex_rows(e_svs, payload)
    # keep header + G rows from the existing file
    src = (outdir / "navbits_300.txt").read_text().splitlines()
    head = [L for L in src if L.startswith("#")]
    g_rows = [L for L in src if not L.startswith("#")
              and L.split()[1].startswith("G")]
    out = head + g_rows + e_lines
    (outdir / "navbits_300.txt").write_text("\n".join(out) + "\n")
    print(f"rewrote navbits_300.txt: G rows={len(g_rows)} "
          f"E rows={len(e_lines)} (was {sum(1 for L in src if not L.startswith('#'))})")
    for k, pl in list(payload.items())[:2]:
        secs = sorted(pl)
        print(f"  {k}: secs {len(secs)} [{secs[0]}..{secs[-1]}] "
              f"median bits {sorted(len(pl[s]) for s in secs)[len(secs)//2]}")


if __name__ == "__main__":
    main()
