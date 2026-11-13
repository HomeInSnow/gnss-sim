# PocketSDR 深入分析与 gnss-sim 第三方互验报告

| 项目 | 内容 |
|------|------|
| 分析对象 | D:\workbuddy\GNSSSignal\PocketSDR（GitHub tomojitakasu/PocketSDR，本地 HEAD 77a85b0，版本 0.22，2026-11-03） |
| 分析日期 | 2026-11-13 |
| 分析方法 | README/AGENTS.md 与全部目录实地取证（三个探查子代理分工应用层/硬件层/测试文档层）+ 核心库源码精读 + 本地编译与冒烟实验 |
| 互验场景 | gnss-sim 仿真场景 out/20261113T033315803665（Tampere，12 星 GPS L1 C/A，25 Msps CS16，60 s） |

## 执行摘要

- PocketSDR 是 RTKLIB 作者 T. TAKASU 主导的全栈开源 GNSS SDR 参考实现（BSD 2-Clause），覆盖七大系统几乎全部公开信号，是当前开源生态中覆盖面最全、工程化最完整的同类项目。
- 端到端互验通过：gnss-sim 仿真信号经本地编译的 PocketSDR 实现 12/12 星捕获锁定、12/12 跟踪、9 星 FIX，水平误差 1.66 m；逐星 C/N0 均值 42.0 dB-Hz 与 FGI-GSRx 的 41.676 dB-Hz 量级一致，佐证任务⑨对 C/N0 偏差的归因结论。
- 垂直误差 −11.45 m 根因已由判决性 A/B 编译实验定案：sdr_pvt.c 硬编码 Klobuchar+Saastamoinen 大气改正，而场景 atmosphere off（引擎未注入任何大气延迟），错扣的仰角相关延迟被最小二乘映射到垂直方向；归因对流层假扣约 −8.5 m、电离层假扣约 −2.7 m，双关闭后垂直收敛到 +0.06 m。
- 用法启示：PocketSDR 用于仿真互验时，必须按场景大气开关自备 IONOOPT_OFF/TROPOPT_OFF 编译版，否则会把 RTKLIB 内置大气模型误差误算到仿真器/接收机头上。

## 一、项目概览与定位

PocketSDR 是 RTKLIB 作者 T. TAKASU（佐藤知司）主导的开源 GNSS 软件定义接收机（SDR），BSD 2-Clause 许可，仓库约 364 MB（含 87 个 PDF 与 136 份 FPGA 工程文件）。一句话定位：从射频前端硬件到 PVT 解的全栈开源 GNSS 接收机参考实现——覆盖 GPS/GLONASS/Galileo/QZSS/BeiDou/NavIC/SBAS 的几乎所有公开信号（含 AltBOC、CBOC、CSK、NB-LDPC 等"难啃"的现代信号），并刻意写成 C/C99+Python、紧凑模块化、无外部构建工具依赖的形态。

与同类项目的定位差异：

| 对比对象 | 定位差异 |
|---|---|
| gpstsdk / gnss-sdr（重量级框架） | PocketSDR 无配置 DSL、无依赖库栈（FFT 自带 pocketfft 头文件库），make 即出全部 11 个 exe |
| FGI-GSRx（MATLAB/Octave 学术接收机） | PocketSDR 是生产级 C，可实时、可回放、带 Web GUI |
| gps-sdr-sim（模拟器，gnss-sim 的兼容对象） | PocketSDR 是接收侧，且其文件输入格式约定（raw + .tag）事实上是 SDR 圈的事实标准之一 |

## 二、总体架构与数据流

系统自上而下分三层：

