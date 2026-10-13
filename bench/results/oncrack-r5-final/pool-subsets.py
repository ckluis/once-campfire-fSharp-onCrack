#!/usr/bin/env python3
"""Sensitivity cut of the R5 headline (not the headline itself: PLAN.md rule 3 pools every session). Geometric mean of the ratios of medians for
subsets of a profile's sessions: all three (the headline), the first two (the plan's design before any re-run), and the one session that passed the
noise rule. Written by the R5 write-up unit; `python3 pool-subsets.py > pooled-subsets.md`."""
import os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool

HERE = pool.HERE


def geo(dirs, routes, mixed, num, den):
    rs = []
    for r in routes:
        a = statistics.median(pool.samples(dirs, num, r, mixed))
        b = statistics.median(pool.samples(dirs, den, r, mixed))
        rs.append(a / b)
    return statistics.geometric_mean(rs), rs


def main():
    print('| Profile | sessions pooled | rounds a cell | fresh/Rust | fresh/C | fresh/port | fresh/cached | C/Rust |')
    print('|---|---|---:|---:|---:|---:|---:|---:|')
    for name, prefix, routes, mixed in [('Normal', 'normal', pool.NORMAL, False), ('Mixed', 'mixed', pool.MIXED, True)]:
        allv = pool.sessions(prefix)
        for label, dirs in [('all three (headline)', allv), ('first two (1 and 2)', allv[:2]), ('the quiet one (1)', allv[:1])]:
            n = len(pool.samples(dirs, 'oncrack', routes[0], mixed))
            vals = [geo(dirs, routes, mixed, a, b)[0] for a, b in [('oncrack', 'rust'), ('oncrack', 'c'), ('oncrack', 'fsharp'), ('oncrack', 'oncrack-cached')]]
            vals.append(geo(dirs, routes, mixed, 'c', 'rust')[0])
            print('| %s | %s | %d | **%.2fx** | **%.2fx** | %.2fx | %.2fx | %.2fx |' % ((name, label, n) + tuple(vals)))


if __name__ == '__main__':
    main()
