# -*- coding: utf-8 -*-
"""引擎 WS 二进制帧解码（src/sdr_web.c send_psd/send_corr/send_corr_hist 实证，
与官方 html/js/ws.js decodeFrame 字段逐一对表）。

帧类型：1=PSD  2=correlator snapshot  3=correlator history
"""
from __future__ import annotations

import struct

import numpy as np

FRM_PSD, FRM_CORR, FRM_CORR_HIST = 1, 2, 3


def decode_frame(b: bytes) -> dict | None:
    n_len = len(b)
    if n_len < 24:
        return None
    t = b[0]
    if t == FRM_PSD:
        # hdr: [0]=1 [1]=rfch [2]=IQ [3]=bits | f32 fs@4 | f32 tave@8
        #      | u32 n@12 | f64 fo@16 | f32 psd[n]@24
        rfch, iq, bits = b[1], b[2], b[3]
        fs, tave = struct.unpack_from("<ff", b, 4)
        n = struct.unpack_from("<I", b, 12)[0]
        fo = struct.unpack_from("<d", b, 16)[0]
        if 24 + n * 4 > n_len:
            return None
        psd = np.frombuffer(b, dtype=np.float32, count=n, offset=24)
        return {"type": "bin", "frm": "psd", "rfch": rfch, "iq": iq,
                "bits": bits, "fs": fs, "tave": tave, "fo": fo, "psd": psd}
    if t == FRM_CORR:
        # hdr: [0]=2 [1]=state | u16 ch@2 | u32 n@4 | u32 npos@8
        #      | f32 fs@12 lock@16 cn0@20 fd@24 time@28 | f64 coff@32
        # body: f32 pos[n] | cpx f32 C[n](2n) | f32 aveP[n] | f32 aveI[n]
        state = b[1]
        ch, = struct.unpack_from("<H", b, 2)
        n, npos = struct.unpack_from("<II", b, 4)
        fs, lock, cn0, fd, time_ = struct.unpack_from("<fffff", b, 12)
        coff, = struct.unpack_from("<d", b, 32)
        if 40 + n * 20 > n_len:
            return None
        pos = np.frombuffer(b, dtype=np.float32, count=n, offset=40)
        C = np.frombuffer(b, dtype=np.float32, count=2 * n, offset=40 + 4 * n)
        ave_p = np.frombuffer(b, dtype=np.float32, count=n,
                              offset=40 + 12 * n)
        ave_i = np.frombuffer(b, dtype=np.float32, count=n,
                              offset=40 + 16 * n)
        return {"type": "bin", "frm": "corr", "state": state, "ch": ch,
                "n": n, "npos": npos, "fs": fs, "lock": lock, "cn0": cn0,
                "fd": fd, "time": time_, "coff": coff,
                "pos": pos, "C": C, "ave_p": ave_p, "ave_i": ave_i}
    if t == FRM_CORR_HIST:
        # hdr: [0]=3 [1]=0 | u16 ch@2 | u32 n@4 | f64 time@8 | f32 T@16 | u32@20
        # body: cpx f32 P[n](2n)@24
        ch, = struct.unpack_from("<H", b, 2)
        n, = struct.unpack_from("<I", b, 4)
        time_, = struct.unpack_from("<d", b, 8)
        T, = struct.unpack_from("<f", b, 16)
        if 24 + n * 8 > n_len:
            return None
        P = np.frombuffer(b, dtype=np.float32, count=2 * n, offset=24)
        return {"type": "bin", "frm": "corr_hist", "ch": ch, "n": n,
                "time": time_, "T": T, "P": P}
    return None
