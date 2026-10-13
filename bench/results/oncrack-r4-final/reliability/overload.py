#!/usr/bin/env python3
"""The overload table of oncrack-r4-final.md: per app, route and client count the median req/s over the session's rounds, with errors and invalid
responses summed over them, from session/harness-output/*.json (the F# port is absent: its contract preparation stops at 'search: differs from seed SQL').

    python3 bench/results/oncrack-r4-final/reliability/overload.py
"""
import glob, json, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
APPS = [('rails', 'Rails 0aa339d'), ('rust', 'Rust f9dca47'), ('c', 'C cd0cbe4'), ('oncrack-prev', 'onCrack before R4.5'), ('oncrack', '**onCrack, fresh (HEAD)**'), ('oncrack-cached', 'onCrack, cached decision')]
ROUTES = ['room_show', 'messages_page', 'sidebar', 'search']
for conc in (64, 256):
    print('Median requests/sec at %d clients, 8 s per route, over the rounds that ran [rounds]; errors / invalid responses summed over them\n' % conc)
    print('| Implementation | Rounds | Room page | Messages page | Sidebar | Search | Errors / invalid |')
    print('|---|---:|---:|---:|---:|---:|---|')
    for a, n in APPS:
        files = sorted(glob.glob(os.path.join(HERE, 'session', 'harness-output', a + '-[0-9].json')))
        rows = [json.load(open(f)) for f in files]
        cells, err, inv = [], 0, 0
        for r in ROUTES:
            v = [x['rps'] for d in rows for x in d['overload'] if x['route'] == r and x['conc'] == conc]
            err += sum(x['errors'] for d in rows for x in d['overload'] if x['route'] == r and x['conc'] == conc)
            inv += sum(x['invalid_responses'] for d in rows for x in d['overload'] if x['route'] == r and x['conc'] == conc)
            cells.append(format(round(st.median(v)), ',') if v else '-')
        print('| %s | %d | %s | %d / %d |' % (n, len(rows), ' | '.join(cells), err, inv))
    print()
