#!/usr/bin/env python3
"""Render index.html (at the repository root): onCrack's page.

Python 3 standard library only. The page is short: the climb chart, the same room page served by four engines, the honest read/write
mix, what onCrack does differently, the Cable fan-out, and a row of proofs. Everything else sits in a side panel a link
opens. Panels are CSS :target drawers, so they work with JavaScript off; with it on they also close on Esc or a click outside, keep
focus inside while open, and give it back on close.

    python3 site/build.py            # write index.html, or fail

**Every number on the page is computed here from a file in the repository, never typed.** A number is a value V (the value, what it
is, the files it came from, how it was worked out); the Ledger prints it as a link to its row in the "Every number" panel, and that row
links the files. After rendering, check() reads the page back and fails the build if any digit a reader can see is not inside an
element the ledger issued (data-src), outside code and the ledger itself, or if any source file is missing. Identifiers that contain
digits (unit names like C2, commit hashes) are marked data-lit and must match a short list of shapes. Headline numbers come from the one
session that measured all four apps (bench/results/oncrack-round1-final); anything divided by the stored references of
bench/results/phase7-final (the climb chart) is labelled so.

bench/progress/build.py runs this after every logged run (bench/quick log), so the chart stays current. The chart is
bench/progress/climb.py. Copy and links are in site/data.json ("oncrack"); the "same pixels" images and facts come from
site/same_pixels.py. The rest of site/data.json and site/collect_tokens.py are the port's story; this page doesn't draw them.
"""
import glob
import html
import json
import math
import os
import re
import statistics
import sys
from datetime import timedelta, timezone
from html.parser import HTMLParser

SITE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SITE)
sys.path.insert(0, os.path.join(REPO, 'bench', 'progress'))
import climb as climb_chart  # noqa: E402  (bench/progress/climb.py)

EDT = timezone(timedelta(hours=-4))
DATA = json.load(open(os.path.join(SITE, 'data.json'), encoding='utf-8'))
OC = DATA['oncrack']
META = OC['meta']


def e(s):
    return html.escape(str(s), quote=True)


def src_url(path):
    """A repository file as a link: relative to index.html, or GitHub's view of it once meta.repo_url is set."""
    base = META.get('repo_url')
    if not base:
        return path
    kind = 'tree' if os.path.isdir(os.path.join(REPO, path)) else 'blob'
    return '%s/%s/%s/%s' % (base.rstrip('/'), kind, META.get('branch', 'main'), path.rstrip('/'))


def code(s):
    return '<code>%s</code>' % e(s)


def lit(s, why='name'):
    """An identifier with digits in it (a unit, a test, a commit): not a measurement, so not in the ledger. check() limits the shapes."""
    return '<span data-lit="%s">%s</span>' % (e(why), e(s))


def lits(s):
    """Escape prose from a results file and mark the unit and test names in it (C2, A1b) as names."""
    return re.sub(r'\b(C[0-4](?:-C[0-4])?|A\d[a-c]?|R[1-5]\.[0-5])\b', lambda m: lit(m.group(1)), e(s))


def flink(path, label=None):
    return '<a href="%s"><code>%s</code></a>' % (e(src_url(path)), e(label or path))


# ================================================================ sources

class V:
    """A number and where it came from."""
    __slots__ = ('v', 'label', 'files', 'how')

    def __init__(self, v, label, files, how=''):
        self.v, self.label, self.files, self.how = v, label, list(files), how

    def over(self, o, label=None):
        return V(self.v / o.v, label or '%s, over %s' % (self.label, o.label), self.files + [f for f in o.files if f not in self.files],
                 '%s ÷ %s' % (g(self.v), g(o.v)))

    def times(self, k, label):
        return V(self.v * k, label, self.files, '%s × %s' % (g(self.v), g(k)))

    def minus(self, o, label):
        return V(self.v - o.v, label, self.files + [f for f in o.files if f not in self.files], '%s − %s' % (g(self.v), g(o.v)))


def g(x):
    return ('%.4g' % x) if isinstance(x, float) and abs(x) < 100 else format(round(x, 1), ',')


def geo(vs, label):
    files = []
    for v in vs:
        files += [f for f in v.files if f not in files]
    return V(math.exp(sum(math.log(v.v) for v in vs) / len(vs)), label, files, 'geometric mean of ' + ', '.join('%.3f' % v.v for v in vs))


class Ledger:
    """Every number the page shows, once per (what, source, derivation, shown text). Row ids are s-1, s-2, ... in order of first use."""

    def __init__(self):
        self.rows, self.by = [], {}

    def row(self, label, files, how, shown, value=None, block=False):
        for f in files:
            if not os.path.exists(os.path.join(REPO, f.split('#')[0])):
                raise SystemExit('build: source file missing: %s (for %s)' % (f, label))
        key = (label, tuple(files), how, shown)
        if key not in self.by:
            rid = 's-%d' % (len(self.rows) + 1)
            self.by[key] = rid
            self.rows.append({'id': rid, 'label': label, 'files': files, 'how': how, 'shown': shown, 'value': value, 'block': block})
        return self.by[key]

    def n(self, v, fmt='{:,.0f}', link=True):
        shown = fmt.format(v.v)
        rid = self.row(v.label, v.files, v.how, shown, v.v)
        if link:
            return '<a class="sn" href="#%s" data-src="%s">%s</a>' % (rid, rid, e(shown))
        return '<span class="sn" data-src="%s">%s</span>' % (rid, e(shown))

    def x(self, v, link=True):
        return self.n(v, '{:.2f}×', link)

    def block(self, label, files, how):
        """For a generated visual whose every number comes from the same files (the climb chart): an attribute for its container."""
        rid = self.row(label, files, how, '(all numbers in the block)', block=True)
        return 'data-src="%s"' % rid

    def link(self, rid, text):
        return '<a class="sn" href="#%s" data-src="%s">%s</a>' % (rid, rid, e(text))


L = Ledger()
_J = {}


def jload(rel):
    if rel not in _J:
        _J[rel] = json.load(open(os.path.join(REPO, rel), encoding='utf-8'))
    return _J[rel]


def jlines(rel):
    return [json.loads(x) for x in open(os.path.join(REPO, rel), encoding='utf-8') if x.strip()]


def text(rel):
    return open(os.path.join(REPO, rel), encoding='utf-8').read()


def md(rel, pattern, label, group=1):
    """A number written in a results file: the pattern must match exactly once."""
    ms = list(re.finditer(pattern, text(rel)))
    if len(ms) != 1:
        raise SystemExit('build: %r matches %d times in %s (want 1)' % (pattern, len(ms), rel))
    return V(float(ms[0].group(group).replace(',', '')), label, [rel], 'written in the results file: "%s"' % ms[0].group(0).strip())


def vnum(pattern, label, group=1):
    """A number in the verifier's verbatim report (verifier.json "report"), which must say it exactly once."""
    VF = 'bench/results/oncrack-verifier/verifier.json'
    rep = jload(VF)['report']
    t = '\n'.join([rep['pixel_parity']] + [f[k] for f in rep['findings'] for k in ('issue', 'evidence', 'fix') if f.get(k)])
    ms = list(re.finditer(pattern, t))
    if len(ms) != 1:
        raise SystemExit('build: %r matches %d times in the verifier report (want 1)' % (pattern, len(ms)))
    return V(float(ms[0].group(group).replace(',', '')), label, [VF], 'the verifier\'s report: "%s"' % ms[0].group(0).strip())


R1 = 'bench/results/oncrack-round1-final'
REVIEW = R1 + '/review'
# The final run (round five, bench/results/oncrack-r5-final.md): every figure on the page that is not history comes from this one directory, by a plan fixed before any
# session ran (PLAN.md there). Three sessions per profile, all pooled; the cable suite's headline is its one quiet session; reliability is three rounds for every app.
R5F = 'bench/results/oncrack-r5-final'
R5REPORT = 'bench/results/oncrack-r5-final.md'
# Cable fan-out: the raw epoll client and a window of 128; Rails was not run in it, and the round-1 Cable numbers (a different client, a different load shape) are not
# comparable, so the picture has three apps. Session 3 is the one quiet, uninterrupted session (cable/RESULTS.md); sessions 1 and 2 are kept beside it, not pooled.
R42 = R5F + '/cable/session-3/t3'
CABLE_SESSIONS = [R5F + '/cable/session-%s' % s for s in ('1-incomplete', '2', '3')]
CABLE_APPS = ['rust', 'fsharp', 'oncrack']
CABLE_COUNTS = (100, 500, 1000, 2000)
# Reliability under load: upstream's bin/reliability cable profiles (PR #6), 1,000 clients; Rails, Rust, C, onCrack, onCrack cached and onCrack before the shared log
# in one harness process (REL_SESSION), the port's cable profiles on their own (REL_PORT); each directory's summary.json is bench/reliability/summarize --write. Three rounds each.
REL_SESSION = R5F + '/reliability/main'
REL_PORT = R5F + '/reliability/fsharp'
REL_APPS = [('reference', 'rails', REL_SESSION), ('rust', 'rust', REL_SESSION), ('c', 'c', REL_SESSION), ('fsharp', 'fsharp', REL_PORT), ('oncrack-before', 'oncrack-prev', REL_SESSION),
            ('oncrack', 'oncrack', REL_SESSION), ('oncrack-cached', 'oncrack-cached', REL_SESSION)]
REL_NAME = {'reference': 'Rails', 'rust': 'Rust', 'c': 'C', 'fsharp': 'F# port', 'oncrack-before': 'onCrack before the shared log', 'oncrack': 'onCrack', 'oncrack-cached': 'onCrack, cached decision'}
R3PIX = R5F + '/pixels'   # the full pixel gate on the final code
NAME = {'reference': 'Rails', 'rust': 'Rust', 'fsharp': 'F# port', 'oncrack': 'onCrack'}
APPS = ['reference', 'rust', 'fsharp', 'oncrack']
ROUTES = [('room_show', 'room page'), ('messages_page', 'messages page'), ('sidebar', 'sidebar'), ('search', 'search'), ('post_message', 'post a message')]
RNAME = dict(ROUTES + [('static_css', 'CSS file'), ('avatar', 'avatar'), ('up', '/up')])
METRIC = {'rps': ('req/s', lambda r: r['rps']),
          'cpu': ('server CPU µs per request', lambda r: r['cost']['server_cpu_us_per_req']),
          'p50': ('p50 latency, ms', lambda r: r['latency']['p50_ms']),
          'p99': ('p99 latency, ms', lambda r: r['latency']['p99_ms']),
          'lg': ('load generator cores busy', lambda r: r['cost']['loadgen_cores_busy']),
          'srv': ('server cores busy', lambda r: r['cost']['server_cores_busy']),
          'lgcpu': ('load generator CPU µs per request', lambda r: r['cost']['loadgen_cpu_us_per_req'])}


def reps(d, app):
    fs = sorted(glob.glob(os.path.join(REPO, d, app + '-[0-9].json')))
    if not fs:
        raise SystemExit('build: no %s reps in %s' % (app, d))
    return [os.path.relpath(f, REPO) for f in fs]


def http(app, route, conc, metric='rps', d=R1):
    files = reps(d, app)
    name, get = METRIC[metric]
    vals = []
    for f in files:
        for r in jload(f)['http']:
            if r['route'] == route and r['conc'] == conc and r.get('gzip', True):
                vals.append(get(r))
    if not vals:
        raise SystemExit('build: no %s %s c=%d in %s' % (app, route, conc, d))
    how = ('median of %d reps: %s' % (len(vals), ', '.join(g(float(v)) for v in vals))) if len(vals) > 1 else 'one run'
    return V(statistics.median(vals), '%s, %s, c=%d, %s (%s)' % (NAME.get(app, app), RNAME[route], conc, name, d.split('/')[-1] if d == R1 else d.replace('bench/results/', '')),
             files, how + ' (http[route=%s, conc=%d].%s)' % (route, conc, metric))


def per_rep(app, label, get, unit_how, d=R1):
    files = reps(d, app)
    vals = [get(jload(f)) for f in files]
    return V(statistics.median(vals), '%s, %s' % (NAME[app], label), files, 'median of %d reps: %s (%s)' % (len(vals), ', '.join(g(float(v)) for v in vals), unit_how))


def cable(app, clients, what):
    def get(d):
        c = next(x for x in d['cable'] if x['clients'] == clients)
        return {'msgs': c['throughput']['delivered_msgs_per_sec'], 'frames': c['throughput']['frames_per_sec'],
                'p50': c['latency']['all_clients']['p50_ms'], 'pss': c['process_memory']['saturated']['peak_total_pss_mb']}[what]
    label = {'msgs': 'Cable, %s clients, messages a second delivered to every client',
             'frames': 'Cable, %s clients, deliveries a second (frames)',
             'p50': 'Cable, %s clients, paced latency to the last client, p50 ms',
             'pss': 'Cable, %s clients saturated, app Pss MB'}[what] % format(clients, ',')
    if app == 'rust':
        label += ' (upstream f9dca47)'
    field = {'msgs': 'throughput.delivered_msgs_per_sec', 'frames': 'throughput.frames_per_sec', 'p50': 'latency.all_clients.p50_ms',
             'pss': 'process_memory.saturated.peak_total_pss_mb'}[what]
    return per_rep(app, label, get, 'cable[clients=%d].%s' % (clients, field), d=R42)


def relnum(key, directory, app, profile, field):
    """A reliability number: the median over the session's rounds (bench/reliability/summarize), with the rounds' own values in the derivation."""
    d = jload(directory + '/summary.json')[app][profile]
    vals = d['rounds'][field]
    what = {'ready': 'clients subscribed', 'disconnected': 'clients the server closed mid-run', 'posted': 'messages posted', 'complete': 'messages delivered to every client',
            'msgs': 'messages a second delivered to every client', 'p99': 'p99 ms from a post to the last client', 'pss': 'peak app Pss MB',
            'drain': 'seconds from the last post to the last delivery'}[field]
    files = [directory + '/summary.json', directory + '/harness-output/%s-1.json' % app, directory + '/run.log']
    if field == 'pss':
        files.append(directory + '/memory.jsonl')
    shown = [v for v in vals if v is not None]
    if not shown:
        return None
    return V(statistics.median(shown), '%s, %s, %s (%s)' % (REL_NAME[key], 'Cable with %d closed-loop posters' % d['posters'] if profile == 'cable_heavy' else 'Cable with %d posters' % d['posters'], what,
                                                              directory.replace('bench/results/', '')),
             files, 'median of %d rounds: %s (summary.json %s.%s.rounds.%s)' % (len(shown), ', '.join(g(float(v)) for v in shown), app, profile, field))


def env_field(pattern, label, rel=R1 + '/env.txt'):
    m = re.search(pattern, text(rel), re.M)
    if not m:
        raise SystemExit('build: %r not in %s' % (pattern, rel))
    return m.group(1), V(0, label, [rel], 'env.txt: "%s"' % m.group(0).strip())


def mixed(app, field, label):
    rows = [r for r in jlines(REVIEW + '/mixed.jsonl') if r['app'] == app]
    vals = [r[field] for r in rows]
    return V(statistics.mean(vals), '%s, reads while writing: %s' % (NAME[app], label), [REVIEW + '/mixed.jsonl', REVIEW + '/mixed.sh'],
             'mean of %d runs: %s (%s)' % (len(vals), ', '.join(g(float(v)) for v in vals), field))


def mixed_first(app, field, label):
    r = next(r for r in jlines(REVIEW + '/mixed.jsonl') if r['app'] == app)
    return V(r[field], '%s, reads while writing (first run): %s' % (NAME[app], label), [REVIEW + '/mixed.jsonl'], 'first run\'s %s' % field)


def param(v, label, rel, how):
    return V(v, label, [rel], how)


# ---- round 2's final review: once-campfire-verification's own harness, current upstream Rust and C (bench/results/oncrack-r2-final)
R2 = 'bench/results/oncrack-r2-final'
UPN, UPM = R2 + '/upstream-normal', R2 + '/upstream-mixed'
UPAPPS = ['rails', 'rust', 'c', 'fsharp', 'oncrack']
UPREV = {'rails': '0aa339d', 'rust': 'f9dca47', 'c': 'cd0cbe4'}
UPBASE = {'rails': 'Rails', 'rust': 'Rust', 'c': 'C', 'fsharp': 'F# port', 'oncrack': 'onCrack'}
UPREADS = ['room_show', 'messages_page', 'sidebar', 'search']


# ---- round 3's final run: fresh authorization on every hit (the default since R3.2), the same harness, current Rust and C, on the final code (bench/results/oncrack-r3-final).
# The final run (round five): each profile is three sessions of three rounds per cell, every session pooled (PLAN.md rule 3, bench/results/oncrack-r5-final/pooled.md); none is dropped.
R3_OLD = 'bench/results/oncrack-r3-final'   # round three's final run: two sessions per profile (history: the hero's older figures)
R4_OLD = 'bench/results/oncrack-r4-final'   # round four's final run: one session per profile (history)
R3 = R5F                                   # the names below point at the final run: three sessions per profile
R3N = [R3 + '/normal-%d' % i for i in (1, 2, 3)]
R3M = [R3 + '/mixed-%d' % i for i in (1, 2, 3)]
R3APPS = ['oncrack', 'oncrack-cached', 'rust', 'c', 'fsharp']
UPBASE['oncrack-cached'] = 'onCrack, cached decision'


def up3(app, route, mixed=False, stat='median'):
    """bin/benchmark's requests/sec at c=16 for one app and route in the final run: the median of every round of every session of the profile (three sessions, nine rounds)."""
    dirs = R3M if mixed else R3N
    files = sorted(os.path.relpath(f, REPO) for d in dirs for f in glob.glob(os.path.join(REPO, d, app + '-[0-9].json')))
    key = 'mixed_http' if mixed else 'http'
    vals = [x['rps'] for f in files for x in jload(f)[key] if x['route'] == route and x['conc'] == 16]
    if len(vals) != 3 * len(dirs) or len(vals) != len(files):
        raise SystemExit('build: %s %s: %d samples in %d rounds' % (app, route, len(vals), len(files)))
    v = {'median': statistics.median, 'min': min, 'max': max}[stat](vals)
    what = 'mixed profile, 10 posts/s writer, three sessions pooled' if mixed else 'normal profile, three sessions pooled'
    return V(v, '%s, %s, c=16, req/s, %s of %d rounds (verification harness, %s)' % (UPBASE[app] + (' ' + UPREV[app] if app in UPREV else ''), RNAME[route], stat, len(vals), what),
             files, '%s of %s (%s[route=%s, conc=16].rps)' % (stat, ', '.join(g(float(x)) for x in vals), key, route))


def upname(a, link=True):
    """An app's name with its measured upstream revision marked as a commit (not a number)."""
    return UPBASE[a] + ((' ' + lit(UPREV[a], 'commit')) if a in UPREV and link else '')


def up(app, route, d=UPN, stat='median'):
    """bin/benchmark's requests/sec for one app and route at c=16: the median (or min, max) of its rounds."""
    files = sorted(os.path.relpath(f, REPO) for f in glob.glob(os.path.join(REPO, d, app + '-[0-9].json')))
    if not files:
        raise SystemExit('build: no %s rounds in %s' % (app, d))
    key = 'mixed_http' if d == UPM else 'http'
    vals = [x['rps'] for f in files for x in jload(f)[key] if x['route'] == route and x['conc'] == 16]
    if len(vals) != len(files):
        raise SystemExit('build: %s %s: %d samples in %d rounds' % (app, route, len(vals), len(files)))
    v = {'median': statistics.median, 'min': min, 'max': max}[stat](vals)
    prof = 'mixed profile, 10 posts/s writer' if d == UPM else 'normal profile'
    return V(v, '%s, %s, c=16, req/s, %s of %d rounds (verification harness, %s)' % (UPBASE[app] + (' ' + UPREV[app] if app in UPREV else ''), RNAME[route], stat, len(vals), prof),
             files, '%s of %s (%s[route=%s, conc=16].rps)' % (stat, ', '.join(g(float(x)) for x in vals), key, route))


# ================================================================ the facts

