# PocketSDR 桌面化改造方案（带界面 Windows 应用）

状态：**待确认**。确认后按 P0→P4 实施。

## 1. 目标与定位

把 PocketSDR（纯 C 的 SDR 接收机 + 自带 Web UI）改造为**原生桌面 Windows 应用**：
双击 exe 即用，无需浏览器、无需命令行拼参数。与 gnss-sim 桌面版同款深空蓝黑科技感界面，两者形成"仿真 → 验证"配套工具链。

与 gnss-sim 桌面化的关键差异：gnss-sim 内核是 Python，桥接层可直接函数级调用；PocketSDR 内核是 C 实时环路，**不可进程内逐步调用**。因此架构改为：

```
┌─ PySide6 桌面壳（原生 UI，复用 gnss-sim desktop 资产）
│   控制台 / 卫星监控 / 定位轨迹 / 日志  四页
├─ 引擎管理器：以子进程启动/停止 PocketSDR Web 版引擎（本地回环端口）
└─ WS 客户端：订阅引擎 13 路 topic → Qt 信号 → 原生渲染
```

## 2. 已核实的引擎接口（TRUTH：src/sdr_web.c）

- 引擎 exe（已编译、无 Soapy 依赖）：`local_build/pocket_web_local.exe`（原版 BRDC/SAAS）、`pocket_web_both_off.exe`（IONO/TROPO OFF 匹配版）、`pocket_web_iflc.exe`（E1+E5a 双频 IFLC）。启动：`-web 127.0.0.1:<port> -ini <ini> [-start]`。
- WS 命令：`sub/get/unsub`、`start/stop`、`set_inp`（inp=2 文件回放：file/fmt/fs/fo/IQ/bits/tscale/toff，fs/fo 单位 MHz）、`set_sig/set_sys/set_out/setopt/log_level`。
- topics：`rcv_stat`（状态机+耗时）、`sat_stat`（JSON：sat/az/el/pvt/obs/eph/svh/fcn → **Skyplot 直接可画**）、`pvt_sol`（解算行字符串）、`ch_stat/rfch_stat`、`hist`、`log`（日志环形缓冲增量推送）、`opts/cfg`、二进制 `psd/corr/corr_hist`（高级图谱，二期）。

## 3. 界面要素映射（= 验收清单）

| 页面 | 要素 | 数据源 |
|---|---|---|
| 控制台 | IQ 文件选择、格式(fmt)/fs/fo/IQ/bits、tscale/toff、信号集(sig/sys)、引擎变体三选、参考真值(可选，可从 gnss-sim run meta 一键读)、启动/停止 | set_inp/set_sig + start/stop |
| 监控 | rcv_stat 状态卡、**Skyplot**（复用 widgets.Skyplot）、卫星状态表（锁定/C/N₀/az/el/#NAV）、C/N₀ 条形图 | sat_stat/ch_stat 订阅 |
| 定位 | 实时解算行 + 解算数统计、**轨迹地图**（复用 MapWidget）+ 平面轨迹图、**误差曲线**（给定真值时：水平/垂直误差，pyqtgraph）、NMEA 落盘导出 | pvt_sol 订阅 |
| 日志 | 分级着色实时日志、清空/导出 | log topic 订阅 |

复用清单：`desktop/ui/theme.py`（QSS/色板/mono）、`widgets.py`（Card/StatCard/Skyplot/MapWidget/fmt_bytes）、`worker.py`（FnWorker）、logpage 配色范式。主题包做成独立 `pocket_desktop/ui/` 目录，复制而非跨包 import（两应用独立打包）。

## 4. 架构分层

- `pocket_desktop/core/engine_mgr.py`：子进程生命周期（subprocess.Popen，随机空闲端口 8085-8099，超时强杀、退出监听、日志重定向）；变体→exe 路径映射（frozen 时取 exe 旁 `engine/`）。
- `pocket_desktop/core/wslink.py`：`websockets`（pip 轻量库，PyInstaller 兼容）异步客户端 → 解析 JSON → Qt Signal；断线自动重连；命令队列（start 前先 set_inp）。
- `pocket_desktop/ui/`：main_window + pages/{console,monitor,solution,log}。
- 引擎产物（3 个 exe）打包进 `dist/engine/`，随包分发。

## 5. 里程碑与验收

| 里程碑 | 内容 | 验收 |
|---|---|---|
| P0 | 骨架：四页壳 + 主题复用渲染 | windows 平台截图逐页审阅 |
| P1 | 引擎管理 + WS 链路：控制台选文件→start→收 pvt_sol/log | 对 whu60b 类 run 回放，CLI 打印解算行；进程可停可控 |
| P2 | 监控页：sat_stat→Skyplot+星表+C/N₀ | 回放 60s：12/12 锁定可见、C/N₀≈40-45 目视正确 |
| P3 | 定位页：轨迹地图+误差曲线+真值联动 gnss-sim run meta | 与本次互验数字对表（both-off 水平 RMS≈0.23 m） |
| P4 | PyInstaller onedir 打包（含 3 引擎 exe）+ `--selftest` | exe 全流程回放出自检 PASS，产物 ~200-300MB |

## 6. 风险与对策

- **pvt_sol 是单串文本**（非结构化 JSON）→ 解析器按实测样本写，解析失败降级为原样显示。
- **引擎假死/端口占用** → 随机端口 + 启动态看门狗（rcv_stat 心跳）+ 一键重启按钮。
- **WS 库打包**：websockets 纯 Python，collect_submodules 即可。
- **引擎不在仓库版本管理内**（PocketSDR 在 gnss-sim 仓库外）：打包从 `PocketSDR/local_build/` 收集，路径写配置项，缺失时设置页红字提示 + 重新编译指引（配方 .workbuddy/build_iflc_tropoff.sh 同族）。
- 本期不做：硬件采集（Soapy 路数）、二进制 topic 高级图谱（PSD/相关峰）、阵列。留二期。

## 7. 交付物

- `pocket_desktop/` 包（新目录，与 desktop/ 平级）；`pocket_desktop.spec` + `pyi_entry_pocket.py`；
- `dist/pocket-desktop/`（双击即用）；`output/pocket_desktop/` 截图与打包说明；
- git 本地 commit（不 push）。
