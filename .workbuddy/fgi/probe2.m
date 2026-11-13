D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData');
c = D.trackData.gpsl1.channel(1);
disp(fieldnames(c.SvId));
x = c.SvId;
fn = fieldnames(x);
for k=1:numel(fn); v=x.(fn{k}); printf('%s class=%s valstr=%s\n', fn{k}, class(v), char(v)); end
