#!/usr/bin/env python3
"""R5.2's rotated runs, round by round: python3 arms-table.py DIR [BASE_ARM]. DIR holds rROUND-ARM run directories (arms-r52.sh, cost-r52.sh).
Per round and arm: server CPU per delivery (us), msgs/s and Pss at saturation (MB) as bench/lib/quicklog.cable_cells computes them, whether
every message reached every client; then per arm the medians and, against BASE_ARM, the per-round ratio of CPU per delivery."""
import glob, os, re, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'lib'))
import quicklog  # noqa: E402

root = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else None
d = {}
for run in sorted(glob.glob(os.path.join(root, 'r*-*'))):
    m = re.match(r'r(\d+)-(.+)$', os.path.basename(run))
    if not m or not os.path.isdir(run):
        continue
    runs = quicklog.load(run, 'oncrack')
    for n, c in quicklog.cable_cells(runs).items():
        ok = all(r['throughput']['posted'] == r['throughput']['complete'] and r['client']['closed_midrun'] == 0 for r in c['runs'])
        d.setdefault(int(m.group(1)), {})[m.group(2)] = (c['cpu_us'][0], c['msgs'][0], c['pss_sat'][0], ok, n)
arms = sorted({a for r in d.values() for a in r}, key=lambda a: (a != base, a))
print('| round | ' + ' | '.join(f'{a}: us / msgs/s / Pss MB' for a in arms) + ' |')
print('|---|' + '---|' * len(arms))
for rd in sorted(d):
    print(f'| {rd} | ' + ' | '.join((f'{d[rd][a][0]:.2f} / {d[rd][a][1]:.0f} / {d[rd][a][2]:.0f}' + ('' if d[rd][a][3] else ' INVALID')) if a in d[rd] else '' for a in arms) + ' |')
print()
for a in arms:
    xs = [d[r][a] for r in d if a in d[r]]
    line = f'{a}: {len(xs)} runs, median CPU {st.median(x[0] for x in xs):.2f} us, msgs/s {st.median(x[1] for x in xs):.0f}, Pss {st.median(x[2] for x in xs):.0f} MB, all delivered {all(x[3] for x in xs)}'
    if base and a != base:
        rat = [d[r][a][0] / d[r][base][0] for r in d if a in d[r] and base in d[r]]
        line += f'; CPU / {base} per round {[round(x, 2) for x in rat]}, median {st.median(rat):.3f}'
    print(line)
