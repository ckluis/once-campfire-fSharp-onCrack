#!/usr/bin/env python3
"""The R3 final headline (PLAN.md): each cell's median over all rounds of all of a profile's sessions (normal-N/, mixed-N/ here; a
directory named aborted-* or discarded-* is never read), and the hand re-runs' medians of server CPU per request (review.jsonl).

    python3 pool.py
"""
import glob, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = ['oncrack', 'oncrack-cached', 'rust', 'c', 'fsharp', 'rails']
NAMES = {'oncrack': '**onCrack, fresh authorization (default)**', 'oncrack-cached': 'onCrack, cached decision (opt-in)', 'rust': 'Rust f9dca47',
         'c': 'C cd0cbe4', 'fsharp': 'F# port', 'rails': 'Rails 0aa339d'}
NORMAL = ['room_show', 'messages_page', 'sidebar', 'search', 'post_message']
MIXED = ['room_show', 'messages_page', 'sidebar', 'search']
RN = {'room_show': 'Room page', 'messages_page': 'Messages page', 'sidebar': 'Sidebar', 'search': 'Search', 'post_message': 'Post a message'}


def sessions(prefix):
    return sorted(d for d in glob.glob(os.path.join(HERE, prefix + '-[0-9]*')) if os.path.isdir(d))


def samples(dirs, app, route, mixed):
    out = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '%s-[0-9].json' % app))):
            out += [x['rps'] for x in json.load(open(f))['mixed_http' if mixed else 'http'] if x['route'] == route and x['conc'] == 16]
    return out


def table(title, dirs, routes, mixed):
    n = len(samples(dirs, 'oncrack', routes[0], mixed))
    print('### %s\n\nMedian requests/sec of %d rounds (%d session%s x 3) [min-max], 16 clients. Sessions: %s\n' % (
        title, n, len(dirs), '' if len(dirs) == 1 else 's', ', '.join(os.path.basename(d) for d in dirs)))
    med = {}
    print('| Implementation | %s |' % ' | '.join(RN[r] for r in routes))
    print('|---|%s' % ('---:|' * len(routes)))
    for a in APPS:
        cells = []
        for r in routes:
            v = samples(dirs, a, r, mixed)
            assert len(v) == n, (a, r, len(v), n)
            med[a, r] = statistics.median(v)
            cells.append('%s [%s-%s]' % (format(round(med[a, r]), ','), format(round(min(v)), ','), format(round(max(v)), ',')))
        print('| %s | %s |' % (NAMES[a], ' | '.join(cells)))
    print('\n| Ratio of medians | %s | Geometric mean |' % ' | '.join(RN[r] for r in routes))
    print('|---|%s---:|' % ('---:|' * len(routes)))
    for num, den in [('oncrack', 'rust'), ('oncrack', 'c'), ('oncrack', 'fsharp'), ('oncrack', 'rails'), ('oncrack', 'oncrack-cached'),
                     ('oncrack-cached', 'rust'), ('oncrack-cached', 'c'), ('oncrack-cached', 'fsharp'), ('c', 'rust')]:
        rs = [med[num, r] / med[den, r] for r in routes]
        print('| %s / %s | %s | **%.2fx** |' % (num, den, ' | '.join('%.2fx' % x for x in rs), statistics.geometric_mean(rs)))
    print()
    return med


def main():
    nd, md = sessions('normal'), sessions('mixed')
    table('Normal profile', nd, NORMAL, False)
    table('Mixed profile (16 readers plus a writer at 10 posts/s)', md, MIXED, True)
    path = os.path.join(HERE, 'review.jsonl')
    if not os.path.exists(path):
        return
    rows = [json.loads(l) for l in open(path) if '"window"' in l]
    key = lambda d: 'oncrack-cached' if d['app'] == 'oncrack' and 'cached' in d['tag'] else d['app']
    print('### Hand re-runs (review.py: 15 s warm-up, 10 s window, 16 clients, server CPU from the cgroup)\n')
    print('| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |')
    print('|---|---|---|---|---:|---:|')
    cpu, rps = {}, {}
    for a in ['oncrack', 'oncrack-cached', 'rust', 'c']:
        for ph in ['room_show', 'mixed', 'post_message']:
            ds = [d for d in rows if key(d) == a and d['phase'] == ph]
            if not ds:
                continue
            cpu[a, ph] = statistics.median(d['server_cpu_us_per_req'] for d in ds)
            rps[a, ph] = statistics.median(d['rps'] for d in ds)
            print('| %s | %s | %s | %s | %s | %.1f |' % (NAMES[a], ph, ', '.join(format(round(d['rps']), ',') for d in ds),
                                                         ', '.join('%.1f' % d['server_cpu_us_per_req'] for d in ds), format(round(rps[a, ph]), ','), cpu[a, ph]))
    print('\n| CPU per request, median over runs | room page | mixed reads | post |')
    print('|---|---:|---:|---:|')
    for a, b in [('rust', 'oncrack'), ('c', 'oncrack'), ('rust', 'oncrack-cached'), ('c', 'oncrack-cached'), ('oncrack', 'oncrack-cached')]:
        cells = []
        for ph in ['room_show', 'mixed', 'post_message']:
            cells.append('%.2fx' % (cpu[a, ph] / cpu[b, ph]) if (a, ph) in cpu and (b, ph) in cpu else '-')
        print('| %s / %s | %s |' % (a, b, ' | '.join(cells)))


if __name__ == '__main__':
    main()
