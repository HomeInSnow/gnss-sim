
% diag4_fgi.m -- dump measured pseudoranges (last epoch) for external compare
P = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post.mat');
nv = numel(P.navData2);
n = P.navData2{nv};
prn = zeros(1, P.obsData2.gpsl1.nrObs);
cpm = zeros(1, P.obsData2.gpsl1.nrObs);
for ch = 1:P.obsData2.gpsl1.nrObs
    o = P.obsData2.gpsl1.channel(ch);
    prn(ch) = o.SvId.satId;
    % find pseudorange-like field at last index
    fnn = fieldnames(o);
end
printf('obs channel fields: %s\n', strjoin(fieldnames(P.obsData2.gpsl1.channel(1)), ','));
printf('truerange %s\n', num2str(n.Pos.trueRange, '%.1f '));
printf('nrSats %s\n', num2str(n.Pos.nrSats, '%d '));
printf('dop %s\n', num2str(n.Pos.dop, '%.2f '));