| 层 | 组成 | 要点 |
|---|---|---|
| 应用层 | 11 个 C exe（app/*/makefile） | pocket_conf/dump/scan（设备）、pocket_acq/trk/snap/calib（接收）、pocket_web（HTTP+WS 全功能 GUI）、convbin/str2str（RTKLIB 衍生） |
| 核心库 | src/ 17 文件 ≈24,700 行（libsdr.a） | sdr_rcv.c 接收机编排（RF→IQ→通道线程→PVT）；sdr_ch.c 捕获/跟踪状态机；sdr_nav.c 导航电文（2.3k 行）；sdr_func.c 相关器/FFT/LPF（AVX2/SSE2 内核）；sdr_code(_gal).c 码库；sdr_fec/ldpc/nb_ldpc.c 译码；sdr_pvt.c PVT（RTKLIB 单点）；sdr_array.c 数字波束/阵列标定；sdr_dev/usb/sdev.c 硬件抽象 |
| 依赖与硬件层 | lib/RTKLIB（源码子集）、lib/pocketfft、lib/SoapySDR（仅头+导入库）；FE_2CH/4CH/8CH 前端 | FE_2CH：EZ-USB FX2LP + AD6643（14b@65M）；FE_4CH：FX3(ARM9) + ADC3282（12b×4@65M）；FE_8CH：FX3 + 1.584G 一次下变频（3-bit 直接采样）；共同 ADF4355 频综 + ADRV6516 VGA + LMX2594；FPGA 全为 Xilinx Spartan-6 家族 |

数据流（doc/algo_desc.md §2.4）：设备/文件 → 每 RF 通道 raw 缓冲 → 1 ms 处理周期（SDR_CYC）→ LPF（可选）→ 数字下变频（LUT 加速）→ 每信号通道线程独立做捕获（FFT 并行码相位）→ 跟踪（FLL→Costas/4Q PLL + 非相干 DLL，最多 106 个相关器）→ 电文解码 → sdr_pvt.c 调 RTKLIB pospri() 出 PVT → NMEA/RTCM3/log/观测值流输出。

## 三、核心 DSP 算法要点（src/ 实测取证）

| 环节 | 实现 | 关键参数（sdr_ch.c） |
|---|---|---|
| 捕获 | FFT 并行码相位，码 FFT 零填充 2N；逐多普勒 bin 相干 1 码周期→非相参累积 | t_acq=20 ms（辅助捕获 100 ms），max_dop=±10 kHz，捕获判决用峰值−均值比换算类 C/N0，门限 34 dB-Hz |
| 载波跟踪 | 先 FLL（dot-cross，宽 10 Hz→窄 5 Hz）1 s 拉入 → 三阶 PLL；数据信号 Costas，导频信号二次码擦除后 4 象限 atan2 相干（t_coh=20 ms） | b_pll=10 Hz |
| 码跟踪 | 非相干 E/L DLL（√E−√L/√E+√L），20 ms 非相干累积，载波辅助码率 | b_dll=0.5 Hz，间距 0.2~0.25 chip |
| 假锁防护 | BOC 加 VE/VL 指 bump-jump（功率比较，BUMP_K=1.3） | 每 T_CN0 检查 |
| C/N0 | 噪声指功率差分式：S=max(|P|²−|N指|², 0.01·N指)，CN0=10log10(S/N指/T)；噪声指在 −120 采样固定偏移（POS_CORR_N） | T_CN0=0.5 s，一阶滤波 FILT_CN0=0.5 |
| 载体锁定 | PLI = Σ(I²−Q²)/Σ(I²+Q²) ≈ cos2φ（Van Dierendonck 平方环） | 门限 0.25，连续 4 窗坏判失锁 |
| 电文 | 2308 行覆盖 LNAV/CNAV/F-NAV/I/NAV/B-C-NUM-D1/D2/D2Q/B-C-NAV-D1、GLONASS 5 型、SBAS 1/3 型、QZSS L1S/L6、NavIC；FEC：卷积(Viterbi)、RS、LDPC(Gallager)、NB-LDPC 新重设计（v0.22） | — |
| 高级特性 | 二次码同步（导频长积分）、E5aQbQ AltBOC 复合、L6 CSK 码域 FFT、天线阵列数字波束成形 + EKF 姿态/逐通道偏差标定（sdr_array.c）、FastReFix 快重捕（v0.22）、快速捕获槽调度 | — |

C/N0 估计器对比（呼应任务⑨结论）：PocketSDR 用噪声指平均功率做 N0 代理（S=(P−N)/N/T），而 FGI 用 −2ch 噪声指功率的时间方差。前者对"目标星自相关泄漏进入噪声指"只有一阶影响（泄漏计入均值，P−N 部分抵消），后者会被 50 bps 比特翻转把常数泄漏随机化成方差、逐星放大偏置（whu60b 实测 FGI 逐星 −0~−5.1 dB）。PocketSDR 的估计器结构天然免疫任务⑨定案的 FGI 偏置机理，适合作为 gnss-sim C/N0 归因的第三方参照。

## 四、应用层、Web UI 与 Python 实现

- 9 个应用：pocket_conf（FE 寄存器/AD9254/LMX2594 配置 + -SAVE 写 flash）、pocket_dump（采集落盘，自动写 .tag 旁车文件）、pocket_scan、pocket_acq、pocket_trk（主力：捕获+跟踪+电文+PVT，输出 NMEA/RTCM3/RINEX/日志）、pocket_snap（无位置解算的快照定位）、pocket_calib（阵列标定）、convbin/str2str（RTKLIB 衍生）。
- 数据源抽象：SDR_DEV_FILE(1)/USB(2)/STR(3)/SOAPY(4) 四类平级，文件是硬件无关的一等公民：sdr_rcv_open_file() → sdr_read_data()，格式支持 INT8/INT8X2/CS8/CS16（int8/int16 交织复 IQ）/RAW8/RAW16/RAW32；.tag 文本旁车（PROG/TIME/FMT/SYS/FS/FO/IQ/BITS），无 tag 时命令行 -f/-fo/-fmt 兜底。
- sample/ 提供 14 个真实采集样例（L1/L2/L5/L6/B1/B3/E1/E5b，4~24 Msps），是纯软回归的免硬件入口。
- pocket_web（2106 行）：自研 mini HTTP + WebSocket 服务器（select 循环，无第三方库），html/ 下 19 个零构建原生 JS 文件；频谱图（2048 点周期图）、通道表、相关分布、星座图、RTKLIB pospri() PVT 状态、轨迹地图全部经 WS JSON 推送，可完全远程操控接收机。
- python/ 21 个脚本：sdr_lib.py 是 C API 的 ctypes 封装；pocket_sdr.py 是独立纯 Python 接收机（Tkinter GUI，含 sdr_rcvr.py 跟踪、sdr_gnsstime.py 纯软件 GPS 授时）——算法可读性最高的参考实现。

## 五、硬件前端（136 份 FPGA 工程的取证）

共同血统：Xilinx Spartan-6 FPGA + Cypress EZ-USB（2CH 用 FX2LP 8051、4CH/8CH 用 FX3 ARM9）+ ADF4355 频率综合器 + LMX2594 第二本振 + ADRV6516 VGA；USB 协议统一为 vendor 请求组（GET_STAT/REG_READ/WRITE/START/STOP/RESET/SAVE）+ 0x86 端点 bulk 流，寄存器表在 lib/cyusb/CyAPI.h 与 src/sdr_dev.c 两侧完全对齐。

| 项目 | FE 2CH | FE 4CH | FE 8CH |
|---|---|---|---|
| ADC | ADI AD6643 14 b 65 Msps ×2 | TI ADC3282 12 b×4 65 Msps（DDR） | 比较器+电阻 ladder 1-bit×8@50 Msps（时间交织→3 b@400 Msps 等效） |
| 下变频 | AD8364 一级正交 | ADL5380 一级正交 | 1.584 GHz 一次下变频（省一级、免镜像） |
| FPGA 资源 | 474/1600 slice (30%) | 4567/9152 (50%) | 4309/9152 (47%) |
| 固件代码量 | 5384 行 Verilog + 23 KB C（RAW8） | 3622 行 + 59 KB C（RAW16） | 5199 行 + 65 KB C（RAW16I/RAW32，含 256 项 64 b 查表解码） |

8CH 的"3-bit"是无传统 ADC 的比较器阵列采样（时间交错 8×1bit），配套 2*256 项 LUT 把 2 字节打包还原 int8——这是它便宜且省芯片的代价：动态范围受限，所以接收端才设计 RAW16/RAW32 两种解包和增益标定工具链。

## 六、测试体系与构建

- 自研轻量框架（test/src/test_sdr.h，36 行宏），共 12 个测试文件 ≈14888 行、573 个 ASSERT、90 个 TEST；硬件模块用 4 个 *_stub.c 隔离——单元测试全离线（仅 test_sdr_dev 用 /sample）。
- make -C test/utest test 一条命令回归；test_sdr_perf 为性能基准（FFT 后端选择、多普勒 20 GHz 精度、相关器对齐）。
- 集成回归脚本 test/script/run_integration_test.sh：bin/*.exe + sample/*.bin 跑 FFT/AVX 双后端、RTCM 往返、Web WS/REST 冒烟。
- 构建：纯 makefile（MSYS2 UCRT64 官方环境），三条依赖红线（C99、公开 API 冻结、无测试专用 #ifdef）；bin/ 预编译产物全部是 Windows UCRT64 exe，Linux/macOS 须自 make install。
- v0.22 演进脉络（HEAD 77a85b0）：NB-LDPC 译码器整体重设计（分层调度的 EMS min-sum，纠错增益 +1.6~1.9 dB、速度 7~17×）、CSK 并行码相位捕获（L6 无导频信号灵敏度提升，对应 IPNTJ 2022 论文）、AltBOC 实现（E5aQbQ 复用 E5aIbI 乘积码+符号擦除）、天线阵列（pocket_array/pocket_calib、EKF 姿态+偏差标定）、FastReFix 快速重捕、Web UI 与快照定位（pocket_snap）。

## 七、与 gnss-sim 的对接要点

1. 格式即插即用：gnss-sim 输出（int16 交织 I/Q、25 Msps、复基带）= PocketSDR 的 CS16 格式；SDR_DEV_FILE 是正式数据源，无需任何模拟器/硬件即可回放。
2. 本地可执行性：仓库自带 bin/*.exe 是作者 MSYS2 UCRT64 构建、硬依赖 SoapySDR.dll + AVRT.dll（本机没有，直接运行 exit 127）。本次已用本机 winlibs GCC 16.2 以"源码 + 测试 stub"配方编出硬件无关静态版 local_build/pocket_trk_local.exe（7.7 MB，链接 lib/win32 的 librtk.a/libpocketfft.a，补 -lwinmm）。
3. 第三方互验价值：PocketSDR 的 C/N0（功率差分式）、PVT（RTKLIB pospri）、跟踪（20 ms 非相干 DLL/1 ms Costas）与 gnss-sim 内置 coh 跟踪解、FGI-GSRx（20 ms 相干 + 方差式 C/N0）三者算法独立，可三角互验；尤其其 C/N0 估计器不受 FGI 的"比特翻转×噪声指自泄漏方差污染"影响（任务⑨定案机理），能给 C/N0 归因提供独立基准。

## 八、风险与注意事项

- bin/ 预编译 exe 在本机不可直接运行（缺 SoapySDR.dll/AVRT.dll）；自编译时 makefile 的 -Ilib/cyusb/inc 路径不存在（cyusb 实际无 inc/，utest makefile 才有），且需 -lwinmm。
- 核心库非线程安全点是共享 IF 缓冲（1 ms 周期读写 rp/wp），分析时注意 sdr_mutex_t 边界（doc/algo_desc.md §2.10）。
- FE 固件源码在 FE_*/Firmware/（README 目录树只写了 FW/FW.zip 别名，实际目录名不同）；FE_8CH 的 AD9523 只在原理图（FE_8CH/Docs/sch.pdf），不在 BOM。
- 仓库根 CLAUDE.md 与 AGENTS.md 内容逐字相同（双工具兼容）；test/utest/build/ 有历史构建残留勿误用。
- .tag 文件缺失时 fs/fo 全靠命令行，配错会静默产生错误相关峰——离线处理建议始终补 tag 或显式 -f/-fo/-fmt。
- -fo 接收 MHz、-f 接收 MHz，但 -fi/-d（pocket_acq）接收 Hz：单位不统一，把 1575420000 当 Hz 传给 pocket_trk -fo 会让中频变成 −1.6e15 Hz、捕获静默全灭（本会话实测最大坑，见第九章）。
- 捕获调度器（update_srch_ch）在 IF 缓冲 >90% 时停摆：pocket_trk 文件回放必须用近实时节奏 -tscale 1，不能 -tscale 1000 全速灌盘；默认 LOG_LEVEL=3 不打印捕获判决，需调级或直接用快照工具 pocket_acq。

