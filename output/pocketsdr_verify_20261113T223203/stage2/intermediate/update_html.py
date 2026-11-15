# -*- coding: utf-8 -*-
"""向已交付 HTML 注入第十二章（PVT 配置三态实验）：摘要第5条、目录、正文、附录。
数字全部抄录自 output/pvt_config_exp_20261115/results.md（materials_digest 已登记）。"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
HTML = os.path.join(STAGE2, "formatted-PocketSDR深入分析与gnss-sim第三方互验报告.html")

with open(os.path.join(HERE, "fig3.b64"), encoding="ascii") as f:
    FIG3 = f.read().strip()

s = io.open(HTML, encoding="utf-8").read()
orig_len = len(s)

# ---- 1. 执行摘要补第 5 条 ----
anchor1 = "<p><span class=\"exec-summary-label\">核心结论四</span>&nbsp;&nbsp;用法启示：PocketSDR 用于仿真互验时，必须按场景大气开关自备 IONOOPT_OFF/TROPOPT_OFF 编译版，否则会把 RTKLIB 内置大气模型误差误算到仿真器/接收机头上。</p>"
add1 = anchor1 + """
        <p><span class="exec-summary-label">核心结论五</span>&nbsp;&nbsp;配置-场景匹配三态实验（2026-11-15 补充）把该铁律双向定量闭合：场景匹配版（大气关+钟差留）3D 误差 0.22 m，基线（错扣大气）11.41 m，「错关钟差」对照 4.65 m——卫星钟差改正必须保留，错关会把 afzero2 星历下的纯相对论偏心率项（实测 11 星振幅 mean 0.45 m、max 1.02 m/星）全量留在伪距上；三变体锁定 12/12、FIX 9/12 完全一致，证明纯属 PVT 层系统偏差。</p>"""
assert s.count(anchor1) == 1, "anchor1"
s = s.replace(anchor1, add1)

# ---- 2. 目录补条目 ----
anchor2 = "      <li><a href=\"#section-12\">十一、结论与用法启示</a></li>"
add2 = anchor2 + """
      <li><a href=\"#section-14\">十二、PVT 配置-场景匹配三态实验（报告发布后专项）</a></li>"""
assert s.count(anchor2) == 1, "anchor2"
s = s.replace(anchor2, add2)

