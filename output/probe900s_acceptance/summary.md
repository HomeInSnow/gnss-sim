# 900 s 场景（out/20261117T022846863288）救援与验收

## 事件
- 按当前配置（复刻 out/20261113T033315803665：Tampere / 12 星 GPS L1CA / 25 Msps
  int16 / atmosphere off / sv_clock on / afzero2 BRDC / AWGN −18.33 dB / seed 20261117）
  生成 900 s。引擎段完整写出 90 GB 原始 IQ；AWGN 后处理按「写 .tmp 副本再替换」
  设计需 2×90 GB 峰值，磁盘（当时 avail 154 GB）在 tmp ~95% 处耗尽：
  `OSError: 4194304 requested and 0 written`（postproc.py _Writer.write）。abort
  保护生效，原始文件未破坏，meta.json 未写。

## 救援（用户批准 in-place 方案）
- `backend/synth/postproc.py` 新增 `_InplaceWriter` + `apply_impairments(inplace=)`：
  末段经 r+ memmap 逐块原地写回，峰值 1×；guard 禁 sample_rate_ppm≠0；默认行为不变。
- 回归：冒烟 IQ 副本同 cfg 分别走 tmp 路径与 in-place 路径 → report 相同、
  输出 sha256 逐字节一致。
- `.workbuddy/rescue_900s.py`：对 90 GB 文件 in-place 加噪（2336 s），脚本内
  功率步变断言因 clip 饱和（σ=37470 LSB > 满量纲 32767，clip 使实测功率增量约
  为理论值 42%）而失败中止；加噪本体已完成，meta 由后续命令补写（含 rescue_note）。

## 验收
- 头/尾 4M 样本加噪后功率 = 冒烟 run（同 cfg 同 seed，原 tmp 路径产物）对表：
  1.2248e9 vs 1.2247e9（相对差 ~5e-5）。
- meta.json：duration 900 / total_samples 2.25e10 / prns 同 12 星 /
  measured_snr_db −18.33。
- 端到端：头 60 s 切片 out/probe_900s/probe60.bin，PocketSDR pocket_trk_local.exe
  （baseline：大气开+钟差开）回放（CS16/f25/fo 1575.42/IQ2/ti10/tscale1）——
  12/12 星 LOCK 58–60 s、C/N0 40.2–45.4 dB-Hz、导航消息零错；29 个 FIX 历元，
  末 10 历元 N−1.378 / E+0.190 / U−11.569，3D=11.65 m —— 与 60 s demo baseline
  11.41 m 同形态（U 主导=baseline 假扣大气的已知签名）。

## 备忘
- 60 s demo（11-13）文件的加噪形态（noise_power 1.77e8、rms 9480、饱和 0.057%）
  与当前链路（2.81e9、rms 24751、饱和 38.5%）不同：旧链路 sig_p 测量口径差异，
  属历史产物；「当前配置」重生成以当前链路（=本次冒烟/救援形态）为准。
- clip 饱和使文件实测 SNR ≈ −14.6 dB（标称 −18.33 dB），系信号满量纲占比
  （rms 6400/32767）与噪声 σ 联动的固有形态，冒烟/正常链路同样如此。
- 产物：probe.log（$POS 29 条）、probe.nmea、probe_tail.txt（末帧通道表）、probe.stdout.txt（原始 ANSI 屏）；
  probe60.bin 6 GB 在 out/probe_900s/（可删）。
