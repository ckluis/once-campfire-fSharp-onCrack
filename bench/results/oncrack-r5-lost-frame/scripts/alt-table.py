#!/usr/bin/env python3
"""R5.2's alternation of the two fixes (pinned object heap, stack pins) by block: python3 alt-table.py ROOT [HOSTLOAD]. ROOT holds blocks
(bench/cable/loop --keep-all 1 with CAMPFIRE_MEM_LOG_MS=1000) named ARM + number. Per phase: msgs/s, and from the app's `mem:` lines in the
phase (first and last), collections (gen0/1/2), GC pause time and the most fragmented bytes the GC reported; with HOSTLOAD (lines
`HH:MM:SS { 1m 5m 15m }` sampled on the Mac), the Mac's 1-minute load average when the phase started."""
import glob, json, os, re, statistics as st, sys
root = sys.argv[1]
host = []
if len(sys.argv) > 2:
    for line in open(sys.argv[2]):
        m = re.match(r'(\d+):(\d+):(\d+) \{ ([\d.]+)', line)
        if m:
            host.append((int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]), float(m[4])))
def load_at(hms):
    h, mi, s = map(int, hms.split(':'))
    t = h * 3600 + mi * 60 + s
    near = [l for (u, l) in host if abs(u - t) <= 15]
    return max(near) if near else None
mem = re.compile(r'mem: .*?frag=([\d.]+).*?gcs=(\d+)/(\d+)/(\d+) pause_ms=(\d+)')
arms = {}
for block in sorted(glob.glob(os.path.join(root, '*/'))):
    name = os.path.basename(block.rstrip('/'))
    arm = re.sub(r'\d+$', '', name)
    pj = os.path.join(block, 'phases.jsonl')
    if not os.path.exists(pj):
        continue
    for line in open(pj):
        p = json.loads(line)
        if p['shape'] != 'target':
            continue
        rows = []
        log = os.path.join(block, p['dir'], 'app.log')
        if not os.path.exists(log):
            log = os.path.join(block, p['dir'], 'mem.log')  # data-r52/alt keeps only the `mem:` lines
        if os.path.exists(log):
            rows = [tuple(float(x) for x in m.groups()) for m in map(mem.search, open(log, errors='replace')) if m]
        if len(rows) >= 2:
            a, b = rows[0], rows[-1]
            gc = f"{int(b[1]-a[1])}/{int(b[2]-a[2])}/{int(b[3]-a[3])}"
            pause = int(b[4] - a[4]); frag = max(r[0] for r in rows)
        else:
            gc, pause, frag = '?', None, None
        ok = p['posted'] == p['complete'] and p['closed_midrun'] == 0
        arms.setdefault(arm, []).append((p['msgs_per_sec'], pause, frag))
        print(f"{name:8} {p['dir']:12} {p['started']} msgs/s {p['msgs_per_sec']:7.0f} gcs {gc:>9} pause {pause if pause is not None else '?':>5} ms frag max {frag if frag is not None else '?':>6} MB "
              f"mac load {load_at(p['started']) or '?'} {'OK' if ok else 'NOT DELIVERED'}")
print()
for arm, xs in arms.items():
    v = sorted(x[0] for x in xs); med = st.median(v)
    pauses = [x[1] for x in xs if x[1] is not None]; frags = [x[2] for x in xs if x[2] is not None]
    print(f"{arm}: {len(v)} phases, median {med:.0f} msgs/s, below half the median {[round(x) for x in v if x < med / 2]}, "
          f"GC pause per phase median {st.median(pauses) if pauses else '?'} ms, fragmentation max median {st.median(frags) if frags else '?'} MB")
