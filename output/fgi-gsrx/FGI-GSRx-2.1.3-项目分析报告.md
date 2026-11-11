# FGI-GSRx v2.1.3 项目完整分析报告

> 分析对象：`D:\workbuddy\GNSSSignal\gnss-sim\FGI-GSRx-2.1.3`（芬兰大地测量研究所 FGI 开源 GNSS 软件接收机）
> 分析日期：2026-11-11 · 方法：源码逐目录取证（224 个 .m 文件）+ 官方 README/Release Notes + 配套硕士论文（本目录 Documentation 内，已同步译为中文 docx）

---

## 1. 项目概览

| 项目 | 内容 |
|---|---|
| 名称 / 版本 | FGI-GSRx（FGI GNSS Software Receiver）v2.1.3 |
| 开发方 | Finnish Geospatial Research Institute（FGI，芬兰大地测量研究所） |
| 语言 / 平台 | MATLAB（全栈），GPL v3 开源 |
| 定位 | **后处理**（post-processing）多星座多频软件接收机：从文件读原始 I/Q，不做实时跟踪 |
| 支持系统 | GPS（L1 C/A、L1C）、Galileo（E1B/E1C）、BDS（B1I；B1C 缺件）、GLONASS（L1 OFDM-CDMA）、NavIC（L5） |
| 特色 | OSNMA 认证服务集成（MATLAB 壳 + 内嵌 Python FGI-OSNMA 库）、三种并行跟踪模式、RINEX 3.04 写出 |
| 规模 | 224 个 `.m` 文件，24 个功能目录，入口唯一：`main/gsrx.m`（182 行） |
| 版本脉络 | v2.1.0 基线 → v2.1.1 增加 PCT parfor 并行 → v2.1.2 增加 RINEX 3.04 写出 → v2.1.3 修补 |

## 2. 目录结构与职责

```
FGI-GSRx-2.1.3/
├── main/            # 唯一入口 gsrx.m + 多实例并行批处理脚本（.bat）
├── param/           # 全部 *.ini 配置（场景模板、信号参数、接收机设置）
├── acq/             # 信号捕获（FFT 并行码相位搜索、检测统计）
├── track/           # 跟踪（49 个文件：表驱动状态机、dll/、bit/ 位同步、PLL/FLL）
├── corr/            # 相关器基元
├── frame/           # 导航电文帧同步与解码（LNAV/L1C/E1B/B1I/GLONASS/NavIC）
│   ├── gpsl1cDecoding/   # L1C 专用：LDPC BP 译码器 reallyFastLDPCdecoder.m
│   └── viterbi/          # K=7 卷积码 Viterbi（E1B I/NAV、NavIC L5）
├── nav/             # 导航解算调度（doNavigation、伪距计算、TOW 管理）
├── lse/             # 最小二乘 PVT（calcPosLSE.m 等）
├── sat/             # 卫星侧：星历→位置/钟差/互偏差
├── obs/             # 观测量生成与改正调度（applyIono/Tropo/ClockCorrections）
├── iono/ + ionex/   # Klobuchar / NeQuick / IONEX 三层壳电离层模型
├── tropo/           # Saastamoinen 等对流层模型
├── geo/             # 大地坐标工具
├── time/            # GNSS 系统时间处理
├── rinex/           # RINEX 3.04 观测/导航文件写出（writeRinex3Obs/Nav.m）
├── osnma/           # OSNMA 认证：MATLAB 壳 + app/（Python CLI）+ crypto/
├── rf/              # 射频/前端损伤参数（配合外部数据集）
├── mod/ stats/ plot/ ui/ utils/   # 调制、统计、绘图、界面与杂项工具
└── Documentation/   # 用户手册、发布说明、FGI-GSRx 论文与 L1C 硕士论文 PDF
```

## 3. 主处理流水线（`main/gsrx.m:47-182`）

`gsrx.m` 按固定顺序调度 12 步，单向流水线、不回头（丢星不重捕）：

