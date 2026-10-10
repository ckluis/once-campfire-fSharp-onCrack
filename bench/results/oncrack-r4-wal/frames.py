#!/usr/bin/env python3
"""Frames and writes per group off a CAMPFIRE_WAL_TRACE file (`writer totals:` lines, one per WAL restart).
   frames.py wal.log [SECONDS]   # the last SECONDS (default 20) of the trace; prints writes/group, frames/post, KB/post"""
import re, sys
between = len(sys.argv) > 4 and sys.argv[2] == "--between"
secs = float(sys.argv[2]) if len(sys.argv) > 2 and not between else 20
def tod(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)
rows = []
for line in open(sys.argv[1]):
    m = re.match(r"(\d\d:\d\d:\d\d\.\d+) ([0-9.]+) writer totals: groups (\d+) writes (\d+) frames (\d+)", line)
    if m:
        rows.append((tod(m.group(1)) if between else float(m.group(2)) / 1000, int(m.group(3)), int(m.group(4)), int(m.group(5))))
if between:
    lo, hi = tod(sys.argv[3]), tod(sys.argv[4])
    rows = [r for r in rows if lo <= r[0] <= hi]
    secs = hi - lo
if len(rows) < 2:
    sys.exit("no writer totals in the trace")
end = rows[-1]
start = next((r for r in rows if r[0] >= end[0] - secs), rows[0])
dg, dw, df, dt = end[1] - start[1], end[2] - start[2], end[3] - start[3], end[0] - start[0]
print(f"{dt:.1f} s: {dw / dt:,.0f} writes/s, {dw / max(dg, 1):.2f} writes/group, {df / max(dw, 1):.3f} frames/post, "
      f"{df * 4120 / max(dw, 1) / 1024:.2f} KB/post, {df * 4120 / dt / 1e6:.0f} MB/s of WAL")
