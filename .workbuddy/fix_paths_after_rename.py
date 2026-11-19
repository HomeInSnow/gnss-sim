# -*- coding: utf-8 -*-
r"""One-shot path rewriter for the gnss-sim -> gnss-sim-desktop rename.

Rewrites old absolute project paths inside text files so tooling keeps
working after the directories are renamed:
  GNSSSignal/<sep>gnss-sim    -> GNSSSignal/<sep>gnss-sim-desktop
  GNSSSignal/<sep>PocketSDR   -> GNSSSignal/<sep>pocketSDR-desktop
(<sep> = one or more / or \ characters; already-renamed strings untouched.)

Usage: python fix_paths_after_rename.py [--apply] <file>...
Without --apply it only reports what would change.
"""
import re
import sys

PATTERNS = [
    (re.compile(r"GNSSSignal([/\\]+)gnss-sim(?!-desktop)"), r"GNSSSignal\1gnss-sim-desktop"),
    (re.compile(r"GNSSSignal([/\\]+)PocketSDR(?!-desktop)"), r"GNSSSignal\1pocketSDR-desktop"),
]


def fix(path: str, apply: bool) -> int:
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        src = f.read()
    out, n = src, 0
    for pat, rep in PATTERNS:
        out, k = pat.subn(rep, out)
        n += k
    if n and apply:
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(out)
    return n


def main(argv):
    apply = False
    if argv and argv[0] == "--apply":
        apply = True
        argv = argv[1:]
    total = 0
    for p in argv:
        n = fix(p, apply)
        if n:
            total += n
            print(("FIXED  " if apply else "WOULD  ") + f"{n:3d}x  {p}")
    print(f"{'APPLIED' if apply else 'DRY-RUN'} total={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
