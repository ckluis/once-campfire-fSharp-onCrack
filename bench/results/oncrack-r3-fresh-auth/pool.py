#!/usr/bin/env python3
"""The R3.2 headline (PLAN.md, fixed before the second normal session): each cell's median over both normal sessions' six rounds,
and the hand re-runs' medians of server CPU per request. Reads upstream-normal-noisy/ and upstream-normal-2/ (bin/benchmark output)
and review.jsonl (review.py lines).

    python3 pool.py
"""
import json, os, statistics, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SESSIONS = ['upstream-normal-noisy', 'upstream-normal-2']
APPS = ['oncrack', 'oncrack-cached', 'rust', 'c', 'fsharp']
NAMES = {'oncrack': 'onCrack, fresh authorization (default)', 'oncrack-cached': 'onCrack, cached decision (opt-in)', 'rust': 'Rust f9dca47',
         'c': 'C cd0cbe4', 'fsharp': 'F# port'}
ROUTES = ['room_show', 'messages_page', 'sidebar', 'search', 'post_message']
RN = {'room_show': 'Room page', 'messages_page': 'Messages page', 'sidebar': 'Sidebar', 'search': 'Search', 'post_message': 'Post a message'}


def samples(app, route):
    out = []
    for s in SESSIONS:
        for f in sorted(glob.glob(os.path.join(HERE, s, '%s-[0-9].json' % app))):
            out += [x['rps'] for x in json.load(open(f))['http'] if x['route'] == route and x['conc'] == 16]
    assert len(out) == 6, (app, route, len(out))
    return out


def main():
    med = {(a, r): statistics.median(samples(a, r)) for a in APPS for r in ROUTES}
    print('Pooled: median requests/sec of six rounds (two sessions x three) [min-max], 16 clients\n')
    print('| Implementation | %s |' % ' | '.join(RN[r] for r in ROUTES))
    print('|---|%s' % ('---:|' * len(ROUTES)))
    for a in APPS:
        print('| %s | %s |' % (NAMES[a], ' | '.join('%s [%s-%s]' % (format(round(med[a, r]), ','), format(round(min(samples(a, r))), ','),
                                                                       format(round(max(samples(a, r))), ',')) for r in ROUTES)))
    print('\n| ratio of pooled medians | %s | geometric mean |' % ' | '.join(RN[r] for r in ROUTES))
    print('|---|%s---:|' % ('---:|' * len(ROUTES)))
    for num, den in [('oncrack', 'rust'), ('oncrack', 'c'), ('oncrack', 'fsharp'), ('oncrack', 'oncrack-cached'),
                     ('oncrack-cached', 'rust'), ('oncrack-cached', 'c'), ('oncrack-cached', 'fsharp')]:
        rs = [med[num, r] / med[den, r] for r in ROUTES]
        print('| %s / %s | %s | **%.2fx** |' % (num, den, ' | '.join('%.2fx' % x for x in rs), statistics.geometric_mean(rs)))
    rows = [json.loads(l) for l in open(os.path.join(HERE, 'review.jsonl')) if '"window"' in l]
    key = lambda d: 'oncrack-cached' if d['app'] == 'oncrack' and 'cached' in d['tag'] else d['app']
    print('\nHand re-runs (review.py, 15 s warm-up, 10 s window, server CPU from the cgroup): every window, then the medians\n')
    print('| App | phase | req/s per run | CPU us/request per run | median CPU us/request |')
    print('|---|---|---|---|---:|')
    cpu = {}
    for a in ['oncrack', 'oncrack-cached', 'rust', 'c']:
        for ph in ['room_show', 'mixed']:
            ds = [d for d in rows if key(d) == a and d['phase'] == ph]
            if not ds:
                continue
            cpu[a, ph] = statistics.median(d['server_cpu_us_per_req'] for d in ds)
            print('| %s | %s | %s | %s | %.1f |' % (NAMES[a], ph, ', '.join(format(round(d['rps']), ',') for d in ds),
                                                  ', '.join('%.1f' % d['server_cpu_us_per_req'] for d in ds), cpu[a, ph]))
    print('\n| CPU per request, median over runs | room page | mixed reads |')
    print('|---|---:|---:|')
    for a, b in [('rust', 'oncrack'), ('c', 'oncrack'), ('rust', 'oncrack-cached'), ('c', 'oncrack-cached'), ('oncrack', 'oncrack-cached')]:
        print('| %s / %s | %.2fx | %.2fx |' % (a, b, cpu[a, 'room_show'] / cpu[b, 'room_show'], cpu[a, 'mixed'] / cpu[b, 'mixed']))


if __name__ == '__main__':
    main()
