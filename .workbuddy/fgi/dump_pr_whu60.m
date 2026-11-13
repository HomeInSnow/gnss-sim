% Export per-epoch per-SV rawP / corrP / clockCorr from the post mat.
% obsData2 is 1x52 cell; each cell.gpsl1 has channel() struct array.
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post_whu60.mat');
fid = fopen('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60_prn.csv', 'w');
fprintf(fid, 'epoch,recv_tow,prn,rawP,corrP,clockCorr\n');
cnt = 0;
for e = 1:numel(S.obsData2)
    o = S.obsData2{e};
    g = o.gpsl1;
    for ch = 1:g.nrObs
        c = g.channel(ch);
        if ~c.bObsOk, continue; end
        if ~isfield(c,'rawP') || ~isfield(c,'corrP') || isnan(c.rawP)
            continue;
        end
        cc = NaN;
        if isfield(c,'clockCorr'), cc = c.clockCorr; end
        rt = NaN;
        if isfield(c,'receiverTow'), rt = c.receiverTow; end
        fprintf(fid, '%d,%.3f,%d,%.4f,%.4f,%.4f\n', ...
                e, rt, c.SvId.satId, c.rawP, c.corrP, cc);
        cnt = cnt + 1;
    end
end
fclose(fid);
printf('dump_pr_whu60 done, %d rows\n', cnt);