def facts():
    F = {}
    # the five workloads, all four apps, one session
    F['w'] = {(a, r, c, m): http(a, r, c, m) for a in APPS for r, _ in ROUTES for c in (1, 16, 64) for m in ('rps', 'cpu')}
    for c in (1, 16, 64):
        F['geo_rust', c] = geo([F['w']['oncrack', r, c, 'rps'].over(F['w']['rust', r, c, 'rps']) for r, _ in ROUTES],
                               'onCrack over Rust, geometric mean of the five workloads, c=%d, same session' % c)
        F['geo_port', c] = geo([F['w']['oncrack', r, c, 'rps'].over(F['w']['fsharp', r, c, 'rps']) for r, _ in ROUTES],
                               'onCrack over the F# port, geometric mean of the five workloads, c=%d, same session' % c)
        F['geo_port_rust', c] = geo([F['w']['fsharp', r, c, 'rps'].over(F['w']['rust', r, c, 'rps']) for r, _ in ROUTES],
                                    'the F# port over Rust, geometric mean of the five workloads, c=%d, same session' % c)
    F['conc'] = {c: param(c, 'connections (concurrency)', R1 + '/env.txt', 'bench/run schedule in env.txt: "concs 1 16 64"') for c in (1, 16, 64)}
    # current upstream, their harness (round 2's final review)
    F['up'] = {(a, r, st): up(a, r, UPN, st) for a in UPAPPS for r, _ in ROUTES for st in ('median', 'min', 'max')}
    F['upm'] = {(a, r, st): up(a, r, UPM, st) for a in UPAPPS for r in UPREADS for st in ('median', 'min', 'max')}
    for b in ('rust', 'c', 'fsharp', 'rails'):
        F['up_geo', b] = geo([F['up']['oncrack', r, 'median'].over(F['up'][b, r, 'median']) for r, _ in ROUTES],
                             'onCrack over %s, geometric mean of the five workloads, c=16, verification harness, same session' % UPBASE[b])
        F['upm_geo', b] = geo([F['upm']['oncrack', r, 'median'].over(F['upm'][b, r, 'median']) for r in UPREADS],
                              'onCrack over %s, geometric mean of the four mixed-profile reads, c=16, verification harness, same session' % UPBASE[b])
    F['up3'] = {(a, r, st): up3(a, r, False, st) for a in R3APPS for r, _ in ROUTES for st in ('median', 'min', 'max')}
    F['up3m'] = {(a, r, st): up3(a, r, True, st) for a in R3APPS for r in UPREADS for st in ('median', 'min', 'max')}
    for num in ('oncrack', 'oncrack-cached'):
        for b in ('rust', 'c', 'fsharp', 'oncrack-cached'):
            if b == num:
                continue
            F['up3_geo', num, b] = geo([F['up3'][num, r, 'median'].over(F['up3'][b, r, 'median']) for r, _ in ROUTES],
                                       '%s over %s, geometric mean of the five workloads, c=16, verification harness, three sessions pooled' % (UPBASE[num], UPBASE[b]))
            F['up3m_geo', num, b] = geo([F['up3m'][num, r, 'median'].over(F['up3m'][b, r, 'median']) for r in UPREADS],
                                        '%s over %s, geometric mean of the four mixed-profile reads, c=16, verification harness, three sessions pooled' % (UPBASE[num], UPBASE[b]))
    F['r3_val'] = {}
    sess = R3N + R3M
    vfiles = [os.path.relpath(f, REPO) for d in sess for f in sorted(glob.glob(os.path.join(REPO, d, '*-[0-9].json')))]
    vraw = [os.path.relpath(f, REPO) for d in sess for f in sorted(glob.glob(os.path.join(REPO, d, 'raw', 'http-*.json')))]
    def r3_timed(f):
        return sum(x['ok'] for x in jload(f)['mixed_http' if '/mixed-' in f else 'http'])
    F['r3_val']['timed'] = V(sum(r3_timed(f) for f in vfiles), 'timed responses validated, the six sessions of the final run', vfiles, 'sum of ok over every timed sample')
    F['r3_val']['writes'] = V(sum(jload(f)['post_write_audit']['acknowledged'] for f in vfiles), 'acknowledged writes audited against the database and FTS, warm-ups included, the six sessions of the final run',
                              vfiles, 'sum of post_write_audit.acknowledged (each verified)')
    F['r3_val']['bad'] = V(sum(jload(f)['errors'] + jload(f)['invalid_responses'] for f in vraw), 'errors and invalid responses, the six sessions of the final run', vraw, 'sum over every raw sample')
    F['r3_val']['gen'] = V(max(jload(f)['generator_cpu_percent'] for f in vraw), 'peak load generator CPU, % (400% available), the six sessions of the final run', vraw, 'max of generator_cpu_percent over every raw sample')
    F['r3_val']['samples'] = V(len(vraw), 'raw samples reconciled against the per-app rows, the six sessions of the final run', vraw, 'count of raw/http-*.json')
    F['up3_rounds'] = V(len(F['up3']['oncrack', 'room_show', 'median'].files), 'rounds per app and workload, three normal sessions pooled (verification harness)',
                        F['up3']['oncrack', 'room_show', 'median'].files, 'oncrack-N.json files of the session')
    F['up_c_rust'] = geo([F['up']['c', r, 'median'].over(F['up']['rust', r, 'median']) for r, _ in ROUTES], 'C over Rust, geometric mean of the five workloads, c=16, verification harness')
    sm = jload(R3N[0] + '/summary.json')['metadata']
    F['up_conc'] = param(16, 'concurrent clients (verification harness)', R3N[0] + '/summary.json', 'metadata.concurrencies "%s"' % sm['concurrencies'])
    F['up_rounds'] = param(sm['rounds'], 'rounds per app and session (verification harness)', R3N[0] + '/summary.json', 'metadata.rounds')
    F['up_rate'] = param(jload(R3M[0] + '/mixed-summary.json')['metadata']['mixed_writer']['maximum_writes_per_second'], 'mixed profile writer cap, posts/s', R3M[0] + '/mixed-summary.json', 'metadata.mixed_writer.maximum_writes_per_second')
    F['up_secs'] = param(sm['duration'], 'seconds per timed sample (verification harness)', R3N[0] + '/summary.json', 'metadata.duration')
    F['up_val'] = {}
    for d, key in ((UPN, 'http'), (UPM, 'mixed_http')):
        files = [os.path.relpath(f, REPO) for f in sorted(glob.glob(os.path.join(REPO, d, '*-[0-9].json')))]
        F['up_val'][d, 'timed'] = V(sum(x['ok'] for f in files for x in jload(f)[key]), 'timed responses validated (%s)' % d.split('/')[-1], files, 'sum of ok over every timed sample')
        F['up_val'][d, 'writes'] = V(sum(jload(f)['post_write_audit']['acknowledged'] for f in files), 'acknowledged writes audited against the database and FTS, warm-ups included (%s)' % d.split('/')[-1],
                                     files, 'sum of post_write_audit.acknowledged (each verified)')
        raws = [os.path.relpath(f, REPO) for f in glob.glob(os.path.join(REPO, d, 'raw', 'http-*.json'))]
        F['up_val'][d, 'gen'] = V(max(jload(f)['generator_cpu_percent'] for f in raws), 'peak load generator CPU, %% (400%% available; %s)' % d.split('/')[-1], sorted(raws), 'max of generator_cpu_percent over every raw sample')
        F['up_val'][d, 'bad'] = V(sum(jload(f)['errors'] + jload(f)['invalid_responses'] for f in raws), 'errors and invalid responses (%s)' % d.split('/')[-1], sorted(raws), 'sum over every raw sample')
    KJ = R5F + '/kloc/kloc.json'
    K = jload(KJ)['counts']
    KN = {'rails': 'Rails', 'rust': 'Rust', 'c': 'C', 'fsharp': 'F# port', 'oncrack': 'onCrack'}
    for a in KN:
        F['kloc', a] = V(K[KN[a]]['total'] / 1000, '%s application KLOC (cloc 2.10, upstream rules: backend code and executable template code, static data left out)' % UPBASE[a], [KJ],
                         '%s lines (backend %s + template %s) / 1000 (counts.%s.total)' % (format(K[KN[a]]['total'], ','), format(K[KN[a]]['backend_code'], ','), format(K[KN[a]]['template_code'], ','), KN[a]))
    F['nreps'] = param(3, 'reps per app', R1 + '/env.txt', 'bench/run schedule in env.txt: "reps 3"')
    # reads while writing
    for a in ('rust', 'fsharp', 'oncrack'):
        F['mix', a, 'read'] = mixed(a, 'read_rps', 'room page reads/s at c=16')
        F['mix', a, 'post'] = mixed(a, 'post_rps', 'posts/s into that room at c=1')
        F['mix', a, 'cpu'] = mixed(a, 'cpu_us_per_req_all', 'CPU µs per request (reads and posts)')
        F['mix', a, 'p50'] = mixed_first(a, 'read_p50', 'read p50 ms')
        F['mix', a, 'p99'] = mixed_first(a, 'read_p99', 'read p99 ms')
        rows = [r for r in jlines(REVIEW + '/mixed.jsonl') if r['app'] == a]
        F['mix', a, 'ok'] = all(r['read_errors'] == 0 and r['post_errors'] == 0 and r['rows_written'] == r['posts_ok'] and
                                set(r['read_statuses']) == {'200'} and set(r['post_statuses']) == {'200'} for r in rows)
    F['mix_runs'] = V(len(jlines(REVIEW + '/mixed.jsonl')), 'reads-while-writing runs', [REVIEW + '/mixed.jsonl'], 'lines in the file')
    F['mix_reads_per_change'] = F['mix', 'oncrack', 'read'].over(F['mix', 'oncrack', 'post'], 'onCrack, reads while writing: reads per change of the room')
    # other suites
    for a in APPS:
        F['cold', a] = per_rep(a, 'cold start, docker run to /up, ms', lambda d: d['cold_start_ms'], 'cold_start_ms')
        F['idle', a] = per_rep(a, 'idle memory.current, MB', lambda d: d['memory']['idle_current_mb'], 'memory.idle_current_mb')
        F['peak', a] = per_rep(a, 'peak memory.current over the whole run, MB', lambda d: d['memory']['peak_current_mb'], 'memory.peak_current_mb')
        F['anon', a] = per_rep(a, 'peak anon memory over the whole run, MB', lambda d: d['memory']['peak_anon_mb'], 'memory.peak_anon_mb')
        F['upload', a] = per_rep(a, 'upload + thumbnail, POST to thumbnail served, ms', lambda d: d['upload']['median_total_ms'], 'upload.median_total_ms')
        if a in CABLE_APPS:
            for n in CABLE_COUNTS:
                for w in ('msgs', 'frames', 'p50'):
                    F['cable', a, n, w] = cable(a, n, w)
            for n in CABLE_COUNTS:
                F['cable', a, n, 'pss'] = cable(a, n, 'pss')
        for r in ('static_css', 'avatar', 'up'):
            for m in ('rps', 'cpu'):
                F['w'][a, r, 16, m] = http(a, r, 16, m)
    for key, app, directory in REL_APPS:
        for profile in ('cable', 'cable_heavy'):
            for field in ('ready', 'disconnected', 'posted', 'complete', 'msgs', 'p99', 'pss'):
                F["rel", key, profile, field] = relnum(key, directory, app, profile, field)
    F['rel_rounds'] = V(len(jload(REL_SESSION + '/summary.json')['oncrack']['cable_heavy']['rounds']['round']), 'rounds of PR #6\'s reliability profiles for every app', [REL_SESSION + '/summary.json'], 'len(oncrack.cable_heavy.rounds.round)')
    F['rel_runs'] = V(4 * F['rel_rounds'].v, 'cable and cable_heavy runs of onCrack, fresh and cached, in the final run', [REL_SESSION + '/summary.json'], '2 profiles x 2 modes x %d rounds' % F['rel_rounds'].v)
    F['rel_clients'] = param(jload(REL_SESSION + '/summary.json')['oncrack']['cable_heavy']['clients'], 'Reliability profile: Cable clients', REL_SESSION + '/summary.json', 'oncrack.cable_heavy.clients')
    F['rel_posters'] = param(jload(REL_SESSION + '/summary.json')['oncrack']['cable_heavy']['posters'], 'Reliability profile: closed-loop posters of cable_heavy', REL_SESSION + '/summary.json', 'oncrack.cable_heavy.posters')
    F['rel_posters_light'] = param(jload(REL_SESSION + '/summary.json')['oncrack']['cable']['posters'], 'Reliability profile: posters of cable', REL_SESSION + '/summary.json', 'oncrack.cable.posters')
    F['window'] = param(jload(R42 + '/oncrack-1.json')['cable'][0]['throughput']['window'], 'Cable suite: messages posted and not yet delivered to every client, at most',
                        R42 + '/oncrack-1.json', 'cable[].throughput.window')
    F['clients'] = {n: param(n, 'Cable clients', R42 + '/oncrack-1.json', 'cable[].clients') for n in CABLE_COUNTS}
    # load generator headroom
    for a in APPS:
        for r, _ in ROUTES + [('static_css', ''), ('avatar', ''), ('up', '')]:
            for c in (1, 16, 64):
                for m in ('lg', 'srv', 'lgcpu', 'rps'):
                    F['w'].setdefault((a, r, c, m), None)
                    if F['w'][a, r, c, m] is None:
                        F['w'][a, r, c, m] = http(a, r, c, m)
    F['lg_cpus'], F['lg_cpus_v'] = env_field(r'loadgen cpus: ([0-9-]+)', 'load generator CPUs')
    F['srv_cpus'], F['srv_cpus_v'] = env_field(r'server cpus: ([0-9-]+)', 'server CPUs')
    F['ncores'] = param(4, 'cores for each side (CPUs %s for the server, %s for the load generator)' % (F['srv_cpus'], F['lg_cpus']), R1 + '/env.txt',
                        'env.txt: "server cpus: 0-3 (nproc 4); loadgen cpus: 4-7"')
    allrps = [(F['w'][a, r, c, 'rps'].v, a, r, c) for (a, r, c, m) in list(F['w']) if m == 'rps' and F['w'][a, r, c, m] is not None]
    F['top_any'] = max(allrps)
    F['top_five'] = max(x for x in allrps if x[1] == 'oncrack' and x[2] in dict(ROUTES))
    probes = []
    for a in APPS:
        for f in reps(R1, a):
            for r in jload(f)['http']:
                probes.append(r['host_probe_after']['ratio'])
    F['probe_max'] = V(max(probes), 'host probe after every measured window, worst ratio to its baseline', reps(R1, 'oncrack')[:1] + [f for a in APPS[:-1] for f in reps(R1, a)],
                       'max over %d windows of http[].host_probe_after.ratio' % len(probes))
    statuses, errs = {}, 0
    for a in APPS:
        for f in reps(R1, a):
            for r in jload(f)['http']:
                errs += r.get('errors', 0)
                for k, n in r['statuses'].items():
                    statuses[k[0]] = statuses.get(k[0], 0) + n
    if set(statuses) != {'2'}:
        raise SystemExit('build: round 1 has non-2xx responses %r; the page says every response was 2xx' % statuses)
    allfiles = [f for a in APPS for f in reps(R1, a)]
    F['responses'] = V(sum(statuses.values()), 'HTTP responses counted in the round-one session, all apps and reps', allfiles, 'sum of http[].statuses (all 2xx, checked on every build)')
    F['conn_errors'] = V(errs, 'connection errors in the round-one session, all apps and reps', allfiles, 'sum of http[].errors')
    F['windows'] = V(len(probes), 'measured HTTP windows in the session', F['probe_max'].files, 'count of http[] entries over all apps and reps')
    # hand-run counts (manual.sh)
    F['manual'] = {}
    for a in ('rust', 'oncrack'):
        rel = REVIEW + '/manual-%s.jsonl' % a
        for r in (json.loads(x) for x in open(os.path.join(REPO, rel), encoding='utf-8') if x.strip().startswith('{')):   # line 1 is the image
            F['manual'][a, r['route'], r['c']] = {k: V(r[k], '%s, hand run, %s c=%d: %s' % (NAME[a], RNAME[r['route']], r['c'], k), [rel, REVIEW + '/manual.sh'], k)
                                                 for k in ('rps_loadgen', 'n_loadgen', 'server_log_lines', 'rows_written', 'cpu_us_per_req', 'cores_busy', 'errors')}
    # pixel parity
    PP = R3PIX + '/pixel-parity.json'
    pp = jload(PP)
    F['pp'] = {s: {k: V(v[k], 'pixel gate, seed %s: %s' % (s, k), [PP, R3PIX + '/pixel_parity.py'], 'seeds.%s.%s' % (s, k)) for k in ('equal', 'screenshots', 'flaky')} for s, v in pp['seeds'].items()}
    for s, v in pp['seeds'].items():
        F['pp'][s]['different'] = V(len(v['different']), 'pixel gate, seed %s: screenshots different' % s, [PP], 'len(seeds.%s.different)' % s)
        F['pp'][s]['not_captured'] = V(len(v['not_captured']), 'pixel gate, seed %s: cells not captured' % s, [PP], 'len(seeds.%s.not_captured)' % s)
        F['pp'][s]['engines'] = {k: V(x['screenshots'], 'pixel gate, seed %s: %s screenshots' % (s, k), [PP], 'seeds.%s.by_engine.%s' % (s, k)) for k, x in v['by_engine'].items()}
    F['pp_total'] = {k: V(pp['total'][k], 'pixel gate, all five seeds: %s' % k, [PP, R3PIX + '/pixel_parity.py'], 'total.%s' % k) for k in pp['total']}
    F['pp_seeds'] = V(len(pp['seeds']), 'seeds in the pixel gate', [PP], 'len(seeds)')
    P3 = 'bench/results/oncrack-r3-pixels/pixel-parity.json'
    F['pp3_total'] = V(jload(P3)['total']['screenshots'], 'round three\'s full pixel gate: screenshots', [P3], 'total.screenshots')
    F['pp_room'] = pp['room_capture']
    # R3.3: the search order changed src/ after that gate; the search states ran again, plus one that tells the two orders apart
    R33PIX = 'bench/results/oncrack-r3-search/pixels.json'
    p33 = jload(R33PIX)
    F['r33_equal'] = V(sum(v['equal'] for v in p33['seeds'].values()), 'search states re-run after the search order change: screenshots pixel-equal', [R33PIX], 'sum(seeds.*.equal)')
    F['r33_total'] = V(sum(v['cells'] for v in p33['seeds'].values()), 'search states re-run after the search order change: screenshots', [R33PIX], 'sum(seeds.*.cells)')
    F['r33_port_diff'] = V(sum(1 for c in p33['port_vs_new_oracle_order_state'] if not c['pixels_equal']), 'the port against the same oracle, search/results/order: cells different', [R33PIX], 'count(port_vs_new_oracle_order_state, not pixels_equal)')
    F['r33_port_cells'] = V(len(p33['port_vs_new_oracle_order_state']), 'the port against the same oracle, search/results/order: cells', [R33PIX], 'len(port_vs_new_oracle_order_state)')
    # the verifier
    VF = 'bench/results/oncrack-verifier/verifier.json'
    vj = jload(VF)
    F['ver'] = vj
    F['ver_n'] = V(len(vj['attacks']), 'attack tests the verifier ran', [VF], 'len(attacks)')
    F['ver_found'] = V(sum(a['result'] == 'found' for a in vj['attacks']), 'attack tests that found a problem', [VF], 'attacks where result = found')
    F['ver_held'] = V(sum(a['result'] == 'held' for a in vj['attacks']), 'attack tests that held', [VF], 'attacks where result = held')
    F['findings'] = {sev: V(sum(f['severity'] == sev for f in vj['report']['findings']), 'verifier findings, %s' % sev, [VF], 'report.findings where severity = %s' % sev) for sev in ('major', 'minor')}
    # durability
    F['dur'] = {(k, c, m): http('oncrack', 'post_message', c, m, 'bench/results/oncrack-c2/t2-group-' + k) for k in ('off', 'on') for c in (1, 16, 64) for m in ('rps', 'cpu')}
    for c in (1, 16, 64):
        for m in ('rps', 'cpu'):
            F['dur']['w200', c, m] = http('oncrack', 'post_message', c, m, 'bench/results/oncrack-c2/t2-window200')
    # what onCrack does: unit A/Bs
    F['ab_cache'] = {(k, r, m): http('oncrack', r, 16, m, 'bench/results/oncrack-c1/t2-cache-' + k) for k in ('off', 'on') for r, _ in ROUTES for m in ('rps', 'cpu')}
    F['ab_len'] = {(k, r, c, m): http('oncrack', r, c, m, 'bench/results/oncrack-c3/t2-length-' + k) for k in ('off', 'on') for r, _ in ROUTES for c in (1, 16) for m in ('rps', 'cpu')}
    C4 = 'bench/results/oncrack-c4/boot.jsonl'
    boot = {r['label']: r for r in jlines(C4)}
    for lab in ('aot-image', 'jit-r2r-image'):
        for k in ('up_ms', 'idle_mb'):
            F['boot', lab, k] = V(boot[lab]['median'][k], 'bench/boot, %s: %s, median of %d fresh containers' % (lab, k, boot[lab]['runs']), [C4], 'median.%s of the "%s" line' % (k, lab))
    for c in (1, 16):
        F['aot_geo', c] = geo([http('oncrack', r, c, 'rps', 'bench/results/oncrack-c4/tier3-aot').over(http('oncrack', r, c, 'rps', 'bench/results/oncrack-c3/tier3')) for r, _ in ROUTES],
                              'Native AOT image over the default JIT image (C3 tier 3), geometric mean of the five workloads, c=%d' % c)
    # fixed parameters written in results files
    F['cache_mb'] = md('bench/results/oncrack-c1.md', r'Bounded at (\d+) MB', 'read cache budget, MB')
    F['group_max'] = md('bench/results/oncrack-c2.md', r'up to (\d+),\s*`CAMPFIRE_GROUP_COMMIT_MAX`', 'writes per group at most')
    F['stripes'] = md('bench/results/oncrack-fixes.md', r'equal modulo ([\d,]+)', 'room counters (ids striped modulo)')
    F['verify_after'] = md('bench/results/oncrack-fixes.md', r'Release build, warnings as errors, ([\d,]+)\s+tests', 'bin/verify tests after the fixes')
    F['fix_changes'] = md('bench/results/oncrack-fixes.md', r'In each, ([\d,]+) changes are made while', 'changes per new read-cache test')
    F['fix_readers'] = md('bench/results/oncrack-fixes.md', r'while (\d+) browsers read the page', 'concurrent readers per new read-cache test')
    F['fix_posts'] = md('bench/results/oncrack-fixes.md', r'all (\d+) arrive with 0 out-of-order pairs', 'posts in the broadcast-order test')
    F['syscalls'] = md('bench/results/oncrack-c3.md', r'syscalls per request fell from ([\d.]+) to', 'syscalls per request with chunked answers (search, c=16)')
    F['syscalls_after'] = md('bench/results/oncrack-c3.md', r'syscalls per request fell from [\d.]+ to ([\d.]+)', 'syscalls per request with Content-Length (search, c=16)')
    F['aot_pp'] = md('bench/results/oncrack-c4.md', r'\*\*(\d+)/\d+\s+screenshots pixel-equal', 'Native AOT image, screenshots pixel-equal (fast matrix, default seed)')
    F['ver_pp_secs'] = vnum(r'0 not captured, in ([\d,]+) s', "verifier's full pixel gate on the pre-fix image, seconds")
    F['kill_threads'] = vnum(r'SIGKILL during (\d+)-thread posting', 'SIGKILL test: posting threads')
    F['kill'] = {k: vnum(p, 'SIGKILL test: ' + lab) for k, p, lab in (
        ('runs', r'default settings: (\d+) runs in colima', 'runs'), ('acked', r'([\d,]+) acknowledged posts, 0 lost', 'acknowledged posts'),
        ('lost', r'acknowledged posts, (\d+) lost', 'acknowledged posts lost'), ('dup', r'(\d+) duplicated', 'duplicated posts'),
        ('unindexed', r'(\d+) missing from the search index', 'acknowledged posts missing from the search index'))}
    F['cache_off_found'] = vnum(r'all three tests found (\d+) stale pages', 'A1, A1b and A1c with the read cache off: stale pages found')
    F['a1_readers'] = vnum(r'checked while (\d+) other browsers read the same page', 'A1, A1b, A1c: concurrent readers')
    F['window_default'] = md('bench/results/oncrack-c2.md', r'`CAMPFIRE_GROUP_COMMIT_WINDOW_US` \((\d+):', 'group commit window by default, µs')
    F['window_tried'] = md('bench/results/oncrack-c2.md', r'`CAMPFIRE_GROUP_COMMIT_WINDOW_US=(\d+)` \(not kept\)', 'group commit window tried, µs')
    F['fix_failed'] = md('bench/results/oncrack-fixes.md', r'tests, (\d+) failed, \d+ skipped', 'bin/verify tests failed after the fixes')
    F['fix_inversions'] = md('bench/results/oncrack-fixes.md', r'arrive with (\d+) out-of-order pairs', 'out-of-order pairs after the broadcast-order fix')
    F['ready_ms'] = md('bench/results/oncrack-c0.md', r'"not ready after (\d+) ms"', 'the harness\'s wait for a page to be ready, ms')
    # the climb (stored references)
    F['stored'] = {c: md('bench/results/oncrack-round1-final.md',
                         r'ratios against the stored phase7-final medians are almost the same: ([\d.]+)x, ([\d.]+)x and ([\d.]+)x Rust', 'onCrack over the stored Rust medians (phase7-final), geometric mean, c=%d' % c,
                         group={1: 1, 16: 2, 64: 3}[c]) for c in (1, 16, 64)}
    # ---- the final run (round five): what the two claims stand on
    for prof, sessions, mixed_ in (('normal', R3N, False), ('mixed', R3M, True)):
        for b in ('rust', 'c'):
            routes = [r for r, _ in ROUTES if not (mixed_ and r == 'post_message')]
            files = sorted(os.path.relpath(f, REPO) for d in sessions[:2] for f in glob.glob(os.path.join(REPO, d, 'oncrack-[0-9].json')))
            def pool(app, r, mixed_=mixed_, sessions=sessions):
                fs = sorted(os.path.relpath(f, REPO) for d in sessions[:2] for f in glob.glob(os.path.join(REPO, d, app + '-[0-9].json')))
                key = 'mixed_http' if mixed_ else 'http'
                vals = [x['rps'] for f in fs for x in jload(f)[key] if x['route'] == r and x['conc'] == 16]
                return V(statistics.median(vals), '%s, %s, c=16, req/s, median of %d rounds (the first two %s sessions pooled)' % (UPBASE[app], RNAME[r], len(vals), prof), fs, 'median of ' + ', '.join(g(float(x)) for x in vals))
            F['sub2', prof, b] = geo([pool('oncrack', r).over(pool(b, r)) for r in routes], 'onCrack over %s, geometric mean of the %s, the first two %s sessions pooled (the plan\'s original design)' % (UPBASE[b], 'four mixed-profile reads' if mixed_ else 'five workloads', prof))
    F['sess_n'] = V(len(R3N), 'sessions of each upstream-harness profile in the final run, all pooled', [d + '/summary.json' for d in R3N], 'count of normal-N directories (PLAN.md rule 3: none dropped)')
    F['sess'] = {}
    for prof, sessions, mixed_ in (('normal', R3N, False), ('mixed', R3M, True)):
        for b in ('rust', 'c'):
            F['sess', prof, b] = [sess_geo(d, b, mixed_) for d in sessions]
            vs = F['sess', prof, b]
            F['sess_lo', prof, b] = V(min(v.v for v in vs), 'onCrack over %s, the lowest session of the three (%s profile)' % (UPBASE[b], prof), sorted({f for v in vs for f in v.files}),
                                      'smallest of ' + ', '.join('%.3f' % v.v for v in vs))
            F['sess_hi', prof, b] = V(max(v.v for v in vs), 'onCrack over %s, the highest session of the three (%s profile)' % (UPBASE[b], prof), sorted({f for v in vs for f in v.files}),
                                      'largest of ' + ', '.join('%.3f' % v.v for v in vs))
    noise = {}
    NF = R5F + '/session-noise.txt'
    for ln in text(NF).splitlines():
        m = re.match(r'host-load-((?:normal|mixed)-\d)\.txt: (\d+) samples during the session, (\d+) at >=150% \((\d+)%\), max (\d+)%, median (\d+)% -> (\w+)', ln)
        if m:
            noise[m.group(1)] = {'pct': V(int(m.group(4)), 'host samples at 150%% non-VM CPU or more, session %s, %%' % m.group(1), [NF, R5F + '/host-load-%s.txt' % m.group(1)], 'written in session-noise.txt: "%s"' % ln.strip()),
                                 'noisy': m.group(7) == 'NOISY'}
    if len(noise) != 6:
        raise SystemExit('build: %s names %d sessions, want six' % (NF, len(noise)))
    F['noise'] = noise
    F['noisy_n'] = V(sum(n['noisy'] for n in noise.values()), 'sessions flagged NOISY by the plan\'s rule (more than a quarter of host samples at 150% non-VM CPU or more), of six', [NF], 'count of lines ending "-> NOISY"')
    F['quiet_n'] = V(len(noise) - F['noisy_n'].v, 'sessions that passed the noise rule, of six', [NF], 'count of lines ending "-> ok"')
    F['sess_total'] = V(len(noise), 'upstream-harness sessions pooled in the final run (three normal, three mixed)', [NF], 'count of session lines')
    # the hand re-runs' quiet sets, named by the plan's rule before anyone looked (review-quiet-sets.md)
    QF = R5F + '/review-quiet-sets.md'
    qm = re.search(r'the three sets whose host was not NOISY \(([^)]*)\)', text(QF))
    quiet_tags = re.findall(r'review-([\w-]+)', qm.group(1))
    rv = [json.loads(l) for l in open(os.path.join(REPO, R3, 'review.jsonl')) if '"window"' in l]
    for a in ('oncrack', 'oncrack-cached', 'rust', 'c'):
        for ph in ('room_show', 'mixed', 'post_message'):
            xs = [d['server_cpu_us_per_req'] for d in rv if (('oncrack-cached' if d['app'] == 'oncrack' and 'cached' in d['tag'] else d['app']) == a) and d['phase'] == ph
                  and d['tag'].split('review-')[-1] in quiet_tags]
            F['cpuq', a, ph] = V(statistics.median(xs), '%s, server CPU us per request, %s, median of the %d hand re-runs on a quiet host (review.py)' % (UPBASE[a], {'room_show': 'room page', 'mixed': 'mixed reads', 'post_message': 'post'}[ph], len(xs)),
                                 [R3 + '/review.jsonl', QF], 'median of ' + ', '.join('%.1f' % x for x in xs))
            xs = [d['server_cpu_us_per_req'] for d in rv if (('oncrack-cached' if d['app'] == 'oncrack' and 'cached' in d['tag'] else d['app']) == a) and d['phase'] == ph]
            F['cpu3', a, ph] = V(statistics.median(xs), '%s, server CPU us per request, %s, median of %d hand re-runs (review.py, all seven sets)' % (UPBASE[a], {'room_show': 'room page', 'mixed': 'mixed reads', 'post_message': 'post'}[ph], len(xs)),
                                 [R3 + '/review.jsonl'], 'median of ' + ', '.join('%.1f' % x for x in xs))
    # PR #6: posts a second each app accepted in cable_heavy (the harness's own count), per round
    for key, app, directory in REL_APPS:
        if key == 'fsharp':
            continue
        vals = [jload(directory + '/harness-output/%s-%d.json' % (app, i))['cable_heavy']['throughput']['posts_per_sec'] for i in (1, 2, 3)]
        F['relposts', key] = V(statistics.median(vals), '%s, posts a second taken in Cable with %d closed-loop posters, median of 3 rounds (%s)' % (REL_NAME[key], F['rel_posters'].v, directory.replace('bench/results/', '')),
                               [directory + '/harness-output/%s-%d.json' % (app, i) for i in (1, 2, 3)], 'median of ' + ', '.join(g(float(x)) for x in vals) + ' (cable_heavy.throughput.posts_per_sec)')
        F['relposts_lo', key] = V(min(vals), '%s, posts a second taken in cable_heavy, the slowest round' % REL_NAME[key], F['relposts', key].files, 'smallest of ' + ', '.join(g(float(x)) for x in vals))
        F['relposts_hi', key] = V(max(vals), '%s, posts a second taken in cable_heavy, the fastest round' % REL_NAME[key], F['relposts', key].files, 'largest of ' + ', '.join(g(float(x)) for x in vals))
    for key in ('oncrack', 'rust', 'oncrack-before'):
        rd = jload(REL_SESSION + '/summary.json')[dict((k, a) for k, a, _ in REL_APPS)[key]]['cable_heavy']['rounds']
        for fld, nm in (('disconnected', 'clients the server closed mid-run'), ('pss', 'peak Pss MB'), ('p99', 'p99 ms from a post to the last client')):
            vals = [v for v in rd[fld] if v is not None]
            files = [REL_SESSION + '/summary.json']
            F['rello', key, fld] = V(min(vals), '%s, Cable with %d closed-loop posters, %s, lowest of 3 rounds' % (REL_NAME[key], F['rel_posters'].v, nm), files, 'smallest of ' + ', '.join(g(float(x)) for x in vals))
            F['relhi', key, fld] = V(max(vals), '%s, Cable with %d closed-loop posters, %s, highest of 3 rounds' % (REL_NAME[key], F['rel_posters'].v, nm), files, 'largest of ' + ', '.join(g(float(x)) for x in vals))
    # every claim of the production panel that the data must back, or the build stops
    rd = jload(REL_SESSION + '/summary.json')
    for app in ('oncrack', 'oncrack-cached'):
        for prof in ('cable', 'cable_heavy'):
            r_ = rd[app][prof]['rounds']
            if any(r_['disconnected']) or r_['posted'] != r_['complete'] or any(x != rd[app][prof]['clients'] for x in r_['ready']):
                raise SystemExit('build: %s %s in the final run cut a client or lost a message; the page says it does neither' % (app, prof))
    if not all(min(rd['rust']['cable_heavy']['rounds']['disconnected']) > 0 for _ in (0,)):
        raise SystemExit('build: Rust cut nobody in cable_heavy; the page says it cuts hundreds')
    # the cable suite: every phase of every session, by the rule of cable/phases.py
    flagged, nphase = [], 0
    pfiles = []
    for sd in CABLE_SESSIONS:
        for sub in ('t3', 'sends'):
            for f in sorted(glob.glob(os.path.join(REPO, sd, sub, '*.json'))):
                rel = os.path.relpath(f, REPO)
                pfiles.append(rel)
                for c in jload(rel)['cable']:
                    t, l, cl = c['throughput'], c['latency'], c.get('client', {})
                    nphase += 1
                    if t['posted'] != t['complete'] or l['messages'] != l['complete'] or c['ready'] != c['clients'] or cl.get('closed_midrun', 0) or cl.get('odd_frames', 0) \
                            or cl.get('markers_past_cap', 0) or cl.get('receipts_without_post_time', 0) or c['failed']:
                        flagged.append((rel, c['clients']))
    if flagged:
        raise SystemExit('build: cable phases where a message did not reach every client or a counter is nonzero: %r; the page says there are none' % flagged[:4])
    F['phases'] = V(nphase, 'Cable phases of the final run (three sessions, rust, the port and onCrack, saturated and paced, sends passes included)', pfiles, 'count of cable[] entries; each posted == complete, paced messages == complete, subscribed == clients, nothing closed mid-run, no odd frames, no failed connects (the rule of cable/phases.py)')
    F['phases_bad'] = V(len(flagged), 'Cable phases of the final run with a message short of any client or a nonzero counter', pfiles, 'count of cable[] entries failing the rule above')
    # tests and the other gates, as their logs say them
    VL = R5F + '/logs/verify.log'
    vt = text(VL)
    for k in ('total', 'failed', 'succeeded', 'skipped'):
        F['verify', k] = md(VL, r'^\s+%s: (\d+)$' % k, 'bin/verify, tests %s' % k) if False else V(float(re.findall(r'^\s+%s: (\d+)$' % k, vt, re.M)[-1]), 'bin/verify (CAMPFIRE_REQUIRE_SEED=1), tests %s' % k, [VL], 'the log\'s summary line "%s:"' % k)
    LC = R5F + '/logs/linux-cable.log'
    lt = text(LC)
    for k in ('total', 'succeeded', 'failed'):
        F['lcable', k] = V(float(re.findall(r'^\s+%s: (\d+)$' % k, lt, re.M)[-1]), 'bin/linux-tests Cable, tests %s' % k, [LC], 'the log\'s summary line "%s:"' % k)
    for k, pat, lab in (('kill_runs', r"The last kill -9 runs are round 3's \((\d+) runs, \d+ lost, \d+ duplicated\)", 'kill -9 runs of the last durability test (round three)'),
                        ('kill_lost', r"The last kill -9 runs are round 3's \(\d+ runs, (\d+) lost, \d+ duplicated\)", 'acknowledged posts lost in those runs'),
                        ('kill_dup', r"The last kill -9 runs are round 3's \(\d+ runs, \d+ lost, (\d+) duplicated\)", 'posts duplicated in those runs'),
                        ('hub_gib', r'bounded by `CAMPFIRE_CABLE_HUB_BYTES` (\d+) GiB', 'the hub\'s total budget for Cable logs, GiB')):
        F[k] = md(R5REPORT, pat, lab)
    # numbers written in the report's history table: each round's own closing headline, as written then (the beats under the chart)
    HT = {
        'pb': r'Phase 5b baseline: ([\d.]+)-([\d.]+)x Rust on the four reads at 16 connections, ([\d.]+)x on posts, (\d+)-(\d+)x Rails',
        'p7': r'`phase7-final`: \*\*([\d.]+)-([\d.]+)x Rust\*\* at 16 connections',
        'r1': r'\*\*([\d.]+)x Rust, ([\d.]+)x the port\*\* at c=16 \(([\d.]+)x at c=1, ([\d.]+)x at c=64\)',
        'r2': r'\*\*([\d.]+)x Rust, ([\d.]+)x C, ([\d.]+)x the port\*\* \(normal\), ([\d.]+)x / ([\d.]+)x on mixed reads',
        'r3': r'Fresh: \*\*([\d.]+)x Rust, ([\d.]+)x C, ([\d.]+)x port\*\* \(normal, two sessions pooled; sessions ([\d.]+)x and ([\d.]+)x\)',
        'r4': r'\*\*([\d.]+)x Rust, ([\d.]+)x C, ([\d.]+)x port\*\* \(one session\); CPU per room page ([\d.]+)x Rust, ([\d.]+)x C; fan-out ([\d.]+) / ([\d.]+) / ([\d.]+) / \*\*([\d.]+)\*\*x Rust',
        'r1g': r'a 100%-cache-hit result\. \| (\d+) / (\d+) pixels \|',
        'r2g': r'\| (\d+) / (\d+) round 1; a (\d+)-screenshot targeted gate after the fixes \|',
        'r3m': r'mixed ([\d.]+)x / ([\d.]+)x; CPU per room page ([\d.]+)x Rust, ([\d.]+)x C\. \|',
        'r3g': r'CPU per room page [\d.]+x Rust, [\d.]+x C\. \| (\d+) / (\d+) \|',
        'r4g': r'\| (\d+) targeted screenshots \|',
        'r4msg': r'one message of ([\d,]+) missing',
    }
    names = {'pb': ['rust_lo', 'rust_hi', 'post', 'rails_lo', 'rails_hi'], 'p7': ['rust_lo', 'rust_hi'], 'r1': ['rust', 'port', 'rust_c1', 'rust_c64'],
             'r2': ['rust', 'c', 'port', 'rust_mixed', 'c_mixed'], 'r3': ['rust', 'c', 'port', 'rust_s1', 'rust_s2'], 'r4': ['rust', 'c', 'port', 'cpu_rust', 'cpu_c', 'f100', 'f500', 'f1000', 'f2000'],
             'r1g': ['equal', 'total'], 'r2g': ['equal', 'total', 'targeted'], 'r3m': ['rust_mixed', 'c_mixed', 'cpu_rust', 'cpu_c'], 'r3g': ['equal', 'total'], 'r4g': ['shots'], 'r4msg': ['posted']}
    F['hist'] = {}
    for key, pat in HT.items():
        for i, nm in enumerate(names[key]):
            F['hist', key, nm] = md(R5REPORT, pat, 'the report\'s history table, %s: %s' % (key, nm), group=i + 1)
    return F


def sess_at(sdir, app, route, mixed=False):
    """One session's median for one app and route at c=16 over its three rounds."""
    files = sorted(os.path.relpath(f, REPO) for f in glob.glob(os.path.join(REPO, sdir, app + '-[0-9].json')))
    key = 'mixed_http' if mixed else 'http'
    vals = [x['rps'] for f in files for x in jload(f)[key] if x['route'] == route and x['conc'] == 16]
    if len(vals) != len(files) or len(vals) != 3:
        raise SystemExit('build: %s %s %s: %d samples in %d rounds' % (sdir, app, route, len(vals), len(files)))
    return V(statistics.median(vals), '%s, %s, c=16, req/s, median of %d rounds (verification harness, %s)' % (UPBASE[app], RNAME[route], len(vals), sdir.split('/')[-1]), files,
             'median of ' + ', '.join(g(float(x)) for x in vals))


def sess_geo(sdir, base, mixed=False):
    routes = [r for r, _ in ROUTES if not (mixed and r == 'post_message')]
    return geo([sess_at(sdir, 'oncrack', r, mixed).over(sess_at(sdir, base, r, mixed)) for r in routes],
               'onCrack over %s, geometric mean of the %s, %s session on its own (verification harness)' % (UPBASE[base], 'four mixed-profile reads' if mixed else 'five workloads', sdir.split('/')[-1]))


# ================================================================ helpers for the page

X, I, D1, D2 = '{:.2f}×', '{:,.0f}', '{:,.1f}', '{:,.2f}'
P50, P99 = '<span data-lit="name">p50</span>', '<span data-lit="name">p99</span>'
FCTX = {}


def cN(c, link=True):
    return 'c=' + L.n(FCTX['F']['conc'][c], link=link)


def tier(n):
    return lit('tier %d' % n)


def counter(v, dec=0, unit='', link=False):
    shown = ('{:,.%df}' % dec).format(v.v)
    rid = L.row(v.label, v.files, v.how, shown + unit, v.v)
    tag = 'a' if link else 'span'
    return ('<span class="num-big"><%s class="sn"%s data-src="%s"><b class="count" data-to="%s" data-dec="%d">%s</b></%s>%s</span>'
            % (tag, (' href="#%s"' % rid) if link else '', rid, ('%.' + str(dec) + 'f') % v.v, dec, shown, tag, ('<i>%s</i>' % e(unit)) if unit else ''))


def panel(pid, kicker, title, body, back):
    return ('<div class="panel" id="%s" role="dialog" aria-modal="true" aria-labelledby="%s-t">'
            '<a class="scrim" href="#%s" data-close tabindex="-1" aria-hidden="true"></a>'
            '<div class="sheet" tabindex="-1"><header class="sheet-head"><div><p class="kicker">%s</p><h2 id="%s-t">%s</h2></div>'
            '<a class="x" href="#%s" data-close aria-label="Close panel"><span aria-hidden="true">&times;</span></a></header>'
            '<div class="sheet-body">%s<p class="back"><a href="#%s" data-close>&larr; Back to the page</a></p></div></div></div>'
            % (pid, pid, back, kicker, pid, title, back, body, back))


def details(pid, label='The details'):
    return '<a class="more" href="#%s">%s <span aria-hidden="true">&rarr;</span></a>' % (pid, label)


def srcline(*paths, lead='Source'):
    return '<p class="src">%s: %s.</p>' % (lead, ', '.join(flink(p) for p in paths))


def tbl(head, rows, caption=None, cls=''):
    """head: list of (label, numeric?); rows: list of lists of HTML cells (first is the row header)."""
    th = ''.join('<th scope="col"%s>%s</th>' % (' class="num"' if num else '', h) for h, num in head)
    body = ''.join('<tr>%s</tr>' % ''.join(('<th scope="row">%s</th>' % c) if i == 0 else ('<td class="num">%s</td>' % c if head[i][1] else '<td>%s</td>' % c)
                                          for i, c in enumerate(r)) for r in rows)
    return '<div class="tw %s"><table>%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
        cls, ('<caption>%s</caption>' % caption) if caption else '', th, body)


# ================================================================ the page

def _r3geo(session):
    return geo([up3_at(R3_OLD, session, 'oncrack', r).over(up3_at(R3_OLD, session, 'rust', r)) for r, _ in ROUTES],
               'onCrack over Rust, geometric mean of the five workloads, %s session of round three&#39;s final run' % ('first normal' if session == 'normal-1' else 'second normal'))


CHART_FILES = ['bench/results/oncrack-log.jsonl', 'bench/results/phase7-log.jsonl', 'bench/results/phase7-final/rust-1.json', 'bench/results/phase7-final/fsharp-1.json',
               'bench/results/phase7-final/reference-1.json', 'bench/results/phase7-start/rust-1.json', 'bench/results/phase7-start/fsharp-1.json', 'bench/progress/history.json', 'bench/progress/climb.py']


def cv(v, label, how):
    """A value read off the climb chart (bench/progress/climb.py), with its sources."""
    return V(v, label, CHART_FILES, how)


def claims_check(F):
    """The hero's two claims, held to the data: the build stops if any word of them stops being true."""
    for b in ('rust', 'c', 'fsharp'):
        for r, _ in ROUTES:
            if not F['up3']['oncrack', r, 'median'].v > F['up3'][b, r, 'median'].v:
                raise SystemExit('build: onCrack is not ahead of %s at the pooled median on %s (normal profile); the faster claim says it is ahead in every cell' % (b, r))
        for r in UPREADS:
            if not F['up3m']['oncrack', r, 'median'].v > F['up3m'][b, r, 'median'].v:
                raise SystemExit('build: onCrack is not ahead of %s at the pooled median on %s (mixed profile); the faster claim says it is ahead in every cell' % (b, r))
    if not (F['sess_lo', 'normal', 'rust'].v > 1 and F['sess_lo', 'mixed', 'rust'].v > 1):
        raise SystemExit('build: a session of the final run has onCrack behind Rust; the claim says every session was ahead')
    if not (F['cpu3', 'rust', 'room_show'].v > F['cpu3', 'oncrack', 'room_show'].v and F['cpu3', 'c', 'room_show'].v > F['cpu3', 'oncrack', 'room_show'].v):
        raise SystemExit('build: onCrack spends more CPU per room page than Rust or C; the claim says less')
    if F['noisy_n'].v < 1:
        raise SystemExit('build: no session was noisy; the copy about the noisy sessions is stale')
    if not F['relposts', 'rust'].v > 3 * F['relposts', 'oncrack'].v:
        raise SystemExit('build: Rust no longer takes several times onCrack\'s posts in cable_heavy; the policy paragraph is stale')


def spread_strip(F):
    """Each session's onCrack over Rust on a line, the pooled figure beside it: the range, drawn. Filled = a session that passed the noise rule, hollow = one that did not."""
    W, H, L0, R0 = 520, 118, 76, 14
    hi = 7.0
    X = lambda v: L0 + (W - L0 - R0) * v / hi
    files = sorted({f for prof in ('normal', 'mixed') for v in F['sess', prof, 'rust'] for f in v.files})
    blk = L.block('the spread strip: onCrack over Rust, geometric mean of each session on its own, and the pooled figure, per profile', files + [R5F + '/session-noise.txt'],
                  'each dot is one session\'s geometric mean of its three rounds\' medians over Rust\'s (up3 per session); the diamond is the pooled figure; filled dots passed the plan\'s noise rule')
    svg = ['<svg viewBox="0 0 %d %d" role="img" aria-label="onCrack over Rust for each of six sessions and the pooled figure">' % (W, H)]
    for g in range(0, 8):
        svg.append('<line class="sp-g" x1="%.1f" x2="%.1f" y1="8" y2="78"/><text class="sp-t" x="%.1f" y="94" text-anchor="middle">%d&times;</text>' % (X(g), X(g), X(g), g))
    svg.append('<line class="sp-one" x1="%.1f" x2="%.1f" y1="8" y2="78"/><text class="sp-t sp-rust" x="%.1f" y="110" text-anchor="middle">Rust is 1&times;</text>' % (X(1), X(1), X(1)))
    for row, (prof, nm, sessions) in enumerate((('normal', 'Normal', R3N), ('mixed', 'Mixed', R3M))):
        y = 28 + row * 34
        svg.append('<text class="sp-l" x="0" y="%d">%s</text>' % (y + 4, nm))
        for k, d in enumerate(sessions):
            v = F['sess', prof, 'rust'][k]
            name = d.split('/')[-1]
            noisy = F['noise'][name]['noisy']
            svg.append('<circle class="%s" cx="%.1f" cy="%d" r="6.5"><title>%s: %.2f&times; Rust (%s)</title></circle>' % ('sp-n' if noisy else 'sp-q', X(v.v), y, name, v.v, 'noisy host' if noisy else 'quiet host'))
        pv = F['up3_geo' if prof == 'normal' else 'up3m_geo', 'oncrack', 'rust'].v
        svg.append('<path class="sp-p" d="M%.1f %d l8 8 l-8 8 l-8 -8z"><title>pooled, all three sessions: %.2f&times; Rust</title></path>' % (X(pv), y - 8, pv))
    svg.append('</svg>')
    return ('<figure class="spread" %s>%s<figcaption><span><i class="sp-k sp-kq"></i>a session on a quiet host</span><span><i class="sp-k sp-kn"></i>a session beside other work</span><span><i class="sp-k sp-kp"></i>all three, pooled</span></figcaption></figure>'
            % (blk, ''.join(svg)))


