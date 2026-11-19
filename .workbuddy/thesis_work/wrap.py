import sys
start, end = int(sys.argv[1]), int(sys.argv[2])
with open(r"D:/workbuddy/GNSSSignal/gnss-sim-desktop/.workbuddy/thesis_work/thesis.md", encoding="utf-8") as f:
    lines = f.readlines()
import textwrap
for i in range(start-1, min(end, len(lines))):
    ln = lines[i].rstrip("\n")
    if len(ln) > 150:
        for j, seg in enumerate(textwrap.wrap(ln, 170)):
            print(f"{i+1}| " + seg if j == 0 else "  | " + seg)
    else:
        print(f"{i+1}| {ln}")
