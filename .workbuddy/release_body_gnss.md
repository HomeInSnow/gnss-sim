## gnss-sim-desktop — Windows x64 build

Self-contained PyInstaller build of the **gnss-sim-desktop** signal simulator
desktop app (source: `desktop/` of this repository, branch `main`).

Changes vs v2026.11.19b:

- Generation progress bar now animates in real time (float→int slot
  truncation made it stick at 0% and jump to 100% only at completion).
- Verify page shows a live elapsed-seconds heartbeat; re-clicking 运行验证
  while a verification runs gets an explicit "already in progress" hint
  instead of silently doing nothing.

Contents of `gnss-sim-desktop/`:

- `gnss-sim-desktop.exe` — desktop application (map scenario editor, generation
  console, ephemeris/sky view, tracking-based verification page).
- `data/rinex/` — pre-seeded broadcast ephemeris cache (BRDC 2023 DOY 271,
  2026 DOY 274 and 283) so multi-constellation runs work fully offline.
- `_internal/` — runtime (native C++20 engine, receiver, frontend assets).

Notes:

- Windows 10/11 x64. The executable is **not code-signed** (SmartScreen may
  warn on first launch).
- Built from branch `main` at tag `v2026.11.19c`.
- Transmit stays disabled by default (`ALLOW_TX`); see the Safety section of
  the README.
