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
    # PocketSDR 是 gnss-sim 仓库的兄弟目录
    return Path(os.environ.get("POCKETSDR_BUILD",
                              repo_root().parent / "PocketSDR" / "local_build"))


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


def ensure_tag(iq_path: str | Path, fmt: int, fs_mhz: float, fo_csv: str,
               iq_csv: str, bits_csv: str) -> str | None:
    """引擎（rcv_open_file）要求 <file>.tag 伴生文件，缺失则按参数补写。

    返回写入的 tag 路径；已存在则返回 None（不覆盖）。
    """
    p = Path(iq_path)
    tag = p.with_name(p.name + ".tag")
    if tag.exists():
        return None
    lines = [
        "PROG = pocket-desktop",
        "TIME = 0000/00/00 00:00:00",
        f"FMT = {_FMT_NAME.get(int(fmt), 'CS16')}",
        "NCH = 1",
        f"F_S = {float(fs_mhz):.6f}",
        f"F_LO = {','.join(f'{float(x):.6f}' for x in fo_csv.split(',') if x.strip())}",
        f"IQ = {','.join(x.strip() for x in iq_csv.split(',') if x.strip())}",
        f"BITS = {','.join(x.strip() for x in bits_csv.split(',') if x.strip())}",
    ]
    tag.write_text("\n".join(lines) + "\n", encoding="ascii")
    return str(tag)


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
        cmd = [str(exe), "-web", f"127.0.0.1:{self.port}",
               "-html", str(html_dir())]
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
