D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData');
tR = D.trackData.gpsl1;
LC = tR.loopCnt;
printf('loopCnt=%d PDIcode=%g\n', LC, tR.PDIcode);
for ch = 1:numel(tR.channel)
  c = tR.channel(ch);
  bs = unique(c.blockSize(1:LC))';
  nl = c.noiseCNOfromSNR(1:LC);
  iP = c.I_P(1:LC); qP = c.Q_P(1:LC);
  sigP = mean(iP.^2 + qP.^2);
  nv = var(nl);
  cn0_re = 10*log10(sigP/nv/0.02);
  cn0s = c.CN0fromSNR(1:LC);
  ok = cn0s > 0;
  frac_small = mean(c.blockSize(1:LC) < 490000);
  pct_decay = 100*mean(abs(iP(1:LC)) < 0.3*median(abs(iP(1:LC))));
  printf('G%-3d bs=%d %d  fracsmall=%.2f cn0mean=%.2f cn0med=%.2f nlMean=%.3e nlStd=%.3e cn0_re=%.2f iPdecay%%=%.1f\n', ...
    c.SvId.satId, bs(1), numel(bs), frac_small, mean(cn0s(ok)), median(cn0s(ok)), mean(nl), std(nl), cn0_re, pct_decay);
end
