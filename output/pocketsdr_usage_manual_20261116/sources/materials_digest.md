# 素材登记（PocketSDR 使用手册，2026-11-16）

组织稿所有数字与命令均出自下列已验证来源，逐条登记出处。凡未列出的一律不写入。

## 源 A：PocketSDR 仓库实地实物（本会话 ls / README 复读）

- `PocketSDR/app/` 目录实测含 10 个工具目录 + makefile：convbin、pocket_acq、pocket_calib、pocket_conf、pocket_dump、pocket_scan、pocket_snap、pocket_trk、pocket_web、str2str。
- README.md L540-560 原文（Web UI 用法）：
  - `$ sudo ./pocket_web -web 8080`（于 `<install_dir>/bin`），浏览器开 `http://localhost:8080/`；
  - "The receiver starts stopped: set the input source, output streams and signals in the Input, Output and Signal Options pages, and press Start."；
  - 设置停止/退出时保存、下次恢复，`-start` 直接带设置自启；
  - 他机访问：`sudo ./pocket_web -web 0.0.0.0:8080`，原文警告 "the interface is unauthenticated and unencrypted"。
- `PocketSDR/python/` 实测文件：pocket_trk.py、pocket_acq.py、pocket_sdr.py、pocket_snap.py、pocket_array.py、pocket_plot.py、pocket_psd.py、sdr_array.py、sdr_ch.py、sdr_ch_plot.py、sdr_code.py、sdr_code_gal.py、sdr_fec.py、sdr_func.py、sdr_ldpc.py、sdr_nav.py、sdr_nb_ldpc.py、fftw_wisdom.py（纯 Python 模块组）。
- `PocketSDR/app/pocket_acq/` 实测：pocket_acq.c（作者原版）+ pocket_acq_new.exe（本会话自建）。
- `PocketSDR/lib/win32/` 实测：librtk.a、librtk.so、libsdr.a、libsdr.so、libpocketfft.a、libpocketfft.so。
- `PocketSDR/local_build/` 实测 exe：pocket_trk_local.exe（正式）、pocket_trk_dbg/agc/log4、pvt_both_off/pvt_iono_off/pvt_tropo_off/pvt_satclk_off.exe。

## 源 B：本机编译配方（本会话实跑成功，产 pvt_satclk_off.exe 7,825,486 字节）

- g++ 路径 `/d/workbuddy/tools/mingw64/bin/g++.exe`；
- 关键项：`-O3 -w -std=c++20 -x c++ -DWIN32`、`-Isrc -Ilib/RTKLIB/src -Ilib/cyusb -Ilib/pocketfft`、链接 `lib/win32/librtk.a lib/win32/libpocketfft.a -lpthread -lws2_32 -lwinmm -static`；
- 源集：app/pocket_trk/pocket_trk.c + src/sdr_*.c（14 个，含 sdr_pvt.c 或其变体）+ test/src/{sdr_dev,sdr_sdev,sdr_usb}_stub.c；
- 坑：缺 `-DWIN32` → `sys/select.h` 编译挂。

## 源 C：回放命令（本会话实跑，12/12 锁定、9/12 FIX 复现）

```
local_build/pocket_trk_local.exe -sig L1CA -prn 4,5,9,11,12,18,20,25,26,28,29,31
  -fmt CS16 -f 25 -fo 1575.42 -IQ 2 -tscale 1 -ti 10
  -log <log> -nmea <nmea> <gpssim.bin>
```
- pocket_trk.c 参数解析实测：`[-NO_SYNC] [-fd dopp] [-log path] [-nmea path] [-rtcm path]`，-nmea/-log/-rtcm 可重复（1.11 版起至多 8 输出流）。
- 铁律（本会话实测定案）：`-fo` 单位 MHz；`-tscale 1` 必带（全速读盘 update_srch_ch 停摆锁不住星）；无 .tag 提示 "tag file open error" 仍可从头播。
- pocket_acq_new（报告附录取证）：`-sig L1CA -prn <列表> -fmt CS16 -f 25 -tint 20 -toff 5000 <file>`；-tint/-toff 毫秒、-nz 关零填充、-d 多普勒窗 Hz。

## 源 D：三态实验定量（output/pvt_config_exp_20261115/results.md，已 commit 17fe09e）

- 三态表：baseline(大气开+钟差开) 3D 11.41 m（N −1.457/E +0.095/U −11.314）；场景匹配版(大气关+钟差留) 3D **0.22 m**（N −0.004/E −0.094/U +0.199）；错关钟差(大气关+钟差关) 3D **4.65 m**（N +3.159/E +2.414/U +2.370）；三变体 FIX 9/12、LOCK 12/12 一致。
- 真值 Tampere 60.182537°N/24.82826°E/椭高 47.248 m；场景 meta：atmosphere off、sv_clock true。
- 相对论项振幅：BRDC_2023271_whu_afzero2.rnx 11 星 mean 0.45 m / max 1.02 m（PRN25 e=0.0112），公式 2√μ·F·e·√A，F=4.442807633e-10 s/m^0.5。
- 配置改动点：src/sdr_pvt.c update_sol() L1126-1134（IONOOPT_BRDC/TROPOPT_SAAS 硬编码、EL_MASK=15.0、posopt[4]=1）。
- satclk_off 抵消依据：pntpos.c L311 残差 `P-(r+dtr-CLIGHT*dts[i*2]+dion+dtrp)` → 预减 `P -= CLIGHT*dts[i*2]`（satposs te_ph=obs[0].time、EPHOPT_BRDC 复刻）。

## 源 E：互验报告既有取证（output/pocketsdr_verify_20261113T223203）

- 定位：RTKLIB 作者 T. TAKASU 主导，BSD 2-Clause，make 即出全部 11 个 exe（无外部依赖，FFT 自带 pocketfft）。
- CS16 与 gnss-sim int8 输出逐字节兼容；SNR −18.33 dB 场景 12/12 锁定正常。
- 9/12 剔星系 RTKLIB EL_MASK=15° 所致（报告第十章）。

## 勘误（相对上一轮口头答复，以磁盘实物为准）

- Web UI 是 **pocket_web**（app/pocket_web/、bin/pocket_web，README L544 原文），不是「pocket_shell」。
- Python 侧是 `python/` 目录多文件模块组（pocket_trk.py 等），不是单文件「pocketsdr.py」。
