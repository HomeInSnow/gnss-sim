# PocketSDR 使用手册（gnss-sim 互验场景版）

| 项目 | 内容 |
|------|------|
| 适用对象 | D:\workbuddy\GNSSSignal\PocketSDR（GitHub tomojitakasu/PocketSDR，本地 HEAD 77a85b0，版本 0.22） |
| 适用场景 | gnss-sim 仿真 IQ 文件的第三方接收机互验（文件回放为主）；亦覆盖构建、快照诊断与 Web UI |
| 整理日期 | 2026-11-16 |
| 取证基础 | 本会话本地编译与多轮回放实测（12/12 锁定、9/12 FIX 复现）+ 三态配置实验定量结论 + README/app/python 目录实地核对 |

## 执行摘要

- PocketSDR 提供实时接收、文件回放、Web 交互三种形态；对 gnss-sim 互验而言，核心入口是**文件回放** `pocket_trk`（读 CS16/CS08 等原始 IQ 文件）与**秒级快照诊断** `pocket_acq_new`。
- 本机（Windows + winlibs GCC）已验证的编译配方一次产出硬件无关静态版 `pocket_trk_local.exe`：关键点为 `-DWIN32`（否则 sys/select.h 编译挂）与三个硬件 stub 替换设备层。
- 文件回放三大铁律（全部实测踩过）：`-fo` 单位是 **MHz**；`-tscale 1` 必带（全速读盘会让捕获调度停摆、锁不住星）；输入按 raw + `.tag` 约定（缺 .tag 提示 tag file open error 但可从文件头播）。
- PVT 配置必须与场景注入匹配（三态实验定量定案）：`atmosphere off` 场景须用 IONOOPT_OFF+TROPOPT_OFF 编译版（3D 0.22 m，错扣大气则 11.41 m）；`sv_clock=true` 场景卫星钟差改正必须保留（错关致 3D 4.65 m）。改动点集中在 `src/sdr_pvt.c update_sol()` 一个函数。

## 一、形态与工具总览

PocketSDR 仓库 `app/` 下共 10 个工具目录（+ makefile），`make` 即出全部 11 个 exe，无外部依赖（FFT 自带 pocketfft 头文件库）：

| 工具 | 用途 | 互验常用度 |
|---|---|---|
| pocket_trk | SDR 跟踪 + PVT 解算（核心，实时/文件双用） | 主用 |
| pocket_acq（pocket_acq_new.exe） | 快照式捕获分析，秒出逐星 C/N₀/多普勒/COFF | 排障利器 |
| pocket_snap / pocket_scan / pocket_dump / pocket_conf / pocket_calib | 快照、扫频、转储、配置、校准 | 辅助 |
| pocket_web | Web UI 接收机（见第五节） | 演示 |
| str2str / convbin | 流转发、RTCM 转 RINEX（RTKLIB 沿用） | 按需 |

另有 `python/` 纯 Python 模块组（pocket_trk.py、pocket_acq.py、pocket_sdr.py、sdr_ch.py、sdr_nav.py、sdr_ldpc.py 等），与 C 侧链路同构，适合读源码学算法。

## 二、本地构建（本机已验证配方）

Windows（Git Bash + winlibs GCC 16.2，路径 `D:\workbuddy\tools\mingw64`）一条命令产出硬件无关静态版：

```
cd /d/workbuddy/GNSSSignal/PocketSDR
/d/workbuddy/tools/mingw64/bin/g++.exe -O3 -w -std=c++20 -x c++ -DWIN32 \
  -Isrc -Ilib/RTKLIB/src -Ilib/cyusb -Ilib/pocketfft \
  app/pocket_trk/pocket_trk.c \
  src/sdr_pvt.c src/sdr_array.c src/sdr_ch.c src/sdr_cmn.c src/sdr_code.c \
  src/sdr_code_gal.c src/sdr_conf.c src/sdr_fec.c src/sdr_func.c src/sdr_ldpc.c \
  src/sdr_nav.c src/sdr_nb_ldpc.c src/sdr_rcv.c src/sdr_web.c \
  test/src/sdr_dev_stub.c test/src/sdr_sdev_stub.c test/src/sdr_usb_stub.c \
  lib/win32/librtk.a lib/win32/libpocketfft.a \
  -lpthread -lws2_32 -lwinmm -static -o local_build/pocket_trk_local.exe
```