| 步 | 函数 | 要点 |
|---|---|---|
| 1 | `readSettings` | 读 param/*.ini：信号集、采样参数、环路带宽、门限 |
| 2 | 断点续算 | 每步产物落盘 .mat，`exist` 守卫跳过已完成阶段 |
| 3 | `generateSpectra` | 读 I/Q 文件、可生成频谱图 |
| 4 | `doAcquisition` | 全部可见卫星捕获（细节见 §5） |
| 5 | 绘图保存 | 捕获/跟踪统计图 |
| 6 | `doBitSynchronization` | 仅在启用 20 ms 跟踪优化前先做位同步（meander/NH 码/GEO 分支） |
| 7 | 跟踪 | 三选一：串行 `doTracking` / 多实例 `doTrackingParallel`（.bat + 单星文件）/ PCT `doTrackingPCT`（parfor，`doTrackingPCT.m:34-72`）；开关 `parallelChannelTracking` + `PCTenabled` |
| 8 | `generateObservations` | 码相位→伪距（发射时刻线性插值）、多普勒→伪距率 |
| 9 | `doFrameDecoding` | 电文帧同步 + 各信号码解析（见 §7） |
| 10 | `doNavigation` | 每系统独立 LS-PVT（见 §8） |
| 11 | `calcStatistics` | 定位误差/可用性等统计 |
| 12 | `generateRinex` | RINEX 3.04 观测 + 导航文件写出 |

## 4. 信号支持矩阵（能力完整度）

| 信号 | 捕获 | 跟踪 | 电文解码 | 备注 |
|---|---|---|---|---|
| GPS L1 C/A | ✅ | ✅ | ✅ LNAV | 最成熟基线 |
| GPS L1C | ✅ 导频 | ✅ | ✅ CNAV-2（LDPC BP） | 来自 2024 硕士论文工作 |
| Galileo E1B | ✅ B+E 合并 | ✅ | ✅ I/NAV（Viterbi K=7） | 与 L1C 完整度并列第一梯队 |
| Galileo E1C | ❌ | ✅ 仅跟踪 | ❌ | 无独立解码路径 |
| BDS B1I | ✅ | ✅ | ✅ D1/D2（BCH(15,11)） | |
| BDS B1C | ❌ | ❌ | ❌ 8 个函数文件全缺 | 配置存在但实现缺件 |
| GLONASS L1 | ✅ FDMA | ✅ | ✅ 15-string | 频点 (PRN−8)×0.5625 MHz |
| NavIC L5 | ✅ | ✅ | ✅（Viterbi tblen=584） | |
| L2C / L5 / E5 / E6 | ❌ | ❌ | ❌ | 完全未实现 |

**梯队结论**：`gpsl1 ≈ gale1b`（完整）> `gpsl1c ≈ beib1 ≈ glol1 ≈ navicl5`（完整）>> `gale1c`（仅跟踪）>> `beib1c`（缺件）。

## 5. 捕获模块（`acq/`）

- `doAcquisition.m` 只读信号前 **100 ms**；`searchFreqCodePhase.m:60-120` 实现 FFT 并行码相位搜索：本地码 `conj(fft(code))` 与输入一次乘法完成全部码相位候选。
- 频率步进公式：`freqStep = 1000 / (2·codeLengthMs·cohInt)`；两遍搜索（粗多普勒 + ±1 kHz 精多普勒）。
- 检测统计：`peakMetric = (peak − baseline)/std`，门限 `acqThreshold = 9`（B1/GLONASS/NavIC 用 10）；背景基线排除峰值 ±1 码片。
- E1 捕获做 **E1B+E1C 相干合并**；GLONASS 按 FDMA 频点切换中心频率。

## 6. 跟踪模块（`track/`，49 文件）

- **表驱动状态机**：`GNSSTracking.m:34-46` 读 `trackTable` 逐行执行（每行=一个处理步骤：相关→判别→滤波→NCO），各信号提供自己的 `*setTrackingTable.m`——新增信号只需写两张表 + 判别钩子，是框架可扩展性的核心设计。
- **三态带宽调度**：PULL_IN → COARSE → FINE，环路带宽逐级收窄（如 L1C FLL 100/50/10 Hz）。
- 判别器：DLL 非相干功率 EML `(√(E²)−√(L²))/(√(E²)+√(L²))`（NNEML）；PLL Costas `atan(Q/I)/2π`；FLL cross/dot power `atan`；Teunissen 风格三档带宽滤波器系数 `calcLoopCoef.m`。
- 锁定检测：FLL 用 Ma 式、PLL 用 Parkinson 窄带相关式；`CN0fromSNR` 用 2-chip 噪声相关器 + 5 s 窗。
- 码载耦合：`carrToCodeRatio` 实现载波辅助（码速率=(1+fd/fcarr)·fc）。
- 位同步：meander（E1B）、NH 码（GPS L1C 导频/数据合并）、GEO 分支单独处理。

## 7. 电文解码与 FEC（`frame/`）

| 信道编码 | 实现 | 用于 |
|---|---|---|
| Viterbi K=7（G1=171/G2=133 八进制） | `viterbi/viterbiDecoding.m` | E1B I/NAV（tblen=240）、NavIC L5（tblen=584） |
| LDPC 置信传播（BPDMC 软判决，30 迭代） | `gpsl1cDecoding/reallyFastLDPCdecoder.m:19`（H2/H3 稀疏 .mat 矩阵） | GPS L1C CNAV-2（子帧 2/3）+ TOI 覆盖 + CRC-24Q |
| BCH(15,11) | `beib1BCHDecoder.m` | BDS B1I |
| CRC-10 | `gale1bCrcCheck.m` | E1B word |
| 奇偶校验（半页 XOR） | `*NavParityCheck.m` | LNAV / GLONASS |

帧同步：`findPreambles.m`（LNAV/GLONASS 前导码）；L1C 用 L1CO 覆盖码相关（无导言字）。
**注意缺失**：E1C 独立解码、BDS B1C（8 个函数文件全缺）、GLONASS TOW 之外的校验增强均不存在。

## 8. 导航解算（`lse/calcPosLSE.m:52-126`、`nav/`）

- 等权最小二乘 `Δx = (HᵀH)⁻¹HᵀΔρ`，Gauss–Newton 迭代 10 次，收敛判据 fom < 50；
- **每信号一个钟差**吸收 ISB：GPS/Galileo/BDS/GLONASS/NavIC 各解独立，无显式系统间时统（这是多系统融合精度的潜在上限）；
- Sagnac 改正；伪距发射时刻用码相位线性插值；
- 改正链：卫星钟差 −T_GD + 电离层三选一（Klobuchar 常数组 / BDS 广播 / E1B B-C-N-C 播发→NeQuick 或 IONEX 单层壳双线性）+ Saastamoinen 标准大气 ZHD；
- 观测筛选：高度角 5° + SNR 30 dB-Hz 双门限；
- **无** RAIM/RAIM-AR、无 Kalman 滤波、无 PPP/RTK——定位质量完全依赖逐历元 LS。

## 9. OSNMA 集成（`osnma/`）

- MATLAB 壳 `initiateOSNMA.m:59-87` 经 `pyrunfile app/osnma-cli.py` 调 Python FGI-OSNMA 库（依赖 `cryptography`）；
- KPP 公钥经 PEM/TESLA KROOT 验证；13 类认证观测场景（NMA 状态、DKID、ACK 等级等）；
- 仅支持 E1B（OSNMA 数据加载于 E1B-D-C/N）。

## 10. 输入 / 输出接口

| 方向 | 格式 | 说明 |
|---|---|---|
| 输入 I/Q | 二进制 int8/int16（`sampleSize` 复数=I+Q 合计位宽）、可选 `iqSwap` | 配套 IGS XML 元数据（.xml）自动配置中心频率/采样率；LabSat `.ls3w` 有转换函数 |
| 输入场景 | `param/*.ini` 模板（含干扰/衰减研究场景，16 份） | 干扰研究依赖外部 FGI-JSDR 数据集，接收机本身**不做信号损伤注入** |
| 输出观测 | RINEX 3.04 obs：E1B/E1C/E1A/L1C（+L1C 多普勒） | `rinex/writeRinex3Obs.m` |
| 输出导航 | RINEX 3.04 nav：E1B/E1C/E1A | `rinex/writeRinex3Nav.m`；注意 GPS 导航电文不回写（v2.1.2 说明） |
| 中间产物 | 每阶段 .mat（断点续算）+ PNG 统计图 | |

## 11. 并行化设计

| 模式 | 机制 | 适用 |
|---|---|---|
| 串行 | `doTracking` 逐星逐历元 | 调试基线 |
| 多实例 | `runGNSSSingleSatelliteTracking.bat` 每星一 MATLAB 进程，产物合并 | 无 PCT 授权环境 |
| PCT parfor | `doTrackingPCT.m:34-72` 各 parfor 工作线程独立卫星跟踪 | 多核机，需 Parallel Computing Toolbox |

## 12. 局限与风险清单

1. **后处理专用**：无实时能力、无重捕获状态机（丢星即弃）。
2. **B1C/E1C/L2C/L5/E5/E6 缺件**：配置界面可勾选但函数缺失，直接运行会报错。
3. 多系统**无统一时统**，ISB 靠每系统独立钟差吸收，融合精度受限。
4. 无 RAIM：单个粗差伪距直接污染 LS 解。
5. MATLAB 性能墙：32 星 L1C 捕获数分钟、15 min 数据跟踪可达数天（硕士论文 §8.3 自述）。
6. 电文缺失容忍度：真实 L1C 无 CNAV-2 播发时无法出 PVT（论文 §7.2 实测结论）。

## 13. 与本项目（gnss-sim）的对照

| 维度 | FGI-GSRx | gnss-sim（本项目） |
|---|---|---|
| 角色 | 通用**接收机**（消费 I/Q） | 信号**仿真生成** + 内置互验接收机 |
| 语言 | MATLAB | Python 后端 + C++20 引擎 + 原生 JS |
| 信号 | 5 系统 8 信号（不等齐） | GPS L1 C/A + Galileo E1 深做（coh E/L + Costas PLL） |
| 跟踪 | 表驱动状态机 + 三态带宽 | SVTracker：NC/E-L/coh 三模式 + NC 块中心锚点 |
| 精度展示 | 场景级统计（米级） | 逐历元真值 vs 接收机 trace 对比（亚米/分米） |
| 电文 | 6 套真格式 | 简化真实感电文（星历对齐 align_for_run 唯一入口） |
| 可借鉴 | 表驱动跟踪框架、断点续算 .mat 守卫、IONEX 处理、并行三模式 | — |

## 14. 关键代码索引（速查）

| 主题 | 位置 |
|---|---|
| 主流水线 | `main/gsrx.m:47-182` |
| FFT 捕获搜索 | `acq/searchFreqCodePhase.m:60-120` |
| 表驱动跟踪 | `track/GNSSTracking.m:34-46`（+ 各 `*setTrackingTable.m`） |
| L1C LDPC BP 译码 | `frame/gpsl1cDecoding/reallyFastLDPCdecoder.m:19` |
| Viterbi | `frame/viterbi/viterbiDecoding.m` |
| LS-PVT | `lse/calcPosLSE.m:52-126` |
| OSNMA 桥 | `osnma/initiateOSNMA.m:59-87` → `app/osnma-cli.py` |
| PCT 并行跟踪 | `track/doTrackingPCT.m:34-72` |
| RINEX 写出 | `rinex/writeRinex3Obs.m`、`writeRinex3Nav.m` |

## 15. 总结

FGI-GSRx 是一部**教科书式可扩展的多星座后处理软件接收机**：表驱动跟踪 + INI 场景模板 + 阶段化落盘，使其长期作为 FGI 干扰/抗欺骗/OSNMA 研究的实验床；L1C 支持（即同目录 2024 硕士论文的成果，本次已全文译中）使其成为少数完整实现 CNAV-2/LDPC 开源接收机之一。短板在于信号覆盖不均（B1C/E1C 缺件）、无 RAIM/卡尔曼与 MATLAB 性能上限。对 gnss-sim 而言，其**表驱动跟踪框架、断点续算守卫与并行三模式**是最值得借鉴的三点工程设计。
