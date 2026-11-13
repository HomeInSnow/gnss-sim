# 资料摘要（materials_digest）

- 资料清单：仅一份主资料 `D:\workbuddy\GNSSSignal\PocketSDR_深入分析_20261113.md`（168 行，md 直读，结构照原样理解）。
- 无数据类文件（csv/xlsx/json），无 docx 快照需求，无资料嵌入配图（md 内无图片引用）→ 不执行图片提取。
- 本报告不产生资料之外的新统计数字；引用数值一律原样抄录并标注源节（TRUTH 铁律）。

## 资料：PocketSDR_深入分析_20261113.md

### 来源与对象（源：文件头）

- 分析对象 `D:\workbuddy\GNSSSignal\PocketSDR`（GitHub tomojitakasu/PocketSDR，本地 HEAD `77a85b0`，版本 0.22，2026-11-03）；分析日期 2026-11-13。
- 方法：README/AGENTS.md 与全部目录实地取证（三个探查子代理分工应用层/硬件层/测试文档层）+ 核心库源码精读 + 本地编译与冒烟实验。

### 项目概览要点（源：§1）

- RTKLIB 作者 T. TAKASU 主导的开源 GNSS SDR，BSD 2-Clause，约 364 MB（87 个 PDF、136 份 FPGA 工程文件）。
- 定位：射频前端到 PVT 解的全栈开源参考实现；覆盖 GPS/GLONASS/Galileo/QZSS/BeiDou/NavIC/SBAS 几乎全部公开信号（含 AltBOC、CBOC、CSK、NB-LDPC）。
- 形态：C/C99+Python、紧凑模块化、无外部构建工具依赖；`make` 即出 11 个 exe。
- 定位差异：vs gpstsdk/gnss-sdr（无配置 DSL、无依赖库栈，FFT 自带 pocketfft）；vs FGI-GSRx（生产级 C，可实时/回放/带 Web GUI）；vs gps-sdr-sim（接收侧；raw+.tag 格式是 SDR 圈事实标准之一）。

### 架构要点（源：§2）

- 三层：应用层 11 个 C exe；核心库 src/ 17 文件 ≈24,700 行（libsdr.a）；依赖 lib/RTKLIB 子集 + lib/pocketfft + lib/SoapySDR（仅头+导入库）；硬件层 FE_2CH/4CH/8CH。
- 数据流（doc/algo_desc.md §2.4）：设备/文件 → 每 RF 通道 raw 缓冲 → 1 ms 处理周期（SDR_CYC）→ LPF（可选）→ 数字下变频（LUT）→ 通道线程独立捕获/跟踪 → 电文解码 → sdr_pvt.c 调 RTKLIB pospri() 出 PVT → NMEA/RTCM3/log/观测值输出。

### 核心 DSP 参数表（源：§3 表格，逐值抄录）

- 捕获：FFT 并行码相位、零填充 2N、t_acq=20 ms（辅助捕获 100 ms）、max_dop=±10 kHz、峰值−均值比判决门限 34 dB-Hz。
- 载波跟踪：FLL（dot-cross 10→5 Hz）1 s 拉入 → 三阶 PLL（b_pll=10 Hz）；导频 4 象限 atan2 相干 t_coh=20 ms。
- 码跟踪：非相干 E/L DLL（√E−√L/√E+√L）、20 ms 非相干累积、b_dll=0.5 Hz、间距 0.2~0.25 chip。
- 假锁防护：BOC VE/VL bump-jump（BUMP_K=1.3）。
- C/N₀：噪声指功率差分式 S=max(|P|²−|N指|², 0.01·N指)，CN0=10log10(S/N指/T)，噪声指 −120 采样偏移（POS_CORR_N），T_CN0=0.5 s、FILT_CN0=0.5。
- 载体锁定：PLI=Σ(I²−Q²)/Σ(I²+Q²)≈cos2φ，门限 0.25、连续 4 窗坏判失锁。
- 电文：2308 行覆盖 LNAV/CNAV/F-NAV/I/NAV/B-C-NUM-D1/D2/D2Q/B-C-NAV-D1、GLONASS 5 型、SBAS 1/3 型、QZSS L1S/L6、NavIC；FEC 含 NB-LDPC 新重设计（v0.22）。
- 高级特性：二次码同步、E5aQbQ AltBOC、L6 CSK 码域 FFT、天线阵列数字波束成形+EKF 标定、FastReFix、快速捕获槽调度。
- C/N₀ 估计器对比结论（可引用原句）："PocketSDR 的估计器结构天然免疫任务⑨定案的 FGI 偏置机理，适合作为 gnss-sim C/N₀ 归因的第三方参照。"

### 应用层/硬件/测试要点（源：§4/§5/§6）

- 9 个 AP；数据源四类 SDR_DEV_FILE/USB/STR/SOAPY，文件是硬件无关一等公民；格式 INT8/INT8X2/CS8/CS16/RAW8/RAW16/RAW32；.tag 旁车；sample/ 14 个真实采集样例（4~24 Msps）。
- pocket_web 2106 行自研 mini HTTP+WS 服务器、19 个零构建原生 JS；python/ 21 脚本、pocket_sdr.py 独立纯 Python 接收机。
- 三 FE：FE_2CH AD6643 14b@65M×2（FX2LP）；FE_4CH ADC3282 12b×4@65M（FX3）；FE_8CH 比较器 1-bit×8@50M 时间交织→3b@400M 等效、1.584G 一次下变频；共同 ADF4355+LMX2594+ADRV6516；全 Spartan-6。
- 测试：自研框架 test_sdr.h 36 行宏、12 测试文件 ≈14888 行、573 ASSERT、90 TEST、4 个 *_stub.c 隔离硬件（单测全离线）；make -C test/utest test 一条命令回归；集成脚本 run_integration_test.sh。
- 构建：纯 makefile（MSYS2 UCRT64）；三条依赖红线（C99、公开 API 冻结、无测试专用 #ifdef）；bin/ 预编译全是 Windows UCRT64 exe。
- v0.22 演进：NB-LDPC 重设计（+1.6~1.9 dB、7~17×速度）、CSK 并行捕获、AltBOC、天线阵列、FastReFix、Web UI 与 pocket_snap。

