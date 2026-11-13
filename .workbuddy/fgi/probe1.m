D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData');
c = D.trackData.gpsl1.channel(1);
printf('SvId class=%s\n', class(c.SvId));
printf('blockSize class=%s size=%s\n', class(c.blockSize), sprintf('%dx%d', size(c.blockSize)));
printf('noise class=%s size=%s\n', class(c.noiseCNOfromSNR), sprintf('%dx%d', size(c.noiseCNOfromSNR)));
printf('IP class=%s size=%s\n', class(c.I_P), sprintf('%dx%d', size(c.I_P)));
