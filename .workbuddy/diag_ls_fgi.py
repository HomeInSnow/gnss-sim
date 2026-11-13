"""Decisive experiment for the FGI whu60 horizontal bias.

LS on FGI's OWN rawP vs corrP (from obsData2), with satellite positions
computed at FGI's decoded transmitTime (mulSatpos convention: orbit
directly at t_tx). If (corrP solution - rawP solution) reproduces the
measured ENU bias (-1.97, -1.93, +0.55), the injected clock correction
c*(relcorr - tgd) on a sv_clock=false signal is confirmed as root cause.
"""
import sys, math, collections
import datetime as dt
import numpy as np

sys.path.insert(0, ".")
from backend import config, geometry                      # noqa: E402
from backend.ephem import ephemeris                        # noqa: E402

C = config.C
LAT, LON, ALT = 60.182537, 24.828260, 47.248
RX = np.array(geometry.llh_to_ecef(LAT, LON, ALT))

req = dt.datetime(2023, 9, 28, 23, 20, 0)
gps = req + dt.timedelta(seconds=config.GPS_UTC_LEAP_S)
week, sow = ephemeris.gps_week_and_sow(gps)
eph = ephemeris.parse_rinex("data/rinex/BRDC_2023271_whu_afzero.rnx",
                            at_gps=gps)
eph = ephemeris.align_for_run(eph, week, sow, "native")

pr = {}
sat = {}
for r in np.genfromtxt("out/fgi/fgi_whu60_prn.csv", delimiter=",",
                       names=True):
    e, p = int(r["epoch"]), int(r["prn"])
    pr.setdefault(e, {})[p] = (float(r["rawP"]), float(r["corrP"]))
for r in np.genfromtxt("out/fgi/fgi_whu60_sat.csv", delimiter=",", names=True):
    e, p = int(r["epoch"]), int(r["prn"])
    sat.setdefault(e, {})[p] = (float(r["reftime"]),
                                np.array([r["posx"], r["posy"], r["posz"]]))

epochs = sorted(set(pr) & set(sat))
print(f"epochs usable: {len(epochs)}")


def ls(pos_map, pr_map, use_corr):
    xyz = RX.copy()
    cd = 0.0
    for _ in range(12):
        A, b = [], []
        for p, (rp, cp) in pr_map.items():
            if p not in pos_map:
                continue
            pos = pos_map[p]
            meas = cp if use_corr else rp
            d = pos - xyz
            rho = float(np.linalg.norm(d))
            erc = config.OMEGA_E_DOT / C * (pos[1]*d[0] - pos[0]*d[1])
            A.append(np.append(-d/rho, C))
            b.append(meas - (rho + erc + C * cd))
        z, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
        xyz = xyz + z[:3]
        cd += z[3]
    d = xyz - RX
    e_ = (-math.sin(math.radians(LON)) * d[0]
          + math.cos(math.radians(LON)) * d[1])
    n_ = (-math.sin(math.radians(LAT)) * math.cos(math.radians(LON)) * d[0]
          - math.sin(math.radians(LAT)) * math.sin(math.radians(LON)) * d[1]
          + math.cos(math.radians(LAT)) * d[2])
    u_ = (math.cos(math.radians(LAT)) * math.cos(math.radians(LON)) * d[0]
          + math.cos(math.radians(LAT)) * math.sin(math.radians(LON)) * d[1]
          + math.sin(math.radians(LAT)) * d[2])
    return np.array([e_, n_, u_]), cd


res_raw, res_corr, mypos_diff, sat_check = [], [], [], []
for e in epochs:
    pos_map = {}
    for p, (rt, fp) in sat[e].items():
        if p in eph:
            pos, E, tk, mu, wdot, geo, frel = geometry._sat_pos(eph[p], rt)
            pos_map[p] = np.asarray(pos, float)
            mypos_diff.append(np.linalg.norm(pos - fp))
    e_raw, cd_r = ls(pos_map, pr[e], False)
    e_cor, cd_c = ls(pos_map, pr[e], True)
    res_raw.append(e_raw); res_corr.append(e_cor)

raw = np.array(res_raw); cor = np.array(res_corr)
print(f"LS on rawP  mean ENU = {raw.mean(0).round(3)}  std {raw.std(0).round(3)}")
print(f"LS on corrP mean ENU = {cor.mean(0).round(3)}  std {cor.std(0).round(3)}")
print(f"delta (corrP - rawP) = {(cor.mean(0) - raw.mean(0)).round(3)}")
print("FGI reported bias (nav csv) = [-1.974 -1.928 +0.553]")
print(f"FGI-vs-my satellite position diff: "
      f"med {np.median(mypos_diff)*1000:.1f} mm  max {np.max(mypos_diff)*1000:.1f} mm")