def claim_fast(F):
    x = lambda v: L.x(v)
    rows = []
    for b, nm in (('rust', 'Rust'), ('c', 'C'), ('fsharp', 'the F# port')):
        rows.append('<li><span class="cl-n">%s</span><span class="cl-l">over %s%s</span></li>' % (
            counter(F['up3_geo', 'oncrack', b], 2, '×', link=True), nm if b == 'fsharp' else upname(b), ''))
    return ('<article class="claim claim-fast" id="claim-fast" aria-labelledby="cf-h"><p class="claim-k">Claim one</p><h2 id="cf-h">Faster.</h2>'
            '<p class="claim-line">Ahead of current upstream Rust and C at the median in every workload of Basecamp&#39;s own harness, with the room being written to and without. '
            '<b>Quote the range, not one number:</b> the three sessions of each profile, pooled, read as below; each session on its own reads %s to %s over Rust (normal) and %s to %s (mixed), '
            'because %s of the %s sessions ran beside other projects&#39; work.</p>'
            '<ul class="claim-nums">%s</ul>%s'
            '<ul class="claim-facts">'
            '<li><b>Fresh authorization.</b> The default re-checks the session and the room membership on every cache hit, as upstream&#39;s contract asks. The cached decision, opt-in, reads %s over Rust.</li>'
            '<li><b>Per room page, the CPU says the same:</b> Rust spends %s and C %s of onCrack&#39;s CPU (%s and %s on the quiet host).</li>'
            '<li><b>Mixed reads:</b> %s over Rust and %s over C while one writer posts into the room.</li></ul>'
            '<p class="claim-foot">%s<span class="cl-note">Not their machine: four of a VM&#39;s CPUs a side. Compare ratios.</span></p></article>'
            % (x(F['sess_lo', 'normal', 'rust']), x(F['sess_hi', 'normal', 'rust']), x(F['sess_lo', 'mixed', 'rust']), x(F['sess_hi', 'mixed', 'rust']),
               L.n(F['noisy_n']), L.n(F['sess_total']), ''.join(rows), spread_strip(F), x(F['up3_geo', 'oncrack-cached', 'rust']),
               x(F['cpu3', 'rust', 'room_show'].over(F['cpu3', 'oncrack', 'room_show'])), x(F['cpu3', 'c', 'room_show'].over(F['cpu3', 'oncrack', 'room_show'])),
               x(F['cpuq', 'rust', 'room_show'].over(F['cpuq', 'oncrack', 'room_show'])), x(F['cpuq', 'c', 'room_show'].over(F['cpuq', 'oncrack', 'room_show'])),
               x(F['up3m_geo', 'oncrack', 'rust']), x(F['up3m_geo', 'oncrack', 'c']),
               details('p-fresh', 'The evidence')))


def claim_prod(F):
    rel = lambda f, key='oncrack': F['rel', key, 'cable_heavy', f]
    return ('<article class="claim claim-prod" id="claim-prod" aria-labelledby="cp-h"><p class="claim-k">Claim two</p><h2 id="cp-h">More runnable in production.</h2>'
            '<p class="claim-line">Fast is easy to buy by dropping what production needs. onCrack keeps the pixels, the durability and every connected client, and it says what that costs.</p>'
            '<ul class="claim-nums">'
            '<li><span class="cl-n">%s</span><span class="cl-l">of %s Cable clients cut in <span data-lit="name">PR #6</span>&#39;s heaviest profile, in %s of %s rounds. Rust cut %s to %s of them.</span></li>'
            '<li><span class="cl-n"><span class="num-big">%s<i class="sl">/</i>%s</span></span><span class="cl-l">screenshots pixel-equal to Rails, on every seed, on the final code.</span></li>'
            '<li><span class="cl-n"><span class="num-big">%s<i class="sl">/</i>%s</span></span><span class="cl-l">posted messages reached every client in the median round, and every posted message did in every round. Rust: %s of %s.</span></li></ul>'
            '<ul class="claim-facts">'
            '<li><b>Durability is Rails&#39;.</b> Every write commits before it is answered; nothing weaker ships. The last <code>kill -9</code> runs (%s of them, round three) lost %s and duplicated %s.</li>'
            '<li><b>Cable&#39;s backlog is bounded.</b> A shared log with a byte budget, %s <span data-lit="name">GiB</span> for the whole hub; over it, the clients furthest behind are cut. Its known slack is in the report.</li>'
            '<li><b>It holds the posters, not the readers.</b> It takes %s posts a second to Rust&#39;s %s, a %s s <span data-lit="name">p99</span> from a post to the slowest client, and about %s MB of memory to Rust&#39;s %s. A different policy, not a free win.</li></ul>'
            '<p class="claim-foot">%s%s</p></article>'
            % (counter(F['relhi', 'oncrack', 'disconnected'], 0, ''), L.n(F['rel_clients']), L.n(V(3, 'rounds of PR #6\'s reliability profiles, every app', [REL_SESSION + '/summary.json'], 'len(rounds.round)')), L.n(V(3, 'rounds of PR #6\'s reliability profiles, every app', [REL_SESSION + '/summary.json'], 'len(rounds.round)')),
               L.n(F['rello', 'rust', 'disconnected']), L.n(F['relhi', 'rust', 'disconnected']),
               L.n(F['pp_total']['equal'], link=False), L.n(F['pp_total']['screenshots'], link=False),
               L.n(F['rel', 'oncrack', 'cable_heavy', 'complete'], link=False), L.n(F['rel', 'oncrack', 'cable_heavy', 'posted'], link=False),
               L.n(F['rel', 'rust', 'cable_heavy', 'complete']), L.n(F['rel', 'rust', 'cable_heavy', 'posted']),
               L.n(F['kill_runs']), L.n(F['kill_lost']), L.n(F['kill_dup']), L.n(F['hub_gib']),
               L.n(F['relposts', 'oncrack']), L.n(F['relposts', 'rust']),
               L.n(V(F['rel', 'oncrack', 'cable_heavy', 'p99'].v / 1000, 'onCrack, Cable with 64 closed-loop posters, p99 seconds from a post to the last client (median of 3 rounds)', F['rel', 'oncrack', 'cable_heavy', 'p99'].files, F['rel', 'oncrack', 'cable_heavy', 'p99'].how + ' / 1000'), '{:.0f}'),
               L.n(F['rel', 'oncrack', 'cable_heavy', 'pss'], '{:,.0f}'), L.n(F['rel', 'rust', 'cable_heavy', 'pss'], '{:,.0f}'),
               details('p-prod', 'The evidence'), details('p-reliability', 'The reliability tables')))


def hero(F, cl):
    c16 = F['up_conc']
    claims_check(F)
    hc = cl
    table_rows = []
    for r, rn in ROUTES:
        table_rows.append([rn[0].upper() + rn[1:], '<b>%s</b>' % L.n(F['up3']['oncrack', r, 'median']),
                           L.x(F['up3']['oncrack', r, 'median'].over(F['up3']['rust', r, 'median'])), L.x(F['up3']['oncrack', r, 'median'].over(F['up3']['c', r, 'median']))] +
                          [L.n(F['up3'][a, r, 'median']) for a in ('rust', 'c', 'fsharp', 'oncrack-cached')])
    table = tbl([('Requests/sec, %s clients' % L.n(c16, link=False), False), ('onCrack', True), ('&divide; Rust', True), ('&divide; C', True)] +
                [(upname(a), True) for a in ('rust', 'c', 'fsharp')] + [('onCrack, cached decision (opt-in)', True)], table_rows)
    chart_src = L.block('the climb chart: the F# port, onCrack fresh and onCrack cached over the stored pinned Rust medians, one dot per version', CHART_FILES,
                        'drawn by bench/progress/climb.py (hero_chart): each dot is the geometric mean over the five workloads at c=16 of the logged run\'s req/s over the median of the stored Rust reps of its era (the port: phase7-start; onCrack: phase7-final); '
                        'cards add the F# port and Rails from the same stored session')
    lat = hc['latest']
    fresh_v = cv(lat['fresh'], 'onCrack, fresh authorization, the last dot of the climb chart (round five, 3e6a300), over pinned Rust', 'the line\'s last dot')
    cached_v = cv(lat['cached'], 'onCrack, cached decision, the last dot of the climb chart (round five, 3e6a300), over pinned Rust', 'the line\'s last dot')
    fork_v = cv(hc['fork'], 'the F# port\'s final result over pinned Rust: the dot onCrack forks from', 'the fork dot')
    start_t = hc['bands'][0]['first'].astimezone(climb_chart.EDT).strftime('%-d %b')
    return ('<section class="hero" id="top" aria-labelledby="hero-h"><div class="glow" aria-hidden="true"></div><div class="wrap">'
            '<p class="kicker hero-in">Basecamp&#39;s ONCE Campfire &middot; the F# port, unchained</p>'
            '<h1 id="hero-h" class="hero-in">onCrack.</h1>'
            '<p class="lede hero-in">The same Campfire, pixel for pixel, on a server that is free to do less work: it keeps finished pages until a commit changes what they show, and commits concurrent posts together. '
            'Who may see a kept page is decided again on every request, as upstream asks. Two claims, each with its evidence one click away. <em>Every number on this page links to the file it came from.</em></p>'
            '<div class="claims hero-in">%s%s</div>'
            '<figure class="climb hero-in" id="climb" aria-labelledby="climb-cap" %s>'
            '<p class="kicker climb-k">How it got here</p>'
            '<h2 class="climb-h">One timeline, three lines.</h2>'
            '%s'
            '<figcaption id="climb-cap"><span><b>The climb on this project&#39;s own suite, over pinned Rust</b> (<span data-lit="commit">ccece30</span>, stored medians): one dot per logged version, geometric mean of the five workloads at 16 connections, '
            'left to right in the order they ran, clock time under the dots. The F# port&#39;s own climb is dotted; onCrack forks from its final re-baseline (%s). Rounds one and two had only the cached decision; the default became fresh authorization in round three, '
            'so the fresh line branches there (the dotted join is not a measurement). Latest: fresh %s, cached %s. <b>Round three&#39;s two dots were measured in round five</b>, on the same day as round five&#39;s, and sit at round three&#39;s close: round three logged none of its own. <b>Round four logged nothing on this suite</b> and its final image was never measured on it. '
            'C was never run on this suite, so it has no line; Rails sits on the floor. The <a href="#upstream">table below</a> is the comparable headline: current Rust and C on upstream&#39;s harness. '
            'Hover or tap a dot for what was done and the numbers.</span>%s</figcaption></figure>'
            '%s'
            '<div class="upstream hero-in" id="upstream"><figure class="climb" aria-labelledby="up-cap">%s'
            '<figcaption id="up-cap"><span><b>Current upstream, their method, their contract.</b> <code>once-campfire-verification</code>&#39;s <code>bin/benchmark</code>: the median of every round of %s sessions, %s rounds a cell, of %s s at %s clients, '
            'every response validated against the seed, every acknowledged post audited in the database and its search index; four server CPUs and four for the load generator, on this '
            'project&#39;s VM, not their Ryzen. <b>onCrack re-reads the session and the room membership on every cache hit</b>, as upstream&#39;s implementations do; '
            'its older cached decision, faster and not comparable, is the last column and an opt-in. Other work on the Mac moves every engine&#39;s samples from one session to the next, so read the ranges in the details. '
            'onCrack&#39;s search lists the newest matches by message id, as upstream&#39;s does and its contract checks (round three, unit <span data-lit="name">R3.3</span>); the port keeps Rails <span data-lit="commit">90b3300</span>&#39;s order.</span>%s</figcaption></figure></div>'
            '</div></section>' % (claim_fast(F), claim_prod(F), chart_src, hc['chart'], L.x(fork_v), L.x(fresh_v), L.x(cached_v), details('p-climb', 'Every dot, as a table'),
                                  beats(F, hc), table, L.n(F['sess_n']), L.n(F['up3_rounds']), L.n(F['up_secs']), L.n(c16), details('p-fresh', 'The details')))


# ---------------------------------------------------------------- the iterations: a short beat under the chart for each band

def beats(F, hc):
    H = lambda key, nm: F['hist', key, nm]
    span = {b['key']: b for b in hc['bands']}

    def when_(key):
        b = span[key]
        if not b['first']:
            return ''
        t0, t1 = b['first'].astimezone(climb_chart.EDT), b['last'].astimezone(climb_chart.EDT)
        s_ = t0.strftime('%-d %b') if t0.date() == t1.date() else '%s &ndash; %s' % (t0.strftime('%-d %b'), t1.strftime('%-d %b'))
        return '<span class="bc-date" %s>%s</span>' % (L.block('the climb chart\'s iteration bands: first and last dot of each, in US Eastern time', CHART_FILES, 'bench/progress/climb.py, hero_chart(): the earliest and latest logged run of each band'), s_)

    def x(v):
        return L.x(v)

    def lastv(series, band):
        ds = [d for d in hc['dots'] if d['band'] == band and d['series'] == series and d['kept']]
        return cv(ds[-1]['v'], 'the climb chart, %s: the last kept dot of %s, over pinned Rust' % (series, band), 'the band\'s last dot') if ds else None

    def chartline(band, series_list, lead='On the chart at its close'):
        parts = []
        for s_, nm in series_list:
            v = lastv(s_, band)
            if v:
                parts.append('%s %s' % (nm, x(v)))
        return '<p class="bc-chart">%s: %s.</p>' % (lead, ', '.join(parts)) if parts else ''

    cards = [
        ('port-build', 'Port, the build', 'Translate it.',
         'The Rust port, crate by crate, into F# on ASP.NET Core and Falco: database, rich text, the kit, the views, the app.',
         'First baseline: %s&ndash;%s&times; Rust on the four reads, %s&times; on posts, %s&ndash;%s&times; Rails (at %s connections).' % (x(H('pb', 'rust_lo')).replace('×', ''), x(H('pb', 'rust_hi')).replace('×', ''), x(H('pb', 'post')).replace('×', ''), L.n(H('pb', 'rails_lo')), L.n(H('pb', 'rails_hi')), L.n(F['conc'][16])),
         chartline('port-build', [('port', 'the port')])),
        ('port-tune', 'Port, the tuning', 'Match Rust&#39;s profile.',
         'Parity first, then tuning against Rust&#39;s own profile: cookies, bodies, row reads, Cable fan-out. Published as the F# port; onCrack forks from its last dot.',
         'Final re-baseline: %s&ndash;%s&times; Rust at %s connections.' % (x(H('p7', 'rust_lo')).replace('×', ''), x(H('p7', 'rust_hi')).replace('×', ''), L.n(F['conc'][16])),
         chartline('port-tune', [('port', 'the port')])),
        ('r1', 'Round one', 'Keep finished pages.',
         'Same pixels, unhinged work per request: a versioned read cache, group commit, Content-Length on gzipped answers, Native AOT as an opt-in.',
         '%s Rust and %s the port at %s connections: a result in which every read was a cache hit.' % (x(H('r1', 'rust')), x(H('r1', 'port')), L.n(F['conc'][16])),
         chartline('r1', [('cached', 'cached')])),
        ('r2', 'Round two', 'Make the benchmark honest, then go faster.',
         'A benchmark that writes while it reads, Cable on its own socket, a front-server fast path, memory and cold start. It ended against upstream&#39;s own harness.',
         '%s Rust, %s C and %s the port on upstream&#39;s harness, with the cached decision, which is not upstream&#39;s contract.' % (x(H('r2', 'rust')), x(H('r2', 'c')), x(H('r2', 'port'))),
         chartline('r2', [('cached', 'cached')])),
        ('r3', 'Round three', 'Check who is asking, every time.',
         '<b>Fresh authorization on every cache hit became the default</b> (<span data-lit="name">R3.2</span>), search by message id as upstream&#39;s (<span data-lit="name">R3.3</span>). The cached decision stays an opt-in.',
         'Fresh: %s Rust, %s C, %s the port on upstream&#39;s harness (two sessions pooled: %s and %s on their own).' % (x(H('r3', 'rust')), x(H('r3', 'c')), x(H('r3', 'port')), x(H('r3', 'rust_s1')), x(H('r3', 'rust_s2'))),
         chartline('r3', [('fresh', 'fresh'), ('cached', 'cached')], 'On the chart, its final image measured in round five')),
        ('r4', 'Round four', 'Fan-out, and keep every subscriber.',
         'Gather writes (one <code>sendmsg</code> over the frames) and Cable reliability: a shared byte-bounded log, a cut for a stall and not for slowness, a gate that slows the posters. The fan-out lead at the largest room was withdrawn.',
         '%s Rust, %s C on one session; fan-out %s, %s, %s and %s&times; Rust at %s, %s, %s and %s clients.' % (x(H('r4', 'rust')), x(H('r4', 'c')), x(H('r4', 'f100')).replace('×', '&times;'), x(H('r4', 'f500')).replace('×', '&times;'), x(H('r4', 'f1000')).replace('×', '&times;'), x(H('r4', 'f2000')).replace('×', ''), *[L.n(F['clients'][n]) for n in CABLE_COUNTS]),
         '<p class="bc-chart">No dot: nothing was logged on this suite in round four.</p>'),
        ('r5', 'Round five', 'Find the one message.',
         'The one message that did not arrive was a compiler turning a recursion into a loop in the gather&#39;s pinning: found by reading the IL, fixed, tested. The memory bound now covers every chunk. Then the final gates and runs.',
         '%s Rust, %s C, %s the port on upstream&#39;s harness, across sessions of %s to %s; no client cut in <span data-lit="name">PR #6</span>.' % (x(F['up3_geo', 'oncrack', 'rust']), x(F['up3_geo', 'oncrack', 'c']), x(F['up3_geo', 'oncrack', 'fsharp']), x(F['sess_lo', 'normal', 'rust']), x(F['sess_hi', 'normal', 'rust'])),
         chartline('r5', [('fresh', 'fresh'), ('cached', 'cached')])),
    ]
    out = []
    for key, label, head, what, close, chart in cards:
        out.append('<li class="bc" id="beat-%s"><p class="bc-k"><b>%s</b> %s</p><h3>%s</h3><p class="bc-what">%s</p><p class="bc-close"><b>Closing headline.</b> %s</p>%s</li>'
                   % (key, label, when_(key), head, what, close, chart))
    return '<ol class="beats" aria-label="What changed in each iteration">%s</ol><p class="btw">%s %s</p>' % (''.join(out), details('p-rounds', 'What changed in each iteration, in full'),
                                                                                                          '<span>Every dot&#39;s own card lists the commits behind it.</span>')


def same_software(F, sp):
    c16 = F['conc'][16]
    w = lambda a: F['w'][a, 'room_show', 16, 'rps']
    rails, rust, port, onc = (w(a) for a in APPS)
    x = {'reference': 'the original',
         'rust': '%s Rails' % L.n(rust.over(rails), '{:.0f}×'),
         'fsharp': '%s Rust' % L.x(port.over(rust)),
         'oncrack': '%s Rust &middot; %s the port' % (L.x(onc.over(rust)), L.x(onc.over(port)))}
    tag = {'reference': 'slow', 'rust': 'fast', 'fsharp': 'faster', 'oncrack': 'cached'}
    rows = []
    for i, a in enumerate(APPS):
        v = w(a)
        rows.append('<li class="sbs-row sbs-%s" style="--i:%d" data-rate="%.1f">'
                    '<p class="sbs-name"><b>%s</b><em class="sbs-tag">%s</em><span class="sbs-x">%s</span></p>'
                    '<p class="sbs-rate">%s<span class="sbs-u sbs-u-rate">requests a second</span>'
                    '<span class="sbs-u sbs-u-live">served while you watch, at %s a second</span></p>'
                    '<span class="sbs-lane" aria-hidden="true"></span></li>'
                    % (a, i, v.v, NAME[a], tag[a], x[a], L.n(v).replace('class="sn"', 'class="sn sbs-n"', 1), L.n(v)))
    same = sp and sp.get('ok')
    badge = ('<span class="sbs-badge"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="9"/><path d="M5.5 10.4l3 3 6-6.6"/></svg>Same pixels</span>'
             if same else '<span class="sbs-badge sbs-differ">The captures differ</span>')
    shot = ('<figure class="sbs-shot reveal"><div class="sbs-frame"><img src="%s" width="1440" height="900" decoding="async" '
            'alt="The All Talk room, signed in as David: the page Rails, Rust, the F# port and onCrack each render to these same pixels."></div>'
            '<figcaption>%s<span>One screenshot, because the four are one: the parity harness&#39;s captures of this page from Rails, Rust, the port and onCrack are byte-identical.</span>'
            '</figcaption></figure>' % (e(sp['image']), badge)) if same else ''
    return ('<section class="sbs" id="sbs" aria-labelledby="sbs-h"><div class="wrap sbs-grid">%s'
            '<div class="sbs-copy reveal"><p class="kicker">Same pixels, four engines &middot; the room page &middot; round one, pinned Rust <span data-lit="commit">ccece30</span></p>'
            '<h2 id="sbs-h">Same software.</h2>'
            '<ol class="sbs-rows">%s</ol>'
            '<p class="sbs-warn"><b>onCrack&#39;s row is cache hits.</b> The benchmark asks for one page over and over and never writes, so onCrack serves it from a stored copy. '
            '<a href="#mix">With the room being written to</a>, the lead is %s Rust, not %s.</p>'
            '<p class="sbs-cap"><span>Each counter ticks at that engine&#39;s measured rate for this page, signed in, at %s connections, all four in the same session.</span>%s</p>'
            '</div></div></section>' % (shot, ''.join(rows), L.x(F['mix', 'oncrack', 'read'].over(F['mix', 'rust', 'read'], 'onCrack over Rust, room page reads/s while the room is written to')),
                                        L.x(onc.over(rust)), L.n(c16), details('p-sbs', 'How we know')))


def mix_beat(F):
    def bars(get, which):
        vs = [(a, get(a)) for a in ('rust', 'fsharp', 'oncrack')]
        return ''.join('<li class="mx-%s"><span class="mx-l">%s</span><span class="mx-bar"><span style="width:%.1f%%"></span></span><span class="mx-v">%s</span></li>'
                       % (a, NAME[a], 100 * v.v / F['w']['oncrack', 'room_show', 16, 'rps'].v, L.n(v)) for a, v in vs)
    ro = F['w']['oncrack', 'room_show', 16, 'rps'].over(F['w']['rust', 'room_show', 16, 'rps'])
    rw = F['mix', 'oncrack', 'read'].over(F['mix', 'rust', 'read'], 'onCrack over Rust, room page reads/s while the room is written to')
    rwp = F['mix', 'oncrack', 'read'].over(F['mix', 'fsharp', 'read'], 'onCrack over the F# port, room page reads/s while the room is written to')
    pw = F['mix', 'oncrack', 'post'].over(F['mix', 'rust', 'post'], 'onCrack over Rust, posts/s into the read room')
    posts = F['mix', 'oncrack', 'post']
    posts_round = V(round(posts.v, -2), 'onCrack, posts a second into the read room, to the nearest hundred', posts.files, posts.how + ', rounded')
    return ('<section class="beat mix" id="mix" aria-labelledby="mix-h"><div class="wrap">'
            '<p class="kicker reveal">The honest version &middot; round one, pinned Rust <span data-lit="commit">ccece30</span></p><h2 id="mix-h" class="reveal">Cache hits, and the other end.</h2>'
            '<p class="line reveal">A stored page is only as good as the writes that don&#39;t touch it. So the same room page was read at %s connections while one more connection '
            'posted into that very room as fast as each app would take it: about %s posts a second, each one invalidating the page.</p>'
            '<div class="mx-grid reveal">'
            '<figure class="mx"><figcaption><span class="mx-big">%s</span><b>Rust, reads only</b><span>%s; every request a cache hit</span></figcaption><ol class="mx-bars">%s</ol></figure>'
            '<figure class="mx mx-real"><figcaption><span class="mx-big">%s</span><b>Rust, reads while the room is written to</b><span>%s the port &middot; its posts in the same window: %s Rust</span></figcaption><ol class="mx-bars">%s</ol></figure>'
            '</div><p class="cap reveal">Room page reads a second at %s connections, same scale in both. %s</p></div></section>'
            % (L.n(F['conc'][16]), L.n(posts_round), L.x(ro), code('bench/run'), bars(lambda a: F['w'][a, 'room_show', 16, 'rps'], 'ro'),
               L.x(rw), L.x(rwp), L.x(pw), bars(lambda a: F['mix', a, 'read'], 'rw'), L.n(F['conc'][16]), details('p-mix', 'How it was measured')))


def does_beat(F):
    tiles = [
        ('d-cache', 'Versioned read cache', 'A trigger bumps a counter inside the write&#39;s own transaction. A stored page is served only while every counter it was built under is unchanged.'),
        ('d-group', 'Group commit', 'Posts that arrive together share one transaction, a savepoint each, one commit. Every post is committed before it is answered.'),
        ('d-length', 'One send, not two', 'A cached gzip page goes out with its Content-Length instead of chunked, so it no longer needs a second send to end it.'),
        ('d-aot', 'Native AOT, opt-in', 'Starts in %s ms instead of %s, but serves less at %s connections, so the default stays JIT.'
         % (L.n(F['boot', 'aot-image', 'up_ms'], link=False), L.n(F['boot', 'jit-r2r-image', 'up_ms'], link=False), L.n(F['conc'][16], link=False))),
    ]
    th = ''.join('<a class="nt reveal" href="#%s" style="--i:%d"><b>%s</b><p>%s</p></a>' % (pid, i, t, d) for i, (pid, t, d) in enumerate(tiles))
    return ('<section class="beat does" id="does" aria-labelledby="does-h"><div class="wrap">'
            '<p class="kicker reveal">What onCrack does that Rust and the port don&#39;t</p><h2 id="does-h" class="reveal">Less work per request.</h2>'
            '<p class="line reveal">The HTML is byte for byte the port&#39;s and Rust&#39;s. What changed is how often it gets made, and how it goes out. Each idea states the rule that keeps it correct.</p>'
            '<div class="ntiles dtiles">%s</div><p class="links reveal">%s</p></div></section>' % (th, details('p-does', 'The four, with their rules and their numbers')))


# ---------------------------------------------------------------- the fan-out picture

def fan_scale(lead):
    for k in (10, 20, 50, 100, 200, 500, 1000, 2000):
        if lead / k <= 7:
            return k
    return 5000


def cable_verdict(n):
    """'ahead' when every onCrack rep of the three delivered more a second than every Rust rep, 'behind' when every one delivered less, else 'level'."""
    def reps_(app):
        return [next(c for c in jload(R42 + '/%s-%d.json' % (app, i))['cable'] if c['clients'] == n)['throughput']['delivered_msgs_per_sec'] for i in (1, 2, 3)]
    o, r = reps_('oncrack'), reps_('rust')
    return 'ahead' if min(o) > max(r) else ('behind' if max(o) < min(r) else 'level')


def fanout(F):
    """One message out to N clients, per app: pulses leave the hub at a rate in proportion to the app's measured messages a second (each pulse
    stands for k messages, the same k for every app at that N), and N clients light up as each pulse lands. CSS only; JS adds counters."""
    panes, tabs, radios = [], [], []
    for n in CABLE_COUNTS:
        lead = max(F['cable', a, n, 'msgs'].v for a in CABLE_APPS)
        k = fan_scale(lead)
        kv = V(k, 'messages per pulse in the fan-out picture at %s clients' % format(n, ','), ['site/build.py'],
               'fan_scale(): the smallest of 10, 20, 50, 100, 200, 500, 1000 that draws the fastest app at no more than 7 pulses a second')
        per_dot = 10 if n <= 1000 else 20
        dotv = V(per_dot, 'clients per dot in the fan-out picture', ['site/build.py'], 'fanout(): one dot per ten clients, per twenty above a thousand')
        dots = n // per_dot
        cols = {10: 5, 50: 10, 100: 10}[dots]
        rows_ = dots // cols
        lanes = []
        rust = F['cable', 'rust', n, 'msgs']
        for a in CABLE_APPS:
            m, fr = F['cable', a, n, 'msgs'], F['cable', a, n, 'frames']
            f = m.v / k                       # pulses a second
            K = 4
            P = K / f                         # seconds for one pulse to cross; K pulses in flight
            gx0, gx1, gy0, gy1 = 300, 392, 8, 52
            dx = (gx1 - gx0) / max(cols - 1, 1)
            dy = (gy1 - gy0) / max(rows_ - 1, 1)
            grid = ''.join('<circle cx="%.1f" cy="%.1f" r="%.1f"/>' % (gx0 + c * dx, gy0 + r * dy if rows_ > 1 else 30, 2.1 if dots <= 10 else 1.7)
                           for r in range(rows_) for c in range(cols))
            fan = ''.join('<line x1="250" y1="30" x2="%.1f" y2="%.1f"/>' % (gx0 - 4, gy0 + r * dy if rows_ > 1 else 30) for r in range(rows_))
            pulses = ''.join('<circle class="fan-p" r="4.5" cx="24" cy="30" style="animation-delay:%.3fs"/>' % (-P * i / K) for i in range(K))
            svg = ('<svg class="fan-svg" viewBox="0 0 400 60" aria-hidden="true" focusable="false" style="--p:%.3fs;--q:%.3fs">'
                   '<line class="fan-wire" x1="24" y1="30" x2="250" y2="30"/><g class="fan-lines">%s</g><g class="fan-grid">%s</g>'
                   '<circle class="fan-hub" cx="24" cy="30" r="9"/><g class="fan-ps">%s</g></svg>' % (P, P / K, fan, grid, pulses))
            if a == 'rust':
                rel = '<span class="fan-tag fan-lead">%s</span>' % ('leads' if m.v == lead else 'Rust')
            else:
                rel = '<span class="fan-tag%s">%s Rust</span>' % ('' if m.v >= rust.v else ' fan-behind', L.x(m.over(rust)))
            behind = '' if a == 'rust' or m.v >= rust.v else (
                '<span class="fan-live" data-gap="%.3f">falls behind Rust by <b class="fan-gap">%s</b> messages every second</span>'
                % (rust.v - m.v, L.n(rust.minus(m, 'Cable, %s clients: Rust minus %s, messages a second delivered to every client' % (format(n, ','), NAME[a])))))
            lanes.append('<li class="fan-lane fan-%s" data-rate="%.2f"><div class="fan-info"><p class="fan-name"><b>%s</b>%s</p>'
                         '<p class="fan-rate">%s <span>messages a second to all of them</span></p>'
                         '<p class="fan-sub">%s deliveries a second%s</p></div>%s</li>'
                         % (a, m.v, NAME[a], rel, L.n(m), L.n(fr), (' &middot; ' + behind) if behind else '', svg))
        radios.append('<input class="fan-r" type="radio" name="fan-n" id="fan-n%d"%s>' % (n, ' checked' if n == 1000 else ''))
        tabs.append('<label for="fan-n%d">%s clients</label>' % (n, L.n(F['clients'][n], link=False)))
        panes.append('<div class="fan-pane fan-p%d"><ol class="fan-lanes">%s</ol><p class="fan-key">Each dot is %s clients; each pulse is %s messages, '
                     'leaving at the app&#39;s measured rate.</p></div>'
                     % (n, ''.join(lanes), L.n(dotv), L.n(kv)))
    ratio = {n: F['cable', 'oncrack', n, 'msgs'].over(F['cable', 'rust', n, 'msgs']) for n in CABLE_COUNTS}
    # The copy below says: ahead at 100, 500 and 1,000 clients (every onCrack rep above every Rust rep) and level at 2,000 (the reps overlap). It refuses to build if the data says otherwise.
    verdict = {n: cable_verdict(n) for n in CABLE_COUNTS}
    if [verdict[n] for n in CABLE_COUNTS] != ['ahead', 'ahead', 'ahead', 'level']:
        raise SystemExit('build: the fan-out copy says onCrack is ahead at the three smaller counts and level at the largest; the data says %r: rewrite it' % verdict)
    return ('<section class="beat fanout" id="fanout" aria-labelledby="fan-h"><div class="wrap">'
            '<p class="kicker reveal">Fan-out</p><h2 id="fan-h" class="reveal">One message, a thousand clients.</h2>'
            '<p class="line reveal">A post goes out over Action Cable to everyone in the room. onCrack delivers %s Rust&#39;s messages a second at %s clients, '
            '%s at %s and %s at %s: ahead, with every rep of onCrack above every rep of Rust in the one quiet session of the three. At %s clients it is %s, <b>level, not ahead</b>: the reps overlap and both servers are bound by the <code>sendmsg</code> syscall. '
            'Every message reached every client in every one of the %s Cable phases of the final run.</p>'
            '<div class="fan reveal">%s<div class="fan-tabs" role="presentation">%s</div><div class="fan-panes">%s</div></div>'
            '<p class="links reveal">%s %s %s</p></div></section>'
            % (L.x(ratio[100]), L.n(F['clients'][100]), L.x(ratio[500]), L.n(F['clients'][500]), L.x(ratio[1000]), L.n(F['clients'][1000]),
               L.n(F['clients'][2000]), L.x(ratio[2000]), L.n(F['phases']), ''.join(radios), ''.join(tabs), ''.join(panes),
               details('p-fanout', 'How the fan-out was measured'), details('p-reliability', 'Under load, nobody is cut'), details('p-rust', 'What Rust still wins')))


