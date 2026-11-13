% post_fgi_whu60b.m -- from the completed FGI run on the WHU-broadcast afzero
% 60 s scenario, dump two CSVs for the thesis comparison:
%   out/fgi/fgi_whu60b_nav.csv   per-epoch positioning (ECEF + LLA + valid)
%   out/fgi/fgi_whu60b_cn0.csv   per-SV per-epoch mean C/No (dB-Hz)
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3'), '-begin');
cd('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3/param');
S  = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat');
settings = S.settings;
if isfield(settings.sys,'msToProcess'), printf('msToProcess %d\n', settings.sys.msToProcess); end

% ---- navigation replay ----
[obsData2, satData2, navData2] = doNavigation(S.obsData, settings, S.ephData);
nv = numel(navData2);
printf('nav epochs %d\n', nv);
fid = fopen('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_nav.csv', 'wt');
fprintf(fid, 'epoch,bvalid,fom,x,y,z,lat,lon,hgt,nrsats\n');
for q = 1:nv
    n = navData2{q}; p = n.Pos;
    ns = -1; if isfield(p,'nrSats'), ns = p.nrSats; end
    if isfield(p,'LLA') && numel(p.LLA) >= 3
        la = p.LLA(1); lo = p.LLA(2); hg = p.LLA(3);
    else la = NaN; lo = NaN; hg = NaN; end
    fprintf(fid, '%d,%d,%.3f,%.4f,%.4f,%.4f,%.7f,%.7f,%.3f,%d\n', ...
        q, p.bValid, p.fom, p.xyz(1), p.xyz(2), p.xyz(3), la, lo, hg, ns);
end
fclose(fid);
disp('nav csv done');

% ---- C/No per SV per epoch ----
tc = S.trackData.gpsl1;
nro = tc.nrObs;
fid = fopen('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_cn0.csv', 'wt');
fprintf(fid, 'prn,epoch_ms,cn0,mean_cn0\n');
for ch = 1:nro
    prn = tc.channel(ch).SvId.satId;
    if ~isfield(tc.channel(ch), 'meanCN0fromSNR'), continue; end
    mcn = tc.channel(ch).meanCN0fromSNR;
    cn  = tc.channel(ch).CN0fromSNR;
    L = min(numel(mcn), numel(cn));
    for q = 1:L
        fprintf(fid, '%d,%d,%.4f,%.4f\n', prn, q*10, cn(q), mcn(q));
    end
end
fclose(fid);
printf('cn0 csv done; %d channels tracked\n', nro);
save('-v6','D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post_whu60b.mat','navData2','obsData2','ephData','satData2');
disp('post_whu60b done');
