# PocketSDR PVT 配置-场景匹配实验（2026-11-15）

## 实验目的
按 whu60b/Tampere 冒烟场景的仿真设置（`meta.json: atmosphere ionosphere/troposphere=off, sv_clock=true`）
调整 PocketSDR `update_sol()`（src/sdr_pvt.c L1126-1134）的 PVT 配置，验证：
1. 大气改正必须**关**（引擎未注入大气延迟，接收机扣减即造假）；
2. 卫星钟差改正必须**留**（引擎 sv_clock=true 注入了真值钟差，接收机广播 af=0 与注入一致，须匹配改正）——
   以「错关钟差」对照变体实证其方向性。

## 数据与方法
- 信号：`out/20261113T033315803665/gpssim.bin`（6 GB，CS16/25 Msps/60 s/12 星
  PRN 4,5,9,11,12,18,20,25,26,28,29,31，Tampere 真值 60.182537°N 24.82826°E 椭高 47.248 m，SNR −18.33 dB）。
- 星历：`data/rinex/BRDC_2023271_whu_afzero2.rnx`（af0/af1/af2 全零实测确认；TGD 清零）。
- 回放：`pocket_trk` 系列，`-sig L1CA -fmt CS16 -f 25 -fo 1575.42 -IQ 2 -tscale 1 -ti 10`。
- 变体实现（`PocketSDR/local_build/`）：
  - `pocket_trk_local.exe`＝baseline：作者原版（IONOOPT_BRDC + TROPOPT_SAAS + 钟差改正）。
  - `pvt_both_off.exe`：IONOOPT_OFF + TROPOPT_OFF，钟差改正保留。
  - `pvt_satclk_off.exe`（源 `sdr_pvt_satclk_off.c`）：IONOOPT_OFF + TROPOPT_OFF，
    并在 pntpos 前对每条 `obs[i].P[0] -= CLIGHT*dts[i*2]`（dts 由与 pntpos 完全相同的
    `satposs(teph=obs[0].time, EPHOPT_BRDC)` 重算）抵消内部钟差改正。
    依据：pntpos.c L311 残差 `v=P-(r+dtr-CLIGHT*dts[i*2]+dion+dtrp)`，
    ephemeris.c L826/L847 dts 写入索引 `i*2` 与之一致。
  - elmin=15°、`posopt[4]=1`(RAIM-FDE) 三变体保持一致。
- 统计口径：`$POS` 末 10 历元均值对真值算 N/E/U（analyze.py；41 历元全部 FIX，6 条 stdout FIX 行）。

## 结果（末 10 历元均值）
| 变体 | 大气 | 钟差 | N (m) | E (m) | U (m) | 水平 (m) | 3D (m) | FIX/星 | LOCK | URV |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 开(错扣) | 开 | −1.457 | +0.095 | **−11.314** | 1.460 | **11.41** | 9/12 | 12/12 | 3.60 |
| 场景匹配版 | 关 | 开 | −0.004 | −0.094 | **+0.199** | 0.094 | **0.22** | 9/12 | 12/12 | 6.37 |
| 错关钟差对照 | 关 | 关 | **+3.159** | **+2.414** | **+2.370** | 3.975 | **4.65** | 9/12 | 12/12 | 6.37 |

复现性：baseline 重跑 U=−11.314 m 与 2026-11-13 单历元记录 −11.45 m 一致；
both_off 重跑椭高 47.447（均值）/47.284（末 FIX 历元）与此前 47.306 一致。

## 定量佐证（钟差侧）
afzero2 星历下接收机 dts＝纯相对论偏心率项，振幅 `2·√μ·F·e·√A`（F=4.442807633e-10 s/m^0.5）：
11 星（PRN12 记录缺失）mean **0.45 m**、max **1.02 m**（PRN25 e=0.0112）。
错关后该 per-star 确定性偏置进伪距，公共钟差参数无法吸收，经 9 星 LS 几何放大
→ 3D ≈ 4.7 m 固定方向系统偏差（三变体 LOCK/FIX/ns 完全一致，证明纯 PVT 层、与跟踪和 RAIM 无关）。

## 结论（配置-场景匹配铁律）
「只改正引擎实际注入的东西」在 PVT 层同样成立、且两个方向都验证过：
- **该关**：大气（Saas 对流层 −8.5 + Klobuchar −2.7 m 全是假扣的）——关后 11.41 → 0.22 m；
- **该留**：卫星钟差（引擎注入真值钟差；错关引入 ~±1 m/星 相对论项 → 3D 4.65 m）；
- **不动**：elmin=15°（只影响剔星数 9/12，非精度因素）、RAIM-FDE（无粗差可剔，中性）。

## 产物清单
- `bl2.log/.nmea/.stdout.txt`（baseline 原版）、`bo2.*`（场景匹配版）、`sco.*`（错关钟差版）
- `analyze.py`（$POS 解析 + 真值 N/E/U 统计）
- 变体源/二进制：`PocketSDR/local_build/sdr_pvt_satclk_off.c`、`pvt_satclk_off.exe` 等
