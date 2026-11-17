# PocketSDR WebUI 手动处理 E1+E5a 双频数据 使用说明（gnss-sim 场景）

适用：在浏览器里手动配置 PocketSDR Web 通道，对 gnss-sim 生成的 Galileo E1+E5a 双频
IQ 文件做捕获→跟踪→电文→IFLC 双频定位。已验证版本：PocketSDR 0.22(DEV)，
exe=`PocketSDR/local_build/pocket_web_iflc.exe`（源码级编译，配方
`gnss-sim/.workbuddy/build_web_iflc.sh`：全套 src + sdr_pvt_iflc/sdr_func_iflc/
ephemeris_iflc/pntpos_iflc 补丁，静态链 librtk+libpocketfft+CyAPI，不含 Soapy）。

---

## 0. 准备（在 gnss-sim 侧完成，一次性）

1. 生成双频场景（例：`out/20261117T123629105786/`，E 星 11 颗，60 s@25 Msps CS16）
   ```bash
   .venv/Scripts/python.exe .workbuddy/gen_e1e5a.py
   ```
   产出 `gpssim.bin`（E1）与 `gpssim_l5.bin`（E5a-I）。
2. 双带合并成 PocketSDR 双通道文件（关键产物是同名 `.tag`）：
   ```bash
   .venv/Scripts/python.exe .workbuddy/merge_tag.py out/<runid>
   ```
   产出 `pocket_e1e5a.bin`（12 GB/60s）+ `pocket_e1e5a.bin.tag`：
   `FMT=CS16 / NCH=2 / F_S=25 / F_LO=1575.42,1176.45 / IQ=2,2 / BITS=16,16`。
   **`.bin` 与 `.tag` 必须同目录同名**——WebUI 的格式参数由 tag 自动接管。

## 1. 启动 Web 服务器

```bash
cd /d/workbuddy/GNSSSignal/PocketSDR/local_build
./pocket_web_iflc.exe -web 127.0.0.1:8081
```
浏览器打开 `http://127.0.0.1:8081/`，右上角 **Connect** 连接（状态栏不再显示 OFFLINE 即成功）。

可选快捷方式（预置+免手填）：
```bash
./pocket_web_iflc.exe -web 127.0.0.1:8081 \
    -ini D:/workbuddy/GNSSSignal/gnss-sim/output/pocket_web_verify/dual_iflc.ini [-start]
```
`-ini` 只预填表单，`-start` 则直接开跑；不加就按下面第 2 节手动填。
注意：**改配置必须先 Stop**（运行中页面会锁定并提示 "Stop the receiver to edit"）；
服务器会记住上次会话配置（下次启动自动恢复，页内 **Reload** 可拉回服务器端当前值）。

## 2. 页面填写（手动模式，按页操作）

### ① Input 页
| 字段 | 值 | 说明 |
|---|---|---|
| Input Source | **IF Data** | 文件回放 |
| Path | `…/out/<runid>/pocket_e1e5a.bin` | 绝对路径，含 `.bin`；`.tag` 须同目录 |
| IF Data Format | CS16 | 以 tag 为准 |
| Sampling Rate (Msps) | 25 | 以 tag 为准 |
| LO Frequency (MHz) | `1575.42,1176.45` | 两通道，顺序=tag 的 NCH 顺序（以 tag 为准） |
| IQ / Bits | 2 / 16（16-bit） | 以 tag 为准 |
| Time Offset (s) | 0 | |
| Time Scale | 1 | 1=实时速度（60s IQ 跑 60s）；<1 加速、>1 减速 |
点 **Apply**。

### ② Signal 页
1. 建议先点 **Unset All**（清掉默认全选）。
2. 找到 **Galileo** 行：勾选系统框，再在 GNSS Signals 里勾 **E1B** 与 **E5AI** 两个复选框。
3. 该行 **Satellite No** 填本次 run 的卫星列表：`2,7,8,10,11,12,14,22,23,24,33`
   （两信号共用；若要分开指定，用底部 **Satellite No Assignments**：
   `E1B:2,7,8,10,11,12,14,22,23,24,33 E5AI:2,7,8,10,11,12,14,22,23,24,33`，
   该字段会覆盖行级 Satellite No）。
