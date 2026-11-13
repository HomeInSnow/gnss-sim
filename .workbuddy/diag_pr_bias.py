"""Root-cause analysis of the horizontal ~2 m bias of the FGI whu60 run.

Hypothesis: FGI's mulSatpos.m applies satClkCorr (incl. the relativistic
term relcorr = F_REL*e*sqrtA*sinE) unconditionally, while the engine
(sv_clock=false) injected NO satellite clock term into the pseudorange
(af AND the relativistic term were both removed, see synth/engine.py
sv_clock_inj branch). FGI therefore "removes" a clock error that was never
there -> per-SV bias c*relcorr -> LS shifts the fix horizontally.

Checks:
  1) clockCorr exported from FGI vs offline-predicted c*relcorr  (corr~1?)
  2) rawP residuals vs engine true pseudorange after clock removal  (clean?)
  3) synthetic replication: LS on true pseudorange + c*relcorr -> compare
     the ENU shift against the measured FGI fix bias (-1.97,-1.93,+0.55).
"""
import sys, math, collections
import datetime as dt
import numpy as np

sys.path.insert(0, ".")
from backend import config, geometry                      # noqa: E402
from backend.ephem import ephemeris                        # noqa: E402

F_REL = -4.442807633e-10
C = config.C
LAT, LON, ALT = 60.182537, 24.828260, 47.248
RX = geometry.llh_to_ecef(LAT, LON, ALT)

req_start = dt.datetime(2023, 9, 28, 23, 20, 0)
gps_start = req_start + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps_start)
eph = ephemeris.parse_rinex("data/rinex/BRDC_2023271_whu_afzero.rnx",
                            at_gps=gps_start)
eph = ephemeris.align_for_run(eph, week, sow, "native")
print(f"week {week} sow {sow}  sats parsed {len(eph)}")

d = np.genfromtxt("out/fgi/fgi_whu60_prn.csv", delimiter=",", names=True)
by = collections.defaultdict(dict)
for r in d:
    by[int(r["epoch"])][int(r["prn"])] = (float(r["rawP"]),
                                          float(r["corrP"]),
                                          float(r["clockCorr"]))
epochs = sorted(by)
print(f"epochs {len(epochs)}: {epochs[:3]}...{epochs[-3:]}")


def relcorr(eph_row, t_gps):
    pos, E, tk, mu, wdot, is_geo, frel = geometry._sat_pos(eph_row, t_gps)
    return F_REL * eph_row["e"] * math.sqrt(eph_row["sqrtA"]) * math.sin(E)


# ---- 1) clockCorr vs predicted c*relcorr ---------------------------------
xs, ys = [], []
for e in epochs:
    t_rx = sow + e * 1.0                      # FGI 1 Hz nav epochs
    for prn, (rp, cp, cc) in by[e].items():
        if prn not in eph:
            continue
        t_tx = t_rx - rp / C
        xs.append(cc)
        ys.append(C * relcorr(eph[prn], t_tx) - C * float(eph[prn].get("tgd",0.0)))
xs = np.array(xs); ys = np.array(ys)
k = float(np.dot(xs, ys) / np.dot(ys, ys))
r = float(np.corrcoef(xs, ys)[0, 1])
print(f"[1] FGI clockCorr vs predicted c*relcorr: n={len(xs)}  "
      f"slope={k:.3f}  corr={r:.4f}  rms diff={np.sqrt(np.mean((xs-ys)**2)):.2f} m")
print(f"    clockCorr std {xs.std():.2f} m, predicted std {ys.std():.2f} m")

# ---- 2) rawP residual vs engine truth -------------------------------------
# truth pseudorange (sv_clock=false): geometric tof*C only, Sagnac inside
resid = collections.defaultdict(list)
for e in epochs:
    t_rx = sow + e * 1.0
    for prn, (rp, cp, cc) in by[e].items():
        if prn not in eph:
            continue
        pos, vel, tof, clk = geometry.solve_transmit_time(eph[prn], RX, t_rx,
                                                          compute_vel=False)
        pr_true = tof * C
        resid[prn].append(rp - pr_true)
