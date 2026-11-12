% post_fgi_full.m -- replay navigation from the FULL (200 s) saved state and
% dump a per-epoch CSV for the three-way comparison (FGI vs built-in vs paper).
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3'), '-begin');
cd('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3/param');
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_full_state.mat');
settings = S.settings;
if isfield(settings.sys,'msToProcess'), printf('msToProcess %d\n', settings.sys.msToProcess); end
[obsData2, satData2, navData2] = doNavigation(S.obsData, settings, S.ephData);
nv = numel(navData2);
printf('nav epochs %d\n', nv);

fid = fopen('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_nav_full.csv', 'wt');
fprintf(fid, 'epoch,bvalid,fom,x,y,z,lat,lon,hgt,nrsats,r3,r4,r5,vx,vy,vz,vvalid\n');
for q = 1:nv
    n = navData2{q};
    p = n.Pos;
    if ~isfield(p,'rangeResid'), rr = []; else rr = p.rangeResid; end
    if ~isfield(p,'nrSats'),     ns = -1; else ns = p.nrSats;  end
    if numel(rr) > 2, rr3 = rr(3); rr4 = rr(4); rr5 = rr(5);
    elseif numel(rr) == 2, rr3 = rr(2); rr4 = NaN; rr5 = NaN;
    else rr3 = NaN; rr4 = NaN; rr5 = NaN; end
    if isfield(n,'Vel') && numel(n.Vel.xyz) >= 3
        vx = n.Vel.xyz(1); vy = n.Vel.xyz(2); vz = n.Vel.xyz(3); vv = n.Vel.bValid;
    else
        vx = NaN; vy = NaN; vz = NaN; vv = 0;
    end
    if isfield(p,'LLA') && numel(p.LLA) >= 3
        la = p.LLA(1); lo = p.LLA(2); hg = p.LLA(3);
    else
        la = NaN; lo = NaN; hg = NaN;
    end
    fprintf(fid, '%d,%d,%.3f,%.4f,%.4f,%.4f,%.7f,%.7f,%.3f,%d,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%d\n', ...
        q, p.bValid, p.fom, p.xyz(1), p.xyz(2), p.xyz(3), la, lo, hg, ns, ...
        rr3, rr4, rr5, vx, vy, vz, vv);
end
fclose(fid);
save('-v6','D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post_full.mat','navData2','obsData2','ephData','satData2');
disp('post_full done')