## 九、冒烟实测与端到端互验

场景：out/20261113T033315803665/gpssim.bin（Tampere 60.182537°N/24.82826°E/47.248 m，25 Msps CS16 复基带，60 s，12 星 GPS L1 C/A：PRN 4/5/9/11/12/18/20/25/26/28/29/31，awgn 噪声 SNR −18.33 dB，atmosphere off / sv_clock on）。

回放命令：

```
local_build/pocket_trk_local.exe -sig L1CA \
  -prn 4,5,9,11,12,18,20,25,26,28,29,31 \
  -fmt CS16 -f 25 -fo 1575.42 -IQ 2 \
  -tscale 1 -ti 10 -log <log> -nmea <nmea> \
  D:/workbuddy/GNSSSignal/gnss-sim/out/20261113T033315803665/gpssim.bin
```

结果汇总：

| 指标 | 值 |
|------|----|
| 捕获 | 12/12 星 SIGNAL FOUND（C/N0 38.9~45.9 dB-Hz，逐星 2 s 内完成） |
| 跟踪锁定 | LOCK 12/12 |
| 电文 | $NAV 各星子帧 3（240 字）解码成功，TOW 有效 |
| 定位 | 9/12 星 FIX（GGA fix=1） |
| 收敛位置（23:21:17） | 60.18252216°N / 24.82826244°E / 椭高 35.796 m |
| 定位误差 | 水平 1.66 m（N −1.65 / E +0.14），垂直 −11.45 m（根因见第十章） |