# ---- 3. 正文新章节（插到附录 h1 之前）----
anchor3 = "  <h1 id=\"section-13\">附录：复现命令与产物</h1>"
sec14 = """  <h1 id="section-14">十二、PVT 配置-场景匹配三态实验（报告发布后专项）</h1>
  <p>第十章判定"大气该关"之后，进一步按场景 meta.json 实测设置（atmosphere ionosphere/troposphere=off、sv_clock=true）做三态对照，把"该关的关、该留的留"双向定量闭合。钟差侧与大气侧是镜像关系：引擎 sv_clock=true 注入了真值钟差，afzero2 星历把 af0/af1/af2 清零后，接收机 dts＝纯相对论偏心率项——广播参数与注入真值一致，改正必须保留；错关即把该项全量留在伪距上。</p>
  <p>实验设置：同一 gpssim.bin（12 星 CS16/25 Msps/60 s）、同一回放命令行（-fo 1575.42 -tscale 1 -ti 10），三个编译变体只差在 update_sol()：baseline＝pocket_trk_local.exe（作者原版）；场景匹配版＝pvt_both_off.exe（IONOOPT_OFF+TROPOPT_OFF，钟差保留）；错关钟差版＝pvt_satclk_off.exe（双 OFF 基础上，pntpos 前对每条 obs[i].P[0] 减去 CLIGHT*dts[i*2] 抵消内部钟差改正——dts 用与 pntpos 完全相同的 satposs(teph=obs[0].time, EPHOPT_BRDC) 重算，符号以 pntpos.c L311 残差式 P-(r+dtr-CLIGHT*dts[i*2]+dion+dtrp) 定案：内部是 +C·dts 进残差，抵消须预减）。elmin=15° 与 RAIM-FDE 三变体保持一致。</p>
  <p>结果（$POS 末 10 历元均值对真值 60.182537°N / 24.82826°E / 椭高 47.248 m）：</p>
  <table>
    <thead>
      <tr><th>变体</th><th>大气改正</th><th>钟差改正</th><th>N (m)</th><th>E (m)</th><th>U (m)</th><th>水平 (m)</th><th>3D (m)</th><th>FIX/星</th><th>LOCK</th></tr>
    </thead>
    <tbody>
      <tr><td>基线（作者原版）</td><td>开（错扣）</td><td>开</td><td>−1.457</td><td>+0.095</td><td>−11.314</td><td>1.460</td><td>11.41</td><td>9/12</td><td>12/12</td></tr>
      <tr><td>场景匹配版</td><td>关</td><td>留</td><td>−0.004</td><td>−0.094</td><td>+0.199</td><td>0.094</td><td>0.22</td><td>9/12</td><td>12/12</td></tr>
      <tr><td>错关钟差对照</td><td>关</td><td>关</td><td>+3.159</td><td>+2.414</td><td>+2.370</td><td>3.975</td><td>4.65</td><td>9/12</td><td>12/12</td></tr>
    </tbody>
  </table>
  <p class="fig"><img src="data:image/png;base64,__FIG3__" alt="三态 3D 误差对比"></p>
  <p class="fig-cap">图 3&nbsp;&nbsp;PVT 配置三态 3D 误差对比（数据源：上表，末 10 历元均值 vs 真值）</p>
  <p>定量佐证：从场景 BRDC（BRDC_2023271_whu_afzero2.rnx，af 三系数实测全零）解析 11 颗星的 e 与 √A，相对论项振幅 2·√μ·F·e·√A（F=4.442807633e-10 s/m^0.5）为 mean 0.45 m、max 1.02 m（PRN25，e=0.0112）。该 per-star 确定性偏置（cosE 逐星异号、公共钟差参数无法吸收）经 9 星最小二乘几何放大后呈 3D≈4.7 m 固定方向偏差，量级吻合。三变体 LOCK 12/12、FIX 9/12、使用星数 9 完全一致——错关钟差不影响捕获/跟踪/RAIM，是纯观测量层偏置。</p>
  <p>复现性：基线重跑 U=−11.31 m 与第十章单历元记录 −11.45 m 一致；场景匹配版重跑椭高均值 47.447 m（末 FIX 历元 47.284 m）与第十章双 OFF 记录 47.306 m 一致。</p>
  <p class="callout-warn">&nbsp;&nbsp;结论（配置-场景匹配铁律，PVT 层完整版）："只改正引擎实际注入的东西"在 PVT 层同样成立且两向均已验证——大气该关（11.41→0.22 m）、卫星钟差该留（错关致 3D 4.65 m）、elmin/RAIM 保持（非精度因素）。至此 gnss-sim 注入策略铁律在 FGI-GSRx（大气政策）、内置接收机（atmo_fn/sv_clock 门控）与第三方 PocketSDR（prcopt 配置）三个独立实现上全部闭环。</p>

""" + anchor3
assert s.count(anchor3) == 1, "anchor3"
s = s.replace(anchor3, sec14)

# ---- 4. 附录补产物条目 ----
anchor4 = "    <li>冒烟日志：/tmp/pk_ok.txt（基线状态行）、/tmp/bo.txt、/tmp/to.txt、/tmp/io.txt（A/B 三组）、/tmp/pk_ok_nmea.txt（174 行 NMEA）。</li>"
add4 = anchor4 + """
    <li>三态实验（第十二章）：变体源/二进制 PocketSDR/local_build/sdr_pvt_satclk_off.c/.exe；实验产物 output/pvt_config_exp_20261115/（bl2/bo2/sco 三套 log+nmea+stdout、analyze.py 真值统计脚本、results.md 实验存档）。相对论振幅解析要点：该 whu 合并 BRDC 数据行续行为 RINEX2 式布局（第 3 行 [cuc, e, cus, sqrtA]，√A 在第 4 字段）。</li>"""
assert s.count(anchor4) == 1, "anchor4"
s = s.replace(anchor4, add4)

# ---- 图3 base64 ----
assert s.count("__FIG3__") == 1, "fig3 placeholder"
s = s.replace("__FIG3__", FIG3)

io.open(HTML, "w", encoding="utf-8").write(s)
print("done, %d -> %d chars" % (orig_len, len(s)))
