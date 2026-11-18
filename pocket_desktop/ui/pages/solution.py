# -*- coding: utf-8 -*-
"""定位页：pvt_sol 实时解 + 轨迹（平面/地图）+ 误差曲线（真值联动）。"""
from __future__ import annotations

import math

import pyqtgraph as pg
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from .. import theme
from ..widgets import Card, MapWidget, StatCard

pg.setConfigOptions(background=theme.BG, foreground=theme.MUT, antialias=True)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_pvt(s: str):
    """`2023-09-28 23:21:17.0  lat lon hgt  9/12 FIX` → dict | None。"""
    f = s.split()
    if len(f) < 6:
        return None
    try:
        lat, lon, h = float(f[2]), float(f[3]), float(f[4])
    except ValueError:
        return None
    if abs(lat) < 1e-9 and abs(lon) < 1e-9:       # 无解时输出 0
        return None
    ns = f[5]
    fix = f[6] if len(f) > 6 else ""
    return {"t": f"{f[0]} {f[1]}", "lat": lat, "lon": lon, "h": h,
            "ns": ns, "fix": fix}


class SolutionPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.pts: list[dict] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        # KPI
        kpi = QHBoxLayout()
        kpi.setSpacing(10)
        self.k_fix = StatCard("解算数 / 历元")
        self.k_sat = StatCard("用星 ns/nsat")
        self.k_h = StatCard("水平 RMS / m（vs 真值）", color="blue")
        self.k_v = StatCard("垂直 RMS / m（vs 真值）", color="blue")
        for w in (self.k_fix, self.k_sat, self.k_h, self.k_v):
            kpi.addWidget(w)
        lay.addLayout(kpi)

        row = QHBoxLayout()
        row.setSpacing(10)
        # 实时解 + 轨迹平面 + 误差
        left = QVBoxLayout()
        left.setSpacing(10)
        c1 = Card("实时解算", "pvt_sol")
        self.lbl_now = QLabel("—")
        self.lbl_now.setObjectName("MonoVal")
        self.lbl_now.setStyleSheet("font-size:16px;")
        c1.body.addWidget(self.lbl_now)
        left.addWidget(c1)
        c2 = Card("平面轨迹", "ENU 米，起绿终橙")
        self.pg_xy = pg.PlotWidget()
        self.pg_xy.setAspectLocked(True)
        self.pg_xy.showGrid(x=True, y=True, alpha=0.25)
        self.pg_xy.setMinimumHeight(240)
        c2.body.addWidget(self.pg_xy)
        left.addWidget(c2, 1)
        row.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(10)
        c3 = Card("轨迹地图", "离线世界底图")
        self.map = MapWidget()
        self.map.setMinimumHeight(200)
        c3.body.addWidget(self.map)
        right.addWidget(c3)
        c4 = Card("误差曲线", "水平/垂直 vs 时间")
        self.pg_err = pg.PlotWidget()
        self.pg_err.showGrid(x=True, y=True, alpha=0.25)
        self.pg_err.setMinimumHeight(180)
        c4.body.addWidget(self.pg_err)
        right.addWidget(c4, 1)
        row.addLayout(right, 1)
        lay.addLayout(row, 1)

        self.lbl_hint = QLabel("提示：在控制台页设定真值（或从 gnss-sim run 读取）后误差曲线生效")
        self.lbl_hint.setObjectName("DimTxt")
        lay.addWidget(self.lbl_hint)

    # ── pvt_sol 帧 ──────────────────────────────────────────────
    def reset(self):
        self.pts = []
        self.pg_xy.clear()
        self.pg_err.clear()
        self.lbl_now.setText("—")
        self.map._pos = None
        self.map.update()

    def update_pvt(self, s: str):
        p = parse_pvt(s)
        if p is None:
            return
        self.pts.append(p)
        n = len(self.pts)
        try:
            nsat = int(p["ns"].split("/")[0])
        except (ValueError, IndexError):
            nsat = 0
        self.k_fix.set(n)
        self.k_sat.set(nsat, p["ns"])
        self.lbl_now.setText(
            f"{p['t']}  {p['lat']:.8f}  {p['lon']:.8f}  h={p['h']:.3f}  "
            f"{p['ns']} {p['fix']}")
        self._draw_xy()
        self._draw_err()
        tr = self.win.session.truth
        if tr and tr.get("lat") is not None:
            self.map.set_pos(p["lat"], p["lon"])

    def _draw_xy(self):
        self.pg_xy.clear()
        if len(self.pts) < 1:
            return
        tr = self.win.session.truth or {}
        lat0 = tr.get("lat") or self.pts[0]["lat"]
        lon0 = tr.get("lon") or self.pts[0]["lon"]
        e = [_enu_e(p, lat0, lon0) for p in self.pts]
        n = [_enu_n(p, lat0, lon0) for p in self.pts]
        self.pg_xy.plot(e, n, pen=pg.mkPen(theme.ACC, width=1.5),
                        symbol="o", symbolSize=4,
                        symbolBrush=theme.ACC)
        if e:
            self.pg_xy.plot([e[0]], [n[0]], pen=None, symbol="t",
                            symbolSize=12, symbolBrush=theme.ACC2)
            self.pg_xy.plot([e[-1]], [n[-1]], pen=None, symbol="t1",
                            symbolSize=12, symbolBrush=theme.WARN)

    def _draw_err(self):
        self.pg_err.clear()
        tr = self.win.session.truth
        if not tr or tr.get("lat") is None or len(self.pts) < 2:
            return
        xs = list(range(len(self.pts)))
        he = [haversine(p["lat"], p["lon"], tr["lat"], tr["lon"])
              for p in self.pts]
        ve = [p["h"] - (tr.get("alt") or 0.0) for p in self.pts]
        self.pg_err.plot(xs, he, pen=pg.mkPen(theme.ACC, width=1.5))
        self.pg_err.plot(xs, ve, pen=pg.mkPen(theme.ACC2, width=1.5))
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        self.k_h.set(f"{rms(he):.2f}")
        self.k_v.set(f"{rms(ve):.2f}")
        self.lbl_hint.setText("水平=青 · 垂直=绿（相对任务真值）")


def _enu_e(p, lat0, lon0):
    return math.radians(p["lon"] - lon0) * 6378137.0 * \
        math.cos(math.radians(lat0))


def _enu_n(p, lat0, lon0):
    return math.radians(p["lat"] - lat0) * 6356752.0
