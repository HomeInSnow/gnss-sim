#!/bin/bash
# PocketSDR 双回放：原版 vs 场景匹配版（both-off）
# 用法: bash .workbuddy/pocket_perf_replay.sh <run_dir> <outdir_base>
set -u
RUN="$1"; BASE="$2"
case $RUN in /*) ;; *) RUN="$(pwd)/$RUN";; esac
BIN="$RUN/gpssim.bin"
[ -f "$BIN" ] || { echo "no gpssim.bin in $RUN"; exit 1; }
PS=/d/workbuddy/GNSSSignal/pocketSDR-desktop
PRNS=4,5,9,11,12,18,20,25,26,28,29,31
ARGS=(-sig L1CA -prn $PRNS -fmt CS16 -f 25 -fo 1575.42 -IQ 2 -tscale 1 -ti 1 -log f -nmea f)
for v in orig bothoff; do
  D="$BASE/$v"; mkdir -p "$D"
  case $v in
    orig)     EXE="$PS/local_build/pocket_trk_local.exe";;
    bothoff)  EXE="$PS/local_build/pvt_both_off.exe";;
  esac
  echo "== $v : $EXE"
  ( cd "$D" && "$EXE" "${ARGS[@]}" "$BIN" >stdout.txt 2>&1; echo "exit=$?" >>stdout.txt )
  ls -la "$D" | tail -8
done
echo ALLDONE
