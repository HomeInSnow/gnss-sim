"""Inverse of :mod:`backend.analysis.lnav_encode`.

Demodulate the 50 bps LNAV symbol stream out of native-engine IQ, find
subframe boundaries with a parity check, and reconstruct an ephemeris
dict shaped like :func:`backend.ephem.ephemeris.parse_rinex` output.
"""
from __future__ import annotations

import math

import numpy as np

from backend.analysis import lnav_encode as le
from backend.analysis._bit_utils import normalize_symbols, unpack_int, unpack_uint
from backend.analysis._demod_utils import derotate_bpsk_carrier

_u = unpack_uint
_s = unpack_int


def check_parity(word30, D29_prev: int, D30_prev: int) -> bool:
    w = list(word30)
    d_src = [b ^ D30_prev for b in w[:24]]
    return list(w[24:]) == le.parity_bits(d_src, D29_prev, D30_prev)


def _src_words(words) -> list[list[int]]:
    """10 lists of 24 source data bits, undoing the D30* data inversion."""
    d29 = d30 = 0
    out = []
    for w in words:
        out.append([b ^ d30 for b in w[:24]])
        d29, d30 = w[28], w[29]
    return out


def find_frame(bits) -> list[dict]:
    """Scan a symbol/bit sequence for parity-valid 300-bit subframes.

    Accepts {0,1} bits or {+1,-1} symbols (with +1 -> bit 0). Handles a
    globally inverted stream. Returns one dict per hit with keys
    ``offset``, ``inverted``, ``subframe_id``, ``tow_count``, ``words``
    (10 raw 30-bit words).
    """
    b = normalize_symbols(bits, bpsk_sign=True)
    pre = le.PREAMBLE
    inv = [1 - x for x in pre]
    hits: list[dict] = []
    i = 0
    n = len(b)
    while i + 300 <= n:
        seg = b[i : i + 8]
        inverted = seg == inv
        if seg != pre and not inverted:
            i += 1
            continue
        raw = [1 - x for x in b[i : i + 300]] if inverted else b[i : i + 300]
        words = [raw[k * 30 : (k + 1) * 30] for k in range(10)]
        d29 = d30 = 0
        ok = True
        for w in words:
            if not check_parity(w, d29, d30):
                ok = False
                break
            d29, d30 = w[28], w[29]
        if not ok:
            i += 1
            continue
        how = _src_words(words)[1]
        hits.append({
            "offset": i,
            "inverted": inverted,
            "subframe_id": _u(how[19:22]),
            "tow_count": _u(how[0:17]),
            "words": words,
        })
        i += 300
    return hits


_SC = math.pi  # semicircle -> radian


def decode_ephemeris(subframes: dict) -> dict:
    """Reconstruct clock + Keplerian ephemeris from subframes 1, 2, 3.

    ``subframes`` maps subframe id -> list of 10 raw 30-bit words.
    """
    if not {1, 2, 3} <= set(subframes):
        raise ValueError("need subframes 1, 2 and 3")
    d1 = _src_words(subframes[1])
    d2 = _src_words(subframes[2])
    d3 = _src_words(subframes[3])
    eph: dict = {}

    # subframe 1 -- clock
    eph["gps_week"] = _u(d1[2][0:10])
    eph["health"] = _u(d1[2][12:18])
    eph["iodc"] = (_u(d1[2][22:24]) << 8) | _u(d1[7][0:8])
    eph["tgd"] = _s(d1[6][16:24]) * 2 ** -31
    eph["toc"] = _u(d1[7][8:24]) * 16.0
    eph["af2"] = _s(d1[8][0:8]) * 2 ** -55
    eph["af1"] = _s(d1[8][8:24]) * 2 ** -43
    eph["af0"] = _s(d1[9][0:22]) * 2 ** -31

    # subframe 2 -- ephemeris part 1
    eph["iode"] = _u(d2[2][0:8])
    eph["crs"] = _s(d2[2][8:24]) * 2 ** -5
    eph["delta_n"] = _s(d2[3][0:16]) * 2 ** -43 * _SC
    eph["m0"] = _s(d2[3][16:24] + d2[4][0:24]) * 2 ** -31 * _SC
    eph["cuc"] = _s(d2[5][0:16]) * 2 ** -29
    eph["e"] = _u(d2[5][16:24] + d2[6][0:24]) * 2 ** -33
    eph["cus"] = _s(d2[7][0:16]) * 2 ** -29
    eph["sqrtA"] = _u(d2[7][16:24] + d2[8][0:24]) * 2 ** -19
    eph["toe"] = _u(d2[9][0:16]) * 16.0

    # subframe 3 -- ephemeris part 2
    eph["cic"] = _s(d3[2][0:16]) * 2 ** -29
    eph["omega0"] = _s(d3[2][16:24] + d3[3][0:24]) * 2 ** -31 * _SC
    eph["cis"] = _s(d3[4][0:16]) * 2 ** -29
    eph["i0"] = _s(d3[4][16:24] + d3[5][0:24]) * 2 ** -31 * _SC
    eph["crc"] = _s(d3[6][0:16]) * 2 ** -5
    eph["omega"] = _s(d3[6][16:24] + d3[7][0:24]) * 2 ** -31 * _SC
    eph["omega_dot"] = _s(d3[8][0:24]) * 2 ** -43 * _SC
    eph["idot"] = _s(d3[9][8:22]) * 2 ** -43 * _SC
    return eph


