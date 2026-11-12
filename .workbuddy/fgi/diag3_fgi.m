
% diag3_fgi.m -- code loop convergence trace
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
tR = S.trackData.gpsl1;
for k = 1:4
    ch = tR.channel(k);
    prn = ch.SvId.satId;
    cp = ch.codePhase; ce = ch.codeError; cn = ch.codeNco;
    n = numel(cp);
    printf('prn %2d codePhase first %.4f mid %.4f last %.4f (chips)\n', ...
        prn, cp(1), cp(round(n/2)), cp(end));
    printf('        codeErr mean|.| last1000 %.3f  Nco last %.3f\n', ...
        mean(abs(ce(end-999:end))), cn(end));
    % true code phase from meta (compare offset)
end
