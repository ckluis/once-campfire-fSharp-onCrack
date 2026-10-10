#!/usr/bin/env python3
"""What the R3 final run validated, session by session, and each session's own geometric-mean ratios (the spread behind the pooled headline).

    python3 totals.py        # run in this directory; prints markdown

Reads bin/benchmark's own output (APP-N.json, raw/) in normal-N/ and mixed-N/, and review.jsonl for the hand re-runs.
"""
import glob
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
NORMAL = ['room_show', 'messages_page', 'sidebar', 'search', 'post_message']
MIXED = ['room_show', 'messages_page', 'sidebar', 'search']
APPS = ['oncrack', 'oncrack-cached', 'rust', 'c', 'fsharp', 'rails']


def session(d):
    mixed = d.startswith('mixed')
    key = 'mixed_http' if mixed else 'http'
    ok = audited = 0
    med = {}
    for a in APPS:
        for f in sorted(glob.glob(os.path.join(HERE, d, '%s-[0-9].json' % a))):
            j = json.load(open(f))
            ok += sum(x['ok'] for x in j[key])
            assert j['post_write_audit']['verified']
            audited += j['post_write_audit']['acknowledged']
    raw = [json.load(open(f)) for f in glob.glob(os.path.join(HERE, d, 'raw', 'http-*.json'))]
    bad = sum(s['errors'] + s['invalid_responses'] for s in raw)
    routes = MIXED if mixed else NORMAL
    for a in APPS:
        for r in routes:
            v = []
            for f in sorted(glob.glob(os.path.join(HERE, d, '%s-[0-9].json' % a))):
                v += [x['rps'] for x in json.load(open(f))[key] if x['route'] == r and x['conc'] == 16]
            med[a, r] = statistics.median(v)
    geo = lambda n, b: statistics.geometric_mean(med[n, r] / med[b, r] for r in routes)
    return ok, audited, bad, len(raw), max(s['generator_cpu_percent'] for s in raw), {
        'fresh/rust': geo('oncrack', 'rust'), 'fresh/c': geo('oncrack', 'c'), 'fresh/port': geo('oncrack', 'fsharp'),
        'cached/rust': geo('oncrack-cached', 'rust'), 'cached/c': geo('oncrack-cached', 'c'), 'fresh/cached': geo('oncrack', 'oncrack-cached')}


print('| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |')
print('|---|---:|---:|---:|---:|---:|')
tot = [0, 0, 0, 0]
ratios = {}
for d in ['normal-1', 'normal-2', 'mixed-1', 'mixed-2']:
    ok, au, bad, n, peak, r = session(d)
    ratios[d] = r
    tot = [tot[0] + ok, tot[1] + au, tot[2] + bad, tot[3] + n]
    print('| %s | %s | %s | %d | %d | %.1f |' % (d, format(ok, ','), format(au, ','), bad, n, peak))
print('| **all four** | **%s** | **%s** | **%d** | **%d** | |' % (format(tot[0], ','), format(tot[1], ','), tot[2], tot[3]))
print('\n| Geometric mean of the medians | ' + ' | '.join(ratios['normal-1']) + ' |')
print('|---|' + '---:|' * len(ratios['normal-1']))
for d, r in ratios.items():
    print('| %s | %s |' % (d, ' | '.join('%.2fx' % x for x in r.values())))

rows = [json.loads(l) for l in open(os.path.join(HERE, 'review.jsonl'))]
win = [r for r in rows if r.get('kind') == 'window']
aud = [r for r in rows if r.get('phase') == 'audit']
print('\nHand re-runs (review.jsonl): %d timed windows (every one valid: %s), %d warm-ups, %d database audits (every one ok: %s, rich-text rows equal acknowledged: %s, search-index rows missing: %d), %s acknowledged posts audited.' % (
    len(win), all(r['valid'] for r in win), sum(r.get('kind') == 'warmup' for r in rows), len(aud), all(r['ok'] for r in aud),
    all(r['richtext_rows'] == r['acknowledged'] == r['hq_new_rows'] for r in aud), sum(r['fts_missing'] for r in aud), format(sum(r['acknowledged'] for r in aud), ',')))
