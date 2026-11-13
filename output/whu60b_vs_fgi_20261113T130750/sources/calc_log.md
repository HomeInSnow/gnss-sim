# calc_log（数字来源登记：均为项目内脚本实测输出，非心算）

| # | 数字 | 来源命令/脚本 | basis |
|---|---|---|---|
| 1 | afzero2 af 清零 25086 条、TGD 清零 450 条 | `.venv/Scripts/python.exe .workbuddy/make_afzero4_whu.py` stdout | 正则 token 原位清零计数 |
| 2 | 12/12 星 af0/1/2、tgd 全零 | parse_rinex(path, at_gps=2023-09-28 23:20:18) 逐星断言（stdin 内联脚本） | georinex 解析后字段 |
| 3 | sv_clock=True、atmo off、seed 2281271 | out/20261113T033315803665/meta.json config | 生成服务落盘 |
| 4 | noise_power=1.77347948e8、measured_snr_db=−18.33 | 同上 provenance.impairments.L1 | postproc 加噪前实测 sig_p 标定 |
| 5 | nsv_ref_scale=0.2513 | 同上 bands[0]；理论值 √(12/190)=0.25133 | SIM_NSV_REF=190 环境变量 |
| 6 | σ_I=9488.4 / σ_Q=9480.6 LSB、饱和 0.0558%/0.0529% | numpy 抽样 8 MB @ 1/3 文件处（stdin 内联脚本，\|x\|≥32767 占比） | int16 复基带 interleaved |
| 7 | 内置 3D 0.5928 m、ENU(−0.228,−0.229,−0.497)、PDOP 1.4004、err_chips RMS 0.00366、err_avg RMS 0.00084、phRMS 0.02550、coast 0 | `.venv/Scripts/python.exe .workbuddy/test_tracked_fix.py 20261113T033315803665 10 0.5 coh 10` → trk_20261113T033315803665_coh.json | /api/receiver tracking:true 同代码路径 |
| 8 | FGI 26 解、mean/std/RMSE、逐星 C/N₀ | `.workbuddy/fgi_stats.py whu60b` ← post_fgi_whu60b.m 导出 fgi_whu60b_{nav,cn0}.csv | ECEF→ENU 旋转矩阵在 marker；cn0 口径 mean_cn0>0 行（n=2949/星） |
| 9 | 旧 whu60 FGI 2.7726/0.7396/2.8696、41.291 | `.workbuddy/fgi_stats.py whu60` 重算（与旧版 stats 2.7724/0.7396/2.8693、41.334 差异 <0.05：cn0 口径统一为 mean_cn0>0） | 同 #8 |
| 10 | 真值伪距新旧差（−1.59~+10.92 m，mean +2.95） | 两 run gen 事件流末行 done.svs 逐星 pseudorange_m 差 | sv_clock=false→true 的 −C·clk 注入 |
| 11 | 三源/三层分解基线（−1.41/−1.80/+2.32、−0.57/+1.00/−0.17、0/−1.13/−1.60；−0.46/−1.25/−1.8 dB） | 上一版报告 §8.10 实证（diag_ls_fgi.py / exp_clip_cn0.py，已入库 commit e1ebeca） | 引用为"预期"列 |
| 12 | 名义 C/N₀ 解析 44.86 dB-Hz | −18.33 + 10log10(25e6) − 10log10(12)（postproc 口径） | 与论文 44.85 吻合 |

勾稽自查：改正前后对照表 = #8 vs #9（同脚本同口径）；内置 #7 baseline 6.46 与 tracked
0.59 同 run 同文件；C/N₀ 回升 41.676−41.291=+0.385 ≈ 裁剪项 0.46（差 0.07 在估计器
散布内，如实呈现实测差值，不做凑平）。
