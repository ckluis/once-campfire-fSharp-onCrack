#!/usr/bin/env python3
"""R4.2's run tables: python3 table.py DIR... (each a bench/run --out directory with oncrack-N.json files). One row per client count,
CPU per delivery as bench/lib/quicklog.cable_cells computes it (saturated phase, posting and draining)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'lib'))
import quicklog  # noqa: E402

for d in sys.argv[1:]:
    load = ''
    lp = os.path.join(d, 'load.txt')
    if os.path.exists(lp):
        load = ' | '.join(l.split()[0] + ' ' + l.split()[1] for l in open(lp).read().splitlines())
    for app in ('rust', 'fsharp', 'oncrack'):
        runs = quicklog.load(d, app)
        for n, c in sorted(quicklog.cable_cells(runs).items()):
            cs = c['runs'][0]
            t = cs['throughput']
            ok = all(r['throughput']['posted'] == r['throughput']['complete'] and r['client']['closed_midrun'] == 0
                     and r['throughput']['window_stalls'] == 0 for r in c['runs'])
            print(f"{os.path.basename(d.rstrip('/')):14} {app:8} n={n:5} msgs/s={c['msgs'][0]:8.1f} cpu/deliv={c['cpu_us'][0]:5.2f}us "
                  f"cores={c['srv_cores'][0]:.2f} pss_sat={c['pss_sat'][0]:6.1f} lg={c['lg_cores'][0]:.2f} "
                  f"paced p50/p99={cs['latency']['post']['p50_ms']:.1f}/{cs['latency']['post']['p99_ms']:.1f} {'OK' if ok else 'INVALID'}  [{load}]")
