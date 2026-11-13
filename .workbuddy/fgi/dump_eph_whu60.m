% Export FGI-computed satellite positions/clocks per epoch (satData2).
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post_whu60.mat');
fid = fopen('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60_sat.csv', 'w');
fprintf(fid, 'epoch,prn,reftime,posx,posy,posz,clock,tgd\n');
cnt = 0;
for e = 1:numel(S.satData2)
    sd = S.satData2{e};
    g = sd.gpsl1;
    for ch = 1:numel(g.channel)
        c = g.channel(ch);
        if ~isfield(c,'Pos') || numel(c.Pos) < 3, continue; end
        cl = NaN;  if isfield(c,'Clock'), cl = c.Clock;  end
        tg = NaN;  if isfield(c,'T_GD'),  tg = c.T_GD;   end
        rt = NaN;  if isfield(c,'refTime'), rt = c.refTime; end
        fprintf(fid, '%d,%d,%.6f,%.4f,%.4f,%.4f,%.9e,%.9e\n', ...
                e, c.SvId.satId, rt, c.Pos(1), c.Pos(2), c.Pos(3), cl, tg);
        cnt = cnt + 1;
    end
end
fclose(fid);
printf('dump_eph_whu60 done, %d rows\n', cnt);
