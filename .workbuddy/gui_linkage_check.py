# -*- coding: utf-8 -*-
"""task#101 联动修复行为验证 + 界面取证截图。

判据: LINKAGE-OK + output/linkage/30_sim_newcontrols.png + 31_verify_newcontrols.png
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

SHOT = "output/linkage/"
os.makedirs(SHOT, exist_ok=True)

fails = []


def ck(name, cond):
    print(("PASS " if cond else "FAIL ") + name, flush=True)
    if not cond:
        fails.append(name)


app = QApplication(sys.argv)
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
sim = win.pages["sim"]
v = win.pages["verify"]
win.goto("sim")
win.show()

# A2: OSNMA 只对 E 生效
sim.chip_sys.set_selected(["G", "E"])
sim.chip_sys.changed.emit()
sim.ck_osnma.setChecked(True)
ck("osnma enabled with E", sim.ck_osnma.isEnabled() and sim.ck_osnma.isChecked())
sim.chip_sys.set_selected(["G"])
sim.chip_sys.changed.emit()
ck("osnma auto-unchecked without E", not sim.ck_osnma.isChecked())
ck("osnma disabled without E", not sim.ck_osnma.isEnabled())

# B1: precise 模式启用降级 checkbox
ck("fb disabled in broadcast", not sim.ck_fb.isEnabled())
sim.cb_ephmode.setCurrentText("precise")
ck("fb enabled in precise", sim.ck_fb.isEnabled() and sim.ed_sp3.isEnabled())
sim.cb_ephmode.setCurrentText("broadcast")

# A3: 衰落模式联动
sim.cb_fade.setCurrentIndex(max(0, sim.cb_fade.findData("keyed")))
ck("keyed -> key widgets on", sim.ed_fadekey.isEnabled()
   and sim.btn_faderand.isEnabled() and sim.ck_faderec.isEnabled()
   and not sim.ed_fadeseed.isEnabled())
sim.cb_fade.setCurrentIndex(max(0, sim.cb_fade.findData("seeded")))
ck("seeded -> seed on key off", sim.ed_fadeseed.isEnabled()
   and not sim.ed_fadekey.isEnabled())
sim.cb_fade.setCurrentIndex(max(0, sim.cb_fade.findData("off")))

# B2/B3: 新控件进 body
sim.chip_sys.set_selected(["G", "E", "C"])
sim.ck_svclock.setChecked(False)
sim.ed_mask.setText("12")
t = sim.store_task()
b = t.generate_body()
ck("sv_clock False in body", b.get("sv_clock") is False)
ck("mask_deg in preview body", t.preview_body().get("mask_deg") == 12.0)
b2 = t.generate_body()
b2.pop("sv_clock")  # 仅键存在性检查（值已在上面查）
ck("fallback key absent in broadcast",
   "fallback_to_broadcast" not in b2)
sim.cb_ephmode.setCurrentText("precise")
sim.ck_fb.setChecked(True)
b3 = sim.store_task().generate_body()
ck("fallback True in precise body",
   b3.get("fallback_to_broadcast") is True)
sim.ck_svclock.setChecked(True)
sim.cb_ephmode.setCurrentText("broadcast")

# A4: 切换任务固化编辑
sim.ed_dur.setText("77")
sim._task_btns_ = None  # noqa - just placeholder no-op
win._select_task(1 if len(s.tasks) > 1 else 0)
sim.load_task(s.current())
if len(s.tasks) > 1:
    prev = s.tasks[0]
    win._select_task(0)
    sim.load_task(s.tasks[0])
    ck("switch keeps edited duration", s.tasks[0].duration_s == 77)

sim._cfg_scroll.verticalScrollBar().setValue(0)
win.grab().save(SHOT + "30_sim_newcontrols.png")
win.goto("verify")
win.grab().save(SHOT + "31_verify_newcontrols.png")
print("SCREENSHOTS-SAVED", flush=True)
print("LINKAGE-OK" if not fails else f"LINKAGE-FAIL {fails}", flush=True)
app.quit()
