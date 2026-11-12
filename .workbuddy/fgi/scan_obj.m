function scan_obj(v, path)
  if isobject(v)
    printf('OBJECT at %s : class %s\n', path, class(v));
    return;
  end
  if isstruct(v)
    fn = fieldnames(v);
    for i = 1:numel(fn)
      for k = 1:numel(v)
        scan_obj(v(k).(fn{i}), sprintf('%s.%s(%d)', path, fn{i}, k));
      end
    end
  elseif iscell(v)
    for k = 1:numel(v)
      scan_obj(v{k}, sprintf('%s{%d}', path, k));
    end
  end
end
