#!/usr/bin/env python3
"""Tables for oncrack-r3-fresh-auth.md (from oncrack-r2-final/table.py, with the two onCrack modes and their ratios) from once-campfire-verification's bin/benchmark output, in its own reporting form:
median and observed min-max requests/sec per cell, timed responses validated, acknowledged writes audited (warm-ups included),
peak load generator CPU (100% per core, 400% available), and a reconciliation of every raw sample against the per-app rows.

    python3 table.py DIR [DIR ...]      # DIR: a copy of bin/benchmark's --output (summary.json or mixed-summary.json, APP-N.json, raw/)
"""
import glob
import json
import os
import statistics
import sys

NAMES = {'rails': 'Rails 0aa339d', 'rust': 'Rust f9dca47', 'c': 'C cd0cbe4', 'fsharp': 'F# port', 'oncrack': 'onCrack (fresh authorization, default)', 'oncrack-cached': 'onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0)'}
ROUTES = ['room_show', 'messages_page', 'sidebar', 'search', 'post_message']
RN = {'room_show': 'Room page', 'messages_page': 'Messages page', 'sidebar': 'Sidebar', 'search': 'Search', 'post_message': 'Post a message'}


def load(d):
    s = os.path.join(d, 'summary.json')
    mixed = not os.path.exists(s)
    summary = json.load(open(os.path.join(d, 'mixed-summary.json' if mixed else 'summary.json')))
    meta = summary['metadata']
    apps = list(meta['images'])
    rounds = int(meta['rounds'])
    rows = {(a, r): json.load(open(os.path.join(d, '%s-%d.json' % (a, r)))) for a in apps for r in range(1, rounds + 1)}
    raw = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, 'raw', 'http-*.json')), key=lambda f: int(f.rsplit('-', 1)[1].split('.')[0]))]
    return meta, apps, rounds, rows, raw, mixed


def reconcile(meta, apps, rounds, rows, raw, mixed):
    """Walk the raw samples in run order (apps forward in odd rounds, reversed in even ones; a warm-up then a timed sample per route)
    and check each timed one against the app's row. Returns {app: [raw samples]} or raises."""
    routes = meta['routes'].split(',')
    by_app = {a: [] for a in apps}
    i = 0
    for r in range(rounds):
        order = apps if r % 2 == 0 else list(reversed(apps))
        for a in order:
            timed = rows[a, r + 1]['mixed_http' if mixed else 'http']
            for k, route in enumerate(routes):
                warm, t = raw[i], raw[i + 1]
                i += 2
                assert warm['conc'] == 4 and t['conc'] == 16, (a, r, route)
                assert t['rps'] == timed[k]['rps'] and timed[k]['route'] == route, (a, r, route, t['rps'], timed[k]['rps'])
                by_app[a] += [warm, t]
    assert i == len(raw), (i, len(raw))
    return by_app


def main(dirs):
    for d in dirs:
        meta, apps, rounds, rows, raw, mixed = load(d)
        by_app = reconcile(meta, apps, rounds, rows, raw, mixed)
        routes = meta['routes'].split(',')
        print('## %s (%s, %d rounds, %s s, c=%s, server CPUs %s, client CPUs %s)\n' % (os.path.basename(d.rstrip('/')), meta['profile'], rounds,
              meta['duration'], meta['concurrencies'], meta['server_cpus'], meta['client_cpus']))
        print('| %s | %s |' % ('Implementation', ' | '.join(RN[r] for r in routes)))
        print('|---|%s' % ('---:|' * len(routes)))
        for a in apps:
            cells = []
            for route in routes:
                v = [x['rps'] for rr in range(1, rounds + 1) for x in rows[a, rr]['mixed_http' if mixed else 'http'] if x['route'] == route]
                cells.append('%s [%s-%s]' % (format(round(statistics.median(v)), ','), format(round(min(v)), ','), format(round(max(v)), ',')))
            print('| %s | %s |' % (NAMES.get(a, a), ' | '.join(cells)))
        print()
        print('| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |')
        print('|---|---:|---:|---:|---|---:|---|')
        tot = [0, 0, 0]
        for a in apps:
            timed = [x for rr in range(1, rounds + 1) for x in rows[a, rr]['mixed_http' if mixed else 'http']]
            ok = sum(x['ok'] for x in timed)
            audited = sum(rows[a, rr]['post_write_audit']['acknowledged'] for rr in range(1, rounds + 1))
            assert all(rows[a, rr]['post_write_audit']['verified'] for rr in range(1, rounds + 1))
            assert all(rows[a, rr]['persisted_writes'] == rows[a, rr]['richtext_http_posts'] == rows[a, rr]['post_write_audit']['acknowledged'] for rr in range(1, rounds + 1))
            writer = [x['writer']['ok'] for x in timed if 'writer' in x]
            wrate = [x['writer']['ok'] / x['secs'] for x in timed if 'writer' in x]
            peak = max(s['generator_cpu_percent'] for s in by_app[a])
            room = [x for x in timed if x['route'] == 'room_show']
            lat = '%.3f / %.3f' % (statistics.median(x['latency']['p50_ms'] for x in room), statistics.median(x['latency']['p99_ms'] for x in room)) if room else '-'
            tot[0] += ok; tot[1] += audited; tot[2] += sum(writer)
            print('| %s | %s | %s | %s | %s | %.1f | %s |' % (NAMES.get(a, a), format(ok, ','), format(audited, ','), format(sum(writer), ',') if writer else '-',
                  ('%.1f-%.1f' % (min(wrate), max(wrate))) if wrate else '-', peak, lat))
        print('| all | %s | %s | %s | | %.1f | |' % (format(tot[0], ','), format(tot[1], ','), format(tot[2], ','), max(s['generator_cpu_percent'] for s in raw)))
        med = lambda a, route: statistics.median(x['rps'] for rr in range(1, rounds + 1) for x in rows[a, rr]['mixed_http' if mixed else 'http'] if x['route'] == route)
        geo = lambda xs: statistics.geometric_mean(xs)
        print('| ratio (medians) | %s | geometric mean |' % ' | '.join(RN[r] for r in routes))
        print('|---|%s---:|' % ('---:|' * len(routes)))
        for num in ('oncrack', 'oncrack-cached'):
            for den in ('rust', 'c', 'fsharp', 'oncrack-cached'):
                if num == den or num not in apps or den not in apps:
                    continue
                rs = [med(num, r) / med(den, r) for r in routes]
                print('| %s / %s | %s | **%.2fx** |' % (num, den, ' | '.join('%.2fx' % x for x in rs), geo(rs)))
        print()
        errs = sum(s['errors'] + s['invalid_responses'] for s in raw)
        print('\n%d raw samples reconciled against the per-app rows; errors + invalid responses across all of them: %d.\n' % (len(raw), errs))


if __name__ == '__main__':
    main(sys.argv[1:])
