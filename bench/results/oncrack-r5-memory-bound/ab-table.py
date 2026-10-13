#!/usr/bin/env python3
"""R5.2 memory bound: python3 ab-table.py DIR (arms.log-style dirs rN-before / rN-after of bench/run --out, 1,000 clients). Prints each round's
msgs/s, CPU per delivery and Pss at saturation for both arms, the per-round after/before ratio of CPU per delivery, and the medians."""
import glob, os, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'lib'))
import quicklog  # noqa: E402
root = sys.argv[1]
cells = {}
for d in sorted(glob.glob(os.path.join(root, 'r*-*'))):
    name = os.path.basename(d); rnd, arm = name.split('-')
    runs = quicklog.load(d, 'oncrack')
    for n, c in quicklog.cable_cells(runs).items():
        if n != 1000: continue
        ok = all(r['throughput']['posted'] == r['throughput']['complete'] and r['client']['closed_midrun'] == 0 for r in c['runs'])
        cells[(rnd, arm)] = (c['msgs'][0], c['cpu_us'][0], c['pss_sat'][0], c['lg_cores'][0], ok)
rounds = sorted({r for r, _ in cells}, key=lambda r: int(r[1:]))
print(f"{'round':6} {'arm':7} {'msgs/s':>8} {'cpu us/deliv':>13} {'Pss MB':>7} {'loadgen cores':>14} valid")
for r in rounds:
    for a in ('before', 'after'):
        m, c, p, lg, ok = cells[(r, a)]
        print(f"{r:6} {a:7} {m:8.1f} {c:13.2f} {p:7.1f} {lg:14.2f} {'yes' if ok else 'NO'}")
ratios = [cells[(r, 'after')][1] / cells[(r, 'before')][1] for r in rounds]
print('\nper-round after/before CPU per delivery:', ' '.join(f'{x:.3f}' for x in ratios), '| median', f'{st.median(ratios):.3f}')
for a in ('before', 'after'):
    print(f"{a}: median msgs/s {st.median(cells[(r, a)][0] for r in rounds):.0f}, CPU/delivery {st.median(cells[(r, a)][1] for r in rounds):.2f} us, Pss {st.median(cells[(r, a)][2] for r in rounds):.1f} MB")
