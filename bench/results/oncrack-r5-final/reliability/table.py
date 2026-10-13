#!/usr/bin/env python3
"""The reliability tables of oncrack-r5-final.md from main/summary.json and fsharp/summary.json (bench/reliability/summarize --write):
per app and profile, the rounds' own values (round 1, round 2 ...) and the median. A row repeated in a later directory replaces the earlier.

    python3 bench/results/oncrack-r5-final/reliability/table.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = [('rails', 'Rails 0aa339d'), ('rust', 'Rust f9dca47'), ('c', 'C cd0cbe4'), ('fsharp', 'F# port'),
         ('oncrack-prev', 'onCrack before R4.5 (`21791e2`)'), ('oncrack', '**onCrack, fresh authorization (HEAD)**'), ('oncrack-cached', 'onCrack, cached decision (opt-in)')]
data = {}
for d in ('main', 'fsharp'):
    p = os.path.join(HERE, d, 'summary.json')
    if os.path.exists(p):
        data.update(json.load(open(p)))


def fmt(v, nd=0):
    if v is None:
        return '-'
    return format(round(v, nd), ',.%df' % nd)


def rounds(d, f, nd=0):
    return ' / '.join(fmt(v, nd) for v in d['rounds'][f])


for profile, title in (('cable_heavy', 'cable_heavy: 1,000 clients, 64 closed-loop posters with no limit, the harness waits up to 60 s for every client to have every message'),
                       ('cable', 'cable: 1,000 clients, 4 posters (the default posting load)')):
    print('### %s\n' % title)
    print('| App | Rounds | Subscribed | Disconnected | Delivered to every client / posted | Messages/s | p99 post to last client, ms | Pss peak, MB |')
    print('|---|---:|---|---|---|---|---|---|')
    for k, n in NAMES:
        if k not in data or profile not in data[k]:
            continue
        d = data[k][profile]
        both = ' / '.join('%s of %s' % (fmt(c), fmt(p)) for c, p in zip(d['rounds']['complete'], d['rounds']['posted']))
        print('| %s | %d | %s | %s | %s | %s | %s | %s |' % (n, len(d['rounds']['round']), rounds(d, 'ready'), rounds(d, 'disconnected'), both,
                                                         rounds(d, 'msgs', 1), rounds(d, 'p99'), rounds(d, 'pss')))
    print()
