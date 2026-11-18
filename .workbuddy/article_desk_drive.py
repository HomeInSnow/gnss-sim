# -*- coding: utf-8 -*-
"""公众号文章桌面版驱动：gnss-sim Desktop 全流程跑文章场景并截图。

场景（与文章一致）：坦佩雷 60.182537/24.82826/47.248，
2023-09-28 23:20 UTC 起 60s，GPS L1C/A 单频，25 Msps int16，
Klobuchar+Saastamoinen 注入 IQ，卫星钟差开（SimTask 默认），RINEX AUTO。

流程：配置→截图01（配置态）→Preview→截图02（星空+可见星表）
→Generate→截图03（完成态）→Verify（关跟踪/trace，快照解）→截图04
→日志页截图05。验证完成后 print 结果关键数字（TRUTH 供正文引用）。

用法：.venv/Scripts/python.exe .workbuddy/article_desk_drive.py
"""
import sys

sys.path.insert(0, ".")
from PySide6.QtCore import QTimer, QDateTime, QDate, QTime
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

IMG = "output/wechat_l1ca_article/img/"

app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
sim = win.pages["sim"]
v = win.pages["verify"]

# ── 配置（坦佩雷文章场景）────────────────────────────────────────
win.goto("sim")
win.show()
sim.dt_start.setDateTime(QDateTime(QDate(2023, 9, 28), QTime(23, 20, 0)))
sim.ed_dur.setText("60")
sim.cb_sr.setCurrentText("25000000")
sim.cb_fmt.setCurrentText("int16")
sim.ed_rinex.setText("AUTO")
sim.cb_iono.setCurrentText("klobuchar")
sim.cb_tropo.setCurrentText("saastamoinen")
sim.ck_models_iq.setChecked(True)          # 大气注入 IQ
sim.ck_imp.setChecked(True)                # 损伤注入：高斯白噪声（与文章场景同参数）
sim.ed_impsnr.setText("-18.33")
sim.ed_impseed.setText("2281271")
sim.ed_lat.setText("60.182537")
sim.ed_lon.setText("24.82826")
sim.ed_alt.setText("47.248")
sim._cfg_scroll.verticalScrollBar().setValue(0)
sim.store_task()
QTimer.singleShot(1200, lambda: (win.grab().save(IMG + "01_desk_config.png"),
                                 print("SHOT 01"), sim.btn_preview.click()))

state = {"phase": "preview", "t": 0, "runid": ""}


def poll():
    state["t"] += 2
    if state["phase"] == "preview":
        if sim.tbl.rowCount() > 0:
            dop = (s.current().last_preview or {}).get("dop", {})
            print("PREVIEW sats", sim.tbl.rowCount(),
                  "pdop", dop.get("pdop"), "gdop", dop.get("gdop"))
            sim._cfg_scroll.verticalScrollBar().setValue(0)
            win.grab().save(IMG + "02_desk_preview.png")
            print("SHOT 02")
            state["phase"] = "gen"
            state["t"] = 0
            sim.btn_gen.click()
            return
    elif state["phase"] == "gen":
        txt = sim.hint.text()
        if "生成完成" in txt:
            state["runid"] = s.last_outdir
            print("GEN", txt)
            win.grab().save(IMG + "03_desk_generate.png")
            print("SHOT 03")
            state["phase"] = "verify"
            state["t"] = 0
            win.goto("verify")
            v.ed_outdir.setText(state["runid"])
            v.cb_track.setChecked(False)   # 快照解：快、稳
            if hasattr(v, "cb_trace"):
                v.cb_trace.setChecked(True)   # 逐历元 trace：填 04 图码相位曲线
            # ── 捕获质量门限自动定标：全 PRN 扫度量，取真假星度量间隙中点 ──
            from backend import inspector
            import numpy as np  # noqa: F401
            real = {4, 5, 9, 11, 12, 18, 20, 25, 26, 28, 29, 31}
            iq = inspector.read_iq(f"out/{state['runid']}/gpssim.bin",
                                   "int16", int(25e6 * 0.020))
            met = {}
            for prn in range(1, 33):
                met[prn] = float(inspector.acquire(iq, 25e6, prn)["metric_db"])
            false_max = max(v2 for p, v2 in met.items() if p not in real)
            true_min = min(v2 for p, v2 in met.items() if p in real)
            print("GATE false_max", round(false_max, 2), "true_min",
                  round(true_min, 2), "PRN2", round(met.get(2, 0), 2), flush=True)
            if true_min > false_max + 1.0:
                gate = round((false_max + true_min) / 2.0, 1)
                if gate > 9.0:
                    v.ed_mindb.setText(str(gate))
                    print("GATE set min_db", gate, flush=True)
            v.run_verify()
            return
    elif state["phase"] == "verify":
        txt = v.status_lbl.text()
        if "完成" in txt or "失败" in txt:
            res = v._result or {}
            print("VERIFY", txt, "| runid", state["runid"])
            for k in ("error_m", "pdop", "rms_m", "residual_rms_m", "n_sv",
                      "fix", "lat", "lon", "alt", "clock_s", "prns_used",
                      "llh", "clock_bias_s"):
                if k in res:
                    print("  ", k, "=", res[k])
            if res.get("error_budget"):
                print("   error_budget =", res["error_budget"])
            print("  keys:", sorted(res.keys())[:20])
            psv = res.get("per_sv") or res.get("svs") or {}
            if psv:
                k0 = next(iter(psv.values())) if psv else {}
                print("  per_sv n=", len(psv), "row keys:", sorted(k0.keys())[:16])
                try:
                    emx = max(abs(float((x or {}).get("err_chips", 0)))
                              for x in psv.values())
                    print("  max|err_chips| =", emx)
                except Exception as e:
                    print("  err_chips parse:", e)
            win.pages["verify"].grab().save(IMG + "04_desk_verify.png")
            print("SHOT 04")
            state["phase"] = "log"
            state["t"] = 0
            win.goto("log")
            return
    elif state["phase"] == "log":
        win.grab().save(IMG + "05_desk_log.png")
        print("SHOT 05")
        print("ARTICLE-DRIVE-OK runid", state["runid"])
        app.quit()
        return
    if state["t"] > 900:
        print("TIMEOUT at", state["phase"], sim.hint.text(), v.status_lbl.text())
        app.quit()


tm = QTimer()
tm.timeout.connect(poll)
QTimer.singleShot(1500, lambda: (tm.start(2000)))
sys.exit(app.exec())