逐星 C/N0（dB-Hz，与任务⑨真值口径对照）：

| PRN | G4 | G5 | G9 | G11 | G12 | G18 | G20 | G25 | G26 | G28 | G29 | G31 | 均值 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PocketSDR | 39.8 | 40.9 | 38.9 | 42.1 | 40.2 | 40.0 | 42.8 | 45.1 | 43.2 | 45.1 | 45.9 | 43.8 | ≈42.0 |

均值比 FGI-GSRx 的 41.676 dB-Hz 高 0.3 dB，量级一致。

![图2 PocketSDR 逐星 C/N0 与 FGI-GSRx 均值对照](D:/workbuddy/GNSSSignal/gnss-sim/output/pocketsdr_verify_20261113T223203/stage2/intermediate/fig_cn0.png)

排障实录（本会话踩坑，均非算法问题，是参数/调度）：

1. -fo 单位是 MHz：源码 pocket_trk.c L254 `for j: fo[j]*=1e6`。最初按习惯传 `-fo 1575420000`（Hz）→ 相关器里 fi 变成 −1.5754e15 Hz（调试版打印实证 `fi=-1575418424580000`），载波混频完全错位 → 相关峰淹没在噪声（Ppk≈row_ave、捕获 C/N0 恒为噪声底 31 dB）。改 `-fo 1575.42` 后立即 12/12 锁定。
2. -tscale 节流语义（sdr_rcv.c L1568 `sleep(ix − elapsed·tscale)`）：tscale=1 为实时节奏（正常）；tscale=0 退化为每周期睡 ix 毫秒（比实时慢，非"无节流"）；tscale=1000 全速读盘会让 IF 环形缓冲常 >90%，而 update_srch_ch（L1447）在 buff_use > MAX_BUFF_USE(90%) 时直接 return 不启动任何捕获任务 → 表现为 SRCH 计数在涨但永远 0 锁定、且默认 LOG_LEVEL=3 下连"NOT FOUND"日志都不打印（该日志是 level-4）。诊断需用 tscale≈1（实时/近实时）或临时把默认日志级别调到 4 才能看到 SIGNAL NOT FOUND (cn0) 判决值。

