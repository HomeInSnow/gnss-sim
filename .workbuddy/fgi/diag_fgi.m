
% diag_fgi.m -- inspect FGI smoke trackData: per-PRN bit quality & preamble hits
S = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_smoke_state.mat');
tR = S.trackData.gpsl1;
printf('nrObs=%d\n', tR.nrObs);
ch = tR.channel(1);
fn = fieldnames(ch);
printf('channel fields: %s\n', strjoin(fn', ','));

% GPS L1 TLM preamble 10001011 -> 8 bits as +-1
preamble8 = [1 -1 -1 -1 1 -1 1 1];      % FGI default, 8-bit TLM preamble
preamb_ms = kron(preamble8, ones(1,20));   % 160 ms matched filter
for k = 1:tR.nrObs
    prn = tR.channel(k).SvId.satId;
    ip  = tR.channel(k).I_P;
    n   = numel(ip);
    b   = sign(ip); b(b==0) = 1;
    % sliding correlation with 160-ms preamble over whole record
    N = numel(preamb_ms);
    c = filter(preamb_ms(end:-1:1), 1, b);
    c = c(N:end);
    [mx, mi] = max(abs(c));
    % flips per 1000-ms block in first/last thirds to see pull-in
    blk = 1000;
    flips = zeros(1, floor(n/blk));
    for q = 1:numel(flips)
        seg = b((q-1)*blk+1 : q*blk);
        flips(q) = sum(diff(seg) ~= 0);
    end
    printf('prn %2d n=%d maxcorr=%d@%d flips/s first5=[%s] last5=[%s]\n', ...
        prn, n, mx, mi, num2str(flips(1:min(5,end))), num2str(flips(max(1,end-4):end)));
end
