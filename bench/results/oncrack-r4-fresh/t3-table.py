#!/usr/bin/env python3
"""t3-table.py: the tier 3 reps (t3-N-hold.log / t3-N-nohold.log, written by tier3.sh) as medians per variant, route and concurrency."""
import glob, re, statistics as st, collections
rows = collections.defaultdict(list)
for f in sorted(glob.glob("t3-*-*.log")):
    variant = f.rsplit("-", 1)[1][:-4]
    for line in open(f):
        m = re.search(r"oncrack rep 1: (\w+) c=(\d+) ([\d.]+) rps .*?cpu ([\d.]+) us/req", line)
        if m:
            rows[(m[1], int(m[2]), variant)].append((float(m[3]), float(m[4])))
print("| route | c | variant | reps | req/s median [min-max] | CPU us/req median [min-max] |")
print("|---|---:|---|---:|---:|---:|")
for (route, c, v), xs in sorted(rows.items()):
    r = [x[0] for x in xs]; u = [x[1] for x in xs]
    print(f"| {route} | {c} | {v} | {len(xs)} | {st.median(r):,.0f} [{min(r):,.0f}-{max(r):,.0f}] | {st.median(u):.1f} [{min(u):.1f}-{max(u):.1f}] |")
