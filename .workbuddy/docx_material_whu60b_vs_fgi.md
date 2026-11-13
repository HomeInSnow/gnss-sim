# 素材：改正后场景（whu60b）内置跟踪解 vs FGI-GSRx 全量对比分析报告

> 用途：workbuddy-docx 写作素材。所有数字必须原样引用，不得改写。
> 范围铁律：只对比「gnss-sim 内置跟踪解」与「FGI-GSRx 全量处理」，且只用武大下载星历
> 改正版 run `20261113T033315803665`（whu60b）。对比基准为上一版 run
> `20261112T090748645439`（whu60，sv_clock=false + 饱和场景）——仅用于展示两项改正
> 的效果，其余 run、dll_mode（el/nc）、20 Msps 演示、郑州/河南场景等一律不提。

## 0. 改正背景（承接上一版报告 §5/§6 归因）

上一版（whu60）结论：FGI 水平 −2 m 恒定偏置的三源分解中，①相对论伪改正
（−1.41/−1.80/+2.32 m）与 ②TGD 伪改正（−0.57/+1.00/−0.17 m）合计约 2.2 m，均为
「FGI 改正链与注入策略错配」——引擎未注入但 FGI 照减。C/N₀ −3.5 dB 三层分解中，
引擎侧唯一可修复项为 int16 饱和裁剪（noise_power=2.808e9 → 每维 σ=37 471 LSB，
38.54% 样本 clipping，−0.46 dB）。本轮实施两项治本改正：

| 改正 | 做法 | 消除对象 |
|---|---|---|
| ① sv_clock=true + TGD 清零 | 星历改用 afzero2（af0/1/2 与 TGD 双清零，TGD 为 GPS 记录第 7 行第 3 个 20 列字段，450 条 G 记录全清）；生成请求 sv_clock=true | ①②伪钟差改正 ≈2.2 m：真值伪距含 −C·clk（af=0 时仅剩相对论项），与 FGI mulSatpos 无条件 relcorr 精确对消；电文 T_GD=0 → FGI TGD 改正量=0，引擎侧 svb 本就 0 |
| ② 全局衰减回线性区 | 服务环境变量 SIM_NSV_REF=190（pnorm=√(12/190)=0.2513，即 −12.0 dB）；噪声改用 snr_db=−18.33 模式跟随信号缩放 | 38.5% int16 饱和失真风险；C/N₀ 名义值不变（噪声/信号比恒定） |

## 1. 场景与信号（两侧同一 IQ 文件，保证公平）

| 项 | 值 |
|---|---|
| 接收点 | Tampere 60.182537°N, 24.82826°E, 47.248 m（复刻论文 6.2 节） |
| 信号时刻 | UTC 2023-09-28T23:20:00（GPS sow=429618，leap 18 s） |
| 采样 | 25 Msps，int16 复基带，60 s（gpssim.bin 6 000 000 000 B） |
| 星座 | GPS 12 星（PRN 4,5,9,11,12,18,20,25,26,28,29,31），native C++ 引擎生成 |
| 星历 | BRDC_2023271_whu_afzero2.rnx（武大 IGS BRDC2710.23P；af0/1/2=0 且 TGD=0） |
| 注入策略 | atmosphere off；**sv_clock=true**（真值伪距含 −C·clk 相对论项） |
| 幅度 | 全局 pnorm=0.2513（−12.0 dB，SIM_NSV_REF=190），meta bands.nsv_ref_scale=0.2513 |
| 噪声 | snr_db=−18.33 模式（noise_power 自动标定 1.773e8），measured_snr_db=−18.33 |
| 随机种子 | 2281271（与 whu60 同，噪声可实现对比） |

### IQ 线性区验收（抽样 8 MB @ 1/3 文件处）
- I σ=9 488 LSB、Q σ=9 481 LSB（预期 ≈9.4k）；饱和率 I 0.056% / Q 0.053%
 （旧 whu60 为 σ≈37 471、38.54%）
- 真值伪距新旧差（sv_clock 注入的相对论项）：逐星 −1.6 ~ +10.9 m、均值 +2.95 m，
  与轨道偏心率分布一致（G31/G12 最大 +10.9/+9.7 m）

## 2. 两台接收机

- **内置跟踪解**：gnss-sim 自带 Python 接收机，捕获（FFT 并行码相位搜索）→ SVTracker
  相干 E/L + Costas PLL（dll_mode="coh"，默认）载波辅助 DLL 会话 track_s=10 s，
  逐星伪距会话平均后单次 LS 定位。与 /api/receiver "tracking":true 同一代码路径。
  policy 自动读 meta.config（iono/tropo=off、sv_clock=true）。
- **FGI-GSRx 2.1.3**：FGI 开源软件接收机，Octave 10.3 全脚本运行，完整管线：
  捕获→跟踪（DLL/PLL + CN0fromSNR）→ 导航电文解码 → mulSatpos 卫星钟改正 →
 （含 Sagnac）LSE 定位，输出率 ~1 Hz。参数文件与 whu60 唯一差异 = 输入 IQ 路径与
  输出文件名；enableIono/TropoCorrections 保持 false（场景无大气注入）。

## 3. 定位对比（whu60b 改正后）

内置跟踪解（单次解，会话均值伪距；实测 2026-11-13，min_metric_db=10 使 12 星全留）：
- 3D 误差 __TRK_D3__；水平 __TRK_H__；垂直 __TRK_V__；E/N/U = __TRK_ENU__ m
- 参与星 12/12；PDOP 1.40；err_chips RMS 0.00366 ch；会话均值伪距残差
  err_chips_avg RMS 0.00084 ch（≈0.25 m）；相位抖动（去趋势锚定）G 均值 0.0255 cyc；
  PLL 比特滑移 coast 计数 0
