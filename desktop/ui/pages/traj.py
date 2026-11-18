# -*- coding: utf-8 -*-
"""轨迹页（M3）：航点表 + pyqtgraph 平面轨迹 + 线性航线生成 + 应用到任务。"""
from __future__ import annotations

import math

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QFileDialog)

import pyqtgraph as pg

from .. import theme
from ..widgets import Card

pg.setConfigOptions(background=theme.BG, foreground=theme.MUT,
                    antialias=True)


class TrajPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.session = win.session
        self._editing = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        c = Card("航点编辑", "route = [[lat,lon,alt],…] → 生成时下发")
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["点名", "纬度 °", "经度 °", "高程 m"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemChanged.connect(lambda *_: (None if self._editing
                                                 else self._redraw()))
        c.body.addWidget(self.tbl, 3)
        row = QHBoxLayout()
        for text, slot in (("添加航点", self._add_wp), ("删除选行", self._del_wp),
                           ("清空", self._clear), ("保存 JSON", self._save_json),
                           ("载入 JSON", self._load_json)):
            b = QPushButton(text)
            b.setObjectName("FileBtn")
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        b_apply = QPushButton("✔ 应用到当前任务")
        b_apply.setObjectName("Primary")
        b_apply.clicked.connect(self._apply_to_task)
        row.addWidget(b_apply)
        c.body.addLayout(row)
        lay.addWidget(c, 3)

        gen = Card("线性航线生成器", "LLA Manipulation")
        g = QHBoxLayout()
        self.ed_bearing = self._line("90", "方位 °")
        self.ed_speed = self._line("30", "速度 m/s")
        self.ed_step = self._line("10", "间隔 s")
        self.ed_nwp = self._line("20", "点数")
        for lab, w in (("方位 °", self.ed_bearing), ("速度 m/s", self.ed_speed),
                       ("间隔 s", self.ed_step), ("点数", self.ed_nwp)):
            g.addWidget(QLabel(lab))
            g.addWidget(w, 1)
        b_gen = QPushButton("从任务位置生成")
        b_gen.setObjectName("Ghost")
        b_gen.clicked.connect(self._gen_linear)
        g.addWidget(b_gen)
        gen.body.addLayout(g)
        lay.addWidget(gen)

        c2 = Card("平面轨迹预览")
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        self.plot.setLabel("bottom", "东向 m")
        self.plot.setLabel("left", "北向 m")
        self.plot.setMinimumHeight(220)
        c2.body.addWidget(self.plot, 1)
        lay.addWidget(c2, 2)

    def _line(self, text, ph=""):
        e = QLineEdit(text)
        if ph:
            e.setPlaceholderText(ph)
        return e

    def on_show(self):
        t = self.session.current()
        if t.route and self.tbl.rowCount() == 0:
            self.load_route(t.route)

    # ══ 表操作 ═════════════════════════════════════════════════════
    def _rows(self) -> list:
        out = []
        for r in range(self.tbl.rowCount()):
            try:
                lat = float(self.tbl.item(r, 1).text())
                lon = float(self.tbl.item(r, 2).text())
                alt = float(self.tbl.item(r, 3).text() or 0)
                out.append([lat, lon, alt])
            except (ValueError, AttributeError):
                continue
        return out

    def _add_wp(self):
        t = self.session.current()
        rows = self._rows()
        lat, lon = (rows[-1][0], rows[-1][1]) if rows else (t.lat, t.lon)
        self._insert_row(f"P{self.tbl.rowCount() + 1}", lat, lon, t.alt)
        self._redraw()

    def _insert_row(self, name, lat, lon, alt):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        self._editing = True
        for col, v in ((0, name), (1, f"{lat:.7f}"), (2, f"{lon:.7f}"),
                       (3, f"{alt:.2f}")):
            it = QTableWidgetItem(str(v))
            self.tbl.setItem(r, col, it)
        self._editing = False

    def _del_wp(self):
        r = self.tbl.currentRow()
        if r >= 0:
            self.tbl.removeRow(r)
            self._redraw()

    def _clear(self):
        self.tbl.setRowCount(0)
        self.plot.clear()

    def _gen_linear(self):
        t = self.session.current()
        try:
            brg = math.radians(float(self.ed_bearing.text()))
            spd = float(self.ed_speed.text())
            stp = float(self.ed_step.text())
            n = max(2, int(self.ed_nwp.text()))
        except ValueError:
            self.win.log("线性生成参数无效", "warn")
            return
        self.tbl.setRowCount(0)
        d = spd * stp
        lat, lon = t.lat, t.lon
        for i in range(n):
            self._insert_row(f"P{i + 1}", lat, lon, t.alt)
            dn = d * math.cos(brg)
            de = d * math.sin(brg)
            lat += dn / 111320.0
            lon += de / (111320.0 * math.cos(math.radians(lat)))
        self._redraw()
        self.win.log(f"线性航线生成：{n} 点 × {d:.0f} m", "ok")

    def _apply_to_task(self):
        rows = self._rows()
        t = self.session.current()
        if len(rows) < 2:
            self.win.log("航点不足 2 个，任务 route 已清除（静态点）", "warn")
            t.route = None
        else:
            t.route = rows
            self.win.log(f"任务 {t.name} 已挂轨迹 {len(rows)} 点"
                         "（Generate 将按 route 运动）", "ok")
        self.session.save()
        self.win.pages["sim"].load_task(t)
        self.win.refresh_tasks(select_current=True)

    def _save_json(self):
        p, _ = QFileDialog.getSaveFileName(self, "保存轨迹", "route.json",
                                           "JSON (*.json)")
        if p:
            import json
            try:
                json.dump({"route": self._rows()},
                          open(p, "w", encoding="utf-8"), indent=1)
                self.win.log(f"轨迹已保存：{p}", "ok")
            except OSError as e:
                self.win.log(f"保存失败：{e}", "bad")

    def _load_json(self):
        p, _ = QFileDialog.getOpenFileName(self, "载入轨迹", "",
                                           "JSON (*.json)")
        if not p:
            return
        try:
            import json
            route = json.load(open(p, encoding="utf-8")).get("route", [])
        except (OSError, ValueError) as e:
            self.win.log(f"载入失败：{e}", "bad")
            return
        self.load_route(route)

    def load_route(self, route: list):
        self.tbl.setRowCount(0)
        for i, wp in enumerate(route or []):
            self._insert_row(f"P{i + 1}", wp[0], wp[1],
                             wp[2] if len(wp) > 2 else 0.0)
        self._redraw()

    # ══ 平面图 ═════════════════════════════════════════════════════
    def _redraw(self):
        rows = self._rows()
        self.plot.clear()
        if len(rows) < 2:
            return
        lat0 = math.radians(sum(r[0] for r in rows) / len(rows))
        x = [(r[1] - rows[0][1]) * 111320.0 * math.cos(lat0) for r in rows]
        y = [(r[0] - rows[0][0]) * 111320.0 for r in rows]
        self.plot.plot(x, y, pen=pg.mkPen(theme.ACC, width=1.8),
                       symbol="o", symbolSize=7,
                       symbolBrush=pg.mkBrush(theme.ACC))
        st = pg.ScatterPlotItem(size=12, brush=pg.mkBrush(theme.ACC2),
                                pen=pg.mkPen(theme.BG, width=1))
        st.setData([x[0]], [y[0]])
        self.plot.addItem(st)
        en = pg.ScatterPlotItem(size=12, brush=pg.mkBrush(theme.WARN),
                                pen=pg.mkPen(theme.BG, width=1))
        en.setData([x[-1]], [y[-1]])
        self.plot.addItem(en)
        self.plot.setTitle(f"{len(rows)} 航点（起=绿 终=橙）")
