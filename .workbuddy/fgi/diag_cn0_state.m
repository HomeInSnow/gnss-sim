D = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_whu60b_state.mat','trackData','settings');
td = D.trackData;
fn = fieldnames(td);
printf('fields: %s\n', strjoin(fn,', '));
sig = fn{1};
for k=1:numel(fn)
  if ~strcmp(fn{k},'signal')
    s=fn{k}; try; x=td.(fn{k}); if isstruct(x); printf('%s -> %s\n',fn{k},strjoin(fieldnames(x),',')); end; catch; end
  end
end
