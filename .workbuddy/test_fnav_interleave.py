"""Verify fnav_encode's 8x61 block interleaver direction against PocketSDR.

Root-cause check for the E5AI "F/NAV FRAME ERROR 100%" playback failure:
PocketSDR src/sdr_nav.c decode_gal_syms() does

    for (i = 0, k = 0; i < ncol; i++)
        for (j = 0; j < nrow; j++)
            buff[k++] = rev_soft_sym(syms[j*ncol+i], j % 2);

with (ncol, nrow) = (61, 8), i.e. c_rec[8*i+j] = s[61*j+i] (odd c-space
positions G2-de-inverted).  This harness re-implements that loop in Python
and decodes a page produced by fnav_encode.build_page through it; passing
means the transmitter/receiver interleave directions agree.  It also runs
the project's own fnav_decode.decode_messages end-to-end over nav_stream().

Run from the repo root:  .venv/Scripts/python.exe .workbuddy/test_fnav_interleave.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from backend.analysis import fnav_encode as FE
from backend.analysis import fnav_decode as FD
from backend.analysis import _viterbi
from backend.analysis import _fnav_layout as L
from backend.analysis._crc import crc24q


def pocket_sdr_rx(body):
    """Python mirror of sdr_nav.c decode_gal_syms(syms, ncol=61, nrow=8).

    Returns the 488-symbol *standard* (G2 un-inverted) coded stream the
    C-side sdr_decode_conv() would see.
    """
    assert len(body) == L.CODED_SYMS
    out = [0] * L.CODED_SYMS
    k = 0
    for i in range(61):
        for j in range(8):
            v = body[j * 61 + i]
            if j % 2:
                v ^= 1                      # rev_soft_sym(..., j % 2)
            out[k] = v
            k += 1
    return out


EPH = dict(
    toe=86400.0, toc=86400.0, af0=1.2e-5, af1=3.4e-12, af2=0.0,
    sisa=0.5, tgd_e5a=-1.164e-9, iodnav=42,
    m0=1.23, e=0.0006, sqrtA=5489.6484375, omega0=-2.4, omega=1.7,
    i0=0.95, delta_n=4.5e-9, omega_dot=-8.0e-11, idot=5.0e-10,
    cuc=9e-6, cus=8e-6, crc=120.0, crs=150.0, cic=5e-6, cis=4e-6,
)

WEEK, PRN = 2379, 33
fails = 0


def check(label, ok):
    global fails
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        fails += 1


# --- 1) page-by-page through the emulated PocketSDR loop ---------------------
for wtype in (1, 2, 3, 4):
    tow = 300000 + (wtype - 1) * 10
    page = FE.build_page(wtype, EPH, PRN, tow, WEEK)
    body = page[L.PREAMBLE_SYMS:]

    # preamble uncoded match (PocketSDR sync_frame_soft hard-matches it)
    check(f"type {wtype}: preamble", page[:L.PREAMBLE_SYMS] == FE._PREAMBLE)

    c_rec = pocket_sdr_rx(body)
    bits = _viterbi.viterbi_free_decode(c_rec, invert_g2=False)
    msg, crc = bits[:L.MSG_BITS], bits[L.MSG_BITS:L.MSG_BITS + L.CRC_BITS]
    got_type = int("".join(str(b) for b in msg[:6]), 2)
    check(f"type {wtype}: PocketSDR-loop CRC", crc24q(msg) == crc)
    check(f"type {wtype}: type field round-trip", got_type == wtype)

    # encoder's own paired self-test still passes after the swap
    check(f"type {wtype}: internal check_page_crc", FE.check_page_crc(page))

# --- 2) end-to-end through the project's own receiver-side decoder -----------
syms, rate = FE.nav_stream(EPH, PRN, WEEK, 300000.0, 45.0)
check("nav_stream: rate 50 sym/s", rate == 50.0)
sym01 = (syms < 0).astype(np.int8)          # bit=1 <-> chip -1 (cnav convention)
msgs = FD.decode_messages(sym01)
types = [m["type"] for m in msgs]
check("decode_messages: >=5 CRC-valid pages", len(msgs) >= 5)
# arrival-model schedule: page p arrives at 10p - off_true + tau, E5AI's
# first-sync gate is ~10.49 s, so pages arriving before ~10.7 s are lost.
# Here tow0_sow=300000.0 -> off=0 -> p_a=ceil(11.7/10)=2, i.e. stream types
# 3,4,1,2,3,4,... and pages 2..5 (arrivals ~19/29/39/49 s) form the first
# full 1-4 set, completing on the p5 type-4.
check("page-type schedule 3,4,1,2,3,4,...", types[:6] == [3, 4, 1, 2, 3, 4])
check("first decodable cycle is full 1-4 set", sorted(types[2:6]) == [1, 2, 3, 4])
t1 = next((m for m in msgs if m["type"] == 1), None)
check("decode_messages: type-1 prn", t1 is not None and t1["prn"] == PRN)
check("decode_messages: type-1 tow field",
      t1 is not None and int(t1["fields"]["tow"]) in (300000, 300010, 300020, 300030))
try:
    rec = FD.reconstruct_ephemeris(msgs)
    check("reconstruct_ephemeris: sqrtA", abs(rec["sqrtA"] - EPH["sqrtA"]) < 1e-3)
    check("reconstruct_ephemeris: toe", rec["toe"] == EPH["toe"])
except Exception as exc:                                   # noqa: BLE001
    check(f"reconstruct_ephemeris: raised {exc!r}", False)

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
sys.exit(0 if fails == 0 else 1)
