
P = load('D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_post.mat');
e = P.ephData.gpsl1;
for f = fieldnames(e)'
    fn = f{1};
    v = e.(fn);
    if isnumeric(v)
        printf('%s = [%s]\n', fn, num2str(v(:)', '%g '));
    end
end
