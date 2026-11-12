import io
p = r"D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/run_fgi.m"
s = io.open(p, encoding="utf-8").read()
old = "% make sure every FGI folder (and subfolder) is on the load path\naddpath(genpath(root));"
new = ("% shim dir FIRST (Octave lacks contains() used by gsrx.m)\n"
       "addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));\n"
       "% make sure every FGI folder (and subfolder) is on the load path\n"
       "addpath(genpath(root), '-begin');\n"
       "addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'), '-begin');")
assert old in s, "anchor not found"
io.open(p, "w", encoding="utf-8").write(s.replace(old, new))
print("patched run_fgi.m")