### gnss-sim 对接与风险要点（源：§7/§8）

- gnss-sim 输出 = PocketSDR CS16 格式，SDR_DEV_FILE 直接回放；-fo/-f 收 MHz、-fi/-d（pocket_acq）收 Hz，单位不统一；-tscale 语义反直觉（1=实时；0=反睡；1000 全速→IF 缓冲>90% → update_srch_ch 拒绝调度捕获→0 锁定无日志）；默认 LOG_LEVEL=3 不打印捕获判决。
- bin/ 预编译 exe 缺 SoapySDR.dll/AVRT.dll 不可直接运行；自编译需 -lwinmm 等。
- 本地自编硬件无关静态版 local_build/pocket_trk_local.exe（7.7 MB，链接 lib/win32 librtk.a/libpocketfft.a）。
- 第三方互验价值：C/N₀（功率差分）、PVT（RTKLIB pospri）、跟踪（20 ms 非相干 DLL/1 ms Costas）与内置 coh、FGI 算法独立，可三角互验。

### 冒烟实测数据（源：附录 A，逐值抄录）

- 场景：out/20261113T033315803665/gpssim.bin（Tampere 60.182537°N/24.82826°E/47.248 m，25 Msps CS16，60 s，12 星 GPS L1 C/A PRN 4/5/9/11/12/18/20/25/26/28/29/31，awgn SNR −18.33 dB，atmosphere off / sv_clock on）。
- 捕获 12/12（38.9~45.9 dB-Hz，逐星 2 s 内）；跟踪 LOCK 12/12；$NAV 子帧 3（240 字）解码、TOW 有效；9/12 星 FIX。
- 收敛（23:21:17）60.18252216°N/24.82826244°E/椭高 35.796 m；水平 1.66 m（N −1.65/E +0.14）、垂直 −11.45 m。
- 逐星 C/N₀：G4=39.8 G5=40.9 G9=38.9 G11=42.1 G12=40.2 G18=40.0 G20=42.8 G25=45.1 G26=43.2 G28=45.1 G29=45.9 G31=43.8；均值 ≈42.0，比 FGI 41.676 高 0.3 dB。
- 排障两条：-fo 单位 MHz（传 Hz→fi=−1.5754e15、捕获静默全灭）；tscale 节流语义。
- 复现产物：pocket_trk_local.exe（正式）、pocket_trk_dbg.exe（仪表版不入库）、pocket_acq_new.exe（快照捕获首选利器）。
- 方法学价值（可引用原句）："内置相干跟踪解 ≈ PocketSDR ≈ FGI 名义值、FGI 的 −3.2 dB 主要是其估计器 artifact 而非 CDMA 互扰物理损失"。

### 垂直误差 A/B 数据（源：附录 B，逐值抄录）

- 根因：sdr_pvt.c update_sol()（L1126-1131）硬编码 IONOOPT_BRDC+TROPOPT_SAAS；场景 atmosphere off（引擎 backend/synth/engine.py L230 iono_abs=tropo_abs=0）→ 错扣仰角相关延迟，公共部分进钟差、仰角相关残差映射到垂直；Klobuchar 因 BRDC GPSA 2.5e-8…/GPSB 1.3e5… 非零也错扣。
- A/B（同一 gpssim.bin、同一命令行、真值椭高 47.248 m）：基线 35.796（−11.45）；仅 IONOOPT_OFF 38.455（−8.79）；仅 TROPOPT_OFF 44.335（−2.91）；双 OFF 47.306（+0.06，水平 0.18）。
- 归因：−11.45 ≈ 对流层假扣 −8.5 + 电离层假扣 −2.7（双 OFF 残差 +0.06 闭合，余 ~0.2 m LS 弱耦合）；Saastamoinen 斜路径 2.3 m(天顶)→8.75 m(el=15°)；EL_MASK=15° 解释 9/12 FIX（剔 3 低仰角星）但非垂直主因。
- 验证工具：local_build/pvt_both_off.exe / pvt_iono_off.exe / pvt_tropo_off.exe（源码临时改后已 git 还原）。
- 用法启示（可引用原句）："用于仿真互验时，若 atmosphere off 须自备 IONOOPT_OFF/TROPOPT_OFF 编译版……否则会把 RTKLIB 内置大气模型误差误算到仿真器/接收机头上。"

### 结论要点（源：§9）

- "PocketSDR 是当前开源生态中覆盖面最全、工程化最完整的 GNSS SDR 参考实现"；对 gnss-sim 是继 FGI-GSRx 之后最有价值的第三方互验接收机；本地编译与端到端互验均已完成。

## 报告配图（本会话按资料数字生成，非资料自带）

- 图 1 A/B 垂直误差对比：数值取自上表 A/B 四组（stage2/intermediate/fig_ab_vertical.png）。
- 图 2 逐星 C/N₀ 对照：数值取自上表逐星 12 值 + FGI 均值 41.676 + PocketSDR 均值 42.0（stage2/intermediate/fig_cn0.png）。
- 两图均为资料数据的可视化呈现，无新增数值。