要点：

1. `-DWIN32` 必带，否则编译在 `sys/select.h` 挂掉。
2. `test/src/` 三个 stub（sdr_dev/sdr_sdev/sdr_usb）替换 USB/设备硬件层，产出的 exe 不依赖真实前端即可回放文件。
3. 要改 PVT 行为（见第六节），把 `src/sdr_pvt.c` 换成修改版文件、其余不动即可——本会话的 4 个 A/B 变体就是这么出的。
4. 预编译库 `lib/win32/` 提供 librtk.a（RTKLIB 全量对象）与 libpocketfft.a，Linux 侧有对应 .so。
5. 作者原版 Linux `make` 路径同样可用（一次出 11 个 exe）。

## 三、文件回放 pocket_trk（主用法）

实测命令模板（对 gnss-sim 场景 60 s/12 星 CS16/25 Msps）：

```
local_build/pocket_trk_local.exe \
  -sig L1CA -prn 4,5,9,11,12,18,20,25,26,28,29,31 \
  -fmt CS16 -f 25 -fo 1575.42 -IQ 2 \
  -tscale 1 -ti 10 \
  -log run.log -nmea run.nmea \
  path/to/gpssim.bin
```

参数速查：

| 参数 | 含义 | 实测注意点 |
|---|---|---|
| `-fmt CS16` | 8bit I / 8bit Q 复数交织格式 | 与 gnss-sim int8 输出逐字节兼容 |
| `-f 25` | 采样率 25 Msps | 必须与仿真 fs 一致 |
| `-fo 1575.42` | RF 中心频率，**单位 MHz** | 写成 Hz 直接废 |
| `-IQ 2` | 交织 IQ 存放 | — |
| `-tscale 1` | 按实时速率灌入 | **必带**：全速读盘会让捕获调度 update_srch_ch 停摆、锁不住星 |
| `-ti 10` | 定位输出间隔 10 s | 60 s 场景得 6 条 FIX 行 |
| `-log path` / `-nmea path` / `-rtcm path` | 输出流，可重复至多 8 路 | 建议落仓内路径；$POS 行含 lat/lon/椭高/ns/UR |
| `-prn 列表` | 指定跟踪 PRN | 与仿真星表一致 |
| `-NO_SYNC` / `-fd dopp` | 关符号同步 / 多普勒初值 | 按需 |

输入文件约定：原始 IQ 文件 + 同名 `.tag` 尾部标签（gps-sdr-sim 系产物的 SDR 圈事实标准）。无 .tag 会打印 `tag file open error` 并从文件头开始播，互验可用。

输出解读：stdout 的 LOCK 行给出逐星锁定秒数、C/N₀、COFF、多普勒、NAV 字数；状态行 `ns/nsat FIX LOCK: x/12` 为解算健康度。60 s/12 星 SNR −18.33 dB 场景的合格基线：12/12 锁定、9/12 FIX（剔 3 颗低仰角星系 RTKLIB EL_MASK=15° 所致，属正常）。

## 四、快速快照诊断 pocket_acq_new

不经缓冲/调度直读文件，秒出逐星 C/N₀、多普勒、COFF，是排查"锁不住/星数少"的首选：

```
app/pocket_acq/pocket_acq_new.exe -sig L1CA -prn <prn列表> \
  -fmt CS16 -f 25 -tint 20 -toff 5000 <file>
```

注意：`-tint/-toff` 单位毫秒、`-nz` 关零填充、`-d` 多普勒窗单位 Hz。与 pocket_trk 的分工：pocket_acq_new 回答"信号在不在、多强"，pocket_trk 回答"能不能跟踪并解出位置"。

## 五、Web UI（pocket_web）与 Python 孪生

Web 形态（README 原文用法，实时接收机演示）：

```
cd <install_dir>/bin
sudo ./pocket_web -web 8080
```

浏览器打开 `http://localhost:8080/`。接收机初始为停止态：在 Input / Output / Signal Options 页设置输入源、输出流与信号后按 Start；设置在停止与退出时自动保存、下次恢复，加 `-start` 可直接带设置自启。局域网他机访问用 `sudo ./pocket_web -web 0.0.0.0:8080`——注意官方原文警告：该界面**无认证、无加密**，仅限可信网络。