4. **RF CH Assignments** 留空=自动（按 LO 频率匹配通道）；显式写法 `E1B:1 E5AI:2`。
5. 点 **Apply**。

### ③ Log 页
勾选 **POS、OBS、NAV、SAT、CH**，并务必勾上 **EPH**（**$EPH 默认不勾**——历次
"星历=0"假象的头号来源）。

### ④ Output 页
- 第 1 行 Output = **NMEA**，Path = 绝对路径如 `…/output/pocket_web_verify/web_ui.nmea`
- 第 2 行 Output = **LOG**，Path = `…/output/pocket_web_verify/web_ui.log`
（多行 Path 以竖线分隔存储，路径本身不要含 `|`）

### ⑤ Receiver 页
Elevation Mask 默认 15° 即可；其余跟踪参数保持默认。

### ⑥ 开跑
顶栏 **Start**。状态栏依次出现 E1B、E5AI 的 SIGNAL FOUND 与 22 路（11 星×2 信号）$CH 锁定；
I/NAV 页面凑齐后（36 s 左右起）Solution 页出现定位曲线，LOG/NMEA 文件开始落盘。

## 3. 验收基准（本场景 60s 窗口的实测水平）

| 项 | 通过线 | 本次实测 |
|---|---|---|
| $CH 锁定 | 11 星×(E1B,E5AI) 出现 | 22 路全现 |
| $EPH | >0（I/NAV 主源 + 约 4 星 F/NAV） | 29–30 行 |
| $POS FIX | 出现即链路通；数历元受 E5a 配对抖动影响 | 5–9 个历元（重跑数量有 ±3 抖动属正常） |
| 精度（对 Tampere 真值 60.182537,24.82826,47.248） | | 好解 3D 3.5–6.4 m；min3D 3.55 m |

**读解注意**：`ns≥5 且 URV<9` 的解可信；`ns=4`（E5a 配对缺星时的最小几何）可能出
30–40 m 坏解（E14/E23 的 E5a 属边际锁定，逐历元掉队属抖动、非错误——已与 CLI 版
逐星伪距逐位一致对拍）。要更好结果：跑更长场景（E5a 锁定率上升）、或多次回放取优。

## 4. 常见问题
- **cannot open IF data**：路径没带 `.bin` 后缀、或 `.tag` 不在同目录/被改名。
- **页面灰住不让改**：receiver 在跑，先 Stop。
- **$EPH 没输出**：Log 页 EPH 没勾（默认关）。
- **只有 E1B 锁、E5AI 全掉**：检查 LO Freq 两通道顺序与 tag 的 F_LO 一致；或 RF CH
  Assignments 写反（`E1B:2 E5AI:1` 是错的）。
- **首 FIX 比 CLI 晚几秒/解数少几个**：E5a 边际锁定的正常抖动（同 IQ 同代码路径，
  重跑本身也有此抖动）。
- 服务器窗口的 stderr 有 `tag file open error` / `data read error` 等明确报错，先看它。

## 5. 已做的验证（2026-11-17）
- ini 预置 + `-start` 通道：GUI 服务 HTTP 200；22 路双频锁定；$EPH=30、$OBS=515、
  $NAV=299、$POS=6（min3D 3.55 m）。
- 与 CLI 版 `pocket_trk_iflc.exe`（fixA，$POS=9）共同历元 **$OBS 伪距逐位一致**
  （E02@45s 5I：26444738.267 vs 26444738.266 m），通道差异仅剩 E5a 边际配对抖动。
- 浏览器手动路径（不经 -ini/-start）：以最小 WebSocket 客户端重放页面 JS 的
  `set_inp → set_sig → set_out → start` 报文序列验证通过——22 路锁定（11 星×E1B/E5AI）、
  $EPH=24、$OBS=473、$NAV=290、$POS=7、NMEA GGA fix=7、min3D=6.75 m（对真值收敛，
  见同目录 web4 产物；脚本 `.workbuddy/ws_manual_test.py`）。
  注意：裸 WebSocket 客户端**必须回应服务端 ping（10s 周期，30s 无 pong 即断连）**，
  浏览器自动回、脚本要自己回，否则 receiver 被半路过早 stop。
- 产物：`dual_iflc.ini`（预置参考）、`web3.*`/`web4.*`（ini 通道 / 手动通道验证日志）、
  `build_web_iflc.log`（构建）。
