
% diag2_fgi.m -- loop state deep-dive for 2 representative PRNs
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
tR = S.trackData.gpsl1;
for k = [1 5]
    ch = tR.channel(k);
    prn = ch.SvId.satId;
    printf('=== prn %d ===\n', prn);
    printf('acquiredFreq %.1f\n', ch.acquiredFreq);
    d  = ch.doppler;  cf = ch.carrFreq;
    printf('doppler  last5 %s\n', num2str(d(end-4:end), '%.1f '));
    printf('carrFreq last5 %s\n', num2str(cf(end-4:end), '%.1f '));
    printf('doppler  mean(abs diff last 1000 pairs) %.2f\n', mean(abs(diff(d(end-1000:end)))));
    ts = ch.trackState;
    printf('trackState uniq [%s]  last=%d\n', num2str(unique(ts(:)')), ts(end));
   fli = ch.fllLockIndicator; pli = ch.pllLockIndicator;
    printf('fllLock mean %.2f last100 %.2f | pllLock mean %.2f last100 %.2f\n', ...
      mean(fli), mean(pli(end-99:end)), mean(pli), mean(pli(end-99:end)));
    ip = ch.I_P;
    printf('|I_P| mean %.2f std %.2f  (first 5000) | later %.2f %.2f\n', ...
      mean(abs(ip(1:5000))), std(ip(1:5000)), mean(abs(ip(end-5000:end))), std(ip(end-5000:end)));
    % CN0 reported by FGI itself
    printf('meanCN0 %.1f dB-Hz\n', ch.meanCN0fromSNR);
end
