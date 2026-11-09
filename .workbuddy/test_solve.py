import numpy as np
from backend.analysis.receiver import solve_position
rng = np.random.default_rng(1)
# 8 satellites on ~20,200 km orbit-ish ring, arbitrary
sat_pos = {}
truth = np.array([-2.3e6, 4.7e6, 3.5e6])
for i in range(8):
    a = 20200e3
    ang = i/8*2*np.pi
    s = truth + np.array([a*np.cos(ang)*0.6, a*np.sin(ang)*0.6, a*0.5 + (i-4)*4e5])
    sat_pos[i] = s
recv = np.array([0.0,0.0,0.0])
clock_m = 12345.0
pr = {}
for i,s in sat_pos.items():
    pr[i] = np.linalg.norm(s - truth) + clock_m + rng.normal(0,1.0)
# init at a wrong guess to test convergence
sol = solve_position(pr, sat_pos, x0=[*(truth+2000), 0.0])
print("truth", truth)
print("got  ", np.array(sol["ecef"]))
print("err_m", np.linalg.norm(np.array(sol["ecef"])-truth))
print("clock_bias_s*C", sol["clock_bias_s"]*299792458.0, "expected", clock_m)
print("resid", sol["residual_rms_m"])
