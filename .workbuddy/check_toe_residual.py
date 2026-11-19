import datetime as dt
import numpy as np
from backend.ephem.ephemeris import parse_rinex_multi
from backend.analysis.truth import ScenarioTruth
from backend import geometry

truth = ScenarioTruth(lat_deg=60.182537, lon_deg=24.82826, alt_m=47.248,
                      start_utc=dt.datetime(2023,9,28,23,20,0), duration_s=200)
rx = truth.rx_ecef
prns_obs = [4,5,9,11,12,18,20,25,26,29,31]
obs_res = [-486,1222,205,-507,-1607,405,864,-663,376,614,-422]

ephs = parse_rinex_multi(r"D:/workbuddy/GNSSSignal/gnss-sim-desktop/data/rinex/BRDC_2023271.rnx", systems=("G",))
eph_by_prn = {(k[1] if isinstance(k, tuple) else k): v for k, v in ephs.items()}

drho = []
for prn in prns_obs:
    e18 = eph_by_prn[prn]
    e16 = dict(e18); e16['toe'] = round(e18['toe']/16)*16
    sow = truth.sow_at(46.0)
    p18,_,_,_ = geometry.solve_transmit_time(e18, rx, sow)
    p16,_,_,_ = geometry.solve_transmit_time(e16, rx, sow)
    r18 = np.linalg.norm(np.array(p18)-np.array(rx))
    r16 = np.linalg.norm(np.array(p16)-np.array(rx))
    drho.append(r16-r18)
drho = np.array(drho)
pred_res = drho - drho.mean()   # LSE common-clock absorbs mean
print('PRN      drho(m)   pred_res(m)   obs_res(m)')
for prn, d, p, o in zip(prns_obs, drho, pred_res, obs_res):
    print(f'{prn:3d}  {d:10.1f}  {p:10.1f}  {o:9.0f}')
print(f'corr(pred,obs) = {np.corrcoef(pred_res, obs_res)[0,1]:.3f}')
print(f'RMS pred {np.sqrt((pred_res**2).mean()):.1f}  RMS obs {np.sqrt((np.array(obs_res)**2).mean()):.1f}')
