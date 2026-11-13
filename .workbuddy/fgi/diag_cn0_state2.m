D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData');
ch = D.trackData.gpsl1.channel;
nch = numel(ch);
printf('channels=%d PDIcode=%g loopCnt=%d\n', nch, D.trackData.gpsl1.PDIcode, D.trackData.gpsl1.loopCnt);
f = fieldnames(ch(1));
printf('ch fields: %s\n', strjoin(f,', '));