方法学价值：PocketSDR 的功率差分式 C/N0 与 FGI 的方差式（任务⑨定案：20 ms 相干块 × 50 bps 比特翻转把 −2ch 自相关泄漏随机化污染 noiseVariance）结构完全独立，实测两者对本场景给出同一量级（42.0 vs 41.7 dB-Hz），佐证"内置相干跟踪解 ≈ PocketSDR ≈ FGI 名义值、FGI 的 −3.2 dB 主要是其估计器 artifact 而非 CDMA 互扰物理损失"的归因结论。

## 十、垂直误差 −11.45 m 根因判定（判决性 A/B 实验）

现象：冒烟解算水平 1.66 m、垂直 −11.45 m（椭高 35.796 vs 真值 47.248），"垂直远大于水平"。

根因：sdr_pvt.c update_sol()（L1126-1131）把 RTKLIB prcopt 硬编码为 `opt.ionoopt = IONOOPT_BRDC`（Klobuchar 广播电离层模型）+ `opt.tropopt = TROPOPT_SAAS`（Saastamoinen 对流层模型）。而本场景 atmosphere off——引擎侧 iono_abs = tropo_abs = 0（backend/synth/engine.py L230），IQ 里从未注入任何大气延迟。PocketSDR 作为独立接收机照扣不误，等于给每颗星伪距凭空减去一段不存在的仰角相关延迟：公共部分被接收机钟差吸收，仰角相关残差被 LS 映射到垂直方向。这正是任务⑨"只去除引擎实际注入的东西"铁律的镜像（引擎不注入、接收机却扣）——Saastamoinen 无需电文参数、仅凭测站坐标+卫星仰角必算出非零值，故必错扣；Klobuchar 则因本场景 BRDC 的 GPSA/GPSB 参数非零（GPSA 2.5e-8…、GPSB 1.3e5…，引擎把 header 电离层参数无条件写进 LNAV SF4 页18）也在错扣。

