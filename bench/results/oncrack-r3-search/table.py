#!/usr/bin/env python3
"""Tables for oncrack-r3-search.md from once-campfire-verification's bin/benchmark output (route: search only).

    python3 table.py DIR [DIR ...]     # DIR: a copy of bin/benchmark's --output (summary.json or mixed-summary.json, APP-N.json)

Prints, per session and pooled over the normal sessions: median [min-max] requests/sec per app, the ratios, timed responses
validated, errors plus invalid responses, and whether each app's search page listed the message ids of the contract (the search_order
recorded in the metadata), compared across apps.
"""
import json, os, statistics, sys

NAMES = {'oncrack': 'onCrack (this unit)', 'oncrack-prev': 'onCrack before R3.3 (87c1ad1)', 'rust': 'Rust f9dca47', 'c': 'C cd0cbe4', 'fsharp': 'F# port'}


def load(d):
    mixed = not os.path.exists(os.path.join(d, 'summary.json'))
    s = json.load(open(os.path.join(d, 'mixed-summary.json' if mixed else 'summary.json')))
    meta = s['metadata']
    apps = list(meta['images'])
    rounds = int(meta['rounds'])
    rows = {(a, r): json.load(open(os.path.join(d, '%s-%d.json' % (a, r)))) for a in apps for r in range(1, rounds + 1)}
    return meta, apps, rounds, rows, mixed


def samples(rows, app, rounds, mixed):
    out = []
    for r in range(1, rounds + 1):
        for x in rows[app, r]['mixed_http' if mixed else 'http']:
            if x['path'].startswith('/searches'):
                out.append(x)
    return out


def fmt(v):
    return '%s [%s-%s]' % ('{:,.0f}'.format(statistics.median(v)), '{:,.0f}'.format(min(v)), '{:,.0f}'.format(max(v)))


def main(dirs):
    pooled = {}
    ids = {}
    for d in dirs:
        meta, apps, rounds, rows, mixed = load(d)
        print('\n### %s (%s, %d rounds, search order by app: %s)\n' % (d, 'mixed' if mixed else 'normal', rounds, json.dumps(meta['search_order'])))
        print('| App | search req/s median [min-max] | timed responses validated | errors + invalid | p50 / p99 ms |')
        print('|---|---:|---:|---:|---|')
        med = {}
        for a in apps:
            xs = samples(rows, a, rounds, mixed)
            v = [x['rps'] for x in xs]
            med[a] = statistics.median(v)
            pooled.setdefault((mixed, a), []).extend(v)
            lat = [x['latency'] for x in xs]
            p50 = statistics.median(l['p50_ms'] if 'p50_ms' in l else l.get('p50', 0) for l in lat) if lat and isinstance(lat[0], dict) else 0
            p99 = statistics.median(l['p99_ms'] if 'p99_ms' in l else l.get('p99', 0) for l in lat) if lat and isinstance(lat[0], dict) else 0
            print('| %s | %s | %s | %d | %.3f / %.3f |' % (NAMES.get(a, a), fmt(v), '{:,}'.format(sum(x['ok'] for x in xs)),
                                                            sum(x['errors'] + x['invalid_responses'] for x in xs), p50, p99))
            if mixed:
                aud = [rows[a, r]['post_write_audit'] for r in range(1, rounds + 1)]
                print('|  writer audit |  |  acknowledged %d, all verified: %s |  |  |' % (sum(x['acknowledged'] for x in aud), all(x['verified'] for x in aud)))
            for r in range(1, rounds + 1):
                p = rows[a, r]['preflight']['search']
                ids.setdefault(a, set()).add(tuple(p['message_ids']))
        for other in ('rust', 'c', 'oncrack-prev', 'fsharp'):
            if 'oncrack' in med and other in med:
                print('\nonCrack / %s: %.2fx' % (NAMES[other], med['oncrack'] / med[other]), end='')
        print()
    print('\n### pooled over the sessions given, per profile\n')
    for mixed in (False, True):
        keys = [k for k in pooled if k[0] == mixed]
        if not keys:
            continue
        print('%s:' % ('mixed' if mixed else 'normal'))
        base = {a: statistics.median(pooled[(mixed, a)]) for (_, a) in keys}
        for (_, a) in keys:
            print('  %-32s %s  n=%d' % (NAMES.get(a, a), fmt(pooled[(mixed, a)]), len(pooled[(mixed, a)])))
        for other in ('rust', 'c', 'oncrack-prev', 'fsharp'):
            if 'oncrack' in base and other in base:
                print('  onCrack / %-24s %.2fx' % (NAMES[other], base['oncrack'] / base[other]))
    print('\n### the search page\'s message ids, one distinct list per app and session set\n')
    for a, s in ids.items():
        print('  %-14s %d distinct list(s), %d ids' % (a, len(s), len(next(iter(s)))))
    ref = ids.get('rust')
    for a in ids:
        print('  %-14s equals Rust\'s list: %s' % (a, ids[a] == ref))


if __name__ == '__main__':
    main(sys.argv[1:])
