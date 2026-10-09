#!/usr/bin/env python3
"""Unit R3.4: reads a trace-run.sh directory's wal.log: restarts per second, the writer's slow groups (>= 20 ms) and what
ran around each (the checkpoints and restarts within 1.5 s before it), and the RESTART/PASSIVE durations.

  python3 bench/results/oncrack-r3-wal/trace.py DIR [--detail]
"""
import re, statistics, sys
from datetime import datetime

d = sys.argv[1]
detail = "--detail" in sys.argv
rows = []
for line in open(f"{d}/wal.log"):
    clock, ms, msg = line.rstrip("\n").split(" ", 2)
    rows.append((float(ms), clock, msg))
if not rows:
    sys.exit("empty trace")
span = (rows[-1][0] - rows[0][0]) / 1000
restarts = [r for r in rows if r[2].startswith("restarted")]
forced = [r for r in rows if r[2].startswith("RESTART")]
passive = [r for r in rows if r[2].startswith("PASSIVE")]
slow = [r for r in rows if r[2].startswith("slow group")]
num = lambda pat, s: float(re.search(pat, s).group(1))
print(f"{d}: {span:.0f} s traced; WAL restarts {len(restarts)} ({len(restarts) / span:.1f}/s), writer RESTARTs {len(forced)}, PASSIVE {len(passive)}")
if passive:
    pr = [num(r"ran ([\d.]+)", r[2]) for r in passive]
    print(f"  PASSIVE ran ms: median {statistics.median(pr):.1f}, p99 {sorted(pr)[int(len(pr) * .99)]:.1f}, max {max(pr):.1f}; over 100 ms: {sum(x >= 100 for x in pr)}")
if forced:
    w = [num(r"waited ([\d.]+)", r[2]) for r in forced if "waited" in r[2]]
    ran = [num(r"ran ([\d.]+)", r[2]) for r in forced]
    if w:
        print(f"  writer RESTART waited for PASSIVE ms: median {statistics.median(w):.1f}, max {max(w):.1f}; over 100 ms: {sum(x >= 100 for x in w)}")
    print(f"  writer RESTART ran ms: median {statistics.median(ran):.1f}, max {max(ran):.1f}; over 100 ms: {sum(x >= 100 for x in ran)}")
st = [num(r"took ([\d.]+)", r[2]) for r in slow]
print(f"  slow groups (>=20 ms): {len(slow)}; over 100 ms: {sum(x >= 100 for x in st)}; over 500 ms: {sum(x >= 500 for x in st)}; max {max(st, default=0):.0f} ms")
for r in slow:
    took = num(r"took ([\d.]+)", r[2])
    if took < 100:
        continue
    print(f"  {r[1]} {r[2]}")
    if detail:
        for q in rows:
            if r[0] - took - 1500 <= q[0] <= r[0] and q is not r and not q[2].startswith("slow"):
                print(f"      {q[1]} {q[2]}")
