# -*- coding: utf-8 -*-
"""清淡浅白 v3 浅色主题：冷浅灰底 + 白色卡片，深字高对比。"""

BG      = "#eef2f8"
PANEL   = "#ffffff"
PANEL2  = "#e8eef7"
FIELD   = "#f6f9fc"
LINE    = "#b7c4d8"
LINE2   = "#dbe4ef"
TXT     = "#1b2840"
MUT     = "#4c5e7c"
DIM     = "#67788f"
ACC     = "#0b78c2"
ACC2    = "#0d9668"
WARN    = "#b07203"
BAD     = "#cc3d55"

SYS_COLOR = {"G": ACC, "R": BAD, "E": ACC2, "C": WARN, "J": "#6a4bd0",
             "S": MUT, "I": "#5c8f17"}

FONT_UI    = "'Microsoft YaHei UI','Segoe UI',sans-serif"
FONT_MONO  = "'Consolas','JetBrains Mono',monospace"

QSS = f"""
QWidget {{ background:{BG}; color:{TXT}; font-family:{FONT_UI}; font-size:13px; }}
QMainWindow, QDialog {{ background:{BG}; }}

QFrame#Card {{ background:{PANEL}; border:1px solid {LINE}; border-radius:12px; }}
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
QComboBox QAbstractItemView {{ background:{PANEL}; border:1px solid {LINE};
  selection-background-color:{PANEL2}; color:{TXT}; }}

QPushButton#Primary {{
  background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1478d0, stop:1 #0e9f74);
  color:#ffffff; font-weight:800; border:none; border-radius:9px;
  padding:10px 24px; font-size:14px;
}}
QPushButton#Primary:disabled {{ color:#93a5bd; background:{PANEL2}; }}
QPushButton#Ghost {{ background:{PANEL2}; color:{ACC}; border:1px solid rgba(11,120,194,.40);
  border-radius:9px; padding:9px 18px; font-weight:700; }}
QPushButton#Ghost:hover {{ border:1px solid {ACC}; }}
QPushButton#FileBtn {{ background:{PANEL2}; color:{MUT}; border:1px solid {LINE};
  border-radius:7px; padding:5px 10px; font-size:11px; }}
QPushButton#Chip {{ background:{FIELD}; color:{MUT}; border:1px solid {LINE};
  border-radius:11px; padding:3px 12px; font-family:{FONT_MONO}; font-size:11px; }}
QPushButton#Chip:checked {{ background:{ACC}; color:#ffffff; font-weight:800;
  border:1px solid {ACC}; }}
QPushButton#RailBtn {{ background:transparent; border:none; color:{DIM};
  font-size:11px; padding:8px 2px; }}
QPushButton#RailBtn:hover {{ color:{TXT}; }}
QPushButton#RailBtn:checked {{ color:{ACC}; background:rgba(11,120,194,.08);
  border:1px solid rgba(11,120,194,.30); border-radius:10px; }}
QPushButton#TaskItem {{ background:{PANEL}; border:1px solid {LINE2};
  border-radius:9px; padding:8px 10px; text-align:left; color:{TXT}; }}
QPushButton#TaskItem:checked {{ border:1px solid rgba(11,120,194,.50);
  background:rgba(11,120,194,.06); }}
QPushButton#Link {{ color:{ACC}; background:transparent; border:none;
  font-size:11px; padding:2px 4px; }}

QCheckBox {{ background:transparent; spacing:6px; }}
QCheckBox::indicator {{ width:14px; height:14px; border:1px solid {LINE};
  border-radius:4px; background:{FIELD}; }}
QCheckBox::indicator:checked {{ background:{ACC}; border:1px solid {ACC}; }}

QProgressBar {{ background:{PANEL2}; border:none; border-radius:3px; height:6px; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 {ACC}, stop:1 {ACC2}); border-radius:3px; }}

QTableWidget {{ border:1px solid {LINE2}; border-radius:10px; gridline-color:{LINE2};
  background:{PANEL}; alternate-background-color:{PANEL2}; }}
QHeaderView::section {{ background:{PANEL2}; color:{MUT}; border:none;
  border-bottom:1px solid {LINE}; padding:5px 8px; font-size:11px;
  font-weight:700; letter-spacing:1px; }}
QTableWidget::item {{ padding:3px 6px; color:{TXT}; }}
QTableWidget::item:selected {{ background:rgba(11,120,194,.12); }}

QScrollArea {{ border:none; background:transparent; }}
QScrollBar:vertical {{ background:transparent; width:9px; margin:0; }}
QScrollBar::handle:vertical {{ background:{LINE}; border-radius:4px; min-height:24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
QScrollBar:horizontal {{ background:transparent; height:9px; }}
QScrollBar::handle:horizontal {{ background:{LINE}; border-radius:4px; min-width:24px; }}

QFrame#TopBar {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
  stop:0 #ffffff, stop:1 #eaf0f9); border-bottom:1px solid {LINE2}; }}
QFrame#Footer {{ background:#e8eef6; border-top:1px solid {LINE2}; }}
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
