# gnss-sim 桌面化改造方案（Windows 本地应用 · exe）

> 状态：**已确认，实施中**。M0/M0b/M1 完成（`desktop/` 包，2026-11-18）：六页骨架 + 桥接层直调 backend 内核 + 仿真页全量配置/预览/生成/验证；M1 验收已过——同场景桌面桥接与 Web HTTP 链路 gpssim.bin sha256 逐字节一致（`8f39e7c0…8638`，见 `.workbuddy/desktop_m1_smoke.py`）。页面实机截图见 `shots_m1/`。

## 1. 目标与范围

| | 内容 |
|---|---|
| **目标** | 把 gnss-sim 从"FastAPI + 浏览器 WebUI"改造为**自带界面的 Windows 本地应用**，交付 `gnss-sim.exe`（双击即用，无需浏览器、无需起服务） |
| **保留** | 中频采样数据仿真全链路：场景配置 → 几何预览 → 生成 gpssim.bin/meta.json → 内置接收机 Verify Fix → 验证/图谱展示 → 日志/历史；轨迹编辑器与场景库 |
| **本期裁剪（硬件通道）** | SDR kind/连接/TX slot/LO/TX gain/oscillator/dry-run/record session/replay recording、RF Frontend 页、实时播发（Start/timeline/jog/time_shift）、直播类视图（live spectrogram、实时 C/N0、真实接收机回传 UDP/Serial）、RF 确认弹窗 |
| **不变（TRUTH）** | 生成与验证内核**原样复用**：native C++20 引擎（libgnsssynth.dll）+ backend/synth + backend/analysis（l1_acquire/l1_fix/receiver/trace）+ inspector——铁律（align_for_run、at_gps、注入策略对齐）全部沿用，不重写 |

## 2. 架构调整对照

| 层 | 现状（Web 模式） | 目标（桌面模式） |
|---|---|---|
| 界面 | frontend/ 原生 JS SPA + 浏览器 | **PySide6 原生窗口**（QMainWindow + 侧栏 + 卡片式表单 + pyqtgraph 图表） |
| 服务层 | FastAPI `backend/app.py`（HTTP 端点） | **进程内 Service 层**：把 app.py 端点背后的逻辑抽为 `backend/services/*`（preview/generate/receiver/iqplot/correlation/lnav/scenario/trajectory），UI 直调函数，无 HTTP、无端口 |
| 生成 | ctypes → libgnsssynth.dll | 不变（打包进 exe 目录） |
| 验证 | backend/analysis 纯 Python | 不变 |
| 地图 | Leaflet + unpkg CDN | 离线：内置低分辨率世界地图轮廓（Natural Earth shape）自绘可点选位置层 + lat/lon/alt 精确输入 |
| 打包 | uvicorn 常驻 | **PyInstaller**（onedir 优先，`--noconsole --onefile` 可选）：打包 Python、numpy、PySide6、libgnsssynth.dll、字体、图标 |
| 任务形态 | 多"通道卡"（含 TX） | **仿真任务队列**（左侧列表）+ 单任务工作区；无硬件后"通道"语义退化为"任务" |

## 3. 界面信息架构（对应概念稿）

```
┌─ 标题栏：gnss-sim · IF Simulator    [引擎状态●][输出目录][主题][—□×]
├─ 左侧栏：任务列表（新建/复制/删除） │ 页面：仿真·验证·图谱·轨迹·日志·历史
├─ 仿真页（三栏）
│   ① 配置列（卡片分组）        ② 几何预览：Skyplot 极坐标 + 可见星表(Az/El/Pr/Doppler/P)
│   ③ 底部动作条：Preview │ Generate(进度) │ Verify Fix + 体积估算/状态 hint
├─ 验证页：Fix 结果卡(误差/PDOP/残差RMS) + EXP/MEAS 逐星表 + 误差曲线 + 跟踪解(tracking)
├─ 图谱页：捕获度量曲面 / 波形 scrubber / 星座图 / 频谱(分频带小倍数) / C/N0 趋势
├─ 轨迹页：航点表 + 平面轨迹线 + 应用到任务
├─ 日志页：结构化流水（生成/验证每轮留痕）
└─ 历史页：out/<runid> 列表（时间/参数摘要/误差/大小）→ 载入配置/打开目录/重验证
```

## 4. WebUI 要素 → 桌面控件映射（验收清单）

**配置参数（全部保留，除非注明）**

