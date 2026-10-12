#!/usr/bin/env python3
"""R5.3: python3 ab-table.py DIR [BASE_ARM]. DIR holds arms.sh's rN-ARM directories (bench/run --out, cable suite, 1,000 and 2,000 clients).
Prints each round's msgs/s, CPU per delivery and Pss at saturation per arm and client count, the per-round ratio of every arm to BASE_ARM
(default 'default') for msgs/s and CPU per delivery, their medians, and the spread (min-max) of each arm's rounds."""
import glob, os, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'lib'))
import quicklog  # noqa: E402
roots = [a for a in sys.argv[1:] if os.path.isdir(a)]
base = next((a for a in sys.argv[1:] if not os.path.isdir(a)), 'default')
cells = {}
for root in roots:
    for d in sorted(glob.glob(os.path.join(root, 'r*-*'))):
        name = os.path.basename(d); rnd, arm = name.split('-', 1)
        rnd = os.path.basename(root.rstrip('/')) + rnd
        runs = quicklog.load(d, 'oncrack')
        for n, c in quicklog.cable_cells(runs).items():
            ok = all(r['throughput']['posted'] == r['throughput']['complete'] and r['client']['closed_midrun'] == 0
                     and r['throughput']['window_stalls'] == 0 for r in c['runs'])
            load = ''
            lp = os.path.join(d, 'load.txt')
            if os.path.exists(lp):
                load = '/'.join(l.split()[1] for l in open(lp).read().splitlines())
            cells[(n, rnd, arm)] = dict(msgs=c['msgs'][0], cpu=c['cpu_us'][0], pss=c['pss_sat'][0], lg=c['lg_cores'][0], srv=c['srv_cores'][0], ok=ok, load=load)
arms = sorted({a for _, _, a in cells}, key=lambda a: (a != base, a))
for n in sorted({n for n, _, _ in cells}):
    rounds = sorted({r for k, r, _ in cells if k == n}, key=lambda r: (len(r), r))
    print(f"\n== {n} clients ==")
    print(f"{'round':8} {'arm':10} {'msgs/s':>8} {'cpu us/del':>10} {'srv cores':>9} {'lg cores':>8} {'Pss MB':>7} {'VM load b/a':>12} valid")
    for r in rounds:
        for a in arms:
            c = cells.get((n, r, a))
            if c: print(f"{r:8} {a:10} {c['msgs']:8.1f} {c['cpu']:10.2f} {c['srv']:9.2f} {c['lg']:8.2f} {c['pss']:7.1f} {c['load']:>12} {'yes' if c['ok'] else 'NO'}")
    for a in arms:
        cs = [cells[(n, r, a)] for r in rounds if (n, r, a) in cells]
        m = [c['msgs'] for c in cs]; u = [c['cpu'] for c in cs]; p = [c['pss'] for c in cs]
        print(f"{a:10} median msgs/s {st.median(m):7.0f} [{min(m):.0f}-{max(m):.0f}]  CPU/del {st.median(u):.2f} [{min(u):.2f}-{max(u):.2f}]  Pss {st.median(p):.0f}")
    for a in arms:
        if a == base: continue
        rm = [cells[(n, r, a)]['msgs'] / cells[(n, r, base)]['msgs'] for r in rounds if (n, r, a) in cells and (n, r, base) in cells]
        rc = [cells[(n, r, a)]['cpu'] / cells[(n, r, base)]['cpu'] for r in rounds if (n, r, a) in cells and (n, r, base) in cells]
        print(f"{a}/{base} per round: msgs/s " + ' '.join(f'{x:.3f}' for x in rm) + f" | median {st.median(rm):.3f};  CPU/del " + ' '.join(f'{x:.3f}' for x in rc) + f" | median {st.median(rc):.3f}")