_L1_HZ = 1575.42e6


def _linear_wipe(iq, fs, f0: float, f1: float):
    """Remove a LINEAR carrier f(t) = f0 + f1·t (Hz, Hz/s) from complex IQ.

    Chunked so temporaries stay < ~30 MB. ``f1`` (Doppler rate) lets a
    ~13 s sub-window stay phase-flat over its whole span even at several
    Hz/s of Doppler drift -- wiping with a CONSTANT seed leaves ±3 Hz of
    residual over 13 s at the observed −0.5 Hz/s, which rotates the 20 ms
    bit integrators enough to wreck the parity chain.
    """
    iq = np.asarray(iq)
    if not np.iscomplexobj(iq):
        iq = iq.astype(np.complex64)
    out = np.empty_like(iq, dtype=np.complex64)
    step = 1 << 20
    for s0 in range(0, iq.size, step):
        e = min(s0 + step, iq.size)
        t = np.arange(s0, e, dtype=np.float64) / fs
        out[s0:e] = iq[s0:e] * np.exp(-2j * np.pi * (f0 * t + 0.5 * f1 * t * t))
    return out


def _prompt_per_ms(x_wiped, fs, ca, code_phase0_chips, code_rate, *, chunk_ms: int = 100):
    """Complex prompt correlator output, one sample per 1 ms C/A period,
    for a carrier-wiped signal and a given code chipping rate.

    Accumulates in chunked blocks of sub-second intervals (default 100 ms)
    to bound peak temporary memory to < 50 MB even on long captures at high
    sampling rates.
    """
    spms = fs / 1000.0
    m = int(x_wiped.size // spms)
    if m == 0:
        return np.zeros(0, dtype=np.complex128)

    edges = np.floor(np.arange(m + 1) * spms).astype(np.int64)
    out = np.empty(m, dtype=np.complex128)
    rate_div_fs = code_rate / fs

    # Cap chunk size so temporary sample buffers never exceed ~250k samples (< 20 MB)
    max_chunk_samples = 250_000
    chunk_ms = max(10, min(chunk_ms, int(max_chunk_samples // max(1.0, spms))))

    for i0 in range(0, m, chunk_ms):
        i1 = min(i0 + chunk_ms, m)
        s0 = edges[i0]
        s1 = edges[i1]
        ns = s1 - s0
        k_sub = np.arange(ns, dtype=np.float64)
        cph0 = s0 * rate_div_fs - code_phase0_chips
        idx_sub = np.floor(k_sub * rate_div_fs + cph0).astype(np.int32) % 1023
        corr_sub = x_wiped[s0:s1] * ca[idx_sub]
        sub_edges = edges[i0 : i1 + 1] - s0
        csum_sub = np.concatenate(([0.0 + 0j], np.cumsum(corr_sub)))
        out[i0:i1] = csum_sub[sub_edges[1:]] - csum_sub[sub_edges[:-1]]

    return out


def demod_nav_bits(iq, fs, prn, code_phase0_chips, doppler_hz, *,
                   n_bits: int = 1500, align_ms: int | None = None,
                   rate_span: float = 3.0):
    """Hard nav bits (``int8`` {0,1}) from IQ.

    Steps: prompt correlation to 1 ms samples, residual-frequency search,
    BPSK phase de-rotation, then 20 ms integration. ``align_ms`` skips a
    leading partial bit so the 20 ms blocks land on transmitted bit
    boundaries; ``None`` (default) finds it by bit synchronisation -- the
    offset whose 20 ms sums carry the most energy. The generator stamps
    bits on satellite transmit time, so the edges sit wherever the
    propagation delay puts them, not on the capture's 20 ms grid. Global
    sign ambiguity is left for :func:`find_frame`.
    """
    from backend import inspector

    chip_hz = float(inspector.config.CA_CHIP_HZ)
    ca = inspector.ca_code(prn).astype(np.float64)
    iq = np.asarray(iq)
    if not np.iscomplexobj(iq):
        iq = iq.astype(np.complex64)
    elif iq.dtype == np.complex128:
        iq = iq.astype(np.complex64)

    # Carrier wipe in ~1M-sample chunks to keep intermediate memory < 20 MB
    x = np.empty_like(iq)
    chunk = 1 << 20
    carrier_step = -2j * np.pi * doppler_hz / fs
    for start in range(0, iq.size, chunk):
        end = min(start + chunk, iq.size)
        k_chunk = np.arange(start, end, dtype=np.float64)
        cwipe = np.exp(carrier_step * k_chunk).astype(iq.dtype)
        x[start:end] = iq[start:end] * cwipe

    # The engine holds Doppler constant, but the acquired carrier estimate
    # carries a small error; the matching code-rate error walks the replica
    # off over a 20 s capture. Grid-search the residual chipping rate for
    # peak prompt energy.
    base_rate = chip_hz * (1.0 + doppler_hz / _L1_HZ)
    best_p, best_e = None, -1.0
    for drate in np.linspace(-rate_span, rate_span, 31):
        cand = _prompt_per_ms(x, fs, ca, code_phase0_chips, base_rate + drate)
        e = float(np.sum(np.abs(cand)))
        if e > best_e:
            best_e, best_p = e, cand
    p = best_p
    mm = np.arange(p.size, dtype=np.float64)

    # Carrier search uses the NON-COHERENT 20 ms-block energy criterion
    # Σ|Σ_block p| over the first seconds of the prompt train. The previous
    # coherent-sum criterion |Σ p·e^{-jwt}| is pulled toward zero by the random
    # ±1 data modulation of the 50 bps stream (its peak lands on a lucky data
    # pattern, not on the true residual) -- a real-IQ-only failure: clean
    # synthetic IQ hides it, multi-SV captured tracks expose it.
    #
    # The residual and the bit phase are searched JOINTLY (argmax over
    # (f, off)): an un-aligned argmax lets blocks straddle data transitions,
    # and the straddling pattern deforms the broad |sinc|-like response
    # enough to shift argmax by ~15 Hz off the true residual -- past the fine
    # grid's reach (probe: real peaks sit inside the aligned-energy band the
    # un-aligned scan skipped, deterministic per SV, quality-independent).
    n_c = min(p.size, 2000)
    best_f1, best_off, best_e1 = 0.0, 0, -1.0
    if n_c >= 40:
        pc = p[:n_c]
        kc = np.arange(n_c, dtype=np.float64)
        nbo = (n_c - 19) // 20
        offs = np.arange(20)
        ed0 = offs[:, None] + 20 * np.arange(nbo)[None, :]        # (20, nbo)
        for f in np.arange(-50.0, 50.01, 0.5):
            pw = pc * np.exp(-2j * np.pi * f * kc / 1000.0)
            cs = np.concatenate(([0.0 + 0j], np.cumsum(pw)))
            e_mat = np.abs(cs[ed0 + 20] - cs[ed0])                # (20, nbo)
            e = float(e_mat.sum())
            if e > best_e1:
                best_off = int(np.argmax(e_mat.sum(axis=1)))
                best_f1, best_e1 = float(f), e
    p = p * np.exp(-2j * np.pi * best_f1 * mm[:p.size] / 1000.0)

    if align_ms is None:
        align_ms = best_off
    if align_ms:
        p = p[align_ms:]
    nb = min(n_bits, p.size // 20)
    p = p[:nb * 20]
    if nb == 0:
        return np.zeros(0, dtype=np.int8)

    # (b) fine residual via a SQUARED-BLOCK TONE on the bit-aligned train.
    # The non-coherent block-energy criterion CANNOT resolve small residuals:
    # its |sum|20ms| response to f has a ~50 Hz main lobe, so neighbouring
    # 0.05 Hz candidates differ only in noise -- argmax lands anywhere in
    # ±3 Hz, and a consistent 2-3 Hz residual then rotates the block phase by
    # up to 21.6 deg/bit (36 revolutions over 600 bits), the quadratic
    # derotate fit breaks down and the parity chain dies. Deterministic per
    # SV (depends on its data + noise), independent of signal quality -- the
    # exact all-or-nothing failure signature. Squaring the block sums cancels
    # the ±1 data modulation, giving a sharp tone at 2·f_res that the fine
    # grid resolves (~0.006 Hz linewidth over the search span).
    m = np.arange(p.size, dtype=np.float64)
    blk = p[:nb * 20].reshape(nb, 20).sum(axis=1)
    n_sq = min(nb, 600)
    b2 = blk[:n_sq] * blk[:n_sq]
    k_sq = np.arange(n_sq, dtype=np.float64)
    best_f2, best_e2 = 0.0, -1.0
    for f in np.arange(-3.0, 3.001, 0.05):
        e = float(np.abs(np.sum(b2 * np.exp(
            -2j * np.pi * (2.0 * f) * 20.0 * k_sq / 1000.0))))
        if e > best_e2:
            best_f2, best_e2 = float(f), e
    p = p * np.exp(-2j * np.pi * best_f2 * m / 1000.0)

    bits = p.reshape(nb, 20).sum(axis=1)
    bits = derotate_bpsk_carrier(bits, deg=2)
    return (np.real(bits) < 0).astype(np.int8)
