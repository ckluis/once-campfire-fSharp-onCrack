#!/usr/bin/env python3
"""R4 final run: the targeted pixel gate (bin/pixel-parity --fast: Chromium, light, desktop and phone) on the states round 4 touched (realtime, messages, search; the 'a/default' slice was run with --only 'realtime/**,messages/**', the 'b' slices are search and posting),
as data: pixels-fast.json beside this script, from the gitignored reports under parity/out/pixel-parity-r4-final-fast/."""
import glob, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
base = os.path.join(ROOT, 'parity/out/pixel-parity-r4-final-fast')
out = {'_about': "bin/pixel-parity --fast (Chromium, light, desktop and phone) on campfire-oncrack:app, built from ea1f85b (src/ at HEAD is identical: git diff ea1f85b HEAD -- src is empty), against the Rails reference with the dbc7620 search order; screenshot layer only. States: realtime and messages (default seed, 86), search (default 14, custom_styles 2). Corrected 2026-10-10: the first text said 'built from 191c468', copied from round 3's script.",
       'runs': {}}
tot = {'equal': 0, 'screenshots': 0, 'different': 0, 'not_captured': 0}
for rep in sorted(glob.glob(os.path.join(base, '*', '*', 'report.json'))):
    parts = rep.split(os.sep); name = parts[-3] + '/' + parts[-2]
    cells = []
    eq = diff = err = 0
    for r in json.load(open(rep))['results']:
        px = next((l for l in r['layers'] if l['layer'] == 'pixels'), None)
        if r['status'] == 'error': err += 1; cells.append({'state': r['state'], 'cell': r['cell'], 'result': 'not captured'}); continue
        if px is None: continue
        if px['equal']: eq += 1
        else: diff += 1
        cells.append({'state': r['state'], 'cell': r['cell'], 'result': 'equal' if px['equal'] else 'different'})
    out['runs'][name] = {'equal': eq, 'screenshots': eq + diff, 'different': diff, 'not_captured': err,
                         'states': sorted({c['state'] for c in cells}), 'cells': cells}
    for k, v in (('equal', eq), ('screenshots', eq + diff), ('different', diff), ('not_captured', err)): tot[k] += v
out['total'] = tot
json.dump(out, open(os.path.join(HERE, 'pixels-fast.json'), 'w'), indent=1)
print(json.dumps(tot), {k: (v['equal'], v['screenshots']) for k, v in out['runs'].items()})
