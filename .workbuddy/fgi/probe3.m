D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData');
tR = D.trackData.gpsl1;
c = tR.channel(1);
LC = tR.loopCnt;
bs = c.blockSize(1:LC);
[u, ~, ic] = unique(bs);
printf('channel1 unique blockSize:/n');
for k=1:numel(u); printf('  %g  x %d\n', u(k), sum(ic==k)); end
printf('bitSync=%s bitBoundaryIndex=%s\n', mat2str(c.bitSync), mat2str(c.bitBoundaryIndex(1:min(5,end))));
printf('enableMultiCorrelator=%s rate=%g\n', mat2str(tR.enableMultiCorrelatorTracking), tR.multiCorrelatorTrackingRate);
printf('bInited frac=%g\n', mean(c.bInited));
