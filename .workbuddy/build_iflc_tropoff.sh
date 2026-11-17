#!/bin/bash
# 构建 IFLC-tropo-off 诊断变体（三口径对照用）
# 与 pocket_trk_iflc.exe 同源（sdr_pvt_iflc.c），仅 TROPOPT_SAAS -> TROPOPT_OFF：
# 本 run 引擎 atmosphere off，Saas 属"错扣"，用于隔离 fixA 的高程偏置来源。
set -e
export PATH="/d/workbuddy/tools/mingw64/bin:$PATH"
cd /d/workbuddy/GNSSSignal/PocketSDR/local_build

# 变体源：sed 自 sdr_pvt_iflc.c，仅改 tropoopt 一行
sed 's|opt.tropopt = TROPOPT_SAAS;.*|opt.tropopt = TROPOPT_OFF;  // diag: engine troposphere=off|' \
    sdr_pvt_iflc.c > sdr_pvt_iflc_tropoff.c
echo "== diff lines (expect 1) =="
diff <(grep -n "tropopt" sdr_pvt_iflc.c) <(grep -n "tropopt" sdr_pvt_iflc_tropoff.c) || true

INC="-I../src -I../lib/RTKLIB/src -I../lib/cyusb -I../lib/pocketfft"
CFLAGS="-O3 -DWIN32 -Wall -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function"
LIBS="../lib/win32/librtk.a ../lib/win32/libpocketfft.a ../lib/cyusb/CyAPI.a \
      -lsetupapi -lavrt -lwinmm -lws2_32 -lpthread -static"

SRCS="../src/sdr_array.c ../src/sdr_ch.c ../src/sdr_cmn.c ../src/sdr_code.c \
      ../src/sdr_code_gal.c ../src/sdr_conf.c ../src/sdr_dev.c ../src/sdr_fec.c \
      ../src/sdr_ldpc.c ../src/sdr_nav.c ../src/sdr_nb_ldpc.c ../src/sdr_rcv.c \
      ../src/sdr_sdev.c \
      ../src/sdr_usb.c ../src/sdr_web.c \
      sdr_func_iflc.c sdr_pvt_iflc_tropoff.c ephemeris_iflc.c pntpos_iflc.c \
      ../app/pocket_trk/pocket_trk.c"

g++ $CFLAGS $INC $SRCS $LIBS -o pocket_trk_iflc_tropoff.exe
echo "BUILD OK: $(ls -la pocket_trk_iflc_tropoff.exe)"
