"""A/B test: do lnav_encode words pass FGI's gpsl1NavParityCheck equations?

Replicates frame/gpsl1NavParityCheck.m exactly (transmitted-bit domain,
array positions 1,2 = prev word D29*,D30*; 3..26 = D1..D24; 27..32 = parity).
"""
import math, random
import backend.analysis.lnav_encode as le

# FGI calcParity factor index sets (1-based into nDataBits[1..32])
FGI_EQ = [
    [1,3,4,5,7,8,12,13,14,15,16,19,20,22,25],
    [2,4,5,6,8,9,13,14,15,16,17,20,21,23,26],
    [1,3,5,6,7,9,10,14,15,16,17,18,21,22,24],
    [2,4,6,7,8,10,11,15,16,17,18,19,22,23,25],
    [2,3,5,7,8,9,11,12,16,17,18,19,20,23,24,26],
    [1,5,7,8,10,11,12,13,15,17,21,24,25,26],
]

def fgi_check(n):  # n: list of 32 +-1 values (n[0]..n[31] == D29*,D30*,D1..D24,P1..P6)
    n = [1 if v > 0 else -1 for v in n]
    if n[1] != 1:
        n = n[:2] + [-v for v in n[2:26]] + n[26:]
    st = 1
    fails = 0
    for k, eq in enumerate(FGI_EQ):
        p = 1
        for i in eq:
            p *= n[i-1]
        if p != n[26+k]:
            fails += 1
    return fails

def words_of_stream(bits):  # bits 0/1 list -> list of 30-bit words
    return [bits[i:i+30] for i in range(0, len(bits), 30)]

def check_stream(bits, label):
    ws = words_of_stream(bits)
    fails_tot = 0; wpass = 0
    prev29 = 0; prev30 = 0
    fail_by_eq = [0]*6
    d30_1_fail = 0; d30_0_fail = 0
    for w in ws:
        n = [(1 if prev29==0 else -1),(1 if prev30==0 else -1)]
        n += [1 if b==0 else -1 for b in w]
        f = 0
        m = n[:2] + [1 if x>0 else -1 for x in n[2:26]] + n[26:]
        # per-equation failure count WITHOUT polarity gate (parity is polarity-invariant modulo sign handled): replicate exactly incl gate
        nn = list(n)
        if nn[1] != 1:
            nn = nn[:2] + [-v for v in nn[2:26]] + nn[26:]
        for k, eq in enumerate(FGI_EQ):
            p = 1
            for i in eq:
                p *= nn[i-1]
            if p != nn[26+k]:
                fail_by_eq[k] += 1; f += 1
        fails_tot += f
        if f == 0: wpass += 1
        if prev30: 
            if f: d30_1_fail += 1
        else:
            if f: d30_0_fail += 1
        prev29, prev30 = w[28], w[29]
    print(f"{label}: words={len(ws)} pass={wpass} ({100*wpass/len(ws):.1f}%) fail_by_eq={fail_by_eq} fail|D30*=1:{d30_1_fail} fail|D30*=0:{d30_0_fail}")

eph = dict(af0=3.2e-4, af1=1.1e-11, af2=0.0, toc=518400.0, tgd=1.86e-11,
           iode=73, iodc=73, health=0, crs=12.34, delta_n=4.6e-9,
           m0=1.234, cuc=-4.5e-6, e=0.01234, cus=5.1e-6, sqrtA=5153.6,
           toe=518400.0, cic=5.0e-7, omega0=-3.14, cis=-3.3e-6, i0=0.95,
           crc=289.0, omega=2.11, omega_dot=-8.0e-11, idot=5.0e-11)

# 1) single subframe 2, forced nonzero prev bits
for d29,d30 in [(0,0),(0,1),(1,0),(1,1)]:
    bits = le.subframe2(eph, 86401, ) if False else le.subframe2(eph, 86401)
    # subframe() has D29_start/D30_start args
    bits = le.subframe([le.bits_of(0,24) for _ in range(8)], 86401, 2, d29, d30)
    check_stream(bits, f"zero-data subframe prev=({d29},{d30})")

# 2) realistic full frame
bits = le.frame_bits(eph, {}, 2231, 86400, 12, {("G",1): eph})
check_stream(bits, "full frame SF1-5")