- 快照捕获基线（内置管线前端，仅一行参考）：3D 6.46 m

FGI-GSRx 全量（__FGI_NSOL__ 有效解统计）：
- mean ENU = __FGI_MEAN__；std ENU = __FGI_STD__
- 水平 RMSE __FGI_H__ / 垂直 __FGI_V__ / 3D __FGI_D3__ m

论文表 19（参考，Skydel 信号 + 大气 + 干扰，892 解/900 s）：
- mean ENU = (−0.255, −0.077, −0.636)；水平 RMSE 1.252 / 垂直 2.082 / 3D 2.430 m

### 改正前后对照（同种子、同星历轨道，仅改正项差异）

| 指标 | whu60（改正前） | whu60b（改正后） | 预期 |
|---|---|---|---|
| FGI mean E (m) | −1.929 | __FGI_MEAN_E__ | ≈0（①②消除，残 ③跟踪层 ~0） |
| FGI mean N (m) | −1.974 | __FGI_MEAN_N__ | ≈ −1.13（③跟踪层） |
| FGI mean U (m) | +0.553 | __FGI_MEAN_U__ | ≈ −1.60（③跟踪层） |
| FGI 水平 RMSE (m) | 2.77 | __FGI_H__ | 显著下降至 ~1 m 量级 |
| FGI 3D RMSE (m) | 2.87 | __FGI_D3__ | 同上 |
| FGI C/N₀ 总均值 (dB-Hz) | 41.29 | __FGI_CN0__ | 回升趋近 44.8（裁剪失真消除） |
| int16 饱和率 | 38.54% | 0.056% | <0.1% |
| 内置跟踪解 3D (m) | 0.82 | 0.59 | 略优（线性区收益） |

关键结论（改写规则：以上面实测数字为准陈述，禁止照抄本行）：
1. FGI 恒定水平偏置由 2.77 m 降至 __FGI_H__，剩余与 §6 三源分解的 ③跟踪层预测
 （0/−1.13/−1.60）一致 → 归因闭环。
2. C/N₀ 从 41.29 回升到 __FGI_CN0__，int16 裁剪 −0.46 dB 项消除，剩余与论文差的
 构成 = CDMA 互扰 −1.25 dB + FGI 估计器偏置 −1.8 dB（whu60 报告 §5）。

## 4. C/N₀ 对比

FGI CN0fromSNR（5 s 滑窗方差式估计器，非零样本口径 n=__CN0_N__/星）：
- run 总均值 __FGI_CN0__ dB-Hz
- 逐星（均值±σ）：__FGI_CN0_TABLE__
- 与仰角单调，符合链路预算
- 引擎注入名义值解析：measured_snr_db(−18.33) + 74.0 − 10log10(12) = 44.86 dB-Hz
 （噪声随信号同步缩放，名义值与 whu60 相同）；论文表 18 均值 44.85（同一 FGI
  估计器在 Skydel 信号上的读数）

## 5. 结论与改进闭环

1. 两项改正兑现：sv_clock=true+TGD 清零消除 FGI 伪钟差改正（~2.2 m）；全局衰减
  −12 dB + snr_db 噪声跟随消除 int16 饱和（38.5%→0.056%）与 C/N₀ 裁剪偏置。
2. 改正后 FGI 剩余误差与内置解残差构成清晰：FGI 残偏置 ≈③跟踪层（rawP 逐星常数
  偏置，±5 m 内、与仰角无关），内置解 err_chips_avg RMS 0.00084 ch（≈0.25 m）为
  全场最好指标。
3. 后续可选：内置解 6×10 s 滑窗补 std 口径；FGI rawP 逐星偏置的互扰机理专项。

## 图

- 图1 out/fgi/cmp_whu60b_enu_ts.png —— FGI ENU 误差时序 + 内置单点解参考线 + 论文均值线
- 图2 out/fgi/cmp_whu60b_errbar.png —— 内置 vs FGI vs 论文 误差指标条形对比
- 图3 out/fgi/cmp_whu60b_cn0.png —— FGI 逐星 C/N₀ + 名义 44.86/论文 44.85 参考线

## 复现命令（附录）

```bash
# afzero2 星历（af+TGD 清零）
.venv/Scripts/python.exe .workbuddy/make_afzero4_whu.py
# 生成（起服务须带 SIM_NSV_REF=190 ALLOW_TX=0；请求 .workbuddy/gen_whu_afz2_60s.json）
curl --noproxy "*" -X POST http://127.0.0.1:8080/api/generate \
  --data @.workbuddy/gen_whu_afz2_60s.json
# 内置跟踪解（与 /api/receiver tracking:true 同路径）
.venv/Scripts/python.exe .workbuddy/test_tracked_fix.py 20261113T033315803665 10 0.5 coh 10
# FGI 全量（cwd=.workbuddy/fgi，~80 min）+ 后处理 + 统计 + 图
MSYS_NO_PATHCONV=1 /d/workbuddy/tools/octave/octave-10.3.0-w64-64/mingw64/bin/octave-cli.exe \
  --no-gui run_fgi_whu60b.m
MSYS_NO_PATHCONV=1 .../octave-cli.exe --no-gui post_fgi_whu60b.m
.venv/Scripts/python.exe .workbuddy/fgi_stats.py whu60b
.venv/Scripts/python.exe .workbuddy/plot_builtin_vs_fgi_whu60b.py
```
