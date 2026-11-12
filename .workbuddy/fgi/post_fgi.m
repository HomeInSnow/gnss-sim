
% post_fgi.m -- replay navigation from saved state (no re-tracking)
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3'), '-begin');
cd('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3/param');
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
settings = S.settings;
if isfield(settings.sys,'msToProcess'), printf('msToProcess %d\n', settings.sys.msToProcess); end
ephData = S.ephData;
trackData = S.trackData;
[obsData2, satData2, navData2] = doNavigation(S.obsData, settings, S.ephData);
nv = numel(navData2);
printf('nav epochs %d\n', nv);
printf('Pos fields: %s\n', strjoin(fieldnames(navData2{nv}.Pos)', ','));
for q = [1 2 3 nv-2 nv-1 nv]
    if q < 1, continue; end
    n = navData2{q};
    printf('epoch %d nval %d fom %.1f pos %s\n', q ...
       , n.Pos.bValid, n.Pos.fom, num2str(n.Pos.xyz', '%.1f '));
end
last = navData2{nv};
prn = [];
for ch = 1:S.trackData.gpsl1.nrObs
    prn(ch) = S.trackData.gpsl1.channel(ch).SvId.satId;
end
printf('prns %s\n', num2str(prn, '%d '));
printf('resid last epoch %s\n', num2str(last.Pos.rangeResid, '%.1f '));
printf('nrsats used %s\n', num2str(last.Pos.nrSats, '%d '));
save('-v6','D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post.mat','navData2','obsData2','ephData','satData2');
disp('post done')
