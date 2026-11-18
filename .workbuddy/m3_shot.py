import sys
sys.path.insert(0, ".")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from desktop.ui import theme
from desktop.ui.main_window import MainWindow
from desktop.core.session import Session

app = QApplication([])
app.setStyleSheet(theme.QSS)
s = Session()
win = MainWindow(s)
t = s.current()
t.name = "M3验收"

# 轨迹页：线性生成 + 应用
win.pages["traj"]._gen_linear()
win.pages["traj"]._apply_to_task()
win.goto("traj")
win.show()

dlg = None
def phase2():
    win.grab().save("output/desktop_app/shots_m1/win_traj_gen.png")
    win.goto("sim")
    QTimer.singleShot(600, phase3)

def phase3():
    win.grab().save("output/desktop_app/shots_m1/win_sim_map.png")
    from desktop.ui.settings import SettingsDialog
    global dlg
    dlg = SettingsDialog(win)
    dlg.show()
    QTimer.singleShot(600, phase4)

def phase4():
    dlg.grab().save("output/desktop_app/shots_m1/win_settings.png")
    print("M3-SHOTS OK")
    app.quit()

QTimer.singleShot(1200, phase2)
QTimer.singleShot(45000, app.quit)
app.exec()
