#!/usr/bin/env python3
"""R5.3: python3 flip-table.py LOG [BASE]. LOG is bench/cable/flip's output. Prints each arm's runs (rep order), medians with ranges, and per-rep ratios to BASE
(default: the first arm): msgs/s, and server CPU per delivery. A rep whose run the host starved (either run of a pair under 60% of the rep's best msgs/s) is
marked and left out of the 'clean' medians, which are shown beside the all-runs ones."""
import re, statistics as st, sys
log = sys.argv[1]; base = sys.argv[2] if len(sys.argv) > 2 else None
runs = {}
order = []
last = None
for line in open(log):
    h = re.match(r'\s+host ([\d.]+) ([\d.]+)', line)
    if h and last: runs[last]['hb'], runs[last]['ha'] = float(h.group(1)), float(h.group(2)); continue
    m = re.match(r'(\S+) #(\d+)\s+ready\s+(\d+) failed (\d+)\s+([\d.]+) msgs/s\s+server ([\d.]+) cores\s+([\d.]+) us/del\s+loadgen ([\d.]+) cores', line)
    if not m: continue
    name, rep = m.group(1), int(m.group(2))
    last = (name, rep)
    runs[(name, rep)] = dict(msgs=float(m.group(5)), cpu=float(m.group(7)), srv=float(m.group(6)), lg=float(m.group(8)), ready=int(m.group(3)), failed=int(m.group(4)))
    if name not in order: order.append(name)
base = base or order[0]
reps = sorted({r for _, r in runs})
print(f"{'rep':4}" + ''.join(f"{a:>30}" for a in order))
for r in reps:
    print(f"{r:<4}" + ''.join((f"{runs[(a, r)]['msgs']:>10.0f} {runs[(a, r)]['cpu']:>5.2f}us h{runs[(a, r)].get('hb', 0):.2f}/{runs[(a, r)].get('ha', 0):.2f}  " if (a, r) in runs else ' ' * 30) for a in order))
best = {r: max(runs[(a, r)]['msgs'] for a in order if (a, r) in runs) for r in reps}
HOST_MAX = 1.3
starved = {r for r in reps if any((a, r) in runs and (runs[(a, r)]['msgs'] < 0.6 * best[r] or max(runs[(a, r)].get('hb', 0), runs[(a, r)].get('ha', 0)) > HOST_MAX) for a in order)}
clean = [r for r in reps if r not in starved]
print(f"\nreps the host disturbed (a run under 60% of the rep's best, or a host probe over 1.3 before or after any run): {sorted(starved) or 'none'}")
for label, rs in (('all reps', reps), ('clean reps', clean)):
    print(f"\n-- {label} ({len(rs)}) --")
    for a in order:
        m = [runs[(a, r)]['msgs'] for r in rs if (a, r) in runs]; c = [runs[(a, r)]['cpu'] for r in rs if (a, r) in runs]
        if not m: continue
        line = f"{a:10} msgs/s median {st.median(m):7.0f} [{min(m):.0f}-{max(m):.0f}]  CPU/del {st.median(c):.2f} [{min(c):.2f}-{max(c):.2f}] us"
        if a != base:
            rm = [runs[(a, r)]['msgs'] / runs[(base, r)]['msgs'] for r in rs if (a, r) in runs and (base, r) in runs]
            rc = [runs[(a, r)]['cpu'] / runs[(base, r)]['cpu'] for r in rs if (a, r) in runs and (base, r) in runs]
            line += f"  | vs {base}: msgs/s " + ' '.join(f'{x:.2f}' for x in rm) + f" (median {st.median(rm):.3f}); CPU " + ' '.join(f'{x:.2f}' for x in rc) + f" (median {st.median(rc):.3f})"
        print(line)
