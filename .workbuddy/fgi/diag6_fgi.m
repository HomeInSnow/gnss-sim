S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
printf('=== top fields ===\n');
fn = fieldnames(S); for i=1:numel(fn), printf('%s : %s %s\n', fn{i}, class(S.(fn{i})), mat2str(size(S.(fn{i})))); end

E = S.ephData.gpsl1;
printf('\n=== ephData.gpsl1: class=%s size=%s\n', class(E), mat2str(size(E)));
if isfield(E,'sqrtA')
  n = numel(E);
  printf('struct array n=%d\n', n);
  hdr = {'weekNumber','toe','sqrtA','M_0','eccentricity','omega','omegaDot','i0','deltaN','C_uc','C_us','C_rc','C_rs','C_ic','C_is','idot','af0','af1','af2','T_GD','health','IODC','IODE'};
  for k=1:n
    if ~isempty(E(k).sqrtA)
      printf('--- eph idx %d prn=%s\n', k, mat2str(E(k).prn));
      for j=1:numel(hdr)
        f1 = hdr{j};
        if isfield(E(k), f1)
          v = E(k).(f1);
          printf('  %-12s = %s\n', f1, mat2str(v, 10));
        else
          % try FGI alt names
          printf('  %-12s = <missing>\n', f1);
        end
      end
      if k>3, break; end
    end
  end
end

O = S.obsData.gpsl1;
printf('\n=== obsData.gpsl1 fields ===\n');
of = fieldnames(O); printf('%s ', of{:}); printf('\n');
printf('nrObs=%d nrEpochs=%s\n', O.nrObs, mat2str(O.nrEpochs));
cf = fieldnames(O.channel(1));
printf('channel(1) fields: %s\n', strjoin(cf, ', '));
printf('channel(1) prn=%s bEphOk=%s bParityOk=%s bObsOk=%s\n', mat2str(O.channel(1).SvId.satId), mat2str(O.channel(1).bEphOk), mat2str(O.channel(1).bParityOk), mat2str(O.channel(1).bObsOk));
% dump last epoch pseudorange-ish fields for all channels
for k=1:numel(O.channel)
  ch = O.channel(k);
  ne = numel(ch.pseudorange);
  if ne>0
    pr = ch.pseudorange(ne);
    tt = '';
    if isfield(ch,'signalTime'), tt = mat2str(ch.signalTime(ne),12); end
    printf('prn %2d ne=%3d PR_last=%s sigT=%s\n', ch.SvId.satId, ne, mat2str(pr,12), tt);
  else
    printf('prn %2d ne=0 fields?', ch.SvId.satId);
    disp(fieldnames(ch)');
  end
end
