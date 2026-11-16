# -*- coding: utf-8 -*-
"""生成《PocketSDR 使用手册》单文件 HTML：复用互验报告模板 CSS 骨架，重建内容。
内容源：stage1/organized_draft.md（数字均登记于 sources/materials_digest.md）。"""
import io, os

TPL = "D:/workbuddy/GNSSSignal/gnss-sim/output/pocketsdr_verify_20261113T223203/stage2/formatted-报告.tpl.html"
OUT = ("D:/workbuddy/GNSSSignal/gnss-sim/output/pocketsdr_usage_manual_20261116/"
       "stage2/formatted-PocketSDR使用手册.html")

tpl = io.open(TPL, encoding="utf-8").read()
head_end = tpl.index("<body>")
head = tpl[:head_end] + "<body>\n\n"

CONTENT = """
<section role="cover">
  <p class="cover-title">PocketSDR 使用手册<br>（gnss-sim 互验场景版）</p>
  <p class="cover-sub">本地构建 · 文件回放 · 快照诊断 · Web UI · 配置匹配铁律</p>
  <p class="cover-meta">&nbsp;</p>
  <p class="cover-meta">适用对象：GitHub tomojitakasu/PocketSDR（本地 HEAD 77a85b0，版本 0.22）</p>
  <p class="cover-meta">取证基础：本会话本地编译与多轮回放实测（12/12 锁定、9/12 FIX 复现）</p>
  <p class="cover-meta">整理日期：2026 年 11 月 16 日</p>
</section>

<section>
  <h1 id="section-1">执行摘要</h1>
  <table>
    <thead>
      <tr><th>项目</th><th>内容</th></tr>
    </thead>
    <tbody>
      <tr><td>适用场景</td><td>gnss-sim 仿真 IQ 文件的第三方接收机互验（文件回放为主）；亦覆盖构建、快照诊断与 Web UI</td></tr>
      <tr><td>整理日期</td><td>2026-11-16</td></tr>
      <tr><td>配套报告</td><td>《PocketSDR 深入分析与 gnss-sim 第三方互验报告》（output/pocketsdr_verify_20261113T223203/）</td></tr>
    </tbody>
  </table>
  <table class="executive-summary">
    <tbody>
      <tr><td>
        <p><span class="exec-summary-label">要点一</span>&nbsp;&nbsp;PocketSDR 提供实时接收、文件回放、Web 交互三种形态；对 gnss-sim 互验而言，核心入口是文件回放 pocket_trk（读 CS16/CS08 等原始 IQ 文件）与秒级快照诊断 pocket_acq_new。</p>
        <p><span class="exec-summary-label">要点二</span>&nbsp;&nbsp;本机（Windows + winlibs GCC）已验证的编译配方一次产出硬件无关静态版 pocket_trk_local.exe：关键点为 -DWIN32（否则 sys/select.h 编译挂）与三个硬件 stub 替换设备层。</p>
        <p><span class="exec-summary-label">要点三</span>&nbsp;&nbsp;文件回放三大铁律（全部实测踩过）：-fo 单位是 MHz；-tscale 1 必带（全速读盘会让捕获调度停摆、锁不住星）；输入按 raw + .tag 约定（缺 .tag 提示 tag file open error 但可从文件头播）。</p>
        <p><span class="exec-summary-label">要点四</span>&nbsp;&nbsp;PVT 配置必须与场景注入匹配（三态实验定量定案）：atmosphere off 场景须用 IONOOPT_OFF+TROPOPT_OFF 编译版（3D 0.22 m，错扣大气则 11.41 m）；sv_clock=true 场景卫星钟差改正必须保留（错关致 3D 4.65 m）。改动点集中在 src/sdr_pvt.c update_sol() 一个函数。</p>
      </td></tr>
    </tbody>
  </table>
</section>

<section role="cover">
  <nav class="doc-toc" aria-label="文档目录">
    <p class="toc-title">目录</p>
    <ol class="toc-list">
      <li><a href="#section-1">执行摘要</a></li>
      <li><a href="#section-2">一、形态与工具总览</a></li>
      <li><a href="#section-3">二、本地构建（本机已验证配方）</a></li>
      <li><a href="#section-4">三、文件回放 pocket_trk（主用法）</a></li>
      <li><a href="#section-5">四、快速快照诊断 pocket_acq_new</a></li>
      <li><a href="#section-6">五、Web UI（pocket_web）与 Python 孪生</a></li>
      <li><a href="#section-7">六、与 gnss-sim 互验的配置匹配要点（定量定案）</a></li>
      <li><a href="#section-8">七、常用命令速查</a></li>
      <li><a href="#section-9">附录：产物与复现索引</a></li>
    </ol>
  </nav>
</section>

<section role="body" data-page-restart="1">

  <h1 id="section-2">一、形态与工具总览</h1>
  <p>PocketSDR 仓库 app/ 下共 10 个工具目录（+ makefile），make 即出全部 11 个 exe，无外部依赖（FFT 自带 pocketfft 头文件库）：</p>
  <table>
    <thead>
      <tr><th>工具</th><th>用途</th><th>互验常用度</th></tr>
    </thead>
    <tbody>
      <tr><td>pocket_trk</td><td>SDR 跟踪 + PVT 解算（核心，实时/文件双用）</td><td>主用</td></tr>
      <tr><td>pocket_acq（pocket_acq_new.exe）</td><td>快照式捕获分析，秒出逐星 C/N₀/多普勒/COFF</td><td>排障利器</td></tr>
      <tr><td>pocket_snap / pocket_scan / pocket_dump / pocket_conf / pocket_calib</td><td>快照、扫频、转储、配置、校准</td><td>辅助</td></tr>
      <tr><td>pocket_web</td><td>Web UI 接收机（见第五节）</td><td>演示</td></tr>
      <tr><td>str2str / convbin</td><td>流转发、RTCM 转 RINEX（RTKLIB 沿用）</td><td>按需</td></tr>
    </tbody>
  </table>
  <p>另有 python/ 纯 Python 模块组（pocket_trk.py、pocket_acq.py、pocket_sdr.py、sdr_ch.py、sdr_nav.py、sdr_ldpc.py 等），与 C 侧链路同构，适合读源码学算法。</p>

  <h1 id="section-3">二、本地构建（本机已验证配方）</h1>
  <p>Windows（Git Bash + winlibs GCC 16.2，路径 D:\\workbuddy\\tools\\mingw64）一条命令产出硬件无关静态版：</p>
  <pre>cd /d/workbuddy/GNSSSignal/PocketSDR
/d/workbuddy/tools/mingw64/bin/g++.exe -O3 -w -std=c++20 -x c++ -DWIN32 \\
  -Isrc -Ilib/RTKLIB/src -Ilib/cyusb -Ilib/pocketfft \\
  app/pocket_trk/pocket_trk.c \\
  src/sdr_pvt.c src/sdr_array.c src/sdr_ch.c src/sdr_cmn.c src/sdr_code.c \\
  src/sdr_code_gal.c src/sdr_conf.c src/sdr_fec.c src/sdr_func.c src/sdr_ldpc.c \\
  src/sdr_nav.c src/sdr_nb_ldpc.c src/sdr_rcv.c src/sdr_web.c \\
  test/src/sdr_dev_stub.c test/src/sdr_sdev_stub.c test/src/sdr_usb_stub.c \\
  lib/win32/librtk.a lib/win32/libpocketfft.a \\
  -lpthread -lws2_32 -lwinmm -static -o local_build/pocket_trk_local.exe</pre>
  <p>要点：</p>
  <p>1. -DWIN32 必带，否则编译在 sys/select.h 挂掉。</p>
  <p>2. test/src/ 三个 stub（sdr_dev/sdr_sdev/sdr_usb）替换 USB/设备硬件层，产出的 exe 不依赖真实前端即可回放文件。</p>
  <p>3. 要改 PVT 行为（见第六节），把 src/sdr_pvt.c 换成修改版文件、其余不动即可——本会话的 4 个 A/B 变体就是这么出的。</p>
  <p>4. 预编译库 lib/win32/ 提供 librtk.a（RTKLIB 全量对象）与 libpocketfft.a，Linux 侧有对应 .so。</p>
  <p>5. 作者原版 Linux make 路径同样可用（一次出 11 个 exe）。</p>

  <h1 id="section-4">三、文件回放 pocket_trk（主用法）</h1>
  <p>实测命令模板（对 gnss-sim 场景 60 s/12 星 CS16/25 Msps）：</p>
  <pre>local_build/pocket_trk_local.exe \\
  -sig L1CA -prn 4,5,9,11,12,18,20,25,26,28,29,31 \\
  -fmt CS16 -f 25 -fo 1575.42 -IQ 2 \\
  -tscale 1 -ti 10 \\
  -log run.log -nmea run.nmea \\
  path/to/gpssim.bin</pre>
  <p>参数速查：</p>
  <table>
    <thead>
      <tr><th>参数</th><th>含义</th><th>实测注意点</th></tr>
    </thead>
    <tbody>
      <tr><td>-fmt CS16</td><td>8bit I / 8bit Q 复数交织格式</td><td>与 gnss-sim int8 输出逐字节兼容</td></tr>
      <tr><td>-f 25</td><td>采样率 25 Msps</td><td>必须与仿真 fs 一致</td></tr>
      <tr><td>-fo 1575.42</td><td>RF 中心频率，单位 MHz</td><td>写成 Hz 直接废</td></tr>
      <tr><td>-IQ 2</td><td>交织 IQ 存放</td><td>—</td></tr>
      <tr><td>-tscale 1</td><td>按实时速率灌入</td><td>必带：全速读盘会让捕获调度 update_srch_ch 停摆、锁不住星</td></tr>
      <tr><td>-ti 10</td><td>定位输出间隔 10 s</td><td>60 s 场景得 6 条 FIX 行</td></tr>
      <tr><td>-log path / -nmea path / -rtcm path</td><td>输出流，可重复至多 8 路</td><td>建议落仓内路径；$POS 行含 lat/lon/椭高/ns/UR</td></tr>
      <tr><td>-prn 列表</td><td>指定跟踪 PRN</td><td>与仿真星表一致</td></tr>
      <tr><td>-NO_SYNC / -fd dopp</td><td>关符号同步 / 多普勒初值</td><td>按需</td></tr>
    </tbody>
  </table>
  <p>输入文件约定：原始 IQ 文件 + 同名 .tag 尾部标签（gps-sdr-sim 系产物的 SDR 圈事实标准）。无 .tag 会打印 tag file open error 并从文件头开始播，互验可用。</p>
  <p>输出解读：stdout 的 LOCK 行给出逐星锁定秒数、C/N₀、COFF、多普勒、NAV 字数；状态行 ns/nsat FIX LOCK: x/12 为解算健康度。60 s/12 星 SNR −18.33 dB 场景的合格基线：12/12 锁定、9/12 FIX（剔 3 颗低仰角星系 RTKLIB EL_MASK=15° 所致，属正常）。</p>

  <h1 id="section-5">四、快速快照诊断 pocket_acq_new</h1>
  <p>不经缓冲/调度直读文件，秒出逐星 C/N₀、多普勒、COFF，是排查"锁不住/星数少"的首选：</p>
  <pre>app/pocket_acq/pocket_acq_new.exe -sig L1CA -prn &lt;prn列表&gt; \\
  -fmt CS16 -f 25 -tint 20 -toff 5000 &lt;file&gt;</pre>
  <p>注意：-tint/-toff 单位毫秒、-nz 关零填充、-d 多普勒窗单位 Hz。与 pocket_trk 的分工：pocket_acq_new 回答"信号在不在、多强"，pocket_trk 回答"能不能跟踪并解出位置"。</p>

  <h1 id="section-6">五、Web UI（pocket_web）与 Python 孪生</h1>
  <p>Web 形态（README 原文用法，实时接收机演示）：</p>
  <pre>cd &lt;install_dir&gt;/bin
sudo ./pocket_web -web 8080</pre>
  <p>浏览器打开 http://localhost:8080/ 。接收机初始为停止态：在 Input / Output / Signal Options 页设置输入源、输出流与信号后按 Start；设置在停止与退出时自动保存、下次恢复，加 -start 可直接带设置自启。局域网他机访问用 sudo ./pocket_web -web 0.0.0.0:8080——注意官方原文警告：该界面无认证、无加密，仅限可信网络。</p>
  <p>python/ 目录是 C 链路的纯 Python 孪生（pocket_trk.py/pocket_acq.py/sdr_ch.py/sdr_nav.py/sdr_ldpc.py 等），适合理解捕获-跟踪-电文算法细节，不适合当生产工具。</p>

  <h1 id="section-7">六、与 gnss-sim 互验的配置匹配要点（定量定案）</h1>
  <p>互验的前提是"接收机改正 ↔ 场景注入"逐维对齐。三态编译实验（同一 12 星场景、同一命令行，仅改 update_sol()）给出定量结论：</p>
  <table>
    <thead>
      <tr><th>变体</th><th>大气改正</th><th>钟差改正</th><th>3D 误差</th><th>FIX/星</th><th>LOCK</th></tr>
    </thead>
    <tbody>
      <tr><td>基线（作者原版）</td><td>开（错扣）</td><td>开</td><td>11.41 m</td><td>9/12</td><td>12/12</td></tr>
      <tr><td>场景匹配版</td><td>关</td><td>留</td><td>0.22 m</td><td>9/12</td><td>12/12</td></tr>
      <tr><td>错关钟差对照</td><td>关</td><td>关</td><td>4.65 m</td><td>9/12</td><td>12/12</td></tr>
    </tbody>
  </table>
  <p>操作要点：</p>
  <p>1. 大气：场景 atmosphere off 时须用 IONOOPT_OFF+TROPOPT_OFF 编译版——改 src/sdr_pvt.c update_sol()（L1129-1130）两行后按第二节配方重编即可（现成产物 local_build/pvt_both_off.exe）。假扣的 Saastamoinen+Klobuchar 仰角相关延迟会被最小二乘映射到垂直方向（−11.45 m 根因，详见互验报告第十章）。</p>
  <p>2. 卫星钟差：场景 sv_clock=true 时改正必须保留。afzero2 星历下接收机 dts＝纯相对论偏心率项（实测 11 星振幅 mean 0.45 m、max 1.02 m/星），与注入真值一致；错关会把该项全量留在伪距上，per-star 确定性偏置经 9 星最小二乘几何放大成 3D 4.65 m 固定方向偏差（对照变体 pvt_satclk_off.exe）。</p>
  <p>3. 不要动的：EL_MASK=15°（只决定剔星数 9/12，非精度因素）、RAIM-FDE posopt[4]=1（无粗差可剔，中性）。</p>
  <p class="callout-warn">&nbsp;&nbsp;判读：三变体 LOCK 12/12、FIX 9/12 完全一致——配置错配是纯 PVT 层系统偏差，与捕获/跟踪无关；如果连锁定都不正常，先回第四节用 pocket_acq_new 查信号本身。</p>

  <h1 id="section-8">七、常用命令速查</h1>
  <pre># 建（第二节配方省略号处换变体源）
g++.exe ... -o local_build/&lt;name&gt;.exe

# 秒级快照
pocket_acq_new.exe -sig L1CA -prn &lt;列表&gt; -fmt CS16 -f 25 -tint 20 -toff 5000 &lt;file&gt;

# 端到端回放（互验标准姿势）
pocket_trk_local.exe -sig L1CA -prn &lt;列表&gt; -fmt CS16 -f 25 -fo 1575.42 \\
  -IQ 2 -tscale 1 -ti 10 -log &lt;log&gt; -nmea &lt;nmea&gt; &lt;gpssim.bin&gt;

# 场景匹配版回放（atmosphere off 场景）
pvt_both_off.exe  &lt;同上参数&gt;

# 真值统计（本仓库自带）
.venv/Scripts/python.exe output/pvt_config_exp_20261115/analyze.py &lt;目录&gt;</pre>

  <h1 id="section-9">附录：产物与复现索引</h1>
  <ul>
    <li>本机可用 exe：PocketSDR/local_build/（pocket_trk_local.exe 正式；pvt_both_off / pvt_iono_off / pvt_tropo_off / pvt_satclk_off.exe 为配置实验变体；pocket_trk_dbg/agc/log4.exe 为诊断变体）。</li>
    <li>三态实验全量数据与复现：output/pvt_config_exp_20261115/（bl2/bo2/sco 三套 log+nmea+stdout、analyze.py、results.md）。</li>
    <li>深度分析与根因取证：output/pocketsdr_verify_20261113T223203/（《PocketSDR 深入分析与 gnss-sim 第三方互验报告》docx，含第十二章三态实验）。</li>
    <li>互验冒烟场景：out/20261113T033315803665/gpssim.bin（Tampere 12 星，6 GB，60 s，CS16/25 Msps，真值 60.182537°N 24.82826°E 椭高 47.248 m）。</li>
    <li>Web UI 用法出处：PocketSDR README.md L540-560（pocket_web -web 8080）。</li>
  </ul>

</section>

</body>
</html>
"""

out = head + CONTENT
io.open(OUT, "w", encoding="utf-8").write(out)
print("written", OUT, len(out), "chars")
