# materials_digest（whu60b 改正后对比报告）

## 资料 1：.workbuddy/docx_material_whu60b_vs_fgi.md（主素材，实测数据已由项目内脚本产出）

范围铁律：只对比「gnss-sim 内置跟踪解」与「FGI-GSRx 2.1.3 全量」，只用武大星历改正版
run `20261113T033315803665`（whu60b）；旧 run `20261112T090748645439`（whu60）仅作改正
前后对照。其余 run/模式一律不提。

## 资料 2：out/fgi/fgi_whu60b_stats.json（FGI 全量统计，fgi_stats.py 生成）

- n_sol=26；mean_enu=[−0.0555, −0.5751, −1.628] m；std_enu=[0.1978, 0.1644, 0.3759] m
- h_rmse=0.6304；v_rmse=1.6692；d3_rmse=1.7843 m
- cn0_grand_mean=41.676 dB-Hz（min 18.767 / max 46.848，n=2949/星）
- 逐星（mean±std）：G29 45.457±1.123、G25 45.220±0.939、G11 44.454±0.565、
  G20 43.061±0.628、G31 43.036±0.722、G26 42.084±0.502、G12 41.337±0.775、
  G09 40.580±0.490、G05 39.865±0.606、G28 39.140±0.672、G04 38.068±0.786、
  G18 37.814±0.347
- paper 节点（论文表 19 参考值）：mean_enu=[−0.255,−0.077,−0.6359]，
  std=[0.6933,1.0083,1.9839]，h/v/d3 RMSE=1.2517/2.0823/2.4295，n=892/900 s；
  论文表 18 C/N₀ 均值 44.85

## 资料 3：.workbuddy/trk_20261113T033315803665_coh.json（内置跟踪解，coh/10 s/bw 0.5/metric≥10）

- tracked：12/12 星、error_m=0.5928（3D）、PDOP 1.4004、resid_rms=0.16 m、
  ENU=(−0.228, −0.229, −0.497) m（plot 脚本旋转矩阵换算）
- err_chips RMS=0.00366 ch（max 0.00724）；err_chips_avg RMS=0.00084 ch（max 0.00152）
- 相位抖动（去趋势锚定）G 均值 0.02550 cyc（max 0.12975，G18 el 10.6°）；
  |drift| mean 0.0035 cyc/s；PLL bit-flip coast=0；会话 jitter 均值 0.00382 ch
- baseline（快照捕获，参考）：12 星、error_m=6.46、pdop 1.40
- policy（自动读 meta.config）：iono_off/tropo_off/sv_clock=True/atmo_fn=off

## 资料 4：out/20261113T033315803665/meta.json + gen_whu_afz2_events.txt（生成侧验收）

- config：sample_rate=25e6、int16、sv_clock=True、atmosphere iono/tropo off、seed 2281271
- provenance.impairments.L1：applied=[awgn]、noise_power=1.77347948e8、
  measured_snr_db=−18.33、n_samples=1.5e9
- bands[0].nsv_ref_scale=0.2513（=√(12/190)，即 −12.0 dB，SIM_NSV_REF=190 环境变量注入）
- 场景：Tampere 60.182537N/24.82826E/47.248 m、UTC 2023-09-28T23:20:00（sow 429618、
  leap 18 s）、60 s、GPS 12 星（PRN 4,5,9,11,12,18,20,25,26,28,29,31）
- 星历：BRDC_2023271_whu_afzero2.rnx（武大 BRDC2710.23P；af0/1/2 与 TGD 双清零：
  make_afzero4_whu.py 输出 records zeroed(af) 25086 / TGD zeroed 450；parse_rinex
  at_gps=2023-09-28 23:20:18 验证 12/12 星 af 与 tgd 全零）
- IQ 抽样验收（8 MB @ 1/3 文件处）：σ_I=9488.4、σ_Q=9480.6 LSB；饱和率 I 0.0558%、
  Q 0.0529%（|x|≥32767）

## 资料 5：旧 run 对照（whu60：out/fgi/fgi_whu60_stats.json.bak 等）

- FGI（26 解）：mean_enu=[−1.929, −1.9742, +0.5534]、std=[0.2255, 0.1444, 0.5004]、
  h/v/d3 RMSE=2.7726/0.7396/2.8696、cn0_grand_mean=41.291
- IQ：σ≈37471 LSB、饱和 38.54%（noise_power=2.808e9，measured_snr_db=−18.33）
- 内置跟踪解：3D 0.8214 m、ENU=(−0.278, −0.194, −0.748)、err_chips RMS 0.00359、
  err_avg RMS 0.00120、phRMS 均值 0.017（whu60 报告口径）
- 真值伪距新旧差（sv_clock 注入的相对论项，逐星）：G4 −0.522 / G5 +0.079 /
  G9 −1.588 / G11 +1.736 / G12 +9.667 / G18 +2.890 / G20 +0.971 / G25 +5.782 /
  G26 +1.011 / G28 +3.279 / G29 +1.208 / G31 +10.916 m；mean +2.95、min −1.59、max +10.92

## 资料 6：上一版归因（whu60 报告 §5/§6，作为"预期"基线引用）

- 三源分解（whu60 时代实测）：① 相对论伪改正 −1.41/−1.80/+2.32 m；② TGD 伪改正
  −0.57/+1.00/−0.17 m；③ FGI 跟踪层码相位残差 ≈0/−1.13/−1.60 m；合计与实测逐轴 <0.02 m
- C/N₀ 三层分解：① int16 饱和裁剪 −0.46 dB（引擎侧可修复）；② CDMA 互扰 −1.25 dB
  （固有）；③ FGI 估计器偏置 ≈−1.8 dB（论文侧同有）
- 引擎名义注入解析：measured_snr_db(−18.33)+74.0−10log10(12)=44.86 dB-Hz

## 图（stage2 以 base64 dataURI 内联嵌入）

- out/fgi/cmp_whu60b_enu_ts.png（FGI 26 解 ENU 时序 + 内置参考线 + 论文均值线）
- out/fgi/cmp_whu60b_errbar.png（内置/FGI/论文 h/v/3D 条形对比）
- out/fgi/cmp_whu60b_cn0.png（FGI 逐星 C/N₀ + 名义 44.86/论文 44.85 线）
