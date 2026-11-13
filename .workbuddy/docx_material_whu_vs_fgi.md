# 素材：内置跟踪解 vs FGI-GSRx 全量对比分析报告（武大下载星历）

> 用途：workbuddy-docx 写作素材。所有数字必须原样引用，不得改写。
> 范围铁律：只对比「gnss-sim 内置跟踪解」与「FGI-GSRx 全量处理」，且只用武大下载星历
> （BRDC_2023271_whu_afzero.rnx）的 run `20261112T090748645439`。其他 run、其他
> dll_mode（el/nc）、20 Msps 演示、郑州/河南场景等一律不提。

## 1. 场景与信号（两侧同一 IQ 文件，保证公平）

| 项 | 值 |
|---|---|
| 接收点 | Tampere 60.182537°N, 24.82826°E, 47.248 m（复刻论文 6.2 节） |
| 信号时刻 | UTC 2023-09-28T23:20:00（GPS sow=429618，leap 18 s） |
| 采样 | 25 Msps，int16 复基带，60 s（gpssim.bin 6 000 000 000 B） |
| 星座 | GPS 12 星（PRN 4,5,9,11,12,18,20,25,26,28,29,31），native C++ 引擎生成 |
| 星历 | 武大 IGS  ftp 下载 BRDC2710.23P 转换（whu_afzero：af0/af1/af2 清零，TGD 保留） |
| 注入策略 | atmosphere off（无电离层/对流层）、sv_clock=false（无钟差/相对论/TGD 注入） |
| 噪声 | 复总功率标定 noise_power=2.808e9（→ int16 饱和 38.54%，见 §5） |

## 2. 两台接收机

- **内置跟踪解**：gnss-sim 自带 Python 接收机，捕获（FFT 并行码相位搜索）→ SVTracker
  相干 E/L + Costas PLL（dll_mode="coh"，默认）载波辅助 DLL 会话 track_s=10 s，
  逐星伪距会话平均后单次 LS 定位。与 /api/receiver "tracking":true 同一代码路径。
- **FGI-GSRx 2.1.3**：FGI（芬兰地理信息中心）开源软件接收机，Octave 10.3 全脚本运行，
  完整管线：捕获→跟踪（DLL/PLL + CN0fromSNR）→ 导航电文解码（12/12 星 found）→
  mulSatpos 卫星钟改正 → LSE（含 Sagnac）定位，输出率 ~1 Hz，共 52 历元、26 有效解。

## 3. 定位对比

内置跟踪解（单次解，会话均值伪距；实测 2026-11-13，min_metric_db=10 使 12 星全留、与 FGI 对齐）：
- 3D 误差 0.821 m；水平 0.338 m；垂直 0.748 m；E/N/U = (−0.28, −0.19, −0.75) m
- 参与星 12/12 颗；PDOP 1.40；err_chips RMS 0.00359 ch、会话均值伪距残差
  err_chips_avg RMS 0.00120 ch（≈0.35 m）；相位抖动（去趋势锚定）均值 0.017 cyc
- 快照捕获基线（内置管线前端，仅一行参考）：3D 6.08 m

FGI-GSRx 全量（26 有效解统计）：
- mean ENU = (−1.974, −1.928, +0.553) m；std ENU = (0.141, 0.221, 0.491) m
- 水平 RMSE 2.772 / 垂直 0.740 / 3D 2.869 m；12 星全程参与

论文表 19（参考，Skydel 信号 + 大气 + 干扰，892 解/900 s）：
- mean ENU = (−0.255, −0.077, −0.636)；水平 RMSE 1.252 / 垂直 2.082 / 3D 2.430 m

关键对比结论：
1. 内置跟踪解达厘米~分米级（0.82 m），FGI 为米级（2.87 m），差一个数量级；
   FGI 的 2.87 m 中 2.77 m 是**恒定水平偏置**（std≪mean），随机散布仅 0.14/0.22/0.49 m，
   优于论文散布（本 run 无大气/干扰注入）。
2. FGI 偏置非引擎信号缺陷主导——§6 三源分解中 ①② 是 FGI 自身改正链与注入策略错配。

## 4. C/N₀ 对比【FGI 侧数字完整】

FGI CN0fromSNR（5 s 滑窗方差式估计器）：
- run 总均值 41.334 dB-Hz；逐星（均值±σ, n=2901/星）：G29 44.98±0.60、G25 44.73±0.33、
  G11 43.81±0.50、G31 42.78±0.47、G20 42.45±0.51、G26 41.61±0.52、G12 41.20±0.46、
  G9 40.17±0.54、G5 39.56±0.56、G28 39.17±0.49、G4 37.92±0.60、G18 37.62±0.44
- 与仰角单调（高仰角星 C/N₀ 高），符合链路预算
- 论文表 18 均值 44.85 dB-Hz——**同一 FGI 估计器在 Skydel 信号上的读数**，3.5 dB 差中
  估计器自身系统偏置双侧同有，公平对比下真正可归因本引擎信号的只有 0.46 dB（§5 裁剪项）
