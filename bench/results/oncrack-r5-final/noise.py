#!/usr/bin/env python3
"""PLAN.md rule 2: the share of a session's host samples (taken while the session ran, after its quiet wait) with a non-VM CPU sum >= 150%.
    python3 noise.py host-load-NAME.txt ..."""
import re, sys
for f in sys.argv[1:]:
    during, vals = False, []
    for l in open(f):
        if l.startswith('# quiet') or l.startswith('# NOT'): during = True; vals = []; continue
        m = re.search(r'\| sum (\d+) \|', l)
        if during and m: vals.append(int(m.group(1)))
    hi = sum(v >= 150 for v in vals)
    print('%s: %d samples during the session, %d at >=150%% (%.0f%%), max %d%%, median %d%% -> %s' % (f, len(vals), hi, 100 * hi / len(vals), max(vals), sorted(vals)[len(vals) // 2], 'NOISY' if hi / len(vals) > .25 else 'ok'))