print("\n[2] rawP - true pseudorange, per SV (common clock absorbed):")
common = np.concatenate([np.array(v) for v in resid.values()])
cm = float(np.median(common))
print(f"    common mode (receiver clock) = {cm:.2f} m")
for prn in sorted(resid):
    v = np.array(resid[prn]) - cm
    print(f"    G{prn:<3} resid std {v.std():7.2f} m  mean {v.mean():+7.2f} m")

# ---- 3) synthetic replication of the FGI bias ------------------------------
def lla_to_enu(dlat, dlon, dh):
    # small-offset ENU at the reference point
    m = 111132.92 - 559.82*math.cos(2*math.radians(LAT)) + \
        1.175*math.cos(4*math.radians(LAT)) - 0.0023*math.cos(6*math.radians(LAT))
    n = 111412.84*math.cos(math.radians(LAT)) - \
        93.5*math.cos(3*math.radians(LAT))
    return dlat*m, dlon*n, dh


def ls_solve(pr_map, t_rx, cd0=0.0):
    """4-state LS on pseudorange dict {prn: pr}. returns ENU error vector."""
    xyz = np.array(RX, float)
    cd = cd0
    for _ in range(10):
        rows, rhs = [], []
        for prn, pr in pr_map.items():
            pos, vel, tof, clk = geometry.solve_transmit_time(
                eph[prn], xyz, t_rx, compute_vel=False)
            rho = float(np.linalg.norm(pos - xyz))
            h = np.array([pos[0]-xyz[0], pos[1]-xyz[1], pos[2]-xyz[2]])/rho
            rows.append(np.append(-h, C))
            rhs.append(pr - (rho + C*cd))
        A = np.array(rows); b = np.array(rhs)
        dx, *_ = np.linalg.lstsq(A, b, rcond=None)
        xyz = xyz + dx[:3]
        cd = cd + dx[3]
    # ECEF delta -> ENU relative to true RX
    dxyz = xyz - np.array(RX)
    lat, lon, _ = geometry.ecef_to_llh(*RX) if hasattr(geometry, "ecef_to_llh") \
        else (LAT, LON, ALT)
    e = (-math.sin(math.radians(LON))*dxyz[0] + math.cos(math.radians(LON))*dxyz[1])
    north = (-math.sin(math.radians(LAT))*math.cos(math.radians(LON))*dxyz[0]
             - math.sin(math.radians(LAT))*math.sin(math.radians(LON))*dxyz[1]
             + math.cos(math.radians(LAT))*dxyz[2])
    up = (math.cos(math.radians(LAT))*math.cos(math.radians(LON))*dxyz[0]
          + math.cos(math.radians(LAT))*math.sin(math.radians(LON))*dxyz[1]
          + math.sin(math.radians(LAT))*dxyz[2])
    return np.array([e, north, up]), float(cd)


print("\n[3] synthetic LS replication (engine truth pr -> + c*relcorr):")
enus_clean, enus_bias = [], []
for e in epochs:
    t_rx = sow + e * 1.0
    pr_true_map, pr_bias_map = {}, {}
    for prn in by[e]:
        if prn not in eph:
            continue
        pos, vel, tof, clk = geometry.solve_transmit_time(
            eph[prn], RX, t_rx, compute_vel=False)
        pr = tof * C
        rc = relcorr(eph[prn], t_rx - tof)
        pr_true_map[prn] = pr
        pr_bias_map[prn] = pr + C * rc - C * float(eph[prn].get("tgd",0.0))  # FGI err
    e0, _ = ls_solve(pr_true_map, t_rx)
    e1, _ = ls_solve(pr_bias_map, t_rx)
    enus_clean.append(e0); enus_bias.append(e1)
e0m = np.mean(enus_clean, axis=0); e1m = np.mean(enus_bias, axis=0)
print(f"    clean-LS mean ENU error  = {e0m}")
print(f"    +relcorr LS mean ENU err = {e1m}")
print(f"    FGI measured mean ENU    = [-1.974 -1.928 +0.553]")
print(f"    diff(pred - FGI)         = {e1m - np.array([-1.974, -1.928, 0.553])}")