def proof(F):
    lg = F['w']['oncrack', F['top_five'][2], F['top_five'][3], 'lg']
    kill = next(a for a in F['ver']['attacks'] if a['id'] == 'kill')
    VF = 'bench/results/oncrack-verifier/verifier.json'
    tiles = [
        ('p-correct', '%s' % L.n(F['ver_n'], link=False), 'attack tests, round one', 'Round one&#39;s verifier tried to break the caches: %s major bug and %s minor ones, each fixed, with the tests that hold them. Every later round had its own verifier; what each found and fixed is in the iterations panel.'
         % (L.n(F['findings']['major'], link=False), L.n(F['findings']['minor'], link=False))),
        ('p-durability', L.n(F['kill']['lost'], link=False), 'posts lost',
         'of %s acknowledged, with the server killed mid-run (the verifier, round one; round three&#39;s repeat, %s runs, lost %s too). Durability is Rails&#39;, by default.' % (L.n(F['kill']['acked'], link=False), L.n(F['kill_runs'], link=False), L.n(F['kill_lost'], link=False))),
        ('p-prod', L.n(F['relhi', 'oncrack', 'disconnected'], link=False), 'clients cut',
         'of %s, in the heaviest Cable profile, every round; Rust cut hundreds. What that costs is in the panel.' % L.n(F['rel_clients'], link=False)),
        ('p-pixels', '%s<i class="sl">/</i>%s' % (L.n(F['pp_total']['equal'], link=False), L.n(F['pp_total']['screenshots'], link=False)), 'screenshots',
         'pixel-equal to Rails on all %s seeds: the full gate, run on the final code.' % L.n(F['pp_seeds'], link=False)),
        ('p-ceiling', L.n(lg, D2, link=False), 'of %s cores' % L.n(F['ncores'], link=False),
         'the load generator used at onCrack&#39;s fastest workload, in round one&#39;s run. Not the rig&#39;s ceiling.'),
        ('p-repro', '<span class="pt-g" aria-hidden="true">$_</span>', 'Reproduce it', 'The commands, the seed, the CPU pinning and the image digests.'),
        ('p-ledger', '<span data-lit="count">__NROWS__</span>', 'numbers, each sourced', 'Every one, the file it came from and how it was worked out. The build fails without them.'),
    ]
    out = []
    for i, (pid, big, lab, desc) in enumerate(tiles):
        out.append('<a class="pt reveal" href="#%s" style="--i:%d">%s<b>%s</b><p>%s</p></a>'
                   % (pid, i, ('<span class="pt-n">%s</span>' % big) if big else '', lab, desc))
    return ('<section class="beat proof-row" id="check" aria-labelledby="check-h"><div class="wrap">'
            '<p class="kicker reveal">Check it</p><h2 id="check-h" class="reveal">Assume it&#39;s wrong.</h2>'
            '<p class="line reveal">Every claim above has a panel with the evidence, and every number links to its file.</p>'
            '<div class="ptiles">%s</div></div></section>' % ''.join(out))


def cta(F):
    pr = F['geo_port_rust', 16]
    return ('<section class="beat cta" id="port" aria-labelledby="port-h"><div class="wrap cta-grid">'
            '<div class="reveal"><p class="kicker">Where it came from</p><h2 id="port-h">Start with the port.</h2>'
            '<p class="line">onCrack is a fork. The F# port is the faithful one: the same work per request as the Rust port, translated module by module, '
            'and still %s Rust at %s connections in this session. If you want to read how Campfire works in F#, read that.</p></div>'
            '<p class="cta-links reveal"><a class="btn" href="%s">The F# port&#39;s page <span aria-hidden="true">&rarr;</span></a>'
            '<a class="btn btn-2" href="%s">Its repository <span aria-hidden="true">&rarr;</span></a></p>'
            '</div></section>' % (L.x(pr), L.n(F['conc'][16]), e(META['port_page']), e(META['port_repo'])))


# ================================================================ panels

def p_five(F):
    head = [('Workload', False), ('c', True), ('Rails', True), ('Rust', True), ('F# port', True), ('onCrack', True), ('onCrack / Rust', True), ('onCrack / port', True)]
    rows = []
    for r, rn in ROUTES:
        for c in (1, 16, 64):
            w = lambda a, m='rps': F['w'][a, r, c, m]
            cell = lambda a: '%s <small>(%s)</small>' % (L.n(w(a)), L.n(w(a, 'cpu'), D1))
            rows.append([rn, L.n(F['conc'][c]), cell('reference'), cell('rust'), cell('fsharp'), '<b>%s</b>' % cell('oncrack'),
                         '<b>%s</b> <small>CPU %s</small>' % (L.x(w('oncrack').over(w('rust'))), L.x(w('oncrack', 'cpu').over(w('rust', 'cpu')))),
                         '<b>%s</b> <small>CPU %s</small>' % (L.x(w('oncrack').over(w('fsharp'))), L.x(w('oncrack', 'cpu').over(w('fsharp', 'cpu'))))])
    geo_rows = [[L.n(F['conc'][c]), L.x(F['geo_rust', c]), L.x(F['geo_port', c]), L.x(F['geo_port_rust', c]), L.x(F['stored'][c])] for c in (1, 16, 64)]
    body = ''.join([
        '<p class="lead">Requests a second, median of %s reps, with the server&#39;s CPU µs per request in brackets (the container&#39;s cgroup, unprofiled). '
        'All four apps measured in the same session: signed in, keep-alive, gzip, the same seed, the server on CPUs %s and the load generator on %s.</p>'
        % (L.n(F['nreps']), e(F['srv_cpus']).replace('0-3', L.link(L.row(F['srv_cpus_v'].label, F['srv_cpus_v'].files, F['srv_cpus_v'].how, F['srv_cpus']), F['srv_cpus'])),
           L.link(L.row(F['lg_cpus_v'].label, F['lg_cpus_v'].files, F['lg_cpus_v'].how, F['lg_cpus']), F['lg_cpus'])),
        tbl(head, rows, 'The five workloads, all four apps, one session', 'dense'),
        '<h3>Geometric means of the five</h3>',
        tbl([('Connections', False), ('onCrack / Rust', True), ('onCrack / port', True), ('port / Rust', True), ('onCrack / stored Rust', True)], geo_rows),
        '<p>The last column divides by the <b>stored</b> Rust medians of <code>phase7-final</code>, the denominator the climb chart uses. It is not this session&#39;s Rust; it is there to show the two agree.</p>',
        '<ul class="caveats"><li><b>Read pages are cache hits here.</b> <code>bench/run</code> repeats one URL and never writes. <a href="#p-mix">The other end</a> has the room being written to.</li>'
        '<li><b>Every response</b> of every run was a <span data-lit="status">2xx</span> (%s responses, %s connection errors), rows written equal the answers in every post phase, and decoded bodies are byte-identical to Rust&#39;s (the round&#39;s review).</li></ul>'
        % (L.n(F['responses']), L.n(F['conn_errors'])),
        srcline(R1 + '/oncrack-1.json', R1 + '/rust-1.json', R1 + '/fsharp-1.json', R1 + '/reference-1.json', R1 + '/report.md', REVIEW + '/table.py', 'bench/results/oncrack-round1-final.md',
                lead='Sources (and the other reps beside each)'),
    ])
    return panel('p-five', 'Round one, same session', 'The five workloads', body, 'top')


def p_sbs(F, sp):
    w = lambda a, c: F['w'][a, 'room_show', c, 'rps']
    rows = [[L.n(F['conc'][c])] + [L.n(w(a, c)) for a in APPS] + [L.x(w('oncrack', c).over(w('rust', c)))] for c in (1, 16, 64)]
    thumbs = ''
    if sp:
        thumbs = ''.join('<figure><div class="sbs-frame"><img src="%s" width="640" height="400" loading="lazy" decoding="async" alt="The All Talk room as %s renders it."></div>'
                         '<figcaption><b>%s</b><span><code>%s</code></span><span>PNG <code>%s&hellip;</code></span></figcaption></figure>'
                         % (e(a['thumb']), e(a['name']), e(a['name']), e(a['source']), e(a['capture_sha256'][:12])) for a in sp['apps'])
    verdict = ('<p><b>Same pixels, checked.</b> The four PNGs are byte-identical (<span data-lit="name">SHA-256</span> <code>%s&hellip;</code>) and decode to the same pixels as the port&#39;s check recorded '
               '(<code>%s&hellip;</code>). The thumbnails are made one from each app&#39;s own capture and come out the same bytes, which <code>site/build.py</code> checks on every build '
               'before it shows the badge. The big screenshot is onCrack&#39;s own capture, lossless. In round one&#39;s gate this cell matched Rails on every layer the harness compares: %s.</p>'
               % (e(sp['apps'][0]['capture_sha256'][:16]), e((sp.get('pixels_sha256') or '')[:16]), e(', '.join(sp['round1_layers_equal'])))) if sp and sp.get('ok') else \
        '<p><b>The captures differ.</b> Compare the hashes under the thumbnails.</p>'
    body = ''.join([
        '<p class="lead">%s. Each picture is the parity harness&#39;s own capture of that page from one app: Chromium, %s, light scheme, the default seed with the clock frozen.</p>'
        % (e(sp['page']), e(sp['viewport']).replace('1440', L.n(V(1440, 'capture width, px', [R3PIX + '/pixel-parity.json'], 'the cell chromium-desktop-light'), link=True)).replace('900', L.n(V(900, 'capture height, px', [R3PIX + '/pixel-parity.json'], 'the cell chromium-desktop-light')))) if sp else '',
        '<div class="sbs-thumbs">%s</div>' % thumbs,
        verdict,
        srcline(R3PIX + '/pixel-parity.json', 'site/same_pixels.py', 'site/data.json'),
        '<h3>The counters</h3>',
        '<p>Each counter adds its engine&#39;s median requests a second for this page, for every second the section is on screen, and its row of dots moves in the same proportion. '
        'Without JavaScript, or with reduced motion, they show the rates and nothing moves.</p>',
        tbl([('Connections', False)] + [(NAME[a], True) for a in APPS] + [('onCrack / Rust', True)], rows, 'Room page, requests a second, median of the reps, one session'),
        '<p>onCrack&#39;s figures are cache hits: <a href="#p-mix">reads while writing</a> has the room page with the room being posted to.</p>',
        srcline(R1 + '/oncrack-1.json', R1 + '/report.md', lead='Source'),
    ])
    return panel('p-sbs', 'Same pixels, four engines', 'How we know', body, 'sbs')


def p_mix(F):
    rows = []
    for a in ('rust', 'fsharp', 'oncrack'):
        rows.append([NAME[a], L.n(F['mix', a, 'read']), L.n(F['mix', a, 'post']), '%s / %s' % (L.n(F['mix', a, 'p50'], D2), L.n(F['mix', a, 'p99'], D2)), L.n(F['mix', a, 'cpu'], D1)])
    rr = lambda m: F['mix', 'oncrack', m].over(F['mix', 'rust', m])
    rp = lambda m: F['mix', 'oncrack', m].over(F['mix', 'fsharp', m])
    rows.append(['onCrack / Rust', L.x(rr('read')), L.x(rr('post')), '', L.x(rr('cpu'))])
    rows.append(['onCrack / port', L.x(rp('read')), L.x(rp('post')), '', L.x(rp('cpu'))])
    ok = all(F['mix', a, 'ok'] for a in ('rust', 'fsharp', 'oncrack'))
    body = ''.join([
        '<p class="lead"><code>bench/run</code>&#39;s read workloads ask for one URL over and over and never write, so onCrack answers every request from a stored page. '
        'The table on the main page (%s Rust on the room page) is that best case. This is the other end.</p>' % L.x(F['w']['oncrack', 'room_show', 16, 'rps'].over(F['w']['rust', 'room_show', 16, 'rps'])),
        '<h3>How</h3><p><a href="%s"><code>review/mixed.sh</code></a>: %s connections read the room page while one connection posts into the same room as fast as the app answers. '
        'Every post moves the room&#39;s counter, so every post throws the stored page away. %s together as a warm-up, then a measured window; two runs per app, in opposite orders (%s runs in all).</p>'
        % (e(src_url(REVIEW + '/mixed.sh')), L.n(F['conc'][16]), lit('30 s', 'duration in mixed.sh'), L.n(F['mix_runs'])),
        tbl([('', False), ('Reads/s, ' + cN(16), True), ('Posts/s, ' + cN(1), True), ('Read %s / %s ms' % (P50, P99), True), ('CPU <span class="lc">µs</span>/req', True)], rows,
            'Reads and posts a second: mean of the two runs (latency: the first run)'),
        '<ul class="caveats">'
        '<li><b>Still mostly hits.</b> onCrack serves about %s reads for every change to the room, so this is a mix of stored pages and fresh renders, not the miss path alone.</li>'
        '<li><b>The miss path alone is the port&#39;s.</b> With <code>CAMPFIRE_READ_CACHE=off</code> the room page reads %s a second against %s on (%s, one rep, %s; '
        '<a href="#d-cache">the cache&#39;s numbers</a>), which is the port&#39;s speed: the cache adds no cost when it misses.</li>'
        '<li><b>Correct while it raced.</b> %s</li></ul>'
        % (L.n(F['mix_reads_per_change']), L.n(F['ab_cache']['off', 'room_show', 'rps']), L.n(F['ab_cache']['on', 'room_show', 'rps']), tier(2), cN(16),
           'Every response in every run was a <span data-lit="status">200</span>, and the rows written equal the posts answered (checked from the file on every build).' if ok else
           '<b>Not every run was clean: see the file.</b>'),
        srcline(REVIEW + '/mixed.jsonl', REVIEW + '/mixed.sh', 'bench/results/oncrack-round1-final.md'),
    ])
    return panel('p-mix', 'Reads while writing', 'The honest read/write mix', body, 'mix')


def p_does(F):
    ab = F['ab_cache']
    cache_rows = [[rn, L.n(ab['off', r, 'rps']), L.n(ab['on', r, 'rps']), L.x(ab['on', r, 'rps'].over(ab['off', r, 'rps'])), '%s &rarr; %s' % (L.n(ab['off', r, 'cpu'], D1), L.n(ab['on', r, 'cpu'], D1))]
                  for r, rn in ROUTES]
    d = F['dur']
    group_rows = [[L.n(F['conc'][c]), L.n(d['off', c, 'rps']), L.n(d['on', c, 'rps']), L.x(d['on', c, 'rps'].over(d['off', c, 'rps'])), '%s &rarr; %s' % (L.n(d['off', c, 'cpu'], D1), L.n(d['on', c, 'cpu'], D1))]
                  for c in (1, 16, 64)]
    al = F['ab_len']
    len_rows = [[rn, L.n(al['off', r, 16, 'rps']), L.n(al['on', r, 16, 'rps']), L.x(al['on', r, 16, 'rps'].over(al['off', r, 16, 'rps'])), L.x(al['on', r, 1, 'rps'].over(al['off', r, 1, 'rps']))]
                for r, rn in ROUTES]
    deps = tbl([('Page', False), ('Depends on', False)], [
        ['room page, messages page', 'the global counter (under which its user was read), the user, the room'],
        ['sidebar, search', 'the global counter, the user, every room the user is in'],
        ['the session (authentication)', 'the sessions counter'],
        ['the signed-in user', 'the global counter'],
    ], 'What each stored page depends on')
    marks = tbl([('A write to', False), ('Bumps', False)], [
        ['messages', 'its room'], ['boosts; a message&#39;s rich text and attachments', 'the message&#39;s room (global if the message is gone)'],
        ['rooms', 'the room; created or destroyed: the room and global'], ['memberships', 'added or removed: the room and the user; updated: the user'],
        ['searches, push subscriptions', 'the user'], ['sessions', 'sessions'],
        ['accounts, users, bans, webhooks, blobs, variants, other rich text', 'global'], ['the search index (no triggers possible)', 'the message&#39;s room, by the job that writes it'],
    ], 'The triggers (TEMP, on the writer&#39;s connection only, so the database file keeps Rails&#39; schema)')
    body = ''.join([
        '<p class="lead">Four changes, measured one at a time against the build without them. The HTML a browser gets is unchanged (its decoded bytes equal Rust&#39;s on every probed route), '
        'and each change has a switch that turns it off.</p>',
        '<h3 id="d-cache">The versioned read cache</h3>',
        '<p>A global counter, one per room, one per user and one for sessions. Triggers bump them <b>inside the write&#39;s transaction</b>. Room counters are striped: ids equal modulo %s share one, so a URL '
        'naming rooms that don&#39;t exist can&#39;t grow memory (the verifier&#39;s finding).</p>' % L.n(F['stripes']),
        marks, deps,
        '<p class="rule"><b>The invalidation rule.</b> The first bump of a counter in a write makes it odd, before the row changes; the write&#39;s end (after the commit and its after-commit work, '
        'before the caller hears back) makes it even, one past. A request takes its counters before its first query, keeps the page only if all were even and are unchanged when it finishes, '
        'and a stored page is served only while every counter still equals what it was kept under. So nothing is served across a committed change, and a writer always reads its own write.</p>',
        '<p><b>Never shared across users:</b> the key starts with the user&#39;s id, then everything the render reads from the request (route, full URL, host, Turbo-Frame, Referer, User-Agent, '
        'the <code>last_room</code> cookie). A request with a flash message is not cached. The store is bounded at %s MB in two generations. <code>CAMPFIRE_READ_CACHE=off</code> turns it off.</p>' % L.n(F['cache_mb']),
        tbl([('Workload, ' + cN(16), False), ('Cache off', True), ('Cache on', True), ('On / off', True), ('CPU <span class="lc">µs</span>/req', True)], cache_rows, '%s: the same build with the cache off and on, one rep each' % tier(2).replace('>tier', '>Tier')),
        srcline('bench/results/oncrack-c1.md', 'bench/results/oncrack-c1/t2-cache-off/oncrack-1.json', 'bench/results/oncrack-c1/t2-cache-on/oncrack-1.json', 'bench/results/oncrack-fixes.md', lead='Sources'),
        '<h3 id="d-group">Group commit</h3>',
        '<p>The single writer takes every write already queued (up to %s) and runs them in one transaction, <b>a savepoint each</b>, with one <code>COMMIT</code>; then the group&#39;s after-commit '
        'work in one more transaction; then the cache counters are released; then every caller is answered, in queue order. It never waits for a group to fill (the window is %s µs), so at one '
        'connection every group is one write.</p>' % (L.n(F['group_max']), L.n(F['window_default'])),
        '<p class="rule"><b>The durability rule.</b> Every post is committed before its response is written: WAL with <code>synchronous=normal</code>, Rails&#39; own setting. A write that fails rolls '
        'back to its savepoint alone; anything that breaks the group&#39;s transaction leaves nothing committed and the group runs again write by write. Broadcasts go out in commit order.</p>',
        tbl([('Connections', False), ('Group commit off', True), ('On', True), ('On / off', True), ('CPU <span class="lc">µs</span>/req', True)], group_rows, '%s, posting: one write per transaction against grouped, one rep each' % tier(2).replace('>tier', '>Tier')),
        srcline('bench/results/oncrack-c2.md', 'bench/results/oncrack-c2/t2-group-off/oncrack-1.json', 'bench/results/oncrack-c2/t2-group-on/oncrack-1.json', lead='Sources'),
        '<h3 id="d-length">Content-Length on cached gzip answers</h3>',
        '<p>The port copies Rack::Deflater and sends gzip chunked, which costs a second send for the terminating chunk. For a gzipped buffer or a stored page onCrack makes the gzip member before the '
        'headers, sends its length and writes it once. Streams, files and pages rendered in parts stay chunked. <code>CAMPFIRE_GZIP_LENGTH=off</code> restores chunking. On a search at %s, '
        'syscalls per request fell from %s to %s.</p>' % (cN(16), L.n(F['syscalls'], D1), L.n(F['syscalls_after'], D1)),
        tbl([('Workload', False), (cN(16) + ' chunked', True), (cN(16) + ' length', True), (cN(16) + ' gain', True), (cN(1) + ' gain', True)], len_rows, '%s: the same build with the setting off and on, one rep each' % tier(2).replace('>tier', '>Tier')),
        srcline('bench/results/oncrack-c3.md', 'bench/results/oncrack-c3/t2-length-off/oncrack-1.json', 'bench/results/oncrack-c3/t2-length-on/oncrack-1.json', lead='Sources'),
        '<h3 id="d-aot">Native AOT, as an opt-in</h3>',
        '<p><code>docker build --build-arg NATIVE_AOT=true</code> makes <code>campfire-oncrack:aot</code>. It starts in %s ms against the default image&#39;s %s, idles at %s MB against %s, and passes the pixel gate '
        '(%s screenshots, the fast matrix on the default seed). But without tiered PGO it serves %s of the default image at %s connections (%s at one), and it loses <span data-lit="name">HTTP/2</span> without TLS. '
        'The headline is throughput at %s connections, so <b>the default stays JIT + ReadyToRun</b>.</p>'
        % (L.n(F['boot', 'aot-image', 'up_ms']), L.n(F['boot', 'jit-r2r-image', 'up_ms']), L.n(F['boot', 'aot-image', 'idle_mb']), L.n(F['boot', 'jit-r2r-image', 'idle_mb']),
           L.n(F['aot_pp']), L.x(F['aot_geo', 16]), L.n(F['conc'][16]), L.x(F['aot_geo', 1]), L.n(F['conc'][16])),
        srcline('bench/results/oncrack-c4.md', 'bench/results/oncrack-c4/boot.jsonl', 'bench/results/oncrack-c4/tier3-aot/oncrack-1.json', 'bench/results/oncrack-c3/tier3/oncrack-1.json', lead='Sources'),
    ])
    return panel('p-does', 'What onCrack does that Rust and the port don&#39;t', 'Four changes, four rules', body, 'does')


def p_correct(F):
    vj = F['ver']
    VF = 'bench/results/oncrack-verifier/verifier.json'
    VD = 'bench/results/oncrack-verifier/'
    rows = []
    for a in vj['attacks']:
        nums = []
        for k, val in a['numbers'].items():
            vals = val if isinstance(val, list) else [val]
            shown = ', '.join(L.n(V(float(x.replace(',', '')), 'verifier, %s: %s' % (a['id'], k.replace('_', ' ')), [VF], 'attacks[%s].numbers.%s, quoted from the report' % (a['id'], k))) for x in vals)
            nums.append('%s %s' % (k.replace('_', ' '), shown))
        res = {'held': '<span class="res res-ok">held</span>', 'found': '<span class="res res-bad">found a %s bug</span>' % a['finding']}[a['result']]
        logs = ' '.join(flink(VD + a[k], a[k].split('/')[-1]) for k in ('log', 'control', 'script') if a.get(k))
        how = e(a['how']) if not re.search(r'\d', a['how']) else L.link(L.row('verifier, %s: how the test was run' % a['id'], [VF], 'attacks[%s].how' % a['id'], a['how']), a['how'])
        rows.append(['<span data-lit="test">%s</span>' % e(a['id']), lits(a['target']), how,
                     res + ('<small>%s</small>' % '; '.join(nums) if nums else ''), logs])
    findings = vj['report']['findings']
    major = findings[0]
    body = ''.join([
        '<p class="lead">Before the round was scored, a separate reviewer was told to break units %s: stale pages, one user&#39;s data in another&#39;s page, lost or reordered posts, '
        'unbounded memory. It wrote %s attack tests: %s held, and %s found problems, which came down to %s major bug and %s minor ones. Every finding was fixed with a test that fails without the fix.</p>'
        % (lit('C1-C3'), L.n(F['ver_n']), L.n(F['ver_held']), L.n(F['ver_found']), L.n(F['findings']['major']), L.n(F['findings']['minor'])),
        tbl([('Test', False), ('What it attacks', False), ('How', False), ('Result', False), ('Log', False)], rows, 'Every attack test the verifier ran', 'dense'),
        '<h3>The major bug: a stale user row</h3>',
        '<p><b>What:</b> authentication read the signed-in user before the page took its counters. A change to that user committing in between was rendered from the old row and stored under the '
        'new counters, then served until an unrelated write moved one: the name in the room page&#39;s meta tag and composer, the sidebar&#39;s name and avatar, and the administrator-only New Chat Room button.</p>',
        '<p><b>Found by</b> %s, %s and %s, each making %s changes while %s other browsers read the page: %s and %s stale room pages in two runs, %s stale sidebars, %s sidebars showing the wrong role. '
        'With the cache off, all three found %s.</p>' % (lit('A1', 'test'), lit('A1b', 'test'), lit('A1c', 'test'),
            L.n(V(1500, 'verifier, A1: checks', [VF], 'attacks[A1].numbers.checks, quoted from the report')), L.n(F['a1_readers']),
            L.n(V(93, 'verifier, A1: stale', [VF], 'attacks[A1].numbers.stale')), L.n(V(75, 'verifier, A1: stale', [VF], 'attacks[A1].numbers.stale')),
            L.n(V(50, 'verifier, A1b: stale', [VF], 'attacks[A1b].numbers.stale')), L.n(V(79, 'verifier, A1c: stale', [VF], 'attacks[A1c].numbers.stale')), L.n(F['cache_off_found'])),
        '<p class="rule"><b>The fix and its rule:</b> a page&#39;s global dependency is now the global counter&#39;s value <i>the user was read under</i>, not one taken when the action starts. '
        'A page whose user changed since is neither kept nor served; a page whose user was not read through the cache is rendered but not kept. Three tests in '
        '<code>ReadCacheTests</code> make %s changes while %s browsers read; before the fix each failed, after it all pass twice in a row, and also with the cache off.</p>'
        % (L.n(F['fix_changes']), L.n(F['fix_readers'])),
        '<h3>The minor ones</h3><ul class="caveats">'
        '<li><b>A counter for every room id in a URL</b> (%s): fixed by striping room counters modulo %s, at most a %s array per database.</li>'
        '<li><b>Group commit broadcast concurrent posts out of commit order</b> (%s), more often than the port: fixed with a line of places taken in commit order; now all %s posts of the test '
        'arrive with %s out-of-order pairs, group commit on and off.</li>'
        '<li><b><code>bin/kit-differential http</code> failed by default</b> because of the added Content-Length: it now accepts exactly the gzip member&#39;s length and nothing else, with a self-test.</li></ul>'
        % (lit('A2', 'test'), L.n(F['stripes']), lit('512 KB', 'size written in oncrack-fixes.md'), lit('A5', 'test'), L.n(F['fix_posts']), L.n(F['fix_inversions'])),
        '<h3>Gates</h3><p>Before the fixes the verifier also ran <code>bin/verify</code>, <code>bin/db-differential</code>, <code>bin/kit-differential</code> and the full pixel gate; after them '
        '<code>bin/verify</code> ran %s tests with %s failed. The verifier&#39;s report is kept verbatim beside its tests.</p>' % (L.n(F['verify_after']), L.n(F['fix_failed'])),
        srcline(VF, VD + 'AttackTests.fs', VD + 'killtest.py', VD + 'logs/session-results.log', 'bench/results/oncrack-fixes.md', lead='Sources'),
    ])
    del major
    return panel('p-correct', 'Correctness evidence', 'Every attack, and what it found', body, 'check')


def p_durability(F):
    vj = F['ver']
    VF = 'bench/results/oncrack-verifier/verifier.json'
    K = F['kill']
    d = F['dur']
    rows = [['<code>CAMPFIRE_GROUP_COMMIT</code>', 'on', 'Grouped writes, a savepoint each, one commit. Every post commits before it is answered.', 'off: one write per transaction, the port&#39;s writer'],
            ['<code>CAMPFIRE_GROUP_COMMIT_WINDOW_US</code>', L.n(F['window_default']), 'The writer never waits for a group to fill.', 'a wait only adds latency; durability is the same'],
            ['<code>journal_mode</code>, <code>synchronous</code>', 'wal, normal', 'Rails&#39; own settings, unchanged.', 'nothing weaker exists to turn on'],
            ['<code>synchronous=full</code>', 'not built', 'Stronger than Rails: an fsync per commit, which group commit could share.', 'not built or measured']]
    w_rows = [[L.n(F['conc'][c]), L.n(d['off', c, 'rps']), L.n(d['on', c, 'rps']), L.n(d['w200', c, 'rps'])] for c in (1, 16, 64)]
    body = ''.join([
        '<p class="lead"><b>onCrack ships Rails&#39; durability and nothing weaker.</b> The plan allowed weaker settings only behind a switch whose default is Rails&#39;; none was needed. '
        'Group commit shares the commit, not the durability: Rails&#39; <code>synchronous=normal</code> already doesn&#39;t fsync per commit, so there was no per-post sync to share.</p>',
        tbl([('Setting', False), ('Default', False), ('What it does', False), ('The other way', False)], rows, 'Default against the alternatives'),
        '<h3>Killed mid-write</h3>',
        '<p>The verifier posted from %s threads with the default settings, killed the container with SIGKILL mid-run, restarted it on the same storage and looked for every post that had been answered <span data-lit="status">200</span>. '
        '%s runs: %s acknowledged posts, %s lost, %s duplicated, %s missing from the search index, and the newest acknowledged post was on the room page after the restart. A few posts per run were stored '
        'but never acknowledged: committed, killed before the answer went out, which is the order the rule promises.</p>'
        % (L.n(F['kill_threads']), L.n(K['runs']), L.n(K['acked']), L.n(K['lost']), L.n(K['dup']), L.n(K['unindexed'])),
        '<h3>Measured both ways</h3>',
        tbl([('Connections', False), ('Group commit off', True), ('On (the default)', True), ('On, window of %s µs (not kept)' % L.n(F['window_tried']), True)], w_rows,
            'Posts a second, %s, one rep each, same build' % tier(2)),
        '<p>A commit window costs the single connection its whole wait per post and gains nothing at %s or %s connections, where the queue already fills groups, so it stays at %s.</p>'
        % (L.n(F['conc'][16]), L.n(F['conc'][64]), L.n(F['window_default'])),
        srcline(VF, 'bench/results/oncrack-verifier/killtest.py', 'bench/results/oncrack-c2.md', 'bench/results/oncrack-c2/t2-group-off/oncrack-1.json', 'bench/results/oncrack-c2/t2-group-on/oncrack-1.json',
                'bench/results/oncrack-c2/t2-window200/oncrack-1.json', lead='Sources'),
    ])
    return panel('p-durability', 'Durability', 'Rails&#39; default, and nothing weaker', body, 'check')


def p_pixels(F):
    pp = F['pp']
    rows = [[e(s), L.n(v['equal']), L.n(v['screenshots']), L.n(v['different']), L.n(v['not_captured']), L.n(v['flaky']),
             ', '.join('%s %s' % (k, L.n(x)) for k, x in v['engines'].items())] for s, v in pp.items()]
    t = F['pp_total']
    rows.append(['<b>all</b>', '<b>%s</b>' % L.n(t['equal']), '<b>%s</b>' % L.n(t['screenshots']), L.n(t['different']), L.n(t['not_captured']), L.n(t['flaky']), ''])
    body = ''.join([
        '<p class="lead">The rule onCrack works under: every parity screen&#39;s pixels must match Rails&#39;. The server&#39;s HTML, the live DOM and Cable frames may differ; what a person sees may not.</p>',
        tbl([('Seed', False), ('Equal', True), ('Screenshots', True), ('Different', True), ('Not captured', True), ('Flaky', True), ('By engine', False)], rows, 'The full gate on the final code, per seed'),
        '<h3>How it was run</h3><ul class="caveats">'
        '<li><code>bin/pixel-parity</code> against the Rails reference, the harness&#39;s lean matrix: every state on Chromium (desktop and phone, light and dark), the smoke states on Firefox and WebKit, '
        'and the breakpoint sweep, on all %s seeds, on the image <code>campfire-oncrack:app</code> built from a clean worktree at the final commit (<span data-lit="commit">ee5a2e9</span>). <code>src/</code> is the code the verifier closed on: nothing in it changed after the gate.</li>'
        '<li>This is the <b>full</b> gate on the <b>final</b> code. Round three ran the full gate on its own final code (%s screenshots); the %s more here are Chromium cells of <code>search/results/order</code>, the state round three added after that gate to tell the two search orders apart.</li>'
        '<li>The default seed ran in twelve slices so each fit one call; the slices partition its states, and <code>pixel_parity.py</code> checks that no cell ran in two of them. '
        'A cell counts by its last attempt that captured it, as <code>bin/pixel-parity</code> counts it. The room page capture is byte-identical on both sides and equals round one&#39;s.</li></ul>'
        % (L.n(F['pp_seeds']), L.n(F['pp3_total']), L.n(F['pp_total']['screenshots'].minus(F['pp3_total'], 'screenshots added to the full gate since round three'))),
        '<h3>Three harness faults, none a pixel difference</h3><ul class="caveats">'
        '<li><code>auth/sign_in/error</code> was not captured in three attempts (the harness waits %s s for stylesheets on a freshly started server, as in rounds one and three); a fourth run of that state alone captured all four cells, all equal.</li>'
        '<li>The harness crashed %s cells into <code>realtime/**</code> (<code>Response has been disposed</code>, an unhandled rejection in its network capture), and one re-run sat for %s minutes with the VM idle; both passed when run again in smaller slices with a watchdog.</li>'
        '<li>No clean first-pass gate was obtained, and the Mac&#39;s %s GiB free-space floor was breached several times by another project&#39;s Go build cache; the results file says so in full. Nothing in <code>src/</code> or the harness was changed for any of it.</li></ul>'
        % (L.n(md(R5F + '/pixels.md', r"the harness's (\d+) s wait for stylesheets", 'the harness\'s wait for stylesheets on freshly started servers, seconds')),
           L.n(md(R5F + '/pixels.md', r'crashed (\d+) of \d+ cells in', 'cells of realtime/** captured before the harness crashed')),
           L.n(md(R5F + '/pixels.md', r'sat (\d+) minutes at \d+ of \d+ cells', 'minutes one compare sat idle')),
           L.n(md(R5F + '/pixels.md', r'under the (\d+) GiB floor', 'the Mac\'s free-space floor, GiB'))),
        '<p>The reports themselves (every screenshot and diff) are gitignored under <code>parity/out/pixel-parity-r5-final/</code>; <code>pixel_parity.py</code> keeps what they say. The page&#39;s build reads its <code>pixel-parity.json</code>.</p>',
        srcline(R3PIX + '/pixel-parity.json', R3PIX + '/pixel_parity.py', R5F + '/pixels.md', 'bench/results/oncrack-r3-pixels/pixel-parity.json', 'bin/pixel-parity', 'bin/pixel-parity-report', lead='Sources'),
    ])
    return panel('p-pixels', 'Pixel parity', 'Every screenshot, per seed', body, 'claim-prod')


