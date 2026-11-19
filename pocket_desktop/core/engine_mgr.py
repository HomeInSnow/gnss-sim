# -*- coding: utf-8 -*-
"""引擎管理器：以子进程运行 PocketSDR Web 版引擎（免 Soapy 的源码级构建）。

启动形态：pocket_web*.exe -web 127.0.0.1:<port> -html <dir>
exe/ html 定位：源码态 = PocketSDR/local_build 与 PocketSDR/html；
frozen = exe 旁 engine/ 目录（PyInstaller 收集）。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal

# 变体：key -> (界面名, exe 文件名)
VARIANTS = {
    "original": ("原版 BRDC/SAAS", "pocket_web_local.exe"),
    "bothoff":  ("匹配版 大气OFF", "pocket_web_both_off.exe"),
    "iflc":     ("IFLC 双频", "pocket_web_iflc.exe"),
}


def repo_root() -> Path:
    """源码态仓库根（frozen 时不调用）。"""
    return Path(__file__).resolve().parents[2]


def _pkg_root() -> Path:
    """打包资源根：PyInstaller 6.x onedir = _internal（sys._MEIPASS），兜底 exe 旁。"""
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        return Path(mp)
    return Path(sys.executable).resolve().parent


def engine_dir() -> Path:
    if getattr(sys, "frozen", False):
        for cand in (_pkg_root() / "engine",
                     Path(sys.executable).resolve().parent / "engine"):
            if cand.exists():
                return cand
        return _pkg_root() / "engine"
    # pocketSDR-desktop 是 gnss-sim-desktop 仓库的兄弟目录（旧名 PocketSDR 兼容）
    env = os.environ.get("POCKETSDR_BUILD")
    if env:
        return Path(env)
    parent = repo_root().parent
    for name in ("pocketSDR-desktop", "PocketSDR"):
        cand = parent / name / "local_build"
        if cand.exists():
            return cand
    return parent / "pocketSDR-desktop" / "local_build"


def html_dir() -> Path:
    if getattr(sys, "frozen", False):
        for cand in (engine_dir() / "html",
                     _pkg_root() / "engine" / "html"):
            if cand.exists():
                return cand
        return engine_dir() / "html"
    return engine_dir().parent / "html"


def exe_path(variant: str) -> Path:
    return engine_dir() / VARIANTS[variant][1]


_FMT_NAME = {1: "INT8", 2: "INT8X2", 3: "RAW8", 4: "RAW16", 5: "RAW16I",
             6: "RAW32", 7: "CS8", 8: "CS16"}


def _tag_lines(fmt: int, fs_mhz: float, fo_csv: str, iq_csv: str,
               bits_csv: str) -> list[str]:
    """按界面参数生成 tag 行。NCH 随 fo 个数推导（引擎 rcv_open_file 以 tag
    为准并截断超出 NCH 的 F_LO/IQ/BITS，硬编码 1 会让双频文件永远单 RF CH）；
    iq/bits 列表按 NCH 重复补齐。"""
    fo = [f"{float(x):.6f}" for x in fo_csv.split(",") if x.strip()] or \
        ["1575.42"]
    iq = [x.strip() for x in iq_csv.split(",") if x.strip()] or ["2"]
    bits = [x.strip() for x in bits_csv.split(",") if x.strip()] or ["3"]
    nch = len(fo)
    iq = (iq * nch)[:nch]
    bits = (bits * nch)[:nch]
    return [
        "PROG = pocket-desktop",
        "TIME = 0000-00-00 00:00:00",
        f"FMT = {_FMT_NAME.get(int(fmt), 'CS16')}",
        f"NCH = {nch}",
        f"F_S = {float(fs_mhz):.6f}",
        "F_LO = " + ",".join(fo),
        "IQ = " + ",".join(iq),
        "BITS = " + ",".join(bits),
    ]


def _parse_tag(tag: Path) -> dict:
    d = {}
    try:
        for ln in tag.read_text(encoding="ascii", errors="ignore").splitlines():
            if "=" in ln:
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip()
    except OSError:
        pass
    return d


def _same_tag(cur: dict, want: list[str]) -> bool:
    for ln in want:
        k, _, v = ln.partition("=")
        if cur.get(k.strip()) != v.strip():
            return False
    return True


def ensure_tag(iq_path: str | Path, fmt: int, fs_mhz: float, fo_csv: str,
               iq_csv: str, bits_csv: str) -> tuple[str | None, str]:
    """引擎（rcv_open_file）以 <file>.tag 伴生文件为准（set_inp 值会被 tag
    整体覆盖），所以：

    - tag 缺失 → 按界面参数写入，返回 (path, "created")；
    - tag 存在但与界面参数不符 → 重写并返回 (path, "rewritten")；
      桌面端界面即真值来源，不重写会让"改了采样率/中频"静默无效；
    - tag 一致 → (None, "ok")。
    """
    p = Path(iq_path)
    tag = p.with_name(p.name + ".tag")
    want = _tag_lines(fmt, fs_mhz, fo_csv, iq_csv, bits_csv)
    if tag.exists():
        if _same_tag(_parse_tag(tag), want):
            return None, "ok"
        tag.write_text("\n".join(want) + "\n", encoding="ascii")
        return str(tag), "rewritten"
    tag.write_text("\n".join(want) + "\n", encoding="ascii")
    return str(tag), "created"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EngineMgr(QObject):
    """单例式引擎槽位：start/stop/exit 状态机。"""
    exited = Signal(int)          # 引擎退出码（外部停止也发，见 stop()）
    started = Signal(int)         # 携带端口

    def __init__(self, log_fn=None):
        super().__init__()
        self.proc: subprocess.Popen | None = None
        self.port = 0
        self.variant = "bothoff"
        self.logf = None
        self._stopping = False
        self._log = log_fn or (lambda m, lv="info": None)

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def missing_exe(self) -> str:
        bad = [f"{VARIANTS[k][0]}: {exe_path(k).name}"
               for k in VARIANTS if not exe_path(k).exists()]
        return "；".join(bad)

    def start(self, variant: str, runlog_dir: Path) -> int:
        """拉起引擎，返回端口。异常时抛 RuntimeError。"""
        if self.running:
            self.stop()
        exe = exe_path(variant)
        if not exe.exists():
            raise RuntimeError(f"引擎缺失：{exe}")
        runlog_dir.mkdir(parents=True, exist_ok=True)
        logp = runlog_dir / f"engine_{time.strftime('%Y%m%dT%H%M%S')}.log"
        self.logf = open(logp, "w", encoding="utf-8", errors="ignore")
        self.port = free_port()
        # 每变体独立 ini：默认 pocket_web.ini 与官方 Web UI / 其他变体共用
        # 一份（str_type/log_mask/opt/fftw 等未覆盖项会互相污染），缺失时
        # 引擎回落内置默认（load_cfg fopen 失败即返回 0）。
        ini = runlog_dir / f"desktop_{variant}.ini"
        cmd = [str(exe), "-web", f"127.0.0.1:{self.port}",
               "-html", str(html_dir()), "-ini", str(ini)]
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=str(engine_dir()), stdout=self.logf,
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                creationflags=flags)
        except OSError as e:
            raise RuntimeError(f"引擎启动失败：{e}") from e
        self.variant = variant
        self._log(f"引擎已启动 {VARIANTS[variant][0]} pid={self.proc.pid} "
                  f"port={self.port}，日志 {logp.name}", "ok")
        self.started.emit(self.port)
        threading.Thread(target=self._watch, args=(self.proc,),
                         daemon=True).start()
        return self.port

    def _watch(self, proc: subprocess.Popen):
        rc = proc.wait()
        if proc is self.proc:          # 未被 stop() 换掉才算事件
            self._log(f"引擎退出 rc={rc}", "warn" if rc else "info")
            self.exited.emit(rc)

    def stop(self):
        if self.proc is None:
            return
        self._stopping = True
        p, self.proc = self.proc, None
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:              # noqa: BLE001 - 兜底强杀
            try:
                p.kill()
            except OSError:
                pass
        if self.logf:
            try:
                self.logf.close()
            except OSError:
                pass
        self._log("引擎已停止", "info")
        self._stopping = False

    def tail_log(self, n: int = 200) -> list[str]:
        """读取引擎 stdout 尾部（诊断用）。"""
        try:
            with open(self.logf.name, encoding="utf-8", errors="ignore") as f:
                return f.readlines()[-n:]
        except OSError:
            return []
