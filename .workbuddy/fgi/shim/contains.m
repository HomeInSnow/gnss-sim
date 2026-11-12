function out = contains(str, pattern)
%CONTAINS Literal substring test for char / cellstr (Octave shim).
%  Mirrors the MATLAB contains() usage found in FGI-GSRx main/gsrx.m:
%  cellstr + literal char pattern, case sensitive, no regex.
  pat = char(pattern);
  if iscellstr(str)
    out = false(1, numel(str));
    for k = 1:numel(str)
      out(k) = ~isempty(strfind(char(str{k}), pat));
    end
  else
    out = ~isempty(strfind(char(str), pat));
  end
end
