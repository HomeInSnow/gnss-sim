#!/bin/bash
# 构建 pocket_web_iflc.exe：Web UI 通道的 E1+E5a IFLC 变体
# = pocket_web 全套源码（含 sdr_web.c）中把 sdr_pvt.c 替换为 local_build/sdr_pvt_iflc.c，
#   sdr_func.c 替换为 sdr_func_iflc.c（$EPH/$DBG 日志放开），另前置 ephemeris_iflc/pntpos_iflc
#   （覆盖 librtk.a 同名目标：seleph 过滤/IFLC 支路补丁）。
# 与 CLI 版 pocket_trk_iflc.exe 的 PVT 逻辑同源，用于 Web UI 双频回放验证与使用。
set -e
export PATH="/d/workbuddy/tools/mingw64/bin:$PATH"
cd /d/workbuddy/GNSSSignal/PocketSDR/local_build

INC="-I../src -I../lib/RTKLIB/src -I../lib/cyusb -I../lib/pocketfft"
CFLAGS="-O3 -DWIN32 -Wall -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function"
LIBS="../lib/win32/librtk.a ../lib/win32/libpocketfft.a ../lib/cyusb/CyAPI.a \
      -lsetupapi -lavrt -lwinmm -lws2_32 -lpthread -static"

SRCS="../src/sdr_array.c ../src/sdr_ch.c ../src/sdr_cmn.c ../src/sdr_code.c \
      ../src/sdr_code_gal.c ../src/sdr_conf.c ../src/sdr_dev.c ../src/sdr_fec.c \
      ../src/sdr_ldpc.c ../src/sdr_nav.c ../src/sdr_nb_ldpc.c ../src/sdr_rcv.c \
      ../src/sdr_sdev.c ../src/sdr_usb.c ../src/sdr_web.c \
      sdr_func_iflc.c sdr_pvt_iflc.c ephemeris_iflc.c pntpos_iflc.c \
      ../app/pocket_web/pocket_web.c"

g++ $CFLAGS $INC $SRCS $LIBS -o pocket_web_iflc.exe
echo "BUILD OK: $(ls -la pocket_web_iflc.exe)"
