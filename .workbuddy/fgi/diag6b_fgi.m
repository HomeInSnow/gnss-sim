S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
E = S.ephData.gpsl1;
hdr = {'weekNumber','t_oe','sqrtA','M_0','e','omega','omegaDot','i_0','iDot','deltan','C_uc','C_us','C_rc','C_rs','C_ic','C_is','a_f0','a_f1','a_f2','T_GD','health','IODC','t_oc'};
for prn = [4 5 9]
  if numel(E) >= prn && ~isempty(E(prn).sqrtA)
    printf('--- FGI eph prn %d ---\n', prn);
    for j=1:numel(hdr)
      f1 = hdr{j};
      if isfield(E(prn), f1), printf('  %-10s = %s\n', f1, mat2str(E(prn).(f1), 12)); end
    end
  end
end
O = S.obsData.gpsl1;
printf('\nobsData.gpsl1 top fields: %s\n', strjoin(fieldnames(O), ', '));
printf('nrObs=%d nrEpochs=%s\n', O.nrObs, mat2str(O.nrEpochs));
printf('channel(1) fields: %s\n', strjoin(fieldnames(O.channel(1)), ', '));
for k=1:numel(O.channel)
  ch = O.channel(k);
  try
    ne = numel(ch.pseudorange);
    tt = '-';
    if isfield(ch,'signalTime') && ne>0, tt = mat2str(ch.signalTime(ne),12); end
    printf('ch%2d prn %2d bEph=%d bObs=%d ne=%3d PR_last=%s sigT_last=%s\n', k, ch.SvId.satId, ch.bEphOk, ch.bObsOk, ne, mat2str(ch.pseudorange(ne),12), tt);
  catch e
    printf('ch%2d prn %2d ERROR: %s fields=%s\n', k, ch.SvId.satId, e.message, strjoin(fieldnames(ch), ','));
    break
  end
end