判决性证据（A/B 编译对比，同一 gpssim.bin、同一命令行，真值椭高 47.248 m）：

| 变体（改 update_sol） | 椭高 (m) | 垂直误差 | 水平误差 |
|---|---|---|---|
| 基线：IONOOPT_BRDC + TROPOPT_SAAS | 35.796 | −11.45 m | 1.66 m |
| 仅 IONOOPT_OFF（对流层仍开） | 38.455 | −8.79 m | — |
| 仅 TROPOPT_OFF（电离层仍开） | 44.335 | −2.91 m | — |
| 双 OFF | 47.306 | +0.06 m | 0.18 m |

![图1 A/B 编译实验垂直误差对比（数据源：上表）](D:/workbuddy/GNSSSignal/gnss-sim/output/pocketsdr_verify_20261113T223203/stage2/intermediate/fig_ab_vertical.png)

归因：垂直 −11.45 m ≈ 对流层假扣 −8.5 m + 电离层假扣 −2.7 m（双 OFF 残差 +0.06 闭合，余 ~0.2 m 为 LS 弱耦合）。理论自洽：Saastamoinen 斜路径 2.3 m(天顶)→8.75 m(el=15°)，仰角相关部分 ~6 m 主导垂直；RTKLIB EL_MASK=15° 解释了 9/12 FIX（剔 3 颗低仰角星），但垂直误差主因是大气错扣而非星数（双 OFF 用同 9 星即收敛到 0.06 m）。

验证工具：local_build/pvt_both_off.exe / pvt_iono_off.exe / pvt_tropo_off.exe（源码临时改后已 git 还原，仓库 src/sdr_pvt.c 保持作者原样）。

## 十一、结论与用法启示

PocketSDR 是当前开源生态中覆盖面最全、工程化最完整的 GNSS SDR 参考实现：硬件（三款 Spartan-6 前端，含无 ADC 的 8CH 激进方案）、固件、C 核心库（捕获/跟踪/电文/FEC/PVT 全链路 + 现代信号 AltBOC/CSK/NB-LDPC）、零依赖测试体系与纯 Python 孪生实现一应俱全，且作者以 RTKLIB 的 PVT 内核为其兜底。

对 gnss-sim 项目而言，它是继 FGI-GSRx 之后最有价值的第三方互验接收机：文件回放路径官方支持、CS16 格式与仿真输出逐字节兼容、C/N0 估计器结构独立。本地编译与端到端互验均已完成（12/12 星锁定、9 星 FIX、水平误差 1.66 m、逐星 C/N0 均值 42.0 dB-Hz 与 FGI 的 41.7 一致），可直接用于复核内置解与 FGI 的结论。

用法启示：PocketSDR 的 PVT 正确性完全依赖"场景大气 ↔ 接收机大气模型"匹配——用于仿真互验时，若 atmosphere off 须自备 IONOOPT_OFF/TROPOPT_OFF 编译版（或改 sdr_pvt.c 暴露命令行开关），否则会把 RTKLIB 内置大气模型误差误算到仿真器/接收机头上。这与任务⑨对 FGI/内置接收机的大气政策铁律是同一件事的第三方印证。

## 附录：复现命令与产物

- 正式回放产物：`PocketSDR/local_build/pocket_trk_local.exe`（硬件无关静态版，7.7 MB）。
- 诊断版：`pocket_trk_dbg.exe`（含逐星捕获 P_sum 仪表，临时补丁、不纳入 git）。
- 快照捕获工具：`app/pocket_acq/pocket_acq_new.exe`——不经缓冲/调度直读文件，秒出逐星 C/N0/DOP/COFF，是排查捕获问题的首选利器：

```
pocket_acq_new.exe -sig L1CA -prn <prn列表> -fmt CS16 -f 25 -tint 20 -toff 5000 <file>
```

（注意 -tint/-toff 单位毫秒、-nz 关零填充、-d 多普勒窗单位 Hz。）

- A/B 验证三变体：`pvt_both_off.exe` / `pvt_iono_off.exe` / `pvt_tropo_off.exe`。
- 冒烟日志：/tmp/pk_ok.txt（基线状态行）、/tmp/bo.txt、/tmp/to.txt、/tmp/io.txt（A/B 三组）、/tmp/pk_ok_nmea.txt（174 行 NMEA）。