def p_ceiling(F):
    rows = []
    cells = [('oncrack', r, 64) for r, _ in ROUTES] + [(F['top_any'][1], F['top_any'][2], F['top_any'][3])]
    for a, r, c in cells:
        w = lambda m: F['w'][a, r, c, m]
        rows.append(['%s, %s' % (NAME[a], RNAME[r]), L.n(F['conc'][c]), L.n(w('rps')), L.n(w('srv'), D2), L.n(w('lg'), D2), L.n(w('lgcpu'), D1)])
    top = F['top_five']
    lgv = F['w']['oncrack', top[2], top[3], 'lg']
    head = F['ncores'].minus(lgv, 'load generator cores idle at onCrack\'s fastest workload cell')
    m = F['manual']
    hand = []
    for a in ('rust', 'oncrack'):
        for r, c in (('room_show', 16), ('post_message', 16)):
            x = m.get((a, r, c))
            if x:
                hand.append(['%s, %s' % (NAME[a], RNAME[r]), L.n(F['conc'][c]), L.n(x['rps_loadgen']), L.n(x['n_loadgen']), L.n(x['server_log_lines']), L.n(x['rows_written']), L.n(x['errors'])])
    body = ''.join([
        '<p class="lead">A fast server can be under-measured by a slow client. The load generator runs on its own %s cores, and the session recorded how busy they were in every window.</p>'
        % L.n(F['ncores']),
        tbl([('Cell', False), ('c', True), ('Req/s', True), ('Server cores busy', True), ('Load generator cores busy', True), ('Load generator <span class="lc">µs</span>/req', True)], rows,
            'onCrack&#39;s workloads at %s connections, and the fastest cell of the whole session' % L.n(F['conc'][64])),
        '<ul class="caveats">'
        '<li><b>At onCrack&#39;s fastest workload cell</b> the load generator used %s of its %s cores, leaving %s idle, while the server used %s of its %s: the server is the one at its limit.</li>'
        '<li><b>The rig went faster in the same session:</b> the same load generator drove %s requests a second at the %s, %s onCrack&#39;s fastest workload cell. So the workload numbers are not the rig&#39;s ceiling.</li>'
        '<li><b>The host stayed quiet:</b> after each of the %s measured windows a probe timed a fixed spin on the pinned CPUs; the worst was %s its baseline.</li>'
        '<li><b>Not measured:</b> a second load generator, or a client on another machine. The VM has %s CPUs, split evenly, so neither side can be given more without taking from the other.</li></ul>'
        % (L.n(lgv, D2), L.n(F['ncores']), L.n(head, D1), L.n(F['w']['oncrack', top[2], top[3], 'srv'], D2), L.n(F['ncores']),
           L.n(F['w'][F['top_any'][1], F['top_any'][2], F['top_any'][3], 'rps']), RNAME[F['top_any'][2]] + ' (%s, %s connections)' % (NAME[F['top_any'][1]], L.n(F['conc'][F['top_any'][3]])),
           L.x(F['w'][F['top_any'][1], F['top_any'][2], F['top_any'][3], 'rps'].over(F['w']['oncrack', top[2], top[3], 'rps'])),
           L.n(F['windows']), L.n(F['probe_max'], X), L.n(V(8, 'CPUs in the VM', [R1 + '/env.txt'], 'env.txt: "8 threads"'))),
        '<h3>Counted twice</h3><p>A hand run outside <code>bench/run</code> (<code>review/manual.sh</code>) counted requests three ways: the load generator, the server&#39;s own request log, and rows in the database.</p>',
        tbl([('Run', False), ('c', True), ('Req/s', True), ('Load generator count', True), ('Server log lines', True), ('Rows written', True), ('Errors', True)], hand,
            'Fixed warm-up, then a window; onCrack&#39;s log lines trail by its batched log&#39;s last flush'),
        srcline(R1 + '/oncrack-1.json', R1 + '/env.txt', REVIEW + '/manual-oncrack.jsonl', REVIEW + '/manual-rust.jsonl', REVIEW + '/manual.sh', 'bench/lib/cpurun.py', lead='Sources'),
    ])
    return panel('p-ceiling', 'Measurement ceiling', 'Is the load generator the limit?', body, 'check')


def p_rust(F):
    w = F['w']
    r = lambda a, b: a.over(b)
    postcpu = lambda unit: V(next(x for x in jlines('bench/results/oncrack-log.jsonl') if x.get('unit') == unit)['workloads']['post_message']['c16']['cpu_us'],
                             'the climb suite, post a message, c=16, server CPU us per request, %s' % unit, ['bench/results/oncrack-log.jsonl'], 'workloads.post_message.c16.cpu_us of the %s row' % unit)
    p3, p5 = postcpu('r3-final-fresh'), postcpu('r5-final-fresh')
    rows = [
        ['CPU per request, one connection, room page (round one)', L.n(w['rust', 'room_show', 1, 'cpu'], D1), L.n(w['oncrack', 'room_show', 1, 'cpu'], D1), L.x(r(w['oncrack', 'room_show', 1, 'cpu'], w['rust', 'room_show', 1, 'cpu'])),
         'Level: a cached hit is cheap, the rest is the thread pool spinning between requests (the port&#39;s behaviour).'],
        ['CPU per request, one connection, post (round one)', L.n(w['rust', 'post_message', 1, 'cpu'], D1), L.n(w['oncrack', 'post_message', 1, 'cpu'], D1), L.x(r(w['oncrack', 'post_message', 1, 'cpu'], w['rust', 'post_message', 1, 'cpu'])),
         'Same spinning; at one connection a group is one write.'],
        ['CPU per request, CSS file, ' + cN(16) + ' (round one)', L.n(w['rust', 'static_css', 16, 'cpu'], D1), L.n(w['oncrack', 'static_css', 16, 'cpu'], D1), L.x(r(w['oncrack', 'static_css', 16, 'cpu'], w['rust', 'static_css', 16, 'cpu'])),
         'Static files are the port&#39;s; onCrack still serves more of them.'],
        ['idle memory, MB (round one)', L.n(F['idle', 'rust']), L.n(F['idle', 'oncrack']), L.x(r(F['idle', 'oncrack'], F['idle', 'rust'])), 'The .NET runtime.'],
        ['peak anon memory over the run, MB (round one)', L.n(F['anon', 'rust']), L.n(F['anon', 'oncrack']), L.x(r(F['anon', 'oncrack'], F['anon', 'rust'])), 'GC heaps plus the page store.'],
        ['Cable, %s clients saturated, Pss MB' % L.n(F['clients'][1000]), L.n(F['cable', 'rust', 1000, 'pss']), L.n(F['cable', 'oncrack', 1000, 'pss']), L.x(r(F['cable', 'oncrack', 1000, 'pss'], F['cable', 'rust', 1000, 'pss'])),
         'The .NET runtime and the heap the posts leave behind; the same ratio at every size from %s to %s clients. Rust here is upstream %s.' % (L.n(F['clients'][100]), L.n(F['clients'][2000]), lit('f9dca47', 'commit'))],
        ['Cable, %s clients, <span data-lit="name">PR #6</span> cable_heavy, peak Pss MB' % L.n(F['rel_clients']), L.n(F['rel', 'rust', 'cable_heavy', 'pss']), L.n(F['rel', 'oncrack', 'cable_heavy', 'pss']), L.x(r(F['rel', 'oncrack', 'cable_heavy', 'pss'], F['rel', 'rust', 'cable_heavy', 'pss'])),
         'The price of keeping every client: what the slowest has not read stays in memory, up to the hub&#39;s budget.'],
        ['Cable, %s clients, paced post to the last client, %s ms (lower is better)' % (L.n(F['clients'][100]), P50), L.n(F['cable', 'rust', 100, 'p50'], D1), L.n(F['cable', 'oncrack', 100, 'p50'], D1), L.x(r(F['cable', 'oncrack', 100, 'p50'], F['cable', 'rust', 100, 'p50'])),
         'Rust is faster here. Not investigated.'],
        ['Cable, %s clients saturated, messages a second to every client (higher is better)' % L.n(F['clients'][2000]), L.n(F['cable', 'rust', 2000, 'msgs']), L.n(F['cable', 'oncrack', 2000, 'msgs']), L.x(r(F['cable', 'oncrack', 2000, 'msgs'], F['cable', 'rust', 2000, 'msgs'])),
         'Level: the reps overlap, and both servers are bound by <code>sendmsg</code>. Do not read it as a win.'],
        ['Posts taken a second, cable_heavy (higher is better)', L.n(F['relposts', 'rust']), L.n(F['relposts', 'oncrack']), L.x(r(F['relposts', 'oncrack'], F['relposts', 'rust'])),
         'The other side of nobody being cut: the gate slows the posters.'],
        ['cold start, ms (round one)', L.n(F['cold', 'rust']), L.n(F['cold', 'oncrack']), L.x(r(F['cold', 'oncrack'], F['cold', 'rust'])),
         'The JIT. The opt-in AOT image starts in %s ms.' % L.n(F['boot', 'aot-image', 'up_ms'])],
    ]
    body = ''.join([
        '<p class="lead">onCrack is ahead of Rust at the median in every workload of the final run&#39;s harness, and ahead on throughput at the three smaller Cable sizes. Here is everything it is not ahead on, or where the lead has a price.</p>',
        tbl([('', False), ('Rust', True), ('onCrack', True), ('onCrack / Rust', True), ('Why', False)], rows, 'Medians of the reps: the final run where marked, round one&#39;s session for the rows marked round one', 'dense'),
        '<p><b>The post path costs more CPU than it did.</b> On this project&#39;s own suite a post cost %s &micro;s of server CPU in round three&#39;s final image and %s in the final one (fresh, %s over). '
        'Two post-only cross-checks do not settle it, and rounds four and five touched the post path; the cause is not found and may be the host&#39;s disk, which the post path leans on most.</p>'
        % (L.n(p3, D1), L.n(p5, D1), L.x(r(p5, p3))),
        '<p>Also open, from the final report: the harness headline has no quiet repeat; C&#39;s Cable server did not take most of the clients and was not investigated; &ldquo;no lost messages&rdquo; is statistical, with a deterministic test (Linux only) behind it; '
        'and the Linux Cable suite passed %s of %s tests in the gate, with a timing test that may still flake.</p>' % (L.n(F['lcable', 'succeeded']), L.n(F['lcable', 'total'])),
        srcline(R1 + '/rust-1.json', R1 + '/oncrack-1.json', 'bench/results/oncrack-c4/boot.jsonl', 'bench/results/oncrack-round1-final.md', R42 + '/rust-1.json', R42 + '/oncrack-1.json', REL_SESSION + '/summary.json', 'bench/results/oncrack-log.jsonl', R5REPORT, lead='Sources'),
    ])
    return panel('p-rust', 'What Rust still wins', 'Not ahead on these', body, 'fanout')


def p_reliability(F):
    """PR #6's reliability profiles (bin/reliability, cable and cable_heavy): the final run, three rounds for every app."""
    head = [('App', False), ('Subscribed', True), ('Disconnected', True), ('Delivered to every client', True), ('Posted', True), ('Messages a second', True), (P99 + ' ms', True), ('Pss MB', True)]

    def cell(v, fmt=I):
        return L.n(v, fmt) if v is not None else '&ndash;'

    def rows(profile):
        out = []
        for key, _, _ in REL_APPS:
            g_ = lambda f: F['rel', key, profile, f]
            out.append([REL_NAME[key], cell(g_('ready')), cell(g_('disconnected')), cell(g_('complete')), cell(g_('posted')), cell(g_('msgs'), D1), cell(g_('p99'), I), cell(g_('pss'))])
        return out
    pol = tbl([('cable_heavy', False), ('Posts a second taken', True), ('Slowest round', True), ('Fastest round', True), ('Clients cut', True), ('Pss MB', True)],
              [[REL_NAME[k], L.n(F['relposts', k]), L.n(F['relposts_lo', k]), L.n(F['relposts_hi', k]), L.n(F['rel', k, 'cable_heavy', 'disconnected']), L.n(F['rel', k, 'cable_heavy', 'pss'])]
               for k in ('oncrack', 'oncrack-cached', 'rust', 'c', 'reference')],
              'Two policies for a reader that cannot keep up: cut it, or slow the posters (the harness&#39;s own posts-a-second count, each round)')
    body = ''.join([
        '<p class="lead">Upstream&#39;s <code>bin/reliability</code> (<span data-lit="name">PR #6</span>) opens %s signed-in Action Cable clients, each with the room&#39;s subscriptions, and posts into the busy room. '
        '<b>cable_heavy</b> posts from %s closed-loop posters with no limit, then waits up to a minute for every client to have every message; <b>cable</b> posts from %s. '
        '&ldquo;Disconnected&rdquo; counts clients the server closed mid-run. The harness&#39;s clients do not reconnect, so a closed client misses everything after. '
        '<b>%s rounds for every app</b>, in one harness process, medians shown; the rounds themselves are in the ledger.</p>' % (
            L.n(F['rel_clients']), L.n(F['rel_posters']), L.n(F['rel_posters_light']), L.n(F['rel_rounds'])),
        tbl(head, rows('cable_heavy'), 'cable_heavy: posters with no limit'),
        tbl(head, rows('cable'), 'cable: the default posting load'),
        '<h3>A difference of policy, not a free win</h3>',
        '<p>Action Cable never cuts a client for being slow: whatever the socket will not take waits in a queue of that connection&#39;s own, with no bound, which is what Rails&#39; memory above is; '
        'its posters are slow enough that the queues stay short. Rust and onCrack before the shared log post far faster than they can send to a thousand clients, ran past a ring of a few hundred frames, and closed the clients that fell behind: '
        'the harness counts them as disconnected and they miss everything after. onCrack now keeps what the slowest client has not read once, in a log its clients share, '
        'cuts a client only when the log it pins passes a byte budget or its socket takes no byte for half a minute, and makes a post wait (at most two seconds) while most of a room is seconds behind. '
        'So it takes fewer posts than the cutting servers do, and delivers every one of them to every client. A browser that is cut reconnects and fetches what it missed.</p>',
        pol,
        '<p>What this costs: a %s&ndash;%s s %s from a post to the slowest client (Rust&#39;s is under half a second, but it has cut most of its clients), and memory of about a gigabyte, %s&ndash;%s MB against Rust&#39;s %s&ndash;%s, bounded by a %s GiB budget for all of the hub&#39;s logs together.</p>'
        % (L.n(V(F['rello', 'oncrack', 'p99'].v / 1000, 'onCrack, cable_heavy, p99 seconds from a post to the last client, lowest of 3 rounds', F['rello', 'oncrack', 'p99'].files, F['rello', 'oncrack', 'p99'].how + ' / 1000'), '{:.0f}'),
           L.n(V(F['relhi', 'oncrack', 'p99'].v / 1000, 'onCrack, cable_heavy, p99 seconds from a post to the last client, highest of 3 rounds', F['relhi', 'oncrack', 'p99'].files, F['relhi', 'oncrack', 'p99'].how + ' / 1000'), '{:.0f}'), P99,
           L.n(F['rello', 'oncrack', 'pss'], '{:,.0f}'), L.n(F['relhi', 'oncrack', 'pss'], '{:,.0f}'), L.n(F['rello', 'rust', 'pss'], '{:,.0f}'), L.n(F['relhi', 'rust', 'pss'], '{:,.0f}'), L.n(F['hub_gib'])),
        '<p>The control row, onCrack before the shared log, is the same image as it stood before round four&#39;s change, built from its own commit: it reproduces round four&#39;s finding in a new session (%s&ndash;%s clients cut in cable_heavy), so the result is the change and not the host.</p>'
        % (L.n(F['rello', 'oncrack-before', 'disconnected']), L.n(F['relhi', 'oncrack-before', 'disconnected'])),
        '<h3>Overload, the other profile</h3>', p_overload(),
        '<p>The F# port cannot take the overload profile, so only its Cable profiles ran: its contract preparation stops at the search order (the port keeps Rails&#39; order; upstream&#39;s contract wants message id order). '
        'In its cable_heavy rounds it closed clients in two of the three and ended with posts undelivered.</p>',
        '<h3>Read with care</h3><ul class="caveats">'
        '<li><b>C&#39;s Cable server did not take most of the clients in this setup</b>, in either profile (its subscribed count is well under the %s), so its row says only that: its disconnected count also counts clients closed while still connecting, and it says nothing about cutting slow clients. Not investigated.</li>'
        '<li><b>One disturbance.</b> The Mac&#39;s disk guard stopped the session&#39;s wrapper once, in Rust&#39;s second overload round, and not the harness, which ran on; nothing was dropped or re-run, and the wrapper now stops the harness too (the results file has the minute-by-minute).</li>'
        '<li><b>The host was not noisy for this session</b> (under the plan&#39;s line), unlike round four&#39;s, which was stopped half-way.</li></ul>' % L.n(F['rel_clients']),
        srcline(REL_SESSION + '/summary.json', REL_PORT + '/summary.json', REL_SESSION + '/run.log', R5F + '/reliability/RESULTS.md', 'bench/reliability/run', 'bench/reliability/summarize', 'bench/results/oncrack-r4-reliability.md', R5REPORT, lead='Sources (the harness output, the memory samples and the run logs sit beside them)'),
    ])
    return panel('p-reliability', 'Evidence for claim two', 'Nobody is cut for being slow', body, 'claim-prod')


def p_overload():
    """Overload: 64 and 256 clients on four read routes, median of three rounds, from the harness's own output."""
    out = []
    for conc in (64, 256):
        rows = []
        for key, app, directory in REL_APPS:
            if key == 'fsharp':
                continue
            cells, bad = [], 0
            for r, _ in ROUTES[:4]:
                vals, files = [], []
                for i in (1, 2, 3):
                    f = directory + '/harness-output/%s-%d.json' % (app, i)
                    files.append(f)
                    for x in jload(f)['overload']:
                        if x['route'] == r and x['conc'] == conc:
                            vals.append(x['rps'])
                            bad += x.get('errors', 0) + x.get('invalid_responses', 0)
                cells.append(L.n(V(statistics.median(vals), '%s, %s, overload profile, %d clients, req/s, median of 3 rounds (reliability/main)' % (REL_NAME[key], RNAME[r], conc), files,
                                   'median of ' + ', '.join(g(float(x)) for x in vals) + ' (overload[route=%s, conc=%d].rps)' % (r, conc))))
            cells.append(L.n(V(bad, '%s, overload profile, %d clients: errors and invalid responses over 3 rounds, four routes' % (REL_NAME[key], conc), [directory + '/harness-output/%s-%d.json' % (app, i) for i in (1, 2, 3)],
                               'sum of overload[].errors + invalid_responses')))
            rows.append([REL_NAME[key]] + cells)
        out.append(tbl([('Implementation', False)] + [(rn[0].upper() + rn[1:], True) for _, rn in ROUTES[:4]] + [('Errors or invalid', True)], rows, 'Median requests/sec at %s clients, eight seconds a route, three rounds' % L.n(V(conc, 'overload profile clients', [REL_SESSION + '/summary.json'], 'bin/reliability overload: 64 and 256 clients'))))
    return ''.join(out)


def _miss(field):
    ph = next(x for x in jload(R42 + '/oncrack-1.json')['cable'] if x['clients'] == 500)
    return V(ph['throughput'][field], 'onCrack, Cable, 500 clients, rep 1 of the final session, saturated phase: messages %s' % ('every client received' if field == 'complete' else 'posted'),
             [R42 + '/oncrack-1.json'], 'cable[clients=500].throughput.%s' % field)


def p_fanout(F):
    head = [('Clients', False)] + [(NAME[a] + (' ' + lit('f9dca47', 'commit') if a == 'rust' else ''), True) for a in CABLE_APPS] + [('onCrack / Rust', True)]
    rows_m = [[L.n(F['clients'][n])] + [L.n(F['cable', a, n, 'msgs'], D1 if F['cable', a, n, 'msgs'].v < 100 else I) for a in CABLE_APPS] + [L.x(F['cable', 'oncrack', n, 'msgs'].over(F['cable', 'rust', n, 'msgs']))] for n in CABLE_COUNTS]
    rows_f = [[L.n(F['clients'][n])] + [L.n(F['cable', a, n, 'frames']) for a in CABLE_APPS] + [L.x(F['cable', 'oncrack', n, 'frames'].over(F['cable', 'rust', n, 'frames']))] for n in CABLE_COUNTS]
    rows_l = [[L.n(F['clients'][n])] + [L.n(F['cable', a, n, 'p50'], D1) for a in CABLE_APPS] + [L.x(F['cable', 'oncrack', n, 'p50'].over(F['cable', 'rust', n, 'p50']))] for n in CABLE_COUNTS]
    rows_p = [[L.n(F['clients'][n])] + [L.n(F['cable', a, n, 'pss'], I) for a in CABLE_APPS] + [L.x(F['cable', 'oncrack', n, 'pss'].over(F['cable', 'rust', n, 'pss']))] for n in CABLE_COUNTS]
    reps_ = []
    for n in CABLE_COUNTS:
        cells = []
        for a in ('rust', 'oncrack'):
            vals = [next(c for c in jload(R42 + '/%s-%d.json' % (a, i))['cable'] if c['clients'] == n)['throughput']['delivered_msgs_per_sec'] for i in (1, 2, 3)]
            cells.append(' &middot; '.join(L.n(V(v, '%s, Cable, %d clients, messages a second delivered to every client, rep %d' % (NAME[a], n, i + 1), [R42 + '/%s-%d.json' % (a, i + 1)],
                                                  'cable[clients=%d].throughput.delivered_msgs_per_sec' % n)) for i, v in enumerate(vals)))
        reps_.append([L.n(F['clients'][n])] + cells + ['<b>%s</b>' % cable_verdict(n)])
    sess = tbl([('Session', False), ('What happened', False), ('Host samples at a core and a half or more, %', True)],
               [['one', 'Complete except Rust&#39;s third rep (the harness read a memory file at the instant the sampler renamed it); not pooled, re-run', L.n(md(R5REPORT, r'\| 1 \(`cable/session-1-incomplete/`\)[^|]*\|[^|]*\|\s*(\d+)%', 'Cable suite session 1: host samples at 150% or more, %'))],
                ['two', 'All reps complete; the sends pass stopped by the disk guard and finished in a continuation; not pooled, re-run', L.n(md(R5REPORT, r'\| 2 \(`cable/session-2/`\)[^|]*\|[^|]*\|\s*(\d+)%', 'Cable suite session 2: host samples at 150% or more, %'))],
                ['<b>three</b>', '<b>All parts, one uninterrupted session: the headline</b>', L.n(md(R5REPORT, r'\| \*\*3 \(`cable/session-3/`\)\*\*[^|]*\|[^|]*\|\s*\*\*(\d+)%\*\*', 'Cable suite session 3: host samples at 150% or more, %'))]],
               'Three sessions were run; only the quiet one is the headline')
    body = ''.join([
        '<p class="lead"><code>bench/run</code>&#39;s Cable suite: N signed-in clients each hold a WebSocket with the room&#39;s subscriptions, and four posters post into the room, '
        'never more than %s messages ahead of what every client has received. A message counts when the last client has it. The clients are one epoll-driven program with no WebSocket library '
        '(<code>bench/loadgen/src/rawcable.rs</code>), so it is the server that runs out of cores, not the load generator. Three reps, one uninterrupted session, a fresh container for every part, '
        'Rust being upstream&#39;s image. Rails was not run in it, and Cable numbers from before this client are not comparable.</p>' % L.n(F['window']),
        tbl(head, rows_m, 'Messages a second delivered to every client (median of the reps)'),
        tbl([('Clients', False), ('Rust, the three reps', True), ('onCrack, the three reps', True), ('Reading', False)], reps_, 'The reps, in run order: ahead means every onCrack rep is above every Rust rep'),
        tbl(head, rows_f, 'Deliveries a second: messages times clients, as frames on the wire'),
        tbl(head, rows_l, 'Paced: one message at a time, %s ms until the last client has it (onCrack over Rust below one is faster)' % P50),
        tbl(head, rows_p, 'Memory: peak total Pss of the app while saturated, MB'),
        '<h3>Where Rust is faster, and where it ties</h3>'
        '<p>At %s clients the two are level on throughput and both are bound by the <code>sendmsg</code> syscall, which took three quarters of the server&#39;s CPU in the profile; no default changed, because the one setting that helped there cost the smaller sizes. '
        'Rust is clearly faster in paced latency at %s clients (%s against %s ms, %s), and its memory is under half of onCrack&#39;s at every size (onCrack&#39;s saturated Pss is %s to %s of Rust&#39;s).</p>'
        % (L.n(F['clients'][2000]), L.n(F['clients'][100]), L.n(F['cable', 'rust', 100, 'p50'], D1), L.n(F['cable', 'oncrack', 100, 'p50'], D1), L.x(F['cable', 'oncrack', 100, 'p50'].over(F['cable', 'rust', 100, 'p50'])),
           L.x(min((F['cable', 'oncrack', n, 'pss'].over(F['cable', 'rust', n, 'pss']) for n in CABLE_COUNTS), key=lambda v: v.v)), L.x(max((F['cable', 'oncrack', n, 'pss'].over(F['cable', 'rust', n, 'pss']) for n in CABLE_COUNTS), key=lambda v: v.v))),
        '<h3>Every message arrived</h3><p>In every Cable phase of the three sessions (%s phases: three apps, four sizes, saturated and paced, the sends passes included) every posted message reached every client, nobody was closed mid-run, and no frame was odd. '
        'Round four had one phase in which a message of %s did not reach every client; its cause was the server (a payload moved under the kernel by a collection, because the gather pinned only the last payload of a batch), it was fixed with a test that fails on the old code, and it has not recurred in %s target phases since. '
        '<b>%s phases flagged</b> by the rule of <code>cable/phases.py</code>, which this page&#39;s build runs on every build and refuses to publish if it flags one.</p>'
        % (L.n(F['phases']), L.n(F['hist', 'r4msg', 'posted']), L.n(md(R5REPORT, r'(\d+) target phases after the fix lost or corrupted nothing', 'phases after the lost-frame fix that lost or corrupted nothing')), L.n(F['phases_bad'])),
        sess,
        '<h3>How the picture is drawn</h3><p>Each lane sends pulses from its hub at a rate in proportion to its measured messages a second; at a given N one pulse stands for the same number of '
        'messages in every lane, and each dot for ten clients. The pulses are CSS animations, so they run without JavaScript; with JavaScript each lane also counts what it has delivered '
        'since you opened the page, and how far behind Rust that leaves it. With reduced motion nothing moves and the rates are what you read.</p>',
        srcline(R42 + '/oncrack-1.json', R42 + '/rust-1.json', R42 + '/fsharp-1.json', R5F + '/cable/RESULTS.md', R5F + '/cable/phases.py', 'bench/loadgen/src/rawcable.rs', R5REPORT, lead='Sources (and the other reps beside each)'),
    ])
    return panel('p-fanout', 'Cable fan-out', 'One message to N clients', body, 'fanout')


def p_repro(F):
    env = text(R1 + '/env.txt')
    imgs = re.findall(r'^(\w+) image: (\S+) (sha256:[0-9a-f]{64})', env, re.M)
    rows = [[e(NAME.get(a, a)), code(name), '<code>%s</code>' % L.link(L.row('image digest, %s' % a, [R1 + '/env.txt'], 'env.txt "%s image:" line' % a, dg), dg)] for a, name, dg in imgs]
    cmds = ("CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build     # then bin/clean-docker from macOS\n"
            "R=bench/results/oncrack-round1-final/review\n"
            "$R/quiet.sh && $R/part.sh reference 1 'room_show messages_page'   # ... sidebar search | avatar static_css up | post_message\n"
            "$R/quiet.sh && $R/part.sh oncrack 1 'post_message' 'http cable upload'   # each rep's last part\n"
            "bench/report bench/results/oncrack-round1-final > bench/results/oncrack-round1-final/report.md\n"
            "python3 bench/results/oncrack-round1-final/review/table.py\n"
            "$R/manual.sh rust; $R/manual.sh oncrack; $R/mixed.sh rust|fsharp|oncrack; $R/bytes.sh\n"
            "bin/pixel-parity --seeds crowd,custom_styles,first_run,restricted\n"
            "bin/pixel-parity --seeds default --only 'realtime/**'   # ... twelve slices (SLICES in pixel_parity.py)\n"
            "python3 bench/results/oncrack-r3-pixels/pixel_parity.py\n"
            "python3 site/same_pixels.py && python3 site/build.py")
    sched = re.search(r'^schedule: (.+)$', env, re.M).group(1)
    env5 = text(R5F + '/env.txt')
    imgs5 = re.findall(r'^((?:campfire-[\w-]+|rust):[\w.-]+) ([0-9a-f]{12})$', env5, re.M)
    rows5 = [[code(name), '<code>%s</code>' % L.link(L.row('image id, %s' % name, [R5F + '/env.txt'], 'env.txt line "%s"' % name, idv), idv)] for name, idv in imgs5]
    cmds5 = ("# the final run (round five), plan fixed first: bench/results/oncrack-r5-final/PLAN.md\n"
             "CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build        # in the clean measured worktree, then bin/clean-docker and bin/clean-parity\n"
             "colima ssh -- bash -c \"$PWD/bench/results/oncrack-r5-final/scripts/pixel-gate.sh\"   # the full gate, every seed; then:\n"
             "python3 bench/results/oncrack-r5-final/pixels/pixel_parity.py\n"
             "CAMPFIRE_REQUIRE_SEED=1 bin/verify; bin/linux-tests Cable\n"
             "bench/run --apps rust,fsharp,oncrack --suites cable --clients 100 500 1000 2000 --reps 3\n"
             "bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 \\\n"
             "  --apps rails,rust,c,fsharp,oncrack,oncrack-cached --routes room_show,messages_page,sidebar,search,post_message   # mixed: four reads and --mixed-write-rate 10\n"
             "bench/reliability/run OUT --apps oncrack --profiles cable --rounds 3        # PR #6; summarize with bench/reliability/summarize\n"
             "python3 bench/results/oncrack-r5-final/pool.py                              # pooled.md: every round of every session of a profile\n"
             "python3 site/build.py                                                      # the page, or a refusal")
    body = ''.join([
        '<h3>The final run</h3><p>Everything below the page&#39;s headline ran from this plan, with every session&#39;s host load sampled every ten seconds and each session&#39;s noise judged by a rule written before it. '
        'Run from the repository root on branch <code>crack</code>, inside the colima VM where the harness needs Linux.</p>',
        '<pre class="code">%s</pre>' % e(cmds5),
        tbl([('Image', False), ('Id', False)], rows5, 'Images of the final run (from its env.txt; the harness&#39;s own summaries carry the same ids for all six apps)'),
        srcline(R5F + '/PLAN.md', R5F + '/env.txt', R5F + '/RUNLOG.md', R5F + '/RESULTS.md', lead='The final run'),
        '<h3>Round one&#39;s commands</h3>',
        '<p class="lead">Everything runs inside the colima VM (<code>colima ssh -- bash -c "cd $PWD &amp;&amp; ..."</code>), from the repository root, on branch <code>crack</code>. '
        'Each app&#39;s rep runs in parts, one container per part, merged into the rep&#39;s file, so every part fits one call. Order: Rails, Rust, the port, onCrack in reps one and three, reversed in rep two.</p>',
        '<pre class="code">%s</pre>' % e(cmds),
        '<h3>Fixed</h3><ul class="caveats">'
        '<li><b>Seed:</b> <code>parity/.seed/default</code>, copied fresh for every run; signed in as David.</li>'
        '<li><b>CPU pinning:</b> the server on CPUs %s, the load generator on %s, host networking (<code>SERVER_CPUS</code>, <code>LOADGEN_CPUS</code>).</li>'
        '<li><b>Schedule:</b> <code>%s</code>.</li>'
        '<li><b>Warm-up:</b> every route at its measured concurrency until flat (<code>bench/lib/warmup.py</code>); the VM&#39;s load waited down before every part (<code>review/quiet.sh</code>).</li>'
        '<li><b>Durability:</b> the defaults. No setting that weakens it was used.</li></ul>'
        % (L.link(L.row(F['srv_cpus_v'].label, F['srv_cpus_v'].files, F['srv_cpus_v'].how, F['srv_cpus']), F['srv_cpus']),
           L.link(L.row(F['lg_cpus_v'].label, F['lg_cpus_v'].files, F['lg_cpus_v'].how, F['lg_cpus']), F['lg_cpus']), e(sched)),
        tbl([('App', False), ('Image', False), ('Digest', False)], rows, 'Images measured (from the session&#39;s env.txt)'),
        srcline(R1 + '/env.txt', 'bench/results/oncrack-round1-final.md', REVIEW + '/part.sh', REVIEW + '/quiet.sh', 'AGENTS.md', lead='Sources'),
    ])
    return panel('p-repro', 'Reproduce it', 'The commands', body, 'check')


def p_ledger():
    rows = []
    for r in L.rows:
        files = ' '.join(flink(f, f.replace('bench/results/', '')) for f in r['files'])
        rows.append('<li id="%s"><span class="lg-id">%s</span><b class="lg-v">%s</b><span class="lg-l">%s</span><small class="lg-h">%s</small><span class="lg-f">%s</span></li>'
                    % (r['id'], r['id'], e(r['shown']), e(r['label']), e(r['how']), files))
    body = ('<p class="lead">Every number on the page, in order of first appearance, with the file it was computed from and how. <code>site/build.py</code> computes each one from these files '
            'when it builds the page, and refuses to build if anything a reader can see has a digit in it and no row here. %s rows.</p>'
            '<ol class="ledger">%s</ol>' % ('<span data-lit="count">%d</span>' % len(L.rows), ''.join(rows)))
    return panel('p-ledger', 'Every number', 'The ledger', '<div data-ledger>%s</div>' % body, 'check')