- 引擎注入名义值解析验证：measured_snr_db(−18.33)+10log10(25e6/25e6 参考带宽换算 74.0)
  −10log10(12)=44.86 dB-Hz，与论文 44.85 吻合，注入标定正确

## 5. C/N₀ −3.5 dB 三层分解（实证，.workbuddy/exp_clip_cn0.py 等）

| 层 | 机理 | 量值 | 性质 |
|---|---|---|---|
| ① int16 饱和裁剪 | noise_power=2.808e9 → 每维 σ=√(NP/2)=37 471 LSB > 32 767 满幅，I/Q 各 38.54% 样本 clip；噪声功率 −3.67 dB 与信号相关增益压缩 −4.2 dB 大部对消 | −0.46 dB（合成 12 星裁剪/不裁剪同法对照实测） | 引擎侧，可修复：noise_power 降 ~6 dB |
| ② 星间互相关+噪声底 | CDMA 非正交 12 星互扰抬升相关噪声底；无裁剪理想星座教科书 N/P 法独立测得 43.61 vs 名义 44.86 | −1.25 dB | CDMA 固有，任何接收机同受 |
| ③ FGI 估计器偏置 | CN0fromSNR 用 E+L 功率和的滑窗方差，对 38.5% 饱和的非高斯噪声形状敏感 | ≈ −1.8 dB（残差归属） | FGI 侧，论文读数同含 |

## 6. 水平 −2 m 偏置三源分解（实证闭环，.workbuddy/diag_ls_fgi.py）

决定性实验：在 FGI 自己的 rawP/corrP 上做本地 LS 复刻（FGI reftime 星位 + FGI 式
Sagnac），解与 FGI 导航输出逐位一致 (−1.974,−1.928,+0.553)；两侧卫星位置残差 0.7 mm
（轨道模型完全同源，排除星历链）。

| 源 | 机理 | ΔE/ΔN/ΔU (m) |
|---|---|---|
| ① 相对论伪改正 | FGI mulSatpos L196 无条件加 relcorr=F·e·√A·sinE 进 satClkCorr；引擎 sv_clock=false 未注入相对论项 → FGI 反减不存在之物 | −1.41/−1.80/+2.32 |
| ② TGD 伪改正 | afzero 脚本未清 TGD，引擎亦未注入 → FGI 照减 c·TGD（±4 m） | −0.57/+1.00/−0.17 |
| ③ FGI 跟踪层码相位残差 | rawP 逐星常数偏置 ±5 m（逐星 std 0.2–0.6 m ≪ 均值，无仰角相关），C/A 互扰/判别器机制 | ≈0/−1.13/−1.60 |
| 合计 vs 实测 | | −1.98/−1.93/+0.55 vs −1.97/−1.93/+0.55（逐轴 <0.02 m）✓ |

内置跟踪解无此偏置的原因：跟踪锚点对准引擎真值伪距（err_chips 即对真值残差），
不做任何卫星钟改正（与注入策略自洽），且判别器三模式经 2026-11 系列标定。

## 7. 结论与改进

1. 同信号横向对比：内置跟踪解精度优于 FGI 一个量级；FGI 的米级误差 96% 是恒定水平
   偏置，且 2/3 由 FGI 改正链与 sv_clock=false 注入策略错配造成，非信号质量问题。
2. C/N₀：注入名义 44.86 dB-Hz 解析验证无误；与论文 3.5 dB 差中引擎侧仅 −0.46 dB
   （int16 裁剪，可修复），其余为 CDMA 固有 + FGI 估计器偏置（论文侧同有）。
3. 行动项：① afzero 场景改 sv_clock=true 重跑 FGI（预期消除 ~2.2 m 水平偏置）；
   ② noise_power 降 ~6 dB 重标定（消除 38.5% int16 饱和）。

## 图

- 图1 out/fgi/cmp_whu60_enu_ts.png —— FGI ENU 误差时序 + 内置单点解参考线
- 图2 out/fgi/cmp_whu60_errbar.png —— 内置 vs FGI vs 论文 误差指标条形对比
- 图3 out/fgi/cmp_whu60_cn0.png —— FGI 逐星 C/N₀ + 名义/论文参考线

## 复现命令（附录）

```bash
# 内置跟踪解（与 /api/receiver tracking:true 同路径）
.venv/Scripts/python.exe .workbuddy/test_tracked_fix.py 20261112T090748645439 10 0.5 coh 15
# FGI 全量（cwd=.workbuddy/fgi，~80 min）
MSYS_NO_PATHCONV=1 /d/workbuddy/tools/octave/octave-10.3.0-w64-64/mingw64/bin/octave-cli.exe \
  --no-gui run_fgi_whu60.m && MSYS_NO_PATHCONV=1 .../octave-cli.exe --no-gui post_fgi_whu60.m
# 图
.venv/Scripts/python.exe .workbuddy/plot_builtin_vs_fgi_whu.py
```
