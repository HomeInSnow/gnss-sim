# -*- coding: utf-8 -*-
"""深空蓝黑 v2 高对比主题：提亮底色分层与次级文字，表头/时间戳可读性优先。"""

BG      = "#0d1424"
PANEL   = "#161f33"
PANEL2  = "#1d2946"
FIELD   = "#101a2f"
LINE    = "#3a4d78"
LINE2   = "#28395c"
TXT     = "#f2f7ff"
MUT     = "#b6c5de"
DIM     = "#8ea3c6"
ACC     = "#5ecbff"
ACC2    = "#46e8ad"
WARN    = "#ffc46b"
BAD     = "#ff7d90"

SYS_COLOR = {"G": ACC, "R": BAD, "E": ACC2, "C": WARN, "J": "#b48cff",
             "S": MUT, "I": "#a3e635"}

FONT_UI    = "'Microsoft YaHei UI','Segoe UI',sans-serif"
FONT_MONO  = "'Consolas','JetBrains Mono',monospace"

QSS = f"""
QWidget {{ background:{BG}; color:{TXT}; font-family:{FONT_UI}; font-size:13px; }}
QMainWindow, QDialog {{ background:{BG}; }}

QFrame#Card {{ background:{PANEL}; border:1px solid {LINE2}; border-radius:12px; }}
QLabel#CardTitle {{ color:{ACC}; font-weight:700; font-size:13px; letter-spacing:1px; }}
QLabel#CardTag {{ color:{DIM}; font-size:11px; }}
QLabel {{ background:transparent; }}
QLabel#Mut {{ color:{MUT}; }}
QLabel#DimTxt {{ color:{DIM}; font-size:11px; }}
QLabel#MonoVal {{ font-family:{FONT_MONO}; color:{TXT}; }}
QLabel#StatV {{ font-family:{FONT_MONO}; font-size:26px; font-weight:700; color:{ACC2}; }}
QLabel#StatVB {{ font-family:{FONT_MONO}; font-size:26px; font-weight:700; color:{ACC}; }}
QLabel#StatK {{ color:{MUT}; font-size:11px; letter-spacing:1px; }}
QLabel#StatS {{ color:{DIM}; font-size:10px; font-family:{FONT_MONO}; }}
QLabel#RailPage {{ color:{ACC}; font-weight:700; font-size:15px; letter-spacing:2px; }}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateTimeEdit, QPlainTextEdit, QTableWidget {{
  background:{FIELD}; border:1px solid {LINE}; border-radius:7px; padding:5px 8px;
  color:{TXT}; font-family:{FONT_MONO}; font-size:12px; selection-background-color:{ACC};
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus,
QDateTimeEdit:focus, QPlainTextEdit:focus {{ border:1px solid {ACC}; }}
QComboBox::drop-down {{ border:none; width:20px; }}
QComboBox QAbstractItemView {{ background:{FIELD}; border:1px solid {LINE};
  selection-background-color:{PANEL2}; color:{TXT}; }}

QPushButton#Primary {{
  background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #38a8ff, stop:1 #2ee6b0);
  color:#04121f; font-weight:800; border:none; border-radius:9px;
  padding:10px 24px; font-size:14px;
}}
QPushButton#Primary:disabled {{ color:#5a7396; background:{PANEL2}; }}
QPushButton#Ghost {{ background:{PANEL2}; color:{ACC}; border:1px solid rgba(94,203,255,.45);
  border-radius:9px; padding:9px 18px; font-weight:700; }}
QPushButton#Ghost:hover {{ border:1px solid {ACC}; }}
QPushButton#FileBtn {{ background:{PANEL2}; color:{MUT}; border:1px solid {LINE};
  border-radius:7px; padding:5px 10px; font-size:11px; }}
QPushButton#Chip {{ background:{FIELD}; color:{MUT}; border:1px solid {LINE};
  border-radius:11px; padding:3px 12px; font-family:{FONT_MONO}; font-size:11px; }}
QPushButton#Chip:checked {{ background:{ACC}; color:#06121f; font-weight:800;
  border:1px solid {ACC}; }}
QPushButton#RailBtn {{ background:transparent; border:none; color:{DIM};
  font-size:11px; padding:8px 2px; }}
QPushButton#RailBtn:hover {{ color:{TXT}; }}
QPushButton#RailBtn:checked {{ color:{ACC}; background:rgba(94,203,255,.10);
  border:1px solid rgba(94,203,255,.30); border-radius:10px; }}
QPushButton#TaskItem {{ background:{PANEL}; border:1px solid {LINE2};
  border-radius:9px; padding:8px 10px; text-align:left; color:{TXT}; }}
QPushButton#TaskItem:checked {{ border:1px solid rgba(94,203,255,.55);
  background:rgba(94,203,255,.08); }}
QPushButton#Link {{ color:{ACC}; background:transparent; border:none;
  font-size:11px; padding:2px 4px; }}

QCheckBox {{ background:transparent; spacing:6px; }}
QCheckBox::indicator {{ width:14px; height:14px; border:1px solid {LINE};
  border-radius:4px; background:{FIELD}; }}
QCheckBox::indicator:checked {{ background:{ACC}; border:1px solid {ACC}; }}

QProgressBar {{ background:{FIELD}; border:none; border-radius:3px; height:6px; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 {ACC}, stop:1 {ACC2}); border-radius:3px; }}

QTableWidget {{ border:1px solid {LINE2}; border-radius:10px; gridline-color:{LINE2};
  background:{PANEL}; alternate-background-color:{PANEL2}; }}
QHeaderView::section {{ background:{PANEL}; color:{MUT}; border:none;
  border-bottom:1px solid {LINE}; padding:5px 8px; font-size:11px;
  font-weight:700; letter-spacing:1px; }}
QTableWidget::item {{ padding:3px 6px; color:{TXT}; }}
QTableWidget::item:selected {{ background:rgba(94,203,255,.14); }}

QScrollArea {{ border:none; background:transparent; }}
QScrollBar:vertical {{ background:transparent; width:9px; margin:0; }}
QScrollBar::handle:vertical {{ background:{LINE}; border-radius:4px; min-height:24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
QScrollBar:horizontal {{ background:transparent; height:9px; }}
QScrollBar::handle:horizontal {{ background:{LINE}; border-radius:4px; min-width:24px; }}

QFrame#TopBar {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
  stop:0 #17233d, stop:1 #111a2e); border-bottom:1px solid {LINE2}; }}
QFrame#Footer {{ background:#0e1729; border-top:1px solid {LINE2}; }}
QLabel#Foot {{ color:{DIM}; font-family:{FONT_MONO}; font-size:10px; }}
QLabel#Logo {{ font-size:15px; font-weight:800; color:{ACC}; }}
QLabel#LogoSub {{ color:{MUT}; font-size:11px; }}
QLabel#Dot {{ color:{ACC2}; font-size:14px; }}

QPlainTextEdit#LogView {{ font-family:{FONT_MONO}; font-size:11px; }}

QToolTip {{ background:{PANEL2}; color:{TXT}; border:1px solid {LINE};
  padding:4px 8px; font-size:11px; }}
"""


def mono(text, color=None):
    """表格富文本单元（等宽 + 可选着色）。"""
    c = f" style='color:{color}'" if color else ""
    return f"<span{c} font-family='Consolas'>{text}</span>"