def p_fresh(F):
    def rng(t, a, r):
        return '%s <span class="rng">[%s&ndash;%s]</span>' % (L.n(t[a, r, 'median']), L.n(t[a, r, 'min']), L.n(t[a, r, 'max']))
    names = {'oncrack': 'onCrack (fresh, default)', 'oncrack-cached': 'onCrack, cached decision (opt-in)'}
    nm = lambda a: names.get(a) or upname(a)
    normal = tbl([('Implementation', False)] + [(rn, True) for _, rn in ROUTES], [[nm(a)] + [rng(F['up3'], a, r) for r, _ in ROUTES] for a in R3APPS],
                 'Normal profile, %s sessions pooled: median [observed min&ndash;max] of %s rounds, requests/sec at %s clients' % (L.n(F['sess_n']), L.n(F['up3_rounds']), L.n(F['up_conc'])))
    mixed = tbl([('Implementation', False)] + [(RNAME[r], True) for r in UPREADS], [[nm(a)] + [rng(F['up3m'], a, r) for r in UPREADS] for a in R3APPS],
                'Mixed profile, %s sessions pooled: median [observed min&ndash;max] of %s rounds, reads/sec at %s clients while one writer posts up to %s messages/s into HQ' % (L.n(F['sess_n']), L.n(F['up3_rounds']), L.n(F['up_conc']), L.n(F['up_rate'])))
    ratios = tbl([('Over', False), ('onCrack, five workloads', True), ('onCrack, four mixed reads', True), ('cached decision, five workloads', True), ('cached decision, four mixed reads', True)],
                 [[upname(b), L.x(F['up3_geo', 'oncrack', b]), L.x(F['up3m_geo', 'oncrack', b]), L.x(F['up3_geo', 'oncrack-cached', b]), L.x(F['up3m_geo', 'oncrack-cached', b])] for b in ('rust', 'c', 'fsharp')],
                 'Geometric means of the pooled medians')
    sess_rows = []
    for i, d in enumerate(R3N + R3M):
        name = d.split('/')[-1]
        prof = 'normal' if name.startswith('normal') else 'mixed'
        k = int(name.split('-')[1]) - 1
        n = F['noise'][name]
        sess_rows.append([lit(name), L.n(n['pct']), '<b>NOISY</b>' if n['noisy'] else 'ok', L.x(F['sess', prof, 'rust'][k]), L.x(F['sess', prof, 'c'][k])])
    spread = tbl([('Session', False), ('Host samples at a core and a half or more, %', True), ('The plan&#39;s noise rule', False), ('onCrack / Rust', True), ('onCrack / C', True)], sess_rows,
                 'Each session on its own: the geometric mean of its three rounds&#39; medians')
    cpu = tbl([('Server CPU per request, &micro;s', False), ('Room page', True), ('Mixed reads', True), ('Post', True), ('Room page, quiet host', True), ('Mixed, quiet', True), ('Post, quiet', True)],
              [[nm(a)] + [L.n(F['cpu3', a, ph], D1) for ph in ('room_show', 'mixed', 'post_message')] + [L.n(F['cpuq', a, ph], D1) for ph in ('room_show', 'mixed', 'post_message')] for a in ('oncrack', 'oncrack-cached', 'rust', 'c')],
              'Hand re-runs (a warm-up, then a timed window at the same clients, CPU from the container&#39;s cgroup): medians of all seven sets, and of the three whose host was not noisy')
    cpuratio = tbl([('Server CPU per request, over onCrack&#39;s', False), ('Room page', True), ('Mixed reads', True), ('Post', True), ('Room page, quiet host', True)],
                   [[upname(b)] + [L.x(F['cpu3', b, ph].over(F['cpu3', 'oncrack', ph])) for ph in ('room_show', 'mixed', 'post_message')] + [L.x(F['cpuq', b, 'room_show'].over(F['cpuq', 'oncrack', 'room_show']))] for b in ('rust', 'c')],
                   'Rust&#39;s and C&#39;s CPU per request as a multiple of onCrack&#39;s')
    val = tbl([('Final run', False), ('Timed responses validated', True), ('Writes audited', True), ('Errors or invalid', True), ('Raw samples reconciled', True), ('Peak generator CPU, %', True)],
              [['Normal and mixed, all six sessions', L.n(F['r3_val']['timed']), L.n(F['r3_val']['writes']), L.n(F['r3_val']['bad']), L.n(F['r3_val']['samples']), L.n(F['r3_val']['gen'], D1)]])
    kloc = tbl([('Implementation', False), ('Application KLOC', True)], [[upname(a)] + [L.n(F['kloc', a], D1)] for a in ('rails', 'rust', 'c', 'fsharp', 'oncrack')],
               '<code>cloc 2.10</code>, upstream&#39;s rules (backend code and executable template code; tests, vendored code, generated files, static data and tooling left out). Counted from the revisions under test; Rust&#39;s and C&#39;s land within one percent of upstream&#39;s own published figures')
    body = ''.join([
        '<p class="lead">Upstream&#39;s contract re-reads the session and the room membership on every cache hit; until round three onCrack kept the decision its first request made and dropped it on any commit. '
        'Now, by default, every request reads its session and user rows, a kept room or messages page is served after a membership query finds the row, and the front server&#39;s replay first runs one narrow query '
        'for the session, its user and the membership. A room page hit costs %s the CPU of the cached decision on a quiet host: <code>CAMPFIRE_FRESH_AUTH=0</code> keeps the cached decision as an opt-in.</p>'
        % L.x(F['cpuq', 'oncrack', 'room_show'].over(F['cpuq', 'oncrack-cached', 'room_show'])),
        '<h3>The headline, and the range behind it</h3>', normal, mixed, ratios, spread,
        '<p>The plan, fixed before any session ran, pools every round of every session of a profile and drops none. It re-runs a session once when more than a quarter of its host samples show other work at a core and a half or more. '
        '%s of the %s sessions were over that line (other projects&#39; Erlang VMs, Go test binaries and Python workers on the same Mac), so the pooled figure carries them, and each profile spent its whole budget of three sessions. '
        'The noise is not symmetric: onCrack&#39;s reads need about two and a half of the four client cores for a hundred and sixty thousand requests a second, so other work on those cores lowers them more than it lowers Rust&#39;s or C&#39;s, and its post path (the disk) fell tenfold under another project&#39;s fsyncs. '
        'The first two sessions of each profile, the design the plan started from, read %s over Rust and %s over C (normal), %s and %s (mixed): inside the range, not a different answer. '
        '<b>Quote the range, and the CPU per request, which is the steadier number.</b></p>'
        % (L.n(F['noisy_n']), L.n(F['sess_total']), L.x(F['sub2', 'normal', 'rust']), L.x(F['sub2', 'normal', 'c']), L.x(F['sub2', 'mixed', 'rust']), L.x(F['sub2', 'mixed', 'c'])),
        '<h3>CPU per request</h3>', cpu, cpuratio,
        '<p>Round four read Rust at %s and C at %s of onCrack&#39;s CPU on a room page. Why they moved was not tested: the HTTP path&#39;s source did not change between the two rounds, and the quiet sets of round four read lower for Rust and C than this round&#39;s do, which fits a quieter afternoon.</p>'
        % (L.x(F['hist', 'r4', 'cpu_rust']), L.x(F['hist', 'r4', 'cpu_c'])),
        '<h3>What was validated</h3>', val,
        '<h3>Size</h3>', kloc,
        '<p>onCrack is %s larger than the port (the caches, the writer, the Cable log and its bounds, the fresh-check pool) and %s of Rust&#39;s; both F# counts include a first-party port of the <code>html5ever</code> tokenizer that Rust takes as a vendored crate.</p>'
        % (L.n(F['kloc', 'oncrack'].minus(F['kloc', 'fsharp'], 'onCrack minus the F# port, application KLOC'), D1) + ' KLOC', L.x(F['kloc', 'oncrack'].over(F['kloc', 'rust']))),
        '<h3>Read with care</h3><ul class="caveats">'
        '<li><b>No quiet repeat of the headline.</b> The two sessions that passed the noise rule read %s and %s over Rust (normal and mixed), so a quiet host did not make the figure steadier here. A reading nobody can dispute needs a Mac with nothing else on it.</li>'
        '<li><b>The fresh-over-cached ratio is not a result.</b> The two share an image and differ by one lookup; in the pooled tables they read %s and %s, in the hand re-runs level (%s on a room page). The cells swing several-fold inside a session.</li>'
        '<li><b>Not their machine.</b> Four of this VM&#39;s CPUs per side, not the Ryzen&#39;s; compare ratios, not absolute numbers, with their report. Rust and C are upstream&#39;s own images.</li>'
        '<li><b>One normal session was set aside whole</b> (it ran the harness&#39;s default eight routes by mistake): kept in full beside the others, not pooled; it shows onCrack ahead on the three extra routes too.</li></ul>'
        % (L.x(F['sess', 'normal', 'rust'][0]), L.x(F['sess', 'mixed', 'rust'][0]),
           L.x(F['up3_geo', 'oncrack', 'oncrack-cached']), L.x(F['up3m_geo', 'oncrack', 'oncrack-cached']),
           L.x(F['cpu3', 'oncrack', 'room_show'].over(F['cpu3', 'oncrack-cached', 'room_show']))),
        srcline(R5REPORT, R5F + '/RESULTS.md', R5F + '/pooled.md', R5F + '/pooled-subsets.md', R5F + '/totals.md', R5F + '/session-noise.txt', R5F + '/PLAN.md', R5F + '/review-quiet-sets.md', R5F + '/review.jsonl', R5F + '/kloc/kloc.json', lead='Sources'),
    ])
    return panel('p-fresh', 'Evidence for claim one', 'Fresh authorization, against Rust, C and the port', body, 'claim-fast')


def up3_at(base, session, app, route):
    """One normal session's median for one app and route at c=16 (base: the final run's directory, round three's or round four's)."""
    files = sorted(os.path.relpath(f, REPO) for f in glob.glob(os.path.join(REPO, base, session, app + '-[0-9].json')))
    vals = [x['rps'] for f in files for x in jload(f)['http'] if x['route'] == route and x['conc'] == 16]
    return V(statistics.median(vals), '%s, %s, c=16, req/s, median of %d rounds (verification harness, %s/%s)' % (UPBASE[app], RNAME[route], len(vals), base.split('/')[-1], session), files,
             'median of ' + ', '.join(g(float(x)) for x in vals))


def up3_pool(base, sessions, app, route):
    """Several normal sessions pooled, as the plan of that run pooled them: the median over all their rounds."""
    files = sorted(os.path.relpath(f, REPO) for ss in sessions for f in glob.glob(os.path.join(REPO, base, ss, app + '-[0-9].json')))
    vals = [x['rps'] for f in files for x in jload(f)['http'] if x['route'] == route and x['conc'] == 16]
    return V(statistics.median(vals), '%s, %s, c=16, req/s, median of %d rounds (verification harness, %s, %s pooled)' % (UPBASE[app], RNAME[route], len(vals), base.split('/')[-1], ' and '.join(sessions)), files,
             'median of ' + ', '.join(g(float(x)) for x in vals))


def r3_old_cpu(app, phase):
    """Round three's hand re-runs: the median server CPU per request of an app in a phase (bench/results/oncrack-r3-final/review.jsonl)."""
    rv = [json.loads(l) for l in open(os.path.join(REPO, R3_OLD, 'review.jsonl')) if '"window"' in l]
    xs = [d['server_cpu_us_per_req'] for d in rv if d['app'] == app and d['phase'] == phase and ('cached' in d['tag']) == (app == 'oncrack-cached')]
    return V(statistics.median(xs), '%s, server CPU us per request, %s, median of %d hand re-runs of round three (review.py)' % (UPBASE[app], phase, len(xs)), [R3_OLD + '/review.jsonl'], 'median of ' + ', '.join('%.1f' % x for x in xs))


def p_upstream(F):
    def rng(t, a, r):
        return '%s <span class="rng">[%s&ndash;%s]</span>' % (L.n(t[a, r, 'median']), L.n(t[a, r, 'min']), L.n(t[a, r, 'max']))
    head = [('Implementation', False)] + [(rn, True) for _, rn in ROUTES]
    normal = tbl(head, [[upname(a)] + [rng(F['up'], a, r) for r, _ in ROUTES] for a in UPAPPS], 'Normal profile: median [observed min&ndash;max] requests/sec at %s clients' % L.n(F['up_conc']))
    mixed = tbl([('Implementation', False)] + [(RNAME[r], True) for r in UPREADS], [[upname(a)] + [rng(F['upm'], a, r) for r in UPREADS] for a in UPAPPS],
                'Mixed profile: reads/sec at %s clients while one writer posts up to %s messages/s into HQ (reads on Watercooler)' % (L.n(F['up_conc']), L.n(F['up_rate'])))
    ratios = tbl([('onCrack over', False), ('Five workloads', True), ('Four mixed reads', True)],
                 [[upname(b)] + [L.x(F['up_geo', b]), L.x(F['upm_geo', b])] for b in ('rust', 'c', 'fsharp', 'rails')], 'Geometric means, same session')
    val = tbl([('Profile', False), ('Timed responses validated', True), ('Writes audited', True), ('Errors or invalid', True), ('Peak generator CPU, %', True)],
              [[n, L.n(F['up_val'][d, 'timed']), L.n(F['up_val'][d, 'writes']), L.n(F['up_val'][d, 'bad']), L.n(F['up_val'][d, 'gen'], D1)] for d, n in ((UPN, 'Normal'), (UPM, 'Mixed'))])
    body = ''.join([
        '<p class="lead">Round two closed by upstream&#39;s method: <code>once-campfire-verification</code>&#39;s harness, unchanged but for an adapter that names onCrack and the port, '
        'their seed, their load generator and their two profiles, with current Rust and C built as their repositories describe. C over Rust here is %s; upstream measured it near the same ratio on a faster machine, so the '
        'session ranks the engines as theirs does.</p>' % L.x(F['up_c_rust']),
        normal, mixed, ratios, val,
        '<h3>Read with care</h3><ul class="caveats">'
        '<li><b>Not their machine.</b> Four of this VM&#39;s CPUs per side, not the Ryzen&#39;s; compare ratios, not absolute numbers, with their report.</li>'
        '<li><b>A different freshness mechanism, then.</b> Upstream re-reads the session and membership on every cache hit. In round two onCrack kept the decision and dropped it on any commit, by any connection (it watches SQLite&#39;s WAL index); '
        'the round&#39;s verifier attacked that with foreign writers and it held, but a hit was not the same work as theirs. Round three made fresh authorization the default; its numbers are the headline.</li>'
        '<li><b>Search order.</b> Rails <span data-lit="commit">90b3300</span> lists a search&#39;s matches by time; upstream has listed them by message id since <span data-lit="commit">dbc7620</span>. onCrack now lists them by id and passes upstream&#39;s contract unchanged. The port still renders the old order, so the harness checks it against that one.</li>'
        '<li><b>One viewer, one URL.</b> Their read workloads are a cache-hit benchmark; the appendix of the results file keeps this project&#39;s realistic workloads.</li></ul>',
        srcline(UPN + '/', UPM + '/', R2 + '/upstream-performance-review.md', 'bench/results/oncrack-r2-final.md', lead='Sources'),
    ])
    return panel('p-upstream', 'History: round two', 'The cached decision, against Rust, C, Rails and the port', body, 'upstream')


def p_prod(F):
    rd = lambda f, key='oncrack', prof='cable_heavy': F['rel', key, prof, f]
    link = lambda pid, label: '<a href="#%s">%s</a>' % (pid, label)
    rows = [
        ['Nobody is cut', 'onCrack at HEAD, fresh and cached: %s of %s clients disconnected in every one of the %s rounds of <span data-lit="name">PR #6</span>&#39;s cable_heavy and cable profiles. Rust cut %s to %s in cable_heavy; onCrack before the shared log, %s to %s.'
         % (L.n(F['relhi', 'oncrack', 'disconnected']), L.n(F['rel_clients']), L.n(F['rel_rounds']), L.n(F['rello', 'rust', 'disconnected']), L.n(F['relhi', 'rust', 'disconnected']),
            L.n(F['rello', 'oncrack-before', 'disconnected']), L.n(F['relhi', 'oncrack-before', 'disconnected'])), link('p-reliability', 'The tables')],
        ['Every message arrives', 'In the median round of cable_heavy all %s posted messages reached every client, and in every one of the %s cable and cable_heavy runs of onCrack, fresh and cached, every posted message did. '
         'In the Cable suite, %s phases of three sessions: none short of any client, none closed, no odd frame.' % (L.n(rd('posted')), L.n(F['rel_runs']), L.n(F['phases'])), link('p-fanout', 'The fan-out')],
        ['The same pixels', '%s of %s screenshots pixel-equal to Rails on every seed, on the final code, in the full gate.' % (L.n(F['pp_total']['equal']), L.n(F['pp_total']['screenshots'])), link('p-pixels', 'Pixel parity')],
        ['The tests pass', '%s of %s tests passed, %s failed, %s skipped (<code>bin/verify</code>, seed required); the Linux Cable suite %s of %s.' % (
            L.n(F['verify', 'succeeded']), L.n(F['verify', 'total']), L.n(F['verify', 'failed']), L.n(F['verify', 'skipped']), L.n(F['lcable', 'succeeded']), L.n(F['lcable', 'total'])), ''],
        ['Durable by default', 'Rails&#39; settings, and every write committed before it is answered. The last <code>kill -9</code> runs (%s, in round three) lost %s acknowledged posts and duplicated %s. '
         'Nothing in the database or writer changed in round five, so the durability test was not repeated.' % (L.n(F['kill_runs']), L.n(F['kill_lost']), L.n(F['kill_dup'])), link('p-durability', 'Durability')],
        ['Attacked, and fixed', 'Every round closed with an adversarial verifier or a skeptical review; what they found was fixed with a test that fails on the code before. Round five&#39;s three reader-protocol defects and a scratch leak are the latest.', link('p-correct', 'The first round&#39;s attacks')],
        ['Memory has a bound', 'Cable keeps what a slow client has not read once, in a shared log, and the hub&#39;s total is bounded at %s <span data-lit="name">GiB</span>; over it, the clients furthest behind are cut. A client that reads is never cut.' % L.n(F['hub_gib']), ''],
        ['Size', '%s KLOC by upstream&#39;s rules, against %s for Rust, %s for C and %s for the F# port it was forked from.' % (
            L.n(F['kloc', 'oncrack'], D1), L.n(F['kloc', 'rust'], D1), L.n(F['kloc', 'c'], D1), L.n(F['kloc', 'fsharp'], D1)), link('p-fresh', 'The size table')],
    ]
    cost = tbl([('What it costs', False), ('Rust', True), ('onCrack', True)], [
        ['Posts taken a second, cable_heavy', L.n(F['relposts', 'rust']), L.n(F['relposts', 'oncrack'])],
        [P99 + ' from a post to the last client, ms', L.n(rd('p99', 'rust')), L.n(rd('p99'))],
        ['Peak Pss, MB', L.n(rd('pss', 'rust')), L.n(rd('pss'))],
        ['Clients cut', L.n(rd('disconnected', 'rust')), L.n(rd('disconnected'))],
    ], 'cable_heavy: %s clients, %s closed-loop posters, medians of %s rounds' % (L.n(F['rel_clients']), L.n(F['rel_posters']), L.n(F['rel_rounds'])))
    body = ''.join([
        '<p class="lead">&ldquo;Runnable in production&rdquo; is eight checks and one price. Each is a number from the final run, and where to read it.</p>',
        tbl([('Check', False), ('Result', False), ('More', False)], [[a, b, c] for a, b, c in rows], 'What the claim stands on'),
        '<h3>The price</h3>',
        '<p>Rust accepts posts faster than it can send them and cuts the readers who cannot keep up; onCrack slows the posters and keeps everyone. Neither is wrong; they protect different things. '
        'Rails keeps everyone too, at %s posts a second and about %s MB.</p>' % (L.n(F['relposts', 'reference'], D1), L.n(F['rel', 'reference', 'cable_heavy', 'pss'], '{:,.0f}')),
        cost,
        '<h3>What does not hold</h3><ul class="caveats">'
        '<li><b>Memory.</b> onCrack&#39;s is %s to %s of Rust&#39;s in the Cable suite and about a gigabyte in cable_heavy.</li>'
        '<li><b>Rust is faster</b> in paced latency at %s clients (%s against %s ms) and ties on throughput at %s; <a href="#p-fanout">the fan-out panel</a> has the reps.</li>'
        '<li><b>The speed claim has a range</b> and no quiet repeat: <a href="#p-fresh">the evidence for claim one</a>.</li>'
        '<li><b>No clean first-pass pixel gate</b> (three harness faults, each passed on re-run) and a timing test in the Linux Cable suite that may still flake.</li></ul>'
        % (L.x(min((F['cable', 'oncrack', n, 'pss'].over(F['cable', 'rust', n, 'pss']) for n in CABLE_COUNTS), key=lambda v: v.v)),
           L.x(max((F['cable', 'oncrack', n, 'pss'].over(F['cable', 'rust', n, 'pss']) for n in CABLE_COUNTS), key=lambda v: v.v)),
           L.n(F['clients'][100]), L.n(F['cable', 'rust', 100, 'p50'], D1), L.n(F['cable', 'oncrack', 100, 'p50'], D1), L.n(F['clients'][2000])),
        '<p>Not done here and not mine to do: publishing. The repository, its About section, Pages and the pull request are the operator&#39;s.</p>',
        srcline(R5REPORT, REL_SESSION + '/summary.json', R5F + '/pixels/pixel-parity.json', R5F + '/logs/verify.log', R5F + '/logs/linux-cable.log', R5F + '/kloc/kloc.json', R5F + '/cable/RESULTS.md', lead='Sources'),
    ])
    return panel('p-prod', 'Evidence for claim two', 'What &ldquo;runnable in production&rdquo; stands on', body, 'claim-prod')


def p_rounds(F, hc):
    H = lambda key, nm: F['hist', key, nm]
    x = L.x
    rows = [
        ['Port, the build', '', 'The Rust workspace translated crate by crate to F# on ASP.NET Core and Falco: scaffold and plan; Ruby, RailsCompat, Routes, Assets; Db, RichText, Storage; Kit core, front server, Cable; the views; the app: boot, account controllers, the hot path, channels and integrations.',
         'The first baseline: %s&ndash;%s Rust on the four reads at %s connections, %s on posts, %s&ndash;%s Rails.' % (x(H('pb', 'rust_lo')), x(H('pb', 'rust_hi')), L.n(F['conc'][16]), x(H('pb', 'post')), L.n(H('pb', 'rails_lo')), L.n(H('pb', 'rails_hi'))), 'Ported vectors and tests per crate; the image boots under the parity candidate.'],
        ['Port, the tuning', '', 'The parity loop, then five tuning units against Rust&#39;s profile: signed-cookie requests, identity bodies, Db row reads, rich text, plain-frame Cable fan-out. The last phase (Datastar) was dropped. Published as the F# port (fork point %s).' % lit('0ae3436', 'commit'),
         '<code>phase7-final</code>: %s&ndash;%s Rust at %s connections, with less CPU per request than Rust.' % (x(H('p7', 'rust_lo')), x(H('p7', 'rust_hi')), L.n(F['conc'][16])), 'The parity harness.'],
        ['Round one', '', 'The brief: same pixels, unhinged work per request. %s instruments; %s a versioned read cache (per-room and per-user counters bumped by temporary triggers, a page cache, authentication through the cache); %s group commit (up to %s writes, one commit) and a post broadcast in commit order; '
         '%s Content-Length on gzipped answers; %s Native AOT, shipped as an opt-in; four verifier findings fixed.' % (lit('C0'), lit('C1'), lit('C2'), L.n(F['group_max']), lit('C3'), lit('C4')),
         '%s Rust and %s the port at %s connections (%s at one, %s at %s), a result in which every read was a cache hit.' % (x(H('r1', 'rust')), x(H('r1', 'port')), L.n(F['conc'][16]), x(H('r1', 'rust_c1')), x(H('r1', 'rust_c64')), L.n(F['conc'][64])),
         '%s of %s screenshots pixel-equal.' % (L.n(H('r1g', 'equal')), L.n(H('r1g', 'total')))],
        ['Round two', '', '%s made the benchmark honest (realistic workloads that write while they read); %s Cable writes its own socket (probe and pong, one wake for both of a post&#39;s broadcasts); %s posting work cut with Rails&#39; durability kept; %s a front-server fast path; %s one connection; %s memory and cold start. '
         'The verifier&#39;s seven findings were fixed, a critical one among them. It ended against upstream&#39;s own harness and current Rust, C and Rails.' % (lit('R2.0'), lit('R2.1'), lit('R2.2'), lit('R2.3'), lit('R2.4'), lit('R2.5')),
         '%s Rust, %s C, %s the port (normal), %s and %s on mixed reads, with the cached decision, which is not upstream&#39;s contract.' % (x(H('r2', 'rust')), x(H('r2', 'c')), x(H('r2', 'port')), x(H('r2', 'rust_mixed')), x(H('r2', 'c_mixed'))),
         '%s of %s round one&#39;s gate; a %s-screenshot targeted gate after the fixes.' % (L.n(H('r2g', 'equal')), L.n(H('r2g', 'total')), L.n(H('r2g', 'targeted')))],
        ['Round three', '', '%s the full gate on the final code; %s <b>fresh authorization on every cache hit became the default</b> (upstream&#39;s contract; the cached decision kept as an opt-in); %s search ordered by message id as upstream&#39;s; %s the WAL-restart stall traced to the VM&#39;s disk (default unchanged).' % (lit('R3.1'), lit('R3.2'), lit('R3.3'), lit('R3.4')),
         'Fresh: %s Rust, %s C, %s the port (normal, two sessions pooled; the sessions alone %s and %s); mixed %s and %s; CPU per room page %s Rust, %s C.' % (x(H('r3', 'rust')), x(H('r3', 'c')), x(H('r3', 'port')), x(H('r3', 'rust_s1')), x(H('r3', 'rust_s2')), x(H('r3m', 'rust_mixed')), x(H('r3m', 'c_mixed')), x(H('r3m', 'cpu_rust')), x(H('r3m', 'cpu_c'))),
         '%s of %s.' % (L.n(H('r3g', 'equal')), L.n(H('r3g', 'total')))],
        ['Round four', '', '%s the one failing attack test was the test browser&#39;s cookie jar; %s a raw epoll Cable client that measures the server (with a window, since a client that keeps up laps the rings); %s gather writes (<code>sendmsg</code>); %s the fresh check holds a read transaction; %s WAL volume, measured, nothing shipped; '
         '%s Cable reliability: a byte-bounded shared log, publish order across streams, a cut for a stall and not for slowness, a posting gate. The verifier&#39;s four defects were fixed.' % (lit('R4.0'), lit('R4.1'), lit('R4.2'), lit('R4.3'), lit('R4.4'), lit('R4.5')),
         '%s Rust, %s C, %s the port (one session); CPU per room page %s Rust, %s C; fan-out %s, %s, %s and %s Rust (the &ldquo;ahead at every count&rdquo; sentence withdrawn); <span data-lit="name">PR #6</span> incomplete: onCrack the only app to keep all %s clients in cable_heavy. '
         'Two defects left open: one message of %s missing, and a memory gap.' % (x(H('r4', 'rust')), x(H('r4', 'c')), x(H('r4', 'port')), x(H('r4', 'cpu_rust')), x(H('r4', 'cpu_c')), x(H('r4', 'f100')), x(H('r4', 'f500')), x(H('r4', 'f1000')), x(H('r4', 'f2000')), L.n(F['rel_clients']), L.n(H('r4msg', 'posted'))),
         '%s targeted screenshots.' % L.n(H('r4g', 'shots'))],
        ['Round five', '', '%s the missing message traced to the server, a corrupted payload and not a lost frame; %s the gather pinned only the last payload of each batch (a compiler had turned the recursion into a loop), and the hub&#39;s total now reaches every chunk and cuts the furthest behind; '
         '%s the fan-out at %s clients profiled (three quarters of the CPU in <code>sendmsg</code>), the hold and batch settings kept nothing. The verifier fixed three reader-protocol defects and a scratch leak. Then the final gates and runs.' % (lit('R5.1'), lit('R5.2'), lit('R5.3'), L.n(F['clients'][2000])),
         '%s Rust, %s C, %s the port (normal), %s, %s and %s on mixed reads, across sessions of %s to %s; CPU per room page %s Rust, %s C; fan-out %s, %s, %s and %s Rust; <span data-lit="name">PR #6</span>: %s of %s clients cut, every round; %s KLOC.' % (
             x(F['up3_geo', 'oncrack', 'rust']), x(F['up3_geo', 'oncrack', 'c']), x(F['up3_geo', 'oncrack', 'fsharp']), x(F['up3m_geo', 'oncrack', 'rust']), x(F['up3m_geo', 'oncrack', 'c']), x(F['up3m_geo', 'oncrack', 'fsharp']),
             x(F['sess_lo', 'normal', 'rust']), x(F['sess_hi', 'normal', 'rust']), x(F['cpu3', 'rust', 'room_show'].over(F['cpu3', 'oncrack', 'room_show'])), x(F['cpu3', 'c', 'room_show'].over(F['cpu3', 'oncrack', 'room_show'])),
             *[x(F['cable', 'oncrack', n, 'msgs'].over(F['cable', 'rust', n, 'msgs'])) for n in CABLE_COUNTS], L.n(F['relhi', 'oncrack', 'disconnected']), L.n(F['rel_clients']), L.n(F['kloc', 'oncrack'], D1)),
         '%s of %s; <code>bin/verify</code> %s passed, %s failed.' % (L.n(F['pp_total']['equal']), L.n(F['pp_total']['screenshots']), L.n(F['verify', 'succeeded']), L.n(F['verify', 'failed']))],
    ]
    trs = ''.join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (a, c, d, g_) for a, b, c, d, g_ in rows)
    body = ''.join([
        '<p class="lead">Every iteration of the chart, what changed in it, the headline each closed with as its own report wrote it, and the gate. <b>The headlines are not comparable down the column</b>: rounds one and two&#39;s early figures divide by the pinned Rust (<span data-lit="commit">ccece30</span>) on this project&#39;s own suite; '
        'from round two&#39;s final run they divide by current Rust (<span data-lit="commit">f9dca47</span>) and C (<span data-lit="commit">cd0cbe4</span>) on upstream&#39;s harness, in sessions that differ in host noise.</p>',
        '<div class="tw dense"><table><caption>What changed, iteration by iteration</caption><thead><tr><th scope="col">Iteration</th><th scope="col">What changed</th><th scope="col">Headline at its close</th><th scope="col">Gate</th></tr></thead><tbody>%s</tbody></table></div>' % trs,
        '<p>Beats worth telling: the benchmark was made honest twice (round two&#39;s writing workloads, round four&#39;s load generator that stopped being the limit), and each time onCrack&#39;s number moved down before it moved up; the round-one multiple was a result in which every read was a cache hit; '
        'the default stopped being the fast mode in round three (fresh authorization) and round four then bought the cost back; and the one correctness doubt that survived round four, a message that did not reach a client, was a compiler turning a recursion into a loop, found by reading the IL.</p>',
        srcline(R5REPORT, 'bench/results/oncrack-round1-final.md', 'bench/results/oncrack-r2-final.md', 'bench/results/oncrack-r3-final.md', 'bench/results/oncrack-r4-final.md', lead='Sources (each round&#39;s own report; the table is the final report&#39;s history)'),
    ])
    return panel('p-rounds', 'The iterations', 'What changed in each one', body, 'climb')


def p_climb(cl):
    pts = cl.get('dots') or []
    rows = []
    for p in sorted(pts, key=lambda d: (d['t'], d['series'])):
        rows.append('<tr%s><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td><td class="num">%.2f&times;</td><td>%s</td></tr>'
                    % ('' if p['kept'] else ' class="dropped"', e(p['t'].astimezone(EDT).strftime('%-d %b %H:%M')), e({'port': 'F# port', 'cached': 'onCrack, cached', 'fresh': 'onCrack, fresh'}[p['series']]), e(p['unit'] or ''),
                       e(p['change']), p['v'], 'kept' if p['kept'] else 'reverted'))
    src = L.block('the climb chart\'s dots, as a table', CHART_FILES, 'every logged run (req/s over the stored Rust medians of its era, geometric mean of the five at c=16), as bench/progress/climb.py draws it')
    tbl_ = ('<div class="tw" %s><table><caption>Every dot, oldest first</caption><thead><tr><th scope="col">EDT</th><th scope="col">Line</th><th scope="col">Unit</th>'
            '<th scope="col">Change</th><th scope="col" class="num">&times; Rust</th><th scope="col">Kept</th></tr></thead><tbody>%s</tbody></table></div>' % (src, ''.join(rows)))
    body = ''.join([
        '<p class="lead">Each line is the geometric mean of throughput over Rust&#39;s across the five benchmarked workloads (room page, messages page, sidebar, search, post a message) '
        'at %s connections. Dots are spaced evenly in the order they ran, grouped under their iteration; the time under a dot is the clock. A dot that measured only some workloads carries the rest from the last kept run; its card greys them.</p>' % L.n(FCTX['F']['conc'][16]),
        '<h3>Read with care</h3><ul class="caveats">'
        '<li><b>Two denominators, both pinned Rust.</b> The port&#39;s dots divide by the Rust measured in the session of its own tuning phase&#39;s start (or, for its first two, in the same run); onCrack&#39;s divide by the stored Rust medians of the port&#39;s final re-baseline (<code>phase7-final</code>), '
        'so onCrack&#39;s dots compare with each other. The fork dot is on both lines: the same session, read against its own Rust. The headline at the top of the page is current upstream, measured with upstream&#39;s harness.</li>'
        '<li><b>Fresh and cached are two lines.</b> A logged row says which; a row without the field is cached, which is every row of rounds one and two. Only the round three and round five images were measured in both modes. '
        'The dotted segment from round two&#39;s last dot to the first fresh dot is not a measurement: it joins the line to where the default changed.</li>'
        '<li><b>Round three&#39;s dots were measured in round five.</b> Round three logged no project-suite row of its own, so its final image (<span data-lit="commit">37c5988</span>) was measured then, beside round five&#39;s, in both modes; the cached rows are third attempts, '
        'the first two having run while other projects loaded the host (the selection rule was fixed before the third). Round four&#39;s final image was never measured on this suite.</li>'
        '<li><b>Most dots are provisional.</b> A %s dot is one rep of the workloads a change touches, on a build mounted into a container. The numbers that count are %s: a rebuilt image, three reps, all five workloads.</li>'
        '<li><b>Rails is a floor, and C is missing.</b> Rails is the port&#39;s stored baseline, at a few percent of Rust&#39;s throughput on this suite. C was never run on it; its figures are on upstream&#39;s harness, at the top of the page.</li></ul>' % (tier(2), tier(3)),
        tbl_,
        srcline('bench/results/oncrack-log.jsonl', 'bench/results/phase7-log.jsonl', 'bench/progress/history.json', 'bench/progress/climb.py', lead='Sources'),
    ])
    return panel('p-climb', 'The climb', 'Every dot, and how to read the chart', body, 'climb')


