# Galileo E1+E5a 双频 IFLC 三口径对照（2026-11-17）

## 实验目的
同一 E1+E5a 仿真场景下，对照三种接收口径的 `$POS` 精度（口径完全复用
`output/pvt_config_exp_20261115/analyze.py`：$POS 末 min(10,n) 历元均值对真值算 N/E/U）：
1. **单频 E1B baseline**：PocketSDR 作者原版 PVT（IONOOPT_BRDC + TROPOPT_SAAS + 钟差改正 + RAIM-FDE）
2. **单频 E1B 场景匹配**：IONOOPT_OFF + TROPOPT_OFF + 钟差改正（与 #58-60 GPS 三态实验同款 `pvt_both_off.exe`）
3. **双频 IFLC**：`pocket_trk_iflc.exe`（IONOOPT_IFLC + TROPOPT_SAAS，轨道源 E1B I/NAV，#70 验收版）
4. **（诊断列）IFLC + tropo-off**：`pocket_trk_iflc_tropoff.exe`（同 3 仅 TROPOPT_OFF），隔离 Saas 错扣

## 场景（同一 run，无跨 run 变量）
- `out/20261117T123629105786/`：Galileo-only 11 星（E02/07/08/10/11/12/14/22/23/24/33），
  60 s @ 25 Msps CS16，Tampere 真值 60.182537°N 24.82826°E 椭高 47.248 m，AWGN，
  **atmosphere iono/tropo = off，sv_clock = true**（meta.json），
  星历 BRDC_2023271_whu_afzero2.rnx，E1B=I/NAV、E5a-I=BPSK(10) 载荷 F/NAV。
- 信号输入：单频两列回放 `pocket_e1b.bin`（gpssim.bin 硬链 + `.tag` NCH=1/F_S=25/F_LO=1575.42/CS16）；
  双频两列回放 `pocket_e1e5a.bin`（merge_tag.py 交错双通道 + `.tag` NCH=2）。
- 回放 CLI 同源：`-sig E1B -prn 2,7,8,10,11,12,14,22,23,24,33 [-sig E5AI -prn 同上] -ti 10 -tscale 1 -log … -nmea …`，
  每次 70 s 完成。

## 结果（$POS 末 min(10,n) 历元均值，对 Tampere 真值）
| 口径 | 解数 | 首FIX(s) | ns | N(m) | E(m) | U(m) | 水平(m) | 3D(m) | min3D(m) |
|---|---|---|---|---|---|---|---|---|---|
| E1B 单频 baseline（大气开） | 24 | 36 | 8 | +1.20 | +2.25 | **−10.62** | 2.55 | **10.93** | 5.12 |
| E1B 单频 场景匹配（大气关） | 24 | 36 | 8 | −0.21 | +2.58 | −2.50 | 2.59 | **3.60** | 1.98 |
| 双频 IFLC（IFLC+SAAS，fixA 验收版） | 9 | 43 | 6 | +1.31 | +2.76 | −5.39 | 3.05 | **6.19** | 4.88 |
| （诊断）IFLC + tropo-off | 5 | 39 | 4 | −1.59 | +0.46 | +3.01 | 1.66 | **3.44** | 1.74 |

- $EPH 行：fixA=29、tropoff=30（含 4 星 F/NAV + I/NAV 主源）；单频两列 exe 为默认日志掩码，$EPH 未放开，以 $POS 为准。
- 逐历元 ns：单频稳定 8；IFLC 各历元 4–7 波动（双频配对需 E1/E5a 伪距同时可用，E5a 侧边际星逐历元掉队），
  这是 IFLC 解数稀疏（9/5 个 vs 单频 36 s 起每秒连续）与首 FIX 偏晚（39–43 s vs 36 s）的直接原因。

## 结论
1. **「只改正引擎实际注入的东西」推广到 Galileo 双频链路成立**：
   E1B 单频在 iono/tropo=off 场景错扣 Klobuchar+Saas 付出 3D 10.93→3.60 m 的代价（U −10.6→−2.5），
   与 GPS L1CA 三态实验（11.41→0.22）同形态；IFLC 侧同理，错扣 Saas 使 U 偏 −5.4 m、
   关掉后水平 3.05→1.66 m（诊断列）。
2. **无电离层场景下双频 IFLC 不占优**：IFLC 的唯一收益是消电离层，本场景引擎不注入电离层，
   双频只剩成本——E5a 侧噪声放大（IFLC 组合对 E5a 伪距噪声 ~×3 放大）与配对可用星数缩水，
   单频场景匹配版（3.60 m）优于双频 IFLC（6.19 m）。双频的优势需要注入电离层的场景才能兑现
   （引擎 `_atmo_for` 对 E 系 I/NAV NeQuick-G 播零，E1B 无 Klobuchar 参数可扣，同属此因）。
3. **接收配置-场景匹配优先级**：单频场景匹配（3.60）≈ IFLC-tropo-off（3.44，样本少）> IFLC+SAAS（6.19）> 原版 baseline（10.93）。
4. **待查项**：E1B 单频两列与 fixA 三列共有 +2.5 m 量级 E 向偏置（tropo-off 列 +0.46 m 但仅 5 样本，
   结论不稳）；候选源：PocketSDR E1B 相关器组延时或引擎 E1 生成侧共模偏差，后续用逐星伪距残差分离。

## 产物清单（本目录）
- `compare_analyze.py`：三口径统计脚本（真值/口径参数化，可直接复跑）
- `e1b_base.log/.nmea/_stdout.log`、`e1b_match.log/.nmea/_stdout.log`：单频两列
- `iflc_fixA.log/.nmea/_stdout.log`：双频验收版（#70）
- `iflc_tropoff.log/.nmea/_stdout.log`：双频 tropo-off 诊断列
- `build_tropoff.log`：`pocket_trk_iflc_tropoff.exe` 构建日志（配方 `.workbuddy/build_iflc_tropoff.sh`）
- 历史冒烟序列 `iflc_fix*.log` 等保留不删（取证链）

## 复现
```bash
# 构建诊断变体（PocketSDR 源码级, 无 Soapy；与 pocket_trk_iflc.exe 唯一差异 TROPOPT_OFF 一行）
bash gnss-sim/.workbuddy/build_iflc_tropoff.sh
# 回放（4 条，均 70 s；exe 位于 PocketSDR/local_build/）
./pocket_trk_local.exe          -sig E1B -prn 2,7,8,10,11,12,14,22,23,24,33 -ti 10 -tscale 1 \
    -log …/e1b_base.log -nmea …/e1b_base.nmea  out/20261117T123629105786/pocket_e1b.bin
./pvt_both_off.exe              -sig E1B -prn …（同上，输入 pocket_e1b.bin）
./pocket_trk_iflc.exe           -sig E1B -prn … -sig E5AI -prn … -log …/iflc_fixA.log … pocket_e1e5a.bin
./pocket_trk_iflc_tropoff.exe   -sig E1B -prn … -sig E5AI -prn … -log …/iflc_tropoff.log … pocket_e1e5a.bin
# 统计
cd output/e1e5a_dualfreq && ../../.venv/Scripts/python.exe compare_analyze.py
```
