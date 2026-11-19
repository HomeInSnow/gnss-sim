## pocketSDR-desktop console — Windows x64 build

Self-contained PyInstaller build of the **PocketSDR replay console** used to
validate gnss-sim-desktop IQ scenarios with PocketSDR engines.

Contents of `pocketSDR-desktop/`:

- `pocketSDR-desktop.exe` — console app (variant picker, web replay monitors:
  acquisition waterfall, tracking, observables, navigation, live NMEA/fix KPIs).
- `pocket_web_local.exe` — standard engine (BRDC/SAAS, as upstream).
- `pocket_web_both_off.exe` — atmosphere + satellite-clock corrections off.
- `pocket_web_iflc.exe` — E1+E5a dual-frequency IFLC variant.
- `html/` — monitor front-end assets.

The engine variants are built from the patched side-car sources in
[`local_build/`](https://github.com/HomeInSnow/pocketSDR-desktop/tree/master/local_build)
of this repository; the console GUI source lives in the companion project
[gnss-sim-desktop](https://github.com/HomeInSnow/gnss-sim-desktop)
(`pocket_desktop/`).

Notes:

- Windows 10/11 x64, executables are **not code-signed**.
- Designed to replay `out/<runid>/` IQ directories produced by
  gnss-sim-desktop (int8/int16, `.bin`/`.raw` with `.tag` sidecar).