def p_rules():
    body = ''.join([
        '<p class="lead">From <code>plans/oncrack.md</code>: &ldquo;Make the UI exactly the same, but go unhinged with Datastar, caching, or any other improvements we can do.&rdquo; '
        'The port matched the Rust port&#39;s work per request and still beat it. onCrack drops that constraint, and nothing else.</p>',
        '<ol class="caveats">'
        '<li><b>The UI is identical.</b> Every parity screen&#39;s pixels match Rails&#39; (the harness&#39;s screenshot layer, lean matrix, all seeds) and every interaction behaves the same for a person using it. '
        'Server HTML, the live DOM, network requests and Cable frames may differ.</li>'
        '<li><b>Correct, always.</b> No stale reads after a write, no data from one user in another&#39;s response, no lost messages. Every cache states its invalidation rule and has tests that try to break it.</li>'
        '<li><b>Durability is a disclosed choice.</b> Anything that weakens it is measured both ways, documented, and shipped only behind a setting whose default is Rails-equivalent durability.</li>'
        '<li><b>Scored separately.</b> Same harness, same seed and pinned CPUs; every ratio against the Rust port and against the F# port, never presented as a like-for-like port result.</li>'
        '<li><b>Same discipline.</b> Measure before and after, one change at a time, log every run to the climb chart, never manufacture a win.</li></ol>',
        srcline('plans/oncrack.md', lead='Source'),
    ])
    return panel('p-rules', 'The rules', 'What onCrack may and may not do', body, 'more')


def p_port_era():
    hist = climb_chart.history()
    era = climb_chart.climb(climb_chart.PORT_ERA)
    pts = era.get('points') or []
    rows = []
    for p in pts:
        rows.append('<tr%s><th scope="row">%s</th><td>%s</td><td>%s</td><td class="num">%.2f&times;</td><td>%s</td></tr>'
                    % ('' if p['kept'] else ' class="dropped"', e(p['time'].astimezone(EDT).strftime('%-d %b %H:%M')), e(p['unit'] or ''),
                       e(p['change']), p['ratio'], 'kept' if p['kept'] else 'reverted'))
    src = L.block('the F# port\'s own climb (before onCrack)', ['bench/results/phase7-log.jsonl', 'bench/progress/history.json', 'bench/results/phase7-start/rust-1.json', 'bench/progress/climb.py'],
                  'F# port req/s over the stored Rust medians of phase7-start, geometric mean of the five at c=16, per logged run; the "before the port" cards are history.json port_era.prelude')
    body = ''.join([
        '<div %s>' % src,
        '<p class="lead">onCrack was forked from the F# port, a faithful translation of the Rust port that matched Rust&#39;s work per request. The port&#39;s Phase 7 tuning climbed from %.2f&times; '
        'to %.2f&times; of Rust; they are the dotted line of the hero chart, and onCrack forks from its final dot. They measured a different rule (the same work as Rust) against the Rust of the port&#39;s own sessions. '
        'The port itself is at <a href="%s">%s</a>.</p>' % (era.get('start') or 0, era.get('latest') or 0, e(META['port_repo']), e(META['port_repo'].replace('https://', ''))),
        '<div class="tw"><table><caption>Every dot of the port&#39;s climb, oldest first (F# port over Rust, 16 connections)</caption><thead><tr><th scope="col">EDT</th><th scope="col">Unit</th>'
        '<th scope="col">Change</th><th scope="col" class="num">&times; Rust</th><th scope="col">Kept</th></tr></thead><tbody>%s</tbody></table></div>' % ''.join(rows),
        climb_chart.prelude(hist), '</div>',
        srcline('bench/results/phase7-log.jsonl', 'bench/progress/history.json', lead='Sources'),
    ])
    return panel('p-port-era', 'Before onCrack', 'The F# port&#39;s climb', body, 'climb')


def more_row():
    links = [('p-ledger', 'Every number'), ('p-repro', 'Reproduce it'), ('p-rules', 'The rules'), ('p-rounds', 'What changed in each iteration'), ('p-climb', 'Every dot of the climb'), ('p-port-era', 'The port&#39;s own climb'), ('p-upstream', 'History: round two')]
    return ('<section class="more-row" id="more" aria-label="Everything else"><div class="wrap reveal"><p class="kicker">Everything else</p>'
            '<p class="links">%s</p></div></section>' % ''.join(details(p, l) for p, l in links))


# ================================================================ the check

LIT_SHAPES = {   # data-lit reason: the shapes it may hold (a name, never a measurement)
    'name': [r'(?:normal|mixed)-\d', r'C[0-4]', r'C[0-4]-C[0-4]', r'A\d[a-c]?', r'R[1-5]\.[0-5]', r'[Tt]ier [123]', r'p50|p99', r'HTTP/2', r'37signals', r'SHA-256', r'PR #6', r'GiB'],
    'test': [r'A\d[a-c]?', r'kill', r'kit-http'],
    'commit': [r'[0-9a-f]{7,12}'],
    'status': [r'[1-5]\d\d', r'[1-5]xx'],
    'count': [r'\d+'],                              # the ledger's own row count
    'duration in mixed.sh': [r'30 s'],
    'size written in oncrack-fixes.md': [r'512 KB'],
}
LIT_WHY = set(LIT_SHAPES)


class Checker(HTMLParser):
    """Reads the page back: every digit a reader sees must sit inside an element the ledger issued (data-src)."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
    EXEMPT = {'script', 'style', 'code', 'pre', 'title'}

    def __init__(self, ids):
        super().__init__(convert_charrefs=True)
        self.ids, self.stack, self.errors, self.lits, self.spans, self.links = ids, [], [], [], set(), set()

    def ctx(self):
        return any(s[1] for s in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        ok = False
        if 'data-src' in a:
            if a['data-src'] not in self.ids:
                self.errors.append('data-src %s is not a ledger row' % a['data-src'])
            (self.links if tag == 'a' else self.spans).add(a['data-src'])
            ok = True
        if 'data-lit' in a:
            ok = True
            self.lits.append(a['data-lit'])
            if a['data-lit'] not in LIT_WHY:
                self.errors.append('data-lit with an unknown reason: %s' % a['data-lit'])
        if 'data-ledger' in a or tag in self.EXEMPT:
            ok = True
        for k in ('aria-label', 'alt', 'title'):
            if a.get(k) and re.search(r'\d', a[k]) and not (ok or self.ctx()):
                self.errors.append('a digit in %s="%s" with no source' % (k, a[k]))
        if tag in self.VOID:
            return
        self.stack.append((tag, ok, a.get('data-lit')))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        self.errors.append('stray </%s>' % tag)

    def handle_data(self, data):
        if not re.search(r'\d', data):
            return
        lit = next((s[2] for s in reversed(self.stack) if s[2]), None)
        if lit:
            if not any(re.fullmatch(p, data.strip()) for p in LIT_SHAPES.get(lit, [])):
                self.errors.append('data-lit "%s" holds %r, which is not an identifier shape' % (lit, data.strip()))
            return
        if not self.ctx():
            where = '/'.join(s[0] for s in self.stack[-4:])
            self.errors.append('a number with no source: %r (in %s)' % (data.strip()[:80], where))


def check(page):
    c = Checker({r['id'] for r in L.rows})
    c.feed(page)
    c.close()
    orphans = c.spans - c.links
    for rid in sorted(orphans):
        row = next(r for r in L.rows if r['id'] == rid)
        if not row['block']:
            c.errors.append('%s (%s) is shown only inside another link; it must also appear as a link to its row somewhere' % (rid, row['label']))
    return c


def crosscheck(F):
    """Compare a few headline numbers with what the round's results file says; print, don't fail (the files are the source)."""
    t = text('bench/results/oncrack-round1-final.md')
    out = []
    pairs = [('%.2fx' % F['geo_rust', c].v, 'onCrack/Rust geometric mean c=%d' % c) for c in (1, 16, 64)] + \
            [('%.2fx' % F['geo_port', c].v, 'onCrack/port geometric mean c=%d' % c) for c in (1, 16, 64)] + \
            [('%.2fx' % F['mix', 'oncrack', 'read'].over(F['mix', 'rust', 'read']).v, 'reads while writing, onCrack/Rust'),
             ('%.2fx' % F['mix', 'oncrack', 'read'].over(F['mix', 'fsharp', 'read']).v, 'reads while writing, onCrack/port')]
    for s, what in pairs:
        if s not in t:
            out.append('%s: the data gives %s, which oncrack-round1-final.md does not say' % (what, s))
    return out


# ================================================================ CSS and JS

CSS = r"""
:root{
  --bg:#f7f4ee;--surface:#fffdf9;--surface-2:#efe9df;--ink:#16130f;--ink-2:#4b453d;--muted:#7a7368;
  --line:rgba(22,19,15,.13);--line-2:rgba(22,19,15,.07);--accent:#c2410c;--accent-2:#6d4aff;--crit:#c0262d;--good:#0b7a35;--warn:#a15c00;--minor:#6b665d;
  --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;
  --glow-a:rgba(234,88,12,.22);--glow-b:rgba(109,74,255,.15);--shadow:0 1px 2px rgba(0,0,0,.04),0 18px 40px -18px rgba(30,20,10,.18);
  --display:"Instrument Serif",ui-serif,Georgia,serif;--sans:system-ui,-apple-system,"SF Pro Text","Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0c0a09;--surface:#161311;--surface-2:#1f1b18;--ink:#f6f1ea;--ink-2:#cbc3b7;--muted:#91897d;
  --line:rgba(255,255,255,.12);--line-2:rgba(255,255,255,.06);--accent:#ff8a4c;--accent-2:#a594ff;--crit:#ff6b6b;--good:#34c46a;--warn:#e8a33a;--minor:#a39d92;
  --s1:#3987e5;--s2:#d95926;--s3:#199e70;--glow-a:rgba(255,122,61,.22);--glow-b:rgba(140,110,255,.2);--shadow:0 1px 2px rgba(0,0,0,.4),0 18px 44px -18px rgba(0,0,0,.7);color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0c0a09;--surface:#161311;--surface-2:#1f1b18;--ink:#f6f1ea;--ink-2:#cbc3b7;--muted:#91897d;
  --line:rgba(255,255,255,.12);--line-2:rgba(255,255,255,.06);--accent:#ff8a4c;--accent-2:#a594ff;--crit:#ff6b6b;--good:#34c46a;--warn:#e8a33a;--minor:#a39d92;
  --s1:#3987e5;--s2:#d95926;--s3:#199e70;--glow-a:rgba(255,122,61,.22);--glow-b:rgba(140,110,255,.2);--shadow:0 1px 2px rgba(0,0,0,.4),0 18px 44px -18px rgba(0,0,0,.7);color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%;overflow-x:clip}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--sans);overflow-x:clip;-webkit-font-smoothing:antialiased}
html.locked,html.locked body{overflow:hidden}
a{color:var(--accent);text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}
code{overflow-wrap:anywhere;font:.88em var(--mono);background:var(--surface-2);padding:.1em .35em;border-radius:5px}
.wrap{max-width:1200px;margin:0 auto;padding:0 16px}
@media (min-width:720px){.wrap{padding:0 32px}}
.skip{position:absolute;left:-999px}.skip:focus{left:16px;top:8px;z-index:60;background:var(--surface);padding:8px 12px;border-radius:8px}
.kicker{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:650;margin:0 0 12px}
/* top bar */
.bar{position:sticky;top:0;z-index:20;backdrop-filter:saturate(1.6) blur(18px);-webkit-backdrop-filter:saturate(1.6) blur(18px);background:color-mix(in srgb,var(--bg) 80%,transparent);border-bottom:1px solid var(--line-2)}
.bar .wrap{display:flex;align-items:center;gap:12px;height:52px}
.brand{font-weight:650;letter-spacing:-.01em;color:var(--ink);text-decoration:none;white-space:nowrap}.brand span{color:var(--accent)}
.bar nav{flex:1;min-width:0;overflow-x:auto;scrollbar-width:none}.bar nav::-webkit-scrollbar{display:none}
.bar nav ol{display:flex;gap:2px;list-style:none;margin:0;padding:0;justify-content:flex-end}
.bar nav a{display:block;padding:6px 10px;border-radius:999px;color:var(--ink-2);text-decoration:none;font-size:13px;white-space:nowrap}
.bar nav a:hover,.bar nav a:focus-visible{background:var(--surface-2);color:var(--ink)}
.theme{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;width:34px;height:34px;cursor:pointer;flex:none;display:none}
.js .theme{display:inline-grid;place-items:center}
/* hero */
.hero{position:relative;z-index:2;padding:56px 0 24px;isolation:isolate}
.glow{position:absolute;inset:-140px 0 auto;height:700px;z-index:-1;pointer-events:none;
  background:radial-gradient(38% 46% at 22% 35%,var(--glow-a),transparent 70%),radial-gradient(34% 44% at 78% 22%,var(--glow-b),transparent 70%);filter:blur(12px)}
h1{font:400 clamp(52px,10.5vw,138px)/.9 var(--display);letter-spacing:-.025em;margin:0 0 22px;text-wrap:balance}
.lede{font-size:clamp(17px,2.1vw,22px);line-height:1.5;color:var(--ink-2);max-width:780px;margin:0 0 28px}
.lede strong{color:var(--ink)}
.htiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 18px}
.ht{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px 18px;box-shadow:var(--shadow);min-width:0}
.ht .num-big{font-size:clamp(34px,4.6vw,54px)}.ht>span:last-child{display:block;color:var(--muted);font-size:13.5px;margin-top:4px}
@media (max-width:720px){.htiles{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
.climb{margin:0;position:relative;z-index:3}
.climb figcaption{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;justify-content:space-between;color:var(--muted);font-size:13.5px;margin-top:12px}
.climb figcaption>span{flex:1 1 420px;min-width:0}.climb figcaption b{color:var(--ink)}
.cc{--cc-card:var(--surface);--cc-ink:var(--ink);--cc-mute:var(--muted);--cc-line:var(--line);--cc-acc:var(--accent);font-family:var(--sans)}
.cc-chart{border-radius:22px;box-shadow:var(--shadow)}
/* big numbers */
.num-big{display:inline-flex;align-items:baseline;font:400 clamp(60px,12vw,168px)/.9 var(--display);letter-spacing:-.03em;font-variant-numeric:tabular-nums;white-space:nowrap}
.num-big i{font-style:normal;font-size:.5em;margin-left:.04em;color:var(--accent)}
.num-big i:first-child{margin:0 .03em 0 0}
.num-big.small{font-size:clamp(44px,7vw,96px)}
s.strike{text-decoration:none;position:relative;display:inline-block}
s.strike::after{content:"";position:absolute;left:-4%;right:-4%;top:47%;height:.07em;min-height:2px;background:var(--crit);border-radius:2px;transform-origin:left;transition:transform .7s cubic-bezier(.6,0,.2,1) .35s}
/* numbers band */
.numbers{padding:72px 0 24px}
.sec-head h2,.beat h2{font:400 clamp(38px,6.4vw,80px)/.98 var(--display);letter-spacing:-.02em;margin:0 0 16px;text-wrap:balance}
.line{font-size:clamp(17px,1.8vw,20px);line-height:1.55;color:var(--ink-2);margin:0 0 14px;max-width:640px}
.ntiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:28px 0 8px}
.nt{position:relative;display:flex;flex-direction:column;justify-content:space-between;gap:10px;min-height:150px;padding:18px;border-radius:20px;background:var(--surface);border:1px solid var(--line);
  color:var(--ink);text-decoration:none;box-shadow:var(--shadow);transition:transform .25s,border-color .25s}
.nt:hover,.nt:focus-visible{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--line))}
.nt .num-big{font-size:clamp(40px,5vw,60px)}.nt-l{font-size:13.5px;font-weight:600;color:var(--ink-2)}
@media (min-width:1100px){.ntiles{grid-template-columns:repeat(7,1fr)}.nt:first-child{grid-column:span 1}}
/* tips (CSS only): a card above the fact; a sheet at the bottom of a phone screen */
.has-tip{position:relative;cursor:help;border-bottom:1px dashed color-mix(in srgb,currentColor 45%,transparent);outline-offset:2px}
.tip{position:absolute;z-index:30;left:50%;bottom:calc(100% + 10px);transform:translate(-50%,4px);width:max-content;max-width:min(300px,80vw);
  background:var(--ink);color:var(--bg);font:500 13px/1.45 var(--sans);letter-spacing:0;text-transform:none;text-align:left;padding:9px 12px;border-radius:10px;
  box-shadow:0 10px 30px rgba(0,0,0,.25);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .15s,transform .15s;white-space:normal}
.has-tip:hover>.tip,.has-tip:focus>.tip,.nt:hover>.tip,.nt:focus-visible>.tip{opacity:1;visibility:visible;transform:translate(-50%,0)}
.nt>.tip{bottom:auto;top:calc(100% + 8px)}
@media (max-width:640px),(hover:none){.tip{position:fixed;left:12px;right:12px;bottom:12px;top:auto!important;width:auto;max-width:none;transform:none!important;font-size:14px;padding:12px 14px}}
/* beats */
.beat{padding:clamp(56px,8vw,104px) 0;border-top:1px solid var(--line-2);scroll-margin-top:52px;position:relative}
.beat-grid{display:grid;gap:clamp(28px,5vw,72px);align-items:center;grid-template-columns:minmax(0,1fr)}
@media (min-width:900px){.beat-grid{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr)}.beat.flip .beat-visual{order:2}.beat.wide .beat-grid{grid-template-columns:minmax(0,1fr)}}
.beat-visual,.beat-copy{min-width:0}
.beat.wide .beat-visual{order:2}
.beat q{font:400 clamp(22px,2.6vw,30px)/1.25 var(--display);color:var(--ink);quotes:"\201C" "\201D"}
.who{display:block;margin-top:6px;font-size:14px;color:var(--muted)}
.links{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0}
.more{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);
  font-weight:600;font-size:14.5px;text-decoration:none;box-shadow:var(--shadow);transition:transform .2s,border-color .2s,background .2s}