| 分组 | 要素 | 桌面控件 |
|---|---|---|
| 定时输出 | Start UTC / Duration s | 日期时间选择器 / 数值框 |
| 定时输出 | Sample rate（auto+2.6M~27.5M，高频档） | 下拉（FPGA 专属 optgroup 并入普通档） |
| 定时输出 | Format int16/int8；Quantization int16/int12/int8（合并为"量化"） | 下拉 |
| 星历 | RINEX path(AUTO) / Ephemeris broadcast/precise / SP3 path+Load+Compare | 文件选择器 / 下拉 / 路径+按钮（对比弹子窗） |
| 星座信号 | Constellations G/R/E/C/J/S/I；Bands L1/L2/L5；Engine=native；Sample rate Hz(auto) | Chip 多选 |
| OSNMA | 开关 / NMA status / keys | 开关+下拉+按钮 |
| 传播模型 | Preset(4 档)/Ionosphere off·klobuchar/Troposphere off·saastamoinen/Rx clock poly+bias·drift·drift-rate·sawtooth/Multipath specular+2 径(delay·amp·phase)/Apply-to-IQ | 折叠卡+下拉+数值 |
| RF 损伤 | Preset(4 档)/enable/seed/CFO/ppm/相位噪声/IQ 幅度不平衡/IQ 相位误差/DC I/Q/Target SNR dB/clip fraction/quantizer bits | 折叠卡+数值（preset 联动回填） |
| 信道衰落 | off·seeded·keyed / env 4 档 / speed / seed / key+随机密钥 / 记录密钥 | 折叠卡 |
| 位置 | 地图点选 + lat/lon/alt | 离线自绘地图 + 数值框 |
| 场景库 | scenario save/load | 保存/载入按钮 + 任务列表持久化（JSON） |
| **裁剪** | SDR kind/URI/TX slot/LO/TX gain/osc/dryrun/auto-stop/record/replay、timeline、RF Frontend、Live-now | 不做（硬件） |

**显示要素（全部保留，除非注明）**

| 视图 | 内容 | 桌面实现 |
|---|---|---|
| 几何预览 | Skyplot、逐星 Az/El/Pr/Doppler、GDOP/PDOP | pyqtgraph 极坐标 + 表格 |
| Status | 逐星 inspect 表、星功率表、捕获度量曲面、波形 scrubber、星座图、频谱（多频带小倍数） | 图谱页（pyqtgraph + matplotlib 后端可选） |
| Verify Fix | Fix 经纬高/误差/PDOP/残差 RMS/逐星 EXP·MEAS | 验证页卡片+表 |
| Satellites | Selected PRN / 电文面板(lnav) | 验证页子面板 |
| LLA Manipulation | Offsets/距离步长 | 轨迹页内 |
| 日志页 | 每轮生成/验证流水 | 日志页（结构化+可导出） |
| **裁剪** | 实时 spectrogram、直播 C/N0 trend、真实接收机回传、RF 状态条、TRANSMIT 弹窗 | 不做（硬件/直播） |

## 5. 里程碑

| 阶段 | 内容 | 验收 |
|---|---|---|
| M0 骨架（0.5 周） | PySide6 主窗/侧栏/主题/任务队列；工程改造：backend/app.py 逻辑下沉 services 层（app.py 保留为薄壳） | exe 空壳可运行；既有回归脚本对 services 直调全绿 |
| M1 生成链（1 周) | 仿真页全量配置 + Preview + Generate（QThread 后台+进度/取消）+ 体积估算 + 场景库 | 同参数场景生成的 gpssim.bin 与 Web 链路 **sha256 一致** |
| M2 验证与图谱（1 周） | Verify Fix 面板（快照+跟踪解）、逐星 EXP/MEAS、捕获曲面/波形/星座/频谱/C/N0、日志/历史页 | 演示场景 error_m 与现 Web 口径一致（如 Tampere 3.80 m） |
| M3 地图/轨迹/打磨（0.5 周） | 离线选点地图、轨迹页、图标/主题、设置页（输出目录/线程数） | 全流程无浏览器可用 |
| M4 打包发布（0.5 周） | PyInstaller spec、DLL 随包、签名占位、安装目录规范、README | 干净机器双击 exe 完成一次生成+验证 |

## 6. 风险与对策

- **体积/启动**：PySide6+numpy+matplotlib 全量 → onedir ~250-350 MB（可去 matplotlib，pyqtgraph 全覆盖后）；优先 onedir，onefile 作为可选（启动慢 3-8 s）。
- **UI 冻结**：生成/验证为长任务 → QThread + Signal 进度（复用 generate/stop 语义，可中断）。
- **DLL 打包**：libgnsssynth.dll 路径按 frozen 环境解析（sys._MEIPASS 兼容）；回归含"打包后引擎加载"用例。
- **图表性能**：捕获曲面/波形大数组 → pyqtgraph（GPU 友好），matplotlib 仅留导出。
- **WebUI 去留**：改造期内 frontend/ 与 app.py 保留不动（回归基准），M4 验收后再定去留——默认建议归档保留（precise/compare 遗留契约仍依赖 app.py）。

## 7. 请确认的决策点

1. **技术栈**：推荐 **PySide6 + pyqtgraph + PyInstaller**（Python 后端零重写）；备选 Tauri+WebView 壳复用现有 JS（界面 100% 现成，但要维护 sidecar 进程与 HTTP 内部协议，违背"去 Web 化"初衷的程度由你判断）。
2. **界面语言**：中文为主（专业术语保留英文，如 Skyplot/C/N₀）？
3. **任务模型**：左侧"多任务列表"（可同时存在多个场景草稿，单选编辑）是否够用？
4. **地图**：接受"内置离线世界地图轮廓（无街道细节）+ 精确经纬输入"？
5. **量化档位**：int12 是否保留（native 引擎支持）？
6. **主题**：深空蓝黑 + 青蓝高亮（概念稿风格）OK？需要浅色主题吗？