`python/` 目录是 C 链路的纯 Python 孪生（pocket_trk.py/pocket_acq.py/sdr_ch.py/sdr_nav.py/sdr_ldpc.py 等），适合理解捕获-跟踪-电文算法细节，不适合当生产工具。

## 六、与 gnss-sim 互验的配置匹配要点（定量定案）

互验的前提是"接收机改正 ↔ 场景注入"逐维对齐。三态编译实验（同一 12 星场景、同一命令行，仅改 `update_sol()`）给出定量结论：

| 变体 | 大气改正 | 钟差改正 | 3D 误差 | FIX/星 | LOCK |
|---|---|---|---|---|---|
| 基线（作者原版） | 开（错扣） | 开 | 11.41 m | 9/12 | 12/12 |
| 场景匹配版 | 关 | 留 | **0.22 m** | 9/12 | 12/12 |
| 错关钟差对照 | 关 | 关 | 4.65 m | 9/12 | 12/12 |

操作要点：

1. **大气**：场景 `atmosphere off` 时须用 IONOOPT_OFF+TROPOPT_OFF 编译版——改 `src/sdr_pvt.c` update_sol()（L1129-1130）两行后按第二节配方重编即可（现成产物 `local_build/pvt_both_off.exe`）。假扣的 Saastamoinen+Klobuchar 仰角相关延迟会被最小二乘映射到垂直方向（−11.45 m 根因，详见互验报告第十章）。
2. **卫星钟差**：场景 `sv_clock=true` 时改正**必须保留**。afzero2 星历下接收机 dts＝纯相对论偏心率项（实测 11 星振幅 mean 0.45 m、max 1.02 m/星），与注入真值一致；错关会把该项全量留在伪距上，per-star 确定性偏置经 9 星 LS 几何放大成 3D 4.65 m 固定方向偏差（对照变体 `pvt_satclk_off.exe`）。
3. **不要动的**：EL_MASK=15°（只决定剔星数 9/12，非精度因素）、RAIM-FDE posopt[4]=1（无粗差可剔，中性）。
4. 判读：三变体 LOCK 12/12、FIX 9/12 完全一致——配置错配是纯 PVT 层系统偏差，与捕获/跟踪无关；如果连锁定都不正常，先回第四节查信号本身。

## 七、常用命令速查

```
# 建（第二节配方省略号处换变体源）
g++.exe ... -o local_build/<name>.exe

# 秒级快照
pocket_acq_new.exe -sig L1CA -prn <列表> -fmt CS16 -f 25 -tint 20 -toff 5000 <file>

# 端到端回放（互验标准姿势）
pocket_trk_local.exe -sig L1CA -prn <列表> -fmt CS16 -f 25 -fo 1575.42 \
  -IQ 2 -tscale 1 -ti 10 -log <log> -nmea <nmea> <gpssim.bin>

# 场景匹配版回放（atmosphere off 场景）
pvt_both_off.exe  <同上参数>

# 真值统计（本仓库自带）
.venv/Scripts/python.exe output/pvt_config_exp_20261115/analyze.py <目录>
```

## 附录：产物与复现索引

- 本机可用 exe：`PocketSDR/local_build/`（pocket_trk_local.exe 正式；pvt_both_off / pvt_iono_off / pvt_tropo_off / pvt_satclk_off.exe 为配置实验变体；pocket_trk_dbg/agc/log4.exe 为诊断变体）。
- 三态实验全量数据与复现：`output/pvt_config_exp_20261115/`（bl2/bo2/sco 三套 log+nmea+stdout、analyze.py、results.md）。
- 深度分析与根因取证：`output/pocketsdr_verify_20261113T223203/`（《PocketSDR 深入分析与 gnss-sim 第三方互验报告》docx，含第十二章三态实验）。
- 互验冒烟场景：`out/20261113T033315803665/gpssim.bin`（Tampere 12 星，6 GB，60 s，CS16/25 Msps，真值 60.182537°N 24.82826°E 椭高 47.248 m）。
- Web UI 用法出处：PocketSDR README.md L540-560（pocket_web -web 8080）。