.more:hover,.more:focus-visible{transform:translateY(-2px);border-color:var(--accent)}
.more span{color:var(--accent);transition:transform .2s}.more:hover span{transform:translateX(3px)}
.cap{display:block;color:var(--muted);font-size:14px;margin-top:10px}
/* the struck claims (Muse panel) */
.claim-tag{font:400 clamp(30px,4vw,48px)/1 var(--display);margin:0 0 18px;color:var(--ink-2)}
.struck{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 26px}
.struck li{display:flex;flex-direction:column}
.struck .has-tip{border:0}
.struck s{font:400 clamp(48px,8vw,104px)/1 var(--display);color:var(--ink);letter-spacing:-.02em}
.struck small{font-size:12.5px;color:var(--muted);margin-top:4px}
.struck li:nth-child(2) s::after{transition-delay:.45s}.struck li:nth-child(3) s::after{transition-delay:.55s}.struck li:nth-child(4) s::after{transition-delay:.65s}.struck li:nth-child(5) s::after{transition-delay:.75s}
/* before and after (Muse panel) */
.vs{display:grid;gap:18px}
.vs>div>span:last-child{display:block;color:var(--muted);font-size:14px;margin-top:6px}
.vs-bad .num-big{color:var(--muted)}
.vs-good .num-big b{background:linear-gradient(160deg,var(--good),color-mix(in srgb,var(--good) 55%,var(--accent-2)));-webkit-background-clip:text;background-clip:text;color:transparent}
.tags ul,.chips ul,.loop ol{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.tags li .has-tip,.chips li,.loop li .has-tip{display:inline-block;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:5px 12px;font-size:14px;color:var(--ink)}
.tags li .has-tip{border-color:color-mix(in srgb,var(--crit) 45%,var(--line));color:var(--crit)}
.tags,.loop,.chips{margin:0 0 16px}.loop ol{counter-reset:l}.loop li{display:flex;align-items:center;gap:8px}.loop li:not(:last-child)::after{content:"\2192";color:var(--accent);font-weight:700}
.chips b{font-variant-numeric:tabular-nums}
/* the phases strip */
.phases-strip{list-style:none;margin:0;padding:0;display:grid;gap:10px;grid-template-columns:repeat(6,minmax(0,1fr))}
@media (max-width:899px){.phases-strip{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:520px){.phases-strip{gap:8px}.ph a{padding:12px;border-radius:16px}.ph-n{font-size:34px}.ph-t{font-size:13px}.ph-m{display:none!important}.ph-big b{font-size:26px}}
.ph a{display:flex;flex-direction:column;gap:6px;height:100%;padding:16px;border-radius:20px;background:var(--surface);border:1px solid var(--line);color:var(--ink);text-decoration:none;box-shadow:var(--shadow);transition:transform .25s,border-color .25s}
.ph a:hover,.ph a:focus-visible{transform:translateY(-4px);border-color:var(--accent)}
.ph-n{font:400 44px/.85 var(--display);background:linear-gradient(160deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.ph-t{font-weight:650;font-size:15px;line-height:1.25;min-height:2.5em}
.ph-bar{display:block;height:84px;border-radius:10px;background:var(--surface-2);position:relative;overflow:hidden}
.ph-bar span{position:absolute;left:0;right:0;bottom:0;height:calc(var(--h)*100%);background:linear-gradient(0deg,var(--accent),var(--accent-2));border-radius:10px;transform-origin:bottom;transition:transform 1.1s cubic-bezier(.2,.7,.2,1) calc(var(--i)*90ms)}
.ph-big b{display:block;font:400 clamp(30px,3.2vw,40px)/1 var(--display);font-variant-numeric:tabular-nums}.ph-big span,.ph-m{display:block;font-size:12.5px;color:var(--muted)}
.beat-build .beat-copy{max-width:820px}
/* byte for byte */
.proof .of{display:block;font:400 clamp(24px,3vw,36px)/1 var(--display);color:var(--muted);margin-top:6px}
.proof .num-big b{background:linear-gradient(160deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
/* tiers: three big words, details on hover */
.tiers{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 0;align-items:baseline}
.tiers li{display:flex;align-items:baseline}
.tiers li:not(:last-child)::after{content:"\2192";font:400 clamp(28px,4vw,48px)/1 var(--display);color:var(--muted);margin:0 .35em}
.tiers .has-tip{border:0}
.tiers b{font:400 clamp(44px,7vw,96px)/1 var(--display);letter-spacing:-.02em;color:var(--ink)}
.tiers li:last-child b{background:linear-gradient(160deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
@media (max-width:720px){.bar nav ol{justify-content:flex-start}.nt{min-height:112px}.ph-bar{height:48px}.ph-t{min-height:0}}
.btw{margin:18px 0 0;font-size:15px;color:var(--muted)}
.btw a{font-weight:650;text-decoration-thickness:1px}
.btw span{margin-left:4px}
.numbers{padding:48px 0 8px}.numbers .ntiles{margin-top:14px}
.more-row{padding:40px 0 56px;border-top:1px solid var(--line-2)}.more-row .links{margin-top:0}
.sheet-body h4{margin:22px 0 8px;font-size:16px}
.sheet .vs{margin:22px 0}
/* footer */
footer.site{border-top:1px solid var(--line-2);padding:40px 0 64px;color:var(--muted);font-size:14px}
footer.site p{max-width:860px}
/* panels: :target drawers without JS, .open with it */
.panel{position:fixed;inset:0;z-index:50;visibility:hidden;pointer-events:none}
html:not(.js) .panel:target,.panel.open{visibility:visible;pointer-events:auto}
.scrim{position:absolute;inset:0;background:rgba(10,8,6,.45);opacity:0;transition:opacity .3s;cursor:default}
html:not(.js) .panel:target .scrim,.panel.open .scrim{opacity:1}
.sheet{position:absolute;top:0;right:0;bottom:0;width:min(780px,100%);background:var(--bg);color:var(--ink);box-shadow:-24px 0 60px rgba(0,0,0,.25);
  overflow-y:auto;overscroll-behavior:contain;transform:translateX(102%);transition:transform .38s cubic-bezier(.2,.8,.2,1);outline:none}
html:not(.js) .panel:target .sheet,.panel.open .sheet{transform:none}
.sheet-head{position:sticky;top:0;z-index:2;display:flex;gap:16px;align-items:flex-start;justify-content:space-between;padding:22px 24px 16px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line-2)}
.sheet-head h2{font:400 clamp(30px,4.4vw,46px)/1 var(--display);margin:0;letter-spacing:-.015em}
.sheet-head .kicker{margin-bottom:8px}
.x{flex:none;display:grid;place-items:center;width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--surface);color:var(--ink);text-decoration:none;font-size:24px;line-height:1}
.x:hover{border-color:var(--accent)}
.sheet-body{padding:8px 24px 48px;font-size:15.5px}
.sheet-body h3{font:400 28px/1.1 var(--display);margin:34px 0 12px}
.sheet-body .lead{font-size:17.5px;color:var(--ink-2)}
.back{margin-top:36px}
@media (max-width:720px){.sheet{width:100%;box-shadow:none}.sheet-head{padding:16px 16px 12px}.sheet-body{padding:4px 16px 40px}}
.muted{color:var(--muted)}.src{font-size:13px;color:var(--muted)}
.pills{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:12px 0;padding:0}
.pills li{font-size:12.5px;padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink-2)}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:18px 0}.lbl{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.tw{overflow-x:auto;margin:18px 0;border:1px solid var(--line);border-radius:16px;background:var(--surface)}
.tw table{border-collapse:collapse;width:100%;font-size:14px}
.tw caption{text-align:left;padding:14px 16px 4px;font-size:13px;color:var(--muted);caption-side:top}
.tw th,.tw td{padding:9px 14px;border-bottom:1px solid var(--line-2);text-align:left;vertical-align:top}
.tw thead th{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;white-space:nowrap}
.tw tbody th{font-weight:600}.tw tbody tr:last-child>*{border-bottom:0}.tw tr.dropped{color:var(--muted)}
.tw .rng{color:var(--muted);font-size:12px}.tw .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tw.dense th,.tw.dense td{padding:6px 10px;font-size:13px}
.ratio{min-width:160px}.rbar{display:inline-block;position:relative;width:90px;height:8px;border-radius:4px;background:var(--surface-2);vertical-align:middle;margin-right:10px}
.rfill{position:absolute;left:0;top:0;bottom:0;border-radius:4px;background:var(--s1)}.rfill.ahead{background:var(--good)}
.rone{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink);opacity:.55}
.facts{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin:18px 0}
.fact{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px}
.fact b{font:400 38px/1 var(--display)}.fact span{display:block;font-weight:600;margin:6px 0}.fact p{margin:0;color:var(--ink-2);font-size:13.5px}
.log{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.log li{display:grid;grid-template-columns:52px minmax(0,1fr);gap:10px;font-size:14.5px;overflow-wrap:anywhere}
.log time{font:12.5px var(--mono);color:var(--accent);padding-top:2px}
.handoff{margin:0}.handoff figcaption{color:var(--muted);font-size:14px;margin-bottom:10px}
.bubble{background:#1a1d21;color:#e8e8e8;border-radius:18px;padding:16px 18px;font-size:15px}
.bubble-head{display:flex;align-items:center;gap:10px;margin-bottom:6px}.bubble-head b{color:#fff}.bubble-head time{color:#9aa0a6;font-size:12.5px}
.avatar{width:32px;height:32px;border-radius:8px;display:grid;place-items:center;background:linear-gradient(135deg,#c2410c,#6d4aff);color:#fff;font-size:12px;font-weight:700}
.bubble-body p{margin:.5em 0;overflow-wrap:anywhere}
.unknown{display:flex;gap:16px;align-items:center;margin:24px 0;padding:16px 18px;border:1px dashed var(--line);border-radius:16px}
.unknown>span{font:400 64px/1 var(--display);color:var(--muted);opacity:.6}.unknown p{margin:0}
.finding{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0}
.finding h3{font:650 18px/1.3 var(--sans);margin:0 0 8px}.finding p{margin:0 0 10px;color:var(--ink-2)}
.tag{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--crit)!important;font-weight:650}
.evidence{font:13px/1.5 var(--mono);color:var(--muted)!important;border-top:1px dashed var(--line);padding-top:10px;margin:0!important;overflow-wrap:anywhere}
.versus{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 12px}
.v{border-radius:14px;padding:12px;background:var(--surface-2)}.v b{display:block;font:400 26px/1.05 var(--display)}.v span{font-size:13px;color:var(--muted)}
.v.bad b{color:var(--crit);text-decoration:line-through}.v.good b{color:var(--good)}
.pull{margin:18px 0;padding:0 0 0 20px;border-left:3px solid var(--accent)}
.pull p{font:400 clamp(21px,2.6vw,27px)/1.3 var(--display);margin:0 0 8px}.pull footer{color:var(--muted);font-size:14px}
.decisions{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin:18px 0}
.decision{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:14px 16px}
.decision b{font:400 26px var(--display);color:var(--accent)}.decision .q{font-weight:600;margin:2px 0 6px}.decision p{margin:0;font-size:14px;color:var(--ink-2)}
pre{font:13px/1.55 var(--mono);white-space:pre-wrap;word-break:break-word;margin:0}
.reply,.code{background:var(--surface-2);border-radius:14px;padding:14px 16px}
.pmeta{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin:12px 0}
.pmeta div{background:var(--surface);border:1px solid var(--line-2);border-radius:12px;padding:8px 10px}
.pmeta dt{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.pmeta dd{margin:0;font-weight:600;font-variant-numeric:tabular-nums;font-size:14px}
.units{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0;padding:0}
.units li{font-size:13.5px;padding:5px 10px;border-radius:8px;background:color-mix(in srgb,var(--accent-2) 11%,transparent)}
.hl{padding-left:18px;display:grid;gap:8px;color:var(--ink-2)}
.gate{font-weight:600;margin:12px 0}.gate span{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--good);margin-right:8px}
.findings-line{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13px;margin:10px 0}
.fl{display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap}.fl b{color:var(--muted);font-weight:600}
.sev{padding:2px 8px;border-radius:999px;font-weight:600;font-size:12px;border:1px solid currentColor}
.sev-critical{color:var(--crit)}.sev-major{color:var(--warn)}.sev-minor{color:var(--minor)}.sev-none{color:var(--good)}
.pnav{display:flex;flex-wrap:wrap;gap:10px;margin-top:24px}.pnav a{padding:6px 12px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-size:14px;background:var(--surface)}
.routine{list-style:none;margin:16px 0;padding:0;display:grid;gap:10px}
.routine li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:0 12px;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:14px 16px}
.routine .step-n{font:400 34px/1 var(--display);color:var(--accent);grid-row:span 3}.routine b{font-size:16px}.routine .who{margin:0;font-size:13px;color:var(--accent-2);font-weight:600}.routine p{margin:6px 0 0;font-size:14px;color:var(--ink-2)}
.diffs{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin:18px 0}
.diff{padding:18px;border-radius:16px;background:linear-gradient(160deg,color-mix(in srgb,var(--accent) 9%,var(--surface)),var(--surface));border:1px solid var(--line)}
.diff b{display:block;font:400 30px/1.05 var(--display)}.diff span{font-size:14px;color:var(--ink-2)}
.incidents{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.incident{border:1px solid var(--line);border-radius:16px;padding:16px;background:var(--surface)}.incident h4{margin:0 0 6px}.incident p{margin:0;font-size:14px;color:var(--ink-2)}
.note{border-left:3px solid var(--accent-2);padding:4px 0 4px 14px;color:var(--ink-2);font-size:14.5px}
.caveats{padding-left:18px;display:grid;gap:10px;color:var(--ink-2)}.caveats b{color:var(--ink)}
.sheet .cc-prelude h2{display:none}.sheet .cc-sub{display:none}
.pgrid{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.pcard{border:1px dashed var(--line);border-radius:16px;padding:16px}.pcard h3{font:650 17px/1.3 var(--sans);margin:10px 0 6px}.pcard p{margin:0;font-size:14px;color:var(--ink-2)}
.ptop{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.ptop h3{margin:0}.pn{font:400 34px/1 var(--display);color:var(--accent)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.bdot{width:7px;height:7px;border-radius:50%;background:var(--muted)}.badge-done .bdot{background:var(--good)}.badge-in-progress .bdot{background:var(--accent-2)}
.badge-pending{color:var(--muted)}.badge-pending .bdot{background:transparent;border:1.5px dashed var(--muted)}
.pstats{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:12px 0 18px}
.pstats div{border:1px solid var(--line);border-radius:16px;padding:14px;background:var(--surface)}.pstats b{display:block;font:400 36px/1 var(--display)}.pstats span{font-size:13px;color:var(--ink-2)}
.chat{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.msg{display:grid;gap:4px}.msg time{font:12px var(--mono);color:var(--muted)}
.msg p{margin:0;background:linear-gradient(160deg,color-mix(in srgb,var(--accent) 13%,var(--surface)),color-mix(in srgb,var(--accent-2) 9%,var(--surface)));
  border:1px solid var(--line);border-radius:18px 18px 18px 6px;padding:11px 15px;font-size:15px;justify-self:start;max-width:100%;overflow-wrap:anywhere}
.msg.attach p{background:var(--surface-2);font-style:italic;color:var(--muted)}
.prole{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px;margin:10px 0}.prole pre{color:var(--ink-2)}
.prole.common{border-color:color-mix(in srgb,var(--accent) 40%,var(--line))}
.scripts{columns:2 220px;padding-left:18px}.scripts a{font:13px var(--mono)}
.bign{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin:16px 0}
.bign div{border-radius:18px;padding:18px;background:var(--surface);border:1px solid var(--line)}
.bign b{display:block;font:400 clamp(40px,6vw,56px)/1 var(--display)}.bign span{display:block;font-weight:600;margin:6px 0}.bign p{margin:0;color:var(--ink-2);font-size:13.5px}
.measures{display:grid;gap:10px;margin:16px 0}.measures dt{font-weight:650;color:var(--accent)}.measures dd{margin:2px 0 0;font-size:14px;color:var(--ink-2)}
.fig{margin:22px 0;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px}
.fig figcaption{display:flex;flex-direction:column;margin-bottom:8px}.fig figcaption span{color:var(--muted);font-size:13px}
.bars-box{overflow-x:auto}.bars{display:block;width:100%;min-width:560px;height:auto;font-family:var(--sans)}
.bars .bg{stroke:var(--line);stroke-width:1}.bars .bt{fill:var(--muted);font-size:11px}.bars .bl{fill:var(--ink);font-size:13px;font-weight:600}
.bars .bs{fill:var(--muted);font-size:11px}.bars .bv{fill:var(--ink-2);font-size:12px;font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:14px;list-style:none;margin:0 0 8px;padding:0;font-size:13px;color:var(--ink-2)}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
details{margin:18px 0;border:1px solid var(--line);border-radius:16px;background:var(--surface);padding:4px 16px}
details summary{cursor:pointer;padding:12px 0;font-weight:600}details .tw{border:0;margin:0 -16px 8px}
/* motion: everything is visible without JS; with it, things wait for their reveal */
.js .reveal{opacity:0;transform:translateY(26px);transition:opacity .8s cubic-bezier(.2,.7,.2,1),transform .8s cubic-bezier(.2,.7,.2,1)}
.js .reveal.in{opacity:1;transform:none}
.js .nt.reveal{transition-delay:calc(var(--i)*70ms)}
.js .reveal:not(.in) s.strike::after{transform:scaleX(0)}
.js .reveal:not(.in) .ph-bar span{transform:scaleY(0)}
.js .reveal:not(.in) .struck li,.js .reveal:not(.in) .tiers li{opacity:0;transform:translateY(14px)}
.struck li,.tiers li{transition:opacity .6s,transform .6s;transition-delay:calc(var(--i,0)*80ms)}
.js .hero-in{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}
.js h1.hero-in{animation-delay:.05s}.js .lede.hero-in{animation-delay:.12s}.js .htiles.hero-in{animation-delay:.2s}.js .climb.hero-in{animation-delay:.28s}
@keyframes rise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
.js .climb.hero-in{animation-name:fade}
@keyframes fade{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}.js .reveal,.js .reveal *{opacity:1!important;transform:none!important}html{scroll-behavior:auto}}
@media print{.bar,.theme,.panel{display:none}.js .reveal{opacity:1;transform:none}}

.rules{padding:40px 0 8px}.rules .ntiles{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.rules .nt{min-height:0;gap:6px}.rules .nt b{font:400 clamp(28px,3.4vw,40px)/1 var(--display);letter-spacing:-.01em}
.rules .nt p{margin:0;color:var(--ink-2);font-size:14px}
.hero .lede em{font-style:normal;color:var(--ink)}
.era-note{color:var(--muted);font-size:14px}
"""

CSS3 = r"""
/* the hero's two claims, the climb and its iteration beats (round five's page rebuild) */
.claims{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:0 0 56px;align-items:stretch}
@media (max-width:900px){.claims{grid-template-columns:minmax(0,1fr)}}
.claim{background:var(--surface);border:1px solid var(--line);border-radius:24px;padding:clamp(20px,3vw,32px);box-shadow:var(--shadow);min-width:0;display:flex;flex-direction:column;gap:14px}
.claim-k{margin:0;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:650}
.claim h2{font:400 clamp(40px,5.4vw,66px)/.95 var(--display);letter-spacing:-.02em;margin:0}
.claim-line{margin:0;color:var(--ink-2);font-size:15.5px;line-height:1.5}.claim-line b{color:var(--ink)}
.claim-nums{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.claim-nums li{border-top:1px solid var(--line);padding-top:10px;min-width:0}
.cl-n{display:block;line-height:1}.cl-n .num-big{font-size:clamp(34px,4vw,50px)}
.claim-prod .cl-n .num-big{font-size:clamp(28px,3.1vw,38px)}
.spread{margin:2px 0 0}.spread svg{display:block;width:100%;height:auto;overflow:visible}
.sp-g{stroke:var(--line)}.sp-one{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:4 4;opacity:.6}.sp-t{fill:var(--muted);font-size:11px}.sp-rust{fill:var(--ink);font-weight:650}
.sp-l{fill:var(--ink);font-size:12.5px;font-weight:650}
@media (max-width:520px){.sp-t{font-size:16px}.sp-l{font-size:17px}}
.sp-q{fill:var(--s3);stroke:var(--s3);stroke-width:2}.sp-n{fill:var(--surface);stroke:var(--s3);stroke-width:2.5}.sp-p{fill:var(--accent);stroke:var(--surface);stroke-width:1.5}
.spread figcaption{display:flex;flex-wrap:wrap;gap:4px 16px;color:var(--muted);font-size:12px;margin-top:2px}.spread figcaption span{display:inline-flex;align-items:center;gap:6px}
.sp-k{display:inline-block;width:10px;height:10px;border-radius:50%;border:2.5px solid var(--s3)}.sp-kq{background:var(--s3)}.sp-kp{border-radius:2px;background:var(--accent);border-color:var(--accent);transform:rotate(45deg) scale(.85)}
.cl-l{display:block;color:var(--muted);font-size:13px;line-height:1.35;margin-top:6px}
.claim-prod .claim-nums{grid-template-columns:minmax(0,1fr)}
.claim-prod .claim-nums li{display:grid;grid-template-columns:minmax(150px,.46fr) minmax(0,1fr);gap:4px 14px;align-items:center}
.claim-prod .cl-l{margin-top:0}
@media (max-width:520px){.claim-prod .claim-nums li{grid-template-columns:minmax(0,1fr)}.claim-nums{grid-template-columns:minmax(0,1fr)}.claim-nums li{display:grid;grid-template-columns:minmax(100px,.5fr) minmax(0,1fr);gap:4px 12px;align-items:center}.claim-prod .claim-nums li{grid-template-columns:minmax(100px,.5fr) minmax(0,1fr)}}
.claim-facts{margin:0;padding-left:18px;color:var(--ink-2);font-size:14px;line-height:1.45}.claim-facts li{margin:6px 0}.claim-facts b{color:var(--ink)}
.claim-foot{margin:auto 0 0;padding-top:6px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}.claim-foot .links,.claim-foot .more{margin:0}
.cl-note{color:var(--muted);font-size:12.5px}
.climb-k{margin:0 0 8px}.climb-h{font:400 clamp(34px,5vw,60px)/1 var(--display);letter-spacing:-.02em;margin:0 0 18px}
.hero .climb .cc-hero{margin:0}
.beats{list-style:none;margin:22px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:12px}
.bc{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px 18px;scroll-margin-top:70px;min-width:0;display:flex;flex-direction:column}
.bc:target{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.bc-k{margin:0 0 4px;font-size:11.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}.bc-k b{color:var(--ink);letter-spacing:.06em}.bc-date{margin-left:4px}
.bc h3{font:400 26px/1.08 var(--display);margin:0 0 8px;letter-spacing:-.01em}
.bc-what{margin:0 0 10px;font-size:13.5px;line-height:1.45;color:var(--ink-2)}
.bc-close{margin:auto 0 6px;font-size:13.5px;line-height:1.4}.bc-close b{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:block}
.bc-chart{margin:0;font-size:12.5px;color:var(--muted)}
.upstream{margin-top:56px}
.num-big .sl{margin:0 .02em}
"""

CSS2 = r"""
/* same pixels, four engines (from the F# port's page) */
/* same pixels, different engines: one screenshot, three engines */
.sbs{padding:clamp(36px,5vw,64px) 0 clamp(36px,5vw,64px);border-top:1px solid var(--line-2);scroll-margin-top:52px}
.sbs-grid{display:grid;gap:clamp(24px,4vw,56px);align-items:center;grid-template-columns:minmax(0,1fr)}
@media (min-width:900px){.sbs-grid{grid-template-columns:minmax(0,1.08fr) minmax(0,1fr)}}
.sbs-shot,.sbs-copy{margin:0;min-width:0}
.sbs-frame{border-radius:16px;overflow:hidden;border:1px solid var(--line);background:#fff;box-shadow:var(--shadow)}
.sbs-frame img{display:block;width:100%;height:auto;aspect-ratio:8/5}
.sbs-shot figcaption{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin-top:14px;color:var(--muted);font-size:13.5px}
.sbs-shot figcaption>span:last-child{flex:1 1 260px;min-width:0}
.sbs-three{display:grid;gap:10px}
.sbs h2{font:400 clamp(44px,6.4vw,84px)/.95 var(--display);letter-spacing:-.02em;margin:0 0 18px;text-wrap:balance}
.sbs-badge{display:inline-flex;align-items:center;gap:8px;padding:7px 14px 7px 9px;border-radius:999px;font-weight:650;font-size:14.5px;color:var(--good);white-space:nowrap;
  background:color-mix(in srgb,var(--good) 10%,var(--surface));border:1px solid color-mix(in srgb,var(--good) 45%,var(--line))}
.sbs-badge svg{width:19px;height:19px;flex:none}.sbs-badge circle{fill:var(--good)}.sbs-badge path{fill:none;stroke:var(--surface);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.sbs-badge.sbs-differ{color:var(--crit);border-color:var(--crit);background:var(--surface)}
.sbs-rows{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:20px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}
.sbs-row{--c:var(--muted);display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:end;gap:4px 16px;padding:16px 18px 0}
.sbs-row+.sbs-row{border-top:1px solid var(--line-2)}
.sbs-rust{--c:var(--s1)}.sbs-fsharp{--c:var(--accent)}
.sbs-name{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;margin:0 0 6px;min-width:0}.sbs-name b{font-size:18px;letter-spacing:-.01em}
.sbs-tag{font:700 11.5px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;padding:5px 9px;border-radius:999px;color:var(--c);
  border:1px solid color-mix(in srgb,var(--c) 50%,var(--line));background:color-mix(in srgb,var(--c) 8%,var(--surface))}
.sbs-x{flex-basis:100%;font-size:13px;font-weight:600;color:var(--ink-2)}
.sbs-rate{display:flex;flex-direction:column;align-items:flex-end;text-align:right;margin:0 0 8px;min-width:0}
.sbs-n{font:400 clamp(40px,4.2vw,58px)/1 var(--display);letter-spacing:-.02em;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink)}
.sbs-fsharp .sbs-n{background:linear-gradient(160deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.sbs-u{color:var(--muted);font-size:12.5px}.sbs-u-live{display:none}.sbs.live .sbs-u-live{display:block}.sbs.live .sbs-u-rate{display:none}
.sbs-lane{grid-column:1/-1;display:block;height:10px;margin:0 -18px;border-top:1px solid var(--line-2);background-color:color-mix(in srgb,var(--c) 7%,var(--surface));
  background-image:radial-gradient(circle,var(--c) 0 2.2px,transparent 2.8px);background-size:16px 10px;background-repeat:repeat-x;background-position:0 0}
.sbs-cap{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;justify-content:space-between;color:var(--muted);font-size:13.5px;margin:16px 0 0}
.sbs-cap>span{flex:1 1 260px;min-width:0}
.sbs-thumbs{display:grid;gap:10px;grid-template-columns:repeat(3,minmax(0,1fr));margin:18px 0}
.sbs-thumbs figure{margin:0;min-width:0}.sbs-thumbs .sbs-frame{border-radius:10px;box-shadow:none}
.sbs-thumbs figcaption{display:flex;flex-direction:column;gap:2px;margin-top:8px;font-size:12.5px;color:var(--muted);overflow-wrap:anywhere}.sbs-thumbs figcaption b{color:var(--ink);font-size:14px}
@media (max-width:560px){.sbs-thumbs{grid-template-columns:minmax(0,1fr)}.sbs-row{grid-template-columns:minmax(0,1fr);gap:2px;padding:14px 14px 0}.sbs-lane{margin:0 -14px}.sbs-x{flex-basis:auto;margin-left:auto}.sbs-rate{align-items:flex-start;text-align:left}.sbs-n{font-size:40px}}
a.sn,span.sn{color:inherit;text-decoration:none}
a.sn{border-bottom:1px dotted color-mix(in srgb,currentColor 40%,transparent)}
a.sn:hover,a.sn:focus-visible{color:var(--accent);border-bottom-color:var(--accent)}
.num-big a.sn,.sbs-n.sn{border-bottom:0}
.htiles .ht{text-decoration:none;color:var(--ink);transition:transform .2s,border-color .2s}.htiles .ht:hover,.htiles .ht:focus-visible{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--line))}
.hero .lede em{font-style:normal;color:var(--ink);font-weight:600}
.sbs-warn{margin:14px 0 0;padding:12px 14px;border-radius:14px;border:1px solid color-mix(in srgb,var(--warn) 45%,var(--line));background:color-mix(in srgb,var(--warn) 9%,var(--surface));font-size:14.5px;color:var(--ink-2)}
.sbs-warn b{color:var(--ink)}
.sbs-oncrack{--c:var(--accent-2)}
.sbs-oncrack .sbs-n{background:linear-gradient(160deg,var(--accent-2),var(--accent));-webkit-background-clip:text;background-clip:text;color:transparent}
.sbs-thumbs{grid-template-columns:repeat(4,minmax(0,1fr))}
@media (max-width:720px){.sbs-thumbs{grid-template-columns:repeat(2,minmax(0,1fr))}}
/* reads while writing */
.mx-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));margin:26px 0 8px}
.mx{margin:0;padding:20px;border-radius:20px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow)}
.mx figcaption{display:flex;flex-direction:column;gap:2px;margin-bottom:14px}.mx figcaption b{font-size:15px}.mx figcaption>span:last-child{font-size:13.5px;color:var(--muted)}
.mx-big{font:400 clamp(54px,8vw,92px)/.9 var(--display);letter-spacing:-.03em}
.mx-real{border-color:color-mix(in srgb,var(--accent) 45%,var(--line))}.mx-real .mx-big{color:var(--accent)}
.mx-bars{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.mx-bars li{display:grid;grid-template-columns:72px minmax(0,1fr) 76px;align-items:center;gap:10px;font-size:13.5px}
.mx-l{color:var(--ink-2);font-weight:600}.mx-v{text-align:right;font-variant-numeric:tabular-nums}
.mx-bar{height:12px;border-radius:6px;background:var(--surface-2);overflow:hidden}.mx-bar span{display:block;height:100%;border-radius:6px;background:var(--muted)}
.mx-rust .mx-bar span{background:var(--s1)}.mx-fsharp .mx-bar span{background:var(--accent)}.mx-oncrack .mx-bar span{background:linear-gradient(90deg,var(--accent-2),var(--accent))}
.js .reveal:not(.in) .mx-bar span{transform:scaleX(0)}.mx-bar span{transform-origin:left;transition:transform 1s cubic-bezier(.2,.7,.2,1) .2s}
/* what it does */
.dtiles{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))!important}
.dtiles .nt{min-height:0;gap:8px}.dtiles .nt b{font:400 clamp(26px,3vw,34px)/1.05 var(--display)}.dtiles .nt p{margin:0;color:var(--ink-2);font-size:14px}
.rule{border-left:3px solid var(--good);padding:6px 0 6px 14px;color:var(--ink-2)}.rule b{color:var(--ink)}
/* fan-out */
.fan{margin:24px 0 8px;border:1px solid var(--line);border-radius:22px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}
.fan-r{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.fan-tabs{display:flex;gap:6px;padding:12px 12px 0;flex-wrap:wrap}
.fan-tabs label{cursor:pointer;padding:7px 14px;border-radius:999px;border:1px solid var(--line);font-size:14px;font-weight:600;color:var(--ink-2);background:var(--bg)}
#fan-n100:checked~.fan-tabs label[for=fan-n100],#fan-n500:checked~.fan-tabs label[for=fan-n500],#fan-n1000:checked~.fan-tabs label[for=fan-n1000],#fan-n2000:checked~.fan-tabs label[for=fan-n2000]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
#fan-n100:focus-visible~.fan-tabs label[for=fan-n100],#fan-n500:focus-visible~.fan-tabs label[for=fan-n500],#fan-n1000:focus-visible~.fan-tabs label[for=fan-n1000],#fan-n2000:focus-visible~.fan-tabs label[for=fan-n2000]{outline:2px solid var(--accent);outline-offset:2px}
.fan-pane{display:none;padding:6px 12px 14px}
#fan-n100:checked~.fan-panes .fan-p100,#fan-n500:checked~.fan-panes .fan-p500,#fan-n1000:checked~.fan-panes .fan-p1000,#fan-n2000:checked~.fan-panes .fan-p2000{display:block}
.fan-lanes{list-style:none;margin:0;padding:0}
.fan-lane{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:6px 18px;align-items:center;padding:12px 4px;border-top:1px solid var(--line-2)}
.fan-lane:first-child{border-top:0}
.fan-info p{margin:0}.fan-name{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.fan-name b{font-size:17px}
.fan-rate{font:400 clamp(28px,3.4vw,40px)/1.05 var(--display);font-variant-numeric:tabular-nums}.fan-rate span{font:500 13px var(--sans);color:var(--muted)}
.fan-sub{font-size:13px;color:var(--muted)}.fan-sub b{color:var(--crit);font-variant-numeric:tabular-nums}
.fan-tag{font:700 11px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;padding:4px 8px;border-radius:999px;border:1px solid var(--line);color:var(--ink-2)}
.fan-tag.fan-lead{color:var(--good);border-color:color-mix(in srgb,var(--good) 50%,var(--line))}.fan-tag.fan-behind{color:var(--crit);border-color:color-mix(in srgb,var(--crit) 45%,var(--line))}
.fan-key{margin:8px 4px 0;font-size:13px;color:var(--muted)}
.fan-svg{display:block;width:100%;height:auto;overflow:visible}
.fan-wire{stroke:var(--line);stroke-width:2}.fan-lines line{stroke:var(--line);stroke-width:1}
.fan-hub{fill:var(--surface);stroke:var(--fc,var(--muted));stroke-width:3}
.fan-grid circle{fill:var(--fc,var(--muted))}
.fan-p{fill:var(--fc,var(--muted));opacity:0}
.fan-rust{--fc:var(--s1)}.fan-fsharp{--fc:var(--accent)}.fan-oncrack{--fc:var(--accent-2)}.fan-reference{--fc:var(--muted)}
@keyframes fan-move{0%{transform:translateX(0);opacity:0}6%{opacity:1}94%{opacity:1}100%{transform:translateX(226px);opacity:0}}
@keyframes fan-flash{0%{opacity:1}100%{opacity:.28}}
.fan-p{animation:fan-move var(--p) linear infinite}
.fan-grid{animation:fan-flash var(--q) ease-out infinite;opacity:.28}
@media (prefers-reduced-motion:reduce){.fan-p{display:none}.fan-grid{opacity:.8}}
.fan-live{white-space:nowrap}
@media (max-width:640px){.fan-lane{grid-template-columns:minmax(0,1fr)}.fan-rate{font-size:30px}}
/* proofs */
.ptiles{display:grid;gap:10px;grid-template-columns:repeat(4,minmax(0,1fr));margin:24px 0 0}
@media (max-width:1000px){.ptiles{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:720px){.ptiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
.pt-g{font-family:var(--mono)!important;font-size:.7em;color:var(--accent)}
.num-big i.sl,.pt-n i.sl{font-size:.75em;color:var(--accent);margin:0 .04em}
.pt{display:flex;flex-direction:column;gap:4px;padding:18px;border-radius:20px;background:var(--surface);border:1px solid var(--line);color:var(--ink);text-decoration:none;box-shadow:var(--shadow);transition:transform .25s,border-color .25s}
.pt:hover,.pt:focus-visible{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--line))}
.pt-n{font:400 clamp(40px,5vw,56px)/1 var(--display);letter-spacing:-.02em}.pt-n i{font-style:normal;color:var(--accent);font-size:.6em}
.pt b{font-size:15px}.pt p{margin:0;color:var(--ink-2);font-size:13.5px}
/* CTA */
.cta-grid{display:grid;gap:24px;align-items:end;grid-template-columns:minmax(0,1fr)}
@media (min-width:900px){.cta-grid{grid-template-columns:minmax(0,1.4fr) minmax(0,1fr)}}
.cta-links{display:flex;flex-wrap:wrap;gap:10px;margin:0}
.btn{display:inline-flex;gap:8px;align-items:center;padding:13px 20px;border-radius:999px;background:var(--ink);color:var(--bg);text-decoration:none;font-weight:650}
.btn:hover,.btn:focus-visible{background:var(--accent)}.btn-2{background:var(--surface);color:var(--ink);border:1px solid var(--line)}
/* panels: tables, results, the ledger */
.res{display:inline-block;font-size:12px;font-weight:650;padding:2px 8px;border-radius:999px;border:1px solid currentColor;margin-right:6px}
.res-ok{color:var(--good)}.res-bad{color:var(--crit)}
.tw td small,.tw th small{display:block;color:var(--muted);font-size:11.5px;font-weight:400;margin-top:2px}
.tw.dense td small{display:inline;margin:0}
.ledger{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:6px}
.ledger li{display:grid;grid-template-columns:48px 104px minmax(0,1fr);gap:2px 12px;align-items:baseline;padding:10px 12px;border:1px solid var(--line-2);border-radius:12px;background:var(--surface);scroll-margin-top:110px}
.lg-id{font:12px var(--mono);color:var(--muted)}.lg-v{font-variant-numeric:tabular-nums;font-size:15px;white-space:nowrap}.lg-l{font-size:14px;color:var(--ink)}
.lg-h,.lg-f{grid-column:3;font-size:12.5px;color:var(--muted);overflow-wrap:anywhere}.lg-f a{margin-right:8px}.lg-f code{font-size:11.5px}
@media (max-width:560px){.ledger li{grid-template-columns:44px minmax(0,1fr)}.lg-l,.lg-h,.lg-f{grid-column:1/-1}}
.ledger li:target{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 10%,var(--surface))}
.ledger li.flash{animation:rowflash 2.4s ease-out}
@keyframes rowflash{0%,40%{background:color-mix(in srgb,var(--accent) 22%,transparent)}100%{background:transparent}}
html:not(.js) .panel:has(:target){visibility:visible;pointer-events:auto}
html:not(.js) .panel:has(:target) .scrim{opacity:1}
html:not(.js) .panel:has(:target) .sheet{transform:none}
.sheet-body h3[id]{scroll-margin-top:130px}
.lc{text-transform:none}
.beat.mix,.beat.does,.beat.fanout,.beat.proof-row,.beat.cta{padding:clamp(48px,7vw,88px) 0}
"""

JS = r"""
(function(){
  var root=document.documentElement;
  var btn=document.querySelector('.theme');
  function current(){var t=root.getAttribute('data-theme');if(t)return t;return matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
  function label(){if(btn){var c=current();btn.textContent=c==='dark'?'☀':'☾';btn.setAttribute('aria-label','Switch to '+(c==='dark'?'light':'dark')+' theme');}}
  if(btn){btn.addEventListener('click',function(){var next=current()==='dark'?'light':'dark';root.setAttribute('data-theme',next);try{localStorage.setItem('theme',next);}catch(e){}label();});label();}
  var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function fmt(v,dec){return v.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});}
  // counters: the HTML holds the final value; count up to it when it scrolls into view
  function count(el){var to=parseFloat(el.getAttribute('data-to')),dec=+el.getAttribute('data-dec')||0;if(reduce||!isFinite(to))return;
    var t0=null,d=1400;function step(t){if(!t0)t0=t;var k=Math.min((t-t0)/d,1),q=1-Math.pow(1-k,3);el.textContent=fmt(to*q,dec);if(k<1)requestAnimationFrame(step);else el.textContent=fmt(to,dec);}
    el.textContent=fmt(0,dec);requestAnimationFrame(step);}
  var els=[].slice.call(document.querySelectorAll('.reveal,.hero-in'));
  function show(el){el.classList.add('in');[].forEach.call(el.querySelectorAll('.count'),count);}
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){show(en.target);io.unobserve(en.target);}});},{rootMargin:'0px 0px -10% 0px',threshold:0.08});
    els.forEach(function(el){io.observe(el);});
  }else{els.forEach(show);}
  // a ticker: while el is on screen, call f(seconds since the last frame)
  function ticker(el,f){if(!el||reduce||!('IntersectionObserver' in window))return;var on=false,last=0,raf=0;
    function tick(t){var dt=last?Math.min((t-last)/1000,0.1):0;last=t;f(dt);if(on)raf=requestAnimationFrame(tick);}
    new IntersectionObserver(function(es){var vis=es[es.length-1].isIntersecting;if(vis&&!on){on=true;last=0;f(-1);raf=requestAnimationFrame(tick);}else if(!vis&&on){on=false;cancelAnimationFrame(raf);}},{threshold:0.2}).observe(el);}
  // same pixels, four engines: each counter adds its engine's measured req/s for every second the section is on screen
  var sbs=document.getElementById('sbs');
  if(sbs){var lanes=[].slice.call(sbs.querySelectorAll('.sbs-row')).map(function(t){return {rate:parseFloat(t.getAttribute('data-rate'))||0,n:t.querySelector('.sbs-n'),lane:t.querySelector('.sbs-lane'),c:0,x:0};});
    var peak=Math.max.apply(null,lanes.map(function(l){return l.rate;}))||1;
    ticker(sbs.querySelector('.sbs-rows'),function(dt){if(dt<0){if(!sbs.classList.contains('live')){sbs.classList.add('live');lanes.forEach(function(l){l.n.textContent='0';});}return;}
      lanes.forEach(function(l){l.c+=l.rate*dt;l.n.textContent=fmt(Math.floor(l.c),0);l.x=(l.x+160*dt*l.rate/peak)%1600;if(l.lane)l.lane.style.backgroundPosition=l.x.toFixed(2)+'px 0';});});}
  // fan-out: how far behind Rust each lane falls while you watch
  [].forEach.call(document.querySelectorAll('.fan-pane'),function(pane){
    var gaps=[].slice.call(pane.querySelectorAll('.fan-live')).map(function(s){return {gap:parseFloat(s.getAttribute('data-gap'))||0,b:s.querySelector('.fan-gap'),s:s,c:0,base:s.innerHTML};});
    ticker(pane,function(dt){if(dt<0){gaps.forEach(function(g){if(!g.live){g.live=true;g.s.innerHTML='behind Rust by <b class="fan-gap">0</b> messages since you looked';g.b=g.s.querySelector('.fan-gap');}});return;}
      gaps.forEach(function(g){g.c+=g.gap*dt;g.b.textContent=fmt(Math.floor(g.c),0);});});});
  // on a phone the chart scrolls sideways: start at the latest run
  var sc=document.querySelector('.climb .cc-scroll');if(sc&&sc.scrollWidth>sc.clientWidth)sc.scrollLeft=sc.scrollWidth;
  // draw the climb line once
  var pl=document.querySelector('.climb .cc-climb');
  if(pl&&pl.getTotalLength&&!reduce){try{var L=pl.getTotalLength();pl.style.strokeDasharray=L;pl.style.strokeDashoffset=L;pl.getBoundingClientRect();
    pl.style.transition='stroke-dashoffset 1.8s cubic-bezier(.6,0,.2,1) .5s';pl.style.strokeDashoffset=0;}catch(e){}}
  // side panels: :target drawers without JS; with it, opened by class so Esc, click-outside and focus all work.
  // A link to something inside a panel (a ledger row, a section) opens that panel and brings the thing into view.
  var mainEl=document.getElementById('main'),barEl=document.querySelector('.bar'),footEl=document.querySelector('footer.site');
  var openP=null,opener=null;
  function panelOf(el){return el&&el.closest?el.closest('.panel'):null;}
  function setInert(on){[mainEl,barEl,footEl].forEach(function(x){if(x){if(on)x.setAttribute('inert','');else x.removeAttribute('inert');}});}
  function reveal(p,t){var s=p.querySelector('.sheet');if(!t||t===p){s.scrollTop=0;return;}
    setTimeout(function(){var r=t.getBoundingClientRect(),sr=s.getBoundingClientRect();s.scrollTop+=r.top-sr.top-(t.tagName==='LI'?sr.height/3:120);
      if(t.tagName==='LI'){t.classList.remove('flash');void t.offsetWidth;t.classList.add('flash');}},60);}
  function openPanel(p,from,push,t,hash){
    if(openP===p){if(push)history.pushState({panel:p.id},'','#'+(hash||p.id));reveal(p,t);return;}
    if(openP)closePanel(true,true);
    openP=p;opener=from||null;p.classList.add('open');root.classList.add('locked');setInert(true);
    if(push)history.pushState({panel:p.id},'','#'+(hash||p.id));
    reveal(p,t);setTimeout(function(){p.querySelector('.sheet').focus({preventScroll:true});},40);
  }
  function closePanel(silent,keepFocus){
    if(!openP)return;var p=openP;openP=null;p.classList.remove('open');root.classList.remove('locked');setInert(false);
    if(!silent){if(history.state&&history.state.panel===p.id){history.back();}else if(location.hash){history.replaceState(null,'',location.pathname+location.search);}}
    if(!keepFocus){var back=opener;if(!back){var c=p.querySelector('[data-close]');back=c&&document.getElementById(c.getAttribute('href').slice(1));}
      if(back){if(!back.matches('a[href],button,input,[tabindex]'))back.setAttribute('tabindex','-1');back.focus({preventScroll:!!opener});}}
  }
  document.addEventListener('click',function(ev){
    var a=ev.target.closest&&ev.target.closest('a');if(!a)return;
    if(a.hasAttribute('data-close')){ev.preventDefault();closePanel(false);return;}
    var h=a.getAttribute('href')||'';
    if(h.charAt(0)==='#'&&h.length>1){var t=document.getElementById(h.slice(1)),p=panelOf(t);
      if(p){ev.preventDefault();openPanel(p,openP?opener:a,true,t,h.slice(1));}
      else if(openP&&t){ev.preventDefault();closePanel(false,true);setTimeout(function(){t.scrollIntoView({behavior:reduce?'auto':'smooth'});},60);}}
  });
  document.addEventListener('keydown',function(ev){
    if(!openP)return;
    if(ev.key==='Escape'){ev.preventDefault();closePanel(false);return;}
    if(ev.key==='Tab'){var f=[].filter.call(openP.querySelectorAll('a[href],button,summary,[tabindex]:not([tabindex="-1"])'),function(x){return x.offsetParent!==null||x===document.activeElement;});
      if(!f.length)return;var first=f[0],last=f[f.length-1];
      if(ev.shiftKey&&(document.activeElement===first||document.activeElement===openP.querySelector('.sheet'))){ev.preventDefault();last.focus();}
      else if(!ev.shiftKey&&document.activeElement===last){ev.preventDefault();first.focus();}}
  });
  window.addEventListener('popstate',function(){var id=location.hash.slice(1),t=id&&document.getElementById(id),p=panelOf(t);
    if(p)openPanel(p,null,false,t);else if(openP)closePanel(true);});
  var h0=location.hash.slice(1),t0=h0&&document.getElementById(h0),p0=panelOf(t0);if(p0)openPanel(p0,null,false,t0);
})();
"""


# ================================================================ build

def same_pixels_facts():
    sp = OC.get('same_pixels')
    if not sp:
        return None
    files = {}
    for a in sp['apps']:
        p = os.path.join(REPO, a['thumb'])
        files[a['key']] = open(p, 'rb').read() if os.path.exists(p) else None
    ok = (sp['identical'] and len({a['capture_sha256'] for a in sp['apps']}) == 1 and None not in files.values() and len(set(files.values())) == 1
          and bool(sp.get('image')) and os.path.exists(os.path.join(REPO, sp['image'])))
    pp = jload(R3PIX + '/pixel-parity.json')['room_capture']['png_sha256']
    ok = ok and pp['reference'] == pp['candidate'] == sp['apps'][0]['capture_sha256']
    return dict(sp, ok=ok)


def build():
    F = facts()
    FCTX['F'] = F
    cl = climb_chart.hero_chart()
    sp = same_pixels_facts()
    nav = ''.join('<li><a href="%s">%s</a></li>' % h for h in
                  [('#claim-fast', 'Faster'), ('#claim-prod', 'In production'), ('#climb', 'The climb'), ('#sbs', 'Same software'), ('#mix', 'Reads &amp; writes'), ('#does', 'What it does'), ('#fanout', 'Fan-out'), ('#check', 'Check it')])
    main = ''.join([hero(F, cl), same_software(F, sp), mix_beat(F), does_beat(F), fanout(F), proof(F), cta(F), more_row()])
    panels = [p_five(F), p_sbs(F, sp), p_mix(F), p_does(F), p_correct(F), p_durability(F), p_pixels(F), p_ceiling(F), p_rust(F), p_fanout(F), p_reliability(F), p_repro(F),
              p_fresh(F), p_upstream(F), p_prod(F), p_rounds(F, cl), p_climb(cl), p_rules(), p_port_era()]
    panels.append(p_ledger())          # last: it lists every row the others issued
    main = main.replace('__NROWS__', str(len(L.rows)))
    body = ''.join([
        '<a class="skip" href="#main">Skip to content</a>',
        '<header class="bar"><div class="wrap"><a class="brand" href="#top">on<span>Crack</span></a>'
        '<nav aria-label="Sections"><ol>%s</ol></nav><button class="theme" type="button" aria-label="Switch theme"></button></div></header>' % nav,
        '<main id="main">', main, '</main>',
        '<footer class="site"><div class="wrap"><p><b>Sources.</b> %s, %s, %s (the final run&#39;s report), %s (its raw data), %s (round one&#39;s data, review and results), %s, the git history of <code>crack</code>.</p>'
        '<p>onCrack is a fork of <a href="%s">the F# port</a> of Basecamp&#39;s ONCE Campfire. Campfire, the Rust port, its parity harness and vectors are &copy; <span data-lit="name">37signals</span>, LLC, MIT. '
        'Generated from the results by <code>site/build.py</code>, which refuses to show a number it cannot source.</p></div></footer>'
        % (flink('plans/oncrack.md'), flink('AGENTS.md'), flink(R5REPORT), flink(R5F + '/', R5F + '/'), flink(R1 + '/', R1 + '/'), flink('bench/results/oncrack-log.jsonl'), e(META['port_page'])),
        '<div class="panels">%s</div>' % ''.join(panels),
    ])
    page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>onCrack</title><meta name="description" content="%s">'
            '<meta name="color-scheme" content="light dark">'
            '<script>document.documentElement.className+=" js";try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}</script>'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap" media="print" onload="this.media=\'all\'">'
            '<style>%s%s%s</style></head><body>%s<script>%s</script></body></html>\n'
            % (e(META['description']), climb_chart.CSS.strip() + climb_chart.CSS_HERO.strip(), CSS.strip(), CSS2.strip() + CSS3.strip(), body, JS.strip()))
    c = check(page)
    for w in crosscheck(F):
        print('note: ' + w)
    if c.errors:
        sys.stderr.write('build: %d problem(s); index.html not written:\n  %s\n' % (len(c.errors), '\n  '.join(c.errors[:300])))
        sys.exit(1)
    out = os.path.join(REPO, 'index.html')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('wrote %s (%s bytes; %d numbers in the ledger, %d identifiers marked as names)' % (out, format(len(page.encode('utf-8')), ','), len(L.rows), len(c.lits)))


if __name__ == '__main__':
    build()
