# 桌面新版程序 IQ 的 PocketSDR 第三方互验（60s 无大气）

- 日期：2026-11-18 | 生成链路：`desktop.core.bridge`（桌面程序内核，与已打包 exe sha256/selftest 逐位等价）
- 场景：Tampere 60.182537N 24.82826E 椭高47.248 | 2023-09-28T23:20 UTC 60s @25 MHz int16 | 纯 GPS 12 星（4,5,9,11,12,18,20,25,26,28,29,31）| atmo iono/tropo **off**、sv_clock on | whu_afzero2 星历 | SNR −18.33 dB | seed 2281271
- 产物：`out/20261118T104257507553/`（gpssim.bin 6,000,000,000 B，sha256 `88aebd4d5b0ab7442b0f137158bd50e94df7977420889a8ef359fd7f8989b84e`）
- 生成耗时 2m14s（桌面桥接，native 引擎）

## 结果（PocketSDR 回放，同命令行 −tscale 1 −ti 1）

| 口径 | 可执行 | 解数 | 用星 | 水平 RMS | 垂直 RMS（均值） | 锁定 | C/N0 |
|---|---|---|---|---|---|---|---|
| 原版（BRDC/SAAS 硬编码） | local_build/pocket_trk_local.exe | 29 | 9 | 1.529 m | 11.510 m（−11.504） | 12/12 | 40.4~45.5 dB-Hz |
| 场景匹配版（IONO/TROPO OFF） | local_build/pvt_both_off.exe | 29 | 9 | **0.229 m** | **0.432 m（−0.036）** | 12/12 | 40.4~45.5 dB-Hz |

内置侧同 run 快照解算（桌面程序 /api/receiver 同内核）：error_m = 6.46，PDOP 1.399，12 星全用。
（注：PocketSDR GGA alt 为正高，统计已 +大地水准面差距 17.999 m 归算椭高。）

## 对照历史（同参数 whu60b 轮，2026-11-13，WebUI 生成）

| 指标 | 11-13 历史 | 本次（桌面生成） | 一致性 |
|---|---|---|---|
| 原版水平/垂直 RMS | 1.66 / −11.45 m | 1.529 / 11.510(−11.504) m | 吻合 |
| both-off 水平/垂直 RMS | 0.18~0.23 / +0.06~0.45 m | 0.229 / 0.432(−0.036) m | 吻合 |
| 锁定 | 12/12（38.9~45.9 dB-Hz） | 12/12（40.4~45.5） | 吻合 |
| #NAV=8、#ERR=#LOL=0 | 是 | 是 | 吻合 |

## 结论

1. **桌面新版程序生成的 IQ 与 Web 版统计同构**：第三方接收机（PocketSDR）锁定、电文解码、精度三口径全部复现历史基线，桌面化改造未引入任何信号质量退化。
2. **"只改正引擎实际注入的"铁律再次成立**：atmo-off 场景下原版程序假扣 Saastamoinen+Klobuchar 造成 −11.5 m 垂直偏置；匹配版（both-off）去假扣后垂直 −0.04 m。
3. 匹配版 **水平 0.23 m / 垂直 0.43 m 亚米级**，与内置快照 6.46 m（25 MHz 单频快照口径）、历史 coh 跟踪 ~0.2 m 三口径互洽。

## 素材

- 回放产物：`.workbuddy/pocket_perf_20261118/{orig,bothoff}/`（f=log+nmea、stdout.txt、.pocket_navdata.csv）
- 脚本：`.workbuddy/desktop_gen60.py`（桌面链路生成+快照）、`.workbuddy/pocket_perf_replay.sh`（双回放）、`.workbuddy/pocket_perf_stats.py`（GGA 统计）
