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
win.goto("sim")
win.show()

def go():
    scr = win.pages["sim"]._cfg_scroll
    scr.verticalScrollBar().setValue(scr.verticalScrollBar().maximum())
    QTimer.singleShot(700, snap)

def snap():
    win.grab().save("output/desktop_app/shots_m1/win_sim_map.png")
    print("MAP-SHOT OK")
    app.quit()

QTimer.singleShot(1500, go)
QTimer.singleShot(40000, app.quit)
app.exec()
