#!/usr/bin/env python3
"""Round 1's pixel gate as data: pixel-parity.json beside this script, from the parity reports bin/pixel-parity wrote.

The reports (report.json per seed and slice, with every screenshot) are in parity/out/pixel-parity-round1-final/, which is
gitignored; this keeps what they say. The default seed ran in ten --only slices (A-J), the other four seeds in one run (small/),
and bin/pixel-parity's own retries of cells it could not capture (I/default-retry1, -retry2) plus one hand retry (I-retry/).
A cell counts by the last report that captured it, as bin/pixel-parity-report counts it; fragment states (responses, no
screenshot) are not counted. It also records the room page's two captures (Rails and onCrack), which the project page shows.

    python3 bench/results/oncrack-round1-final/review/pixel_parity.py [--reports DIR]
"""
import argparse
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
ROOM = ('rooms/show/busy/last_page', 'chromium-desktop-light')


def attempts(base):
    """Every report.json under base, grouped by seed, in order of attempt (a slice's first run, then its retries)."""
    out = {}
    for slice_dir in sorted(os.listdir(base)):
        d = os.path.join(base, slice_dir)
        if not os.path.isdir(d):
            continue
        for rep in sorted(glob.glob(os.path.join(d, '*', 'report.json')), key=lambda p: (p.split(os.sep)[-2].split('-retry')[0], p)):
            run = rep.split(os.sep)[-2]
            out.setdefault(run.split('-retry')[0], []).append(rep)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reports', default=os.path.join(ROOT, 'parity/out/pixel-parity-round1-final'))
    a = ap.parse_args()
    seeds, room = {}, None
    for seed, reps in sorted(attempts(a.reports).items()):
        cells = {}
        for path in reps:
            for r in json.load(open(path))['results']:
                key = (r['state'], r['cell'])
                if key in cells and cells[key]['status'] != 'error' and r['status'] == 'error':
                    continue
                cells[key] = dict(r, report=os.path.relpath(path, ROOT))
        equal = flaky = 0
        different, errors, by = [], [], {}
        for (state, cell), r in sorted(cells.items()):
            px = next((l for l in r['layers'] if l['layer'] == 'pixels'), None)
            if r['status'] == 'error':
                errors.append('%s @ %s' % (state, cell))
                continue
            if px is None:
                continue
            engine = cell.split('-')[0]
            b = by.setdefault(engine, [0, 0])
            b[1] += 1
            if px['equal']:
                equal += 1
                b[0] += 1
                flaky += bool(r.get('flaky'))
            else:
                different.append('%s @ %s' % (state, cell))
            if (state, cell) == ROOM:
                shots = {}
                for side in ('reference', 'candidate'):
                    png = os.path.join(os.path.dirname(os.path.join(ROOT, r['report'])), side, state, cell + '.png')
                    shots[side] = hashlib.sha256(open(png, 'rb').read()).hexdigest() if os.path.exists(png) else None
                room = {'seed': seed, 'state': state, 'cell': cell, 'status': r['status'], 'report': r['report'],
                        'layers_equal': [l['layer'] for l in r['layers'] if l.get('equal')], 'png_sha256': shots}
        retried = [os.path.relpath(p, ROOT) for p in reps if '-retry' in p or 'I-retry' in p]
        seeds[seed] = {'equal': equal, 'screenshots': equal + len(different), 'different': different, 'not_captured': errors,
                       'flaky': flaky, 'by_engine': {k: {'equal': v[0], 'screenshots': v[1]} for k, v in sorted(by.items())},
                       'reports': [os.path.relpath(p, ROOT) for p in reps], 'retries': retried}
    total = {k: sum(s[k] for s in seeds.values()) for k in ('equal', 'screenshots', 'flaky')}
    out = {
        '_about': 'bin/pixel-parity (lean matrix: every state on Chromium desktop and phone, light and dark, the smoke states on Firefox and WebKit, '
                  'the breakpoint sweep) against the Rails reference, on campfire-candidate-oncrack built from da1e92f, 2026-10-07/08. Made by '
                  'review/pixel_parity.py from the gitignored reports under parity/out/pixel-parity-round1-final/.',
        'total': dict(total, different=sum(len(s['different']) for s in seeds.values()), not_captured=sum(len(s['not_captured']) for s in seeds.values())),
        'seeds': seeds,
        'room_capture': room,
    }
    dst = os.path.join(HERE, 'pixel-parity.json')
    with open(dst, 'w') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    for s, v in seeds.items():
        print('%-14s %d/%d equal, %d different, %d not captured, %d flaky' % (s, v['equal'], v['screenshots'], len(v['different']), len(v['not_captured']), v['flaky']))
    print('total', out['total'], '->', os.path.relpath(dst, ROOT))


if __name__ == '__main__':
    main()
