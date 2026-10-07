#!/usr/bin/env python3
"""Render index.html (at the repository root): onCrack's page, whose hero is the climb chart.

Python 3 standard library only. The page is short: the title, one paragraph, four numbers, the climb chart and a row of links.
Everything else sits in a side panel a link opens. Panels are CSS :target drawers, so they work with JavaScript off; with it on
they also close on Esc or a click outside, keep focus inside while open, and give it back on close.

    python3 site/build.py            # write index.html

bench/progress/build.py runs this after every logged run (bench/quick log), so the chart stays current. The chart is
bench/progress/climb.py: onCrack's throughput as a share of Rust's, from the F# port's final result (bench/results/phase7-final)
to the latest logged run (bench/results/oncrack-log.jsonl). The port-era dots (Phase 7 of the port this was forked from) are in a panel.
site/data.json and site/collect_tokens.py are the port's story and token ledger; this page doesn't draw them.
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

SITE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SITE)
sys.path.insert(0, os.path.join(REPO, 'bench', 'progress'))
import climb as climb_chart  # noqa: E402  (bench/progress/climb.py)

EDT = timezone(timedelta(hours=-4))
PORT_REPO = 'https://github.com/ckluis/once-campfire-fSharp'


def e(s):
    return html.escape(str(s), quote=True)


def n(x):
    return format(int(x), ',')


def ts(iso):
    if not iso:
        return None
    if iso.endswith('Z'):
        iso = iso[:-1] + '+00:00'
    d = datetime.fromisoformat(iso)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def local(iso, fmt='%-d %b %H:%M'):
    d = ts(iso)
    return d.astimezone(EDT).strftime(fmt) if d else ''


def duration(a, b):
    if not a or not b:
        return ''
    s = int((ts(b) - ts(a)).total_seconds())
    h, m = s // 3600, (s % 3600) // 60
    return '%dh %02dm' % (h, m) if h else '%d min' % m


def para(text):
    return ''.join('<p>%s</p>' % inline(p).replace('\n', '<br>') for p in str(text).split('\n\n'))


def inline(text):
    """Escape, then render `code` spans."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', e(text))


def pills(items):
    return '<ul class="pills">%s</ul>' % ''.join('<li>%s</li>' % e(i) for i in items)


def table(columns, rows, caption=None, num_from=1, cls='', ratio_col=None):
    head = ''.join('<th scope="col"%s>%s</th>' % (' class="num"' if i >= num_from else '', e(c)) for i, c in enumerate(columns))
    body = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            if i == 0:
                cells.append('<th scope="row">%s</th>' % e(c))
            elif ratio_col is not None and i == ratio_col:
                cells.append(ratio_cell(c))
            else:
                cells.append('<td class="num">%s</td>' % e(c) if i >= num_from else '<td>%s</td>' % e(c))
        body.append('<tr>%s</tr>' % ''.join(cells))
    cap = '<caption>%s</caption>' % e(caption) if caption else ''
    return ('<div class="tw %s"><table>%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (cls, cap, head, ''.join(body)))


def ratio_cell(text):
    m = re.match(r'([0-9.]+)', text)
    v = float(m.group(1)) if m else 0
    pct = max(0.0, min(v / 1.25, 1.0)) * 100
    tone = 'ahead' if v >= 1.0 else 'behind'
    return ('<td class="num ratio"><span class="rbar" aria-hidden="true"><span class="rfill %s" style="width:%.1f%%"></span>'
            '<span class="rone" style="left:80%%"></span></span><span class="rval">%s</span></td>' % (tone, pct, e(text)))


def panel(pid, kicker, title, body, back):
    return ('<div class="panel" id="%s" role="dialog" aria-modal="true" aria-labelledby="%s-t">'
            '<a class="scrim" href="#%s" data-close tabindex="-1" aria-hidden="true"></a>'
            '<div class="sheet" tabindex="-1"><header class="sheet-head"><div><p class="kicker">%s</p><h2 id="%s-t">%s</h2></div>'
            '<a class="x" href="#%s" data-close aria-label="Close panel"><span aria-hidden="true">&times;</span></a></header>'
            '<div class="sheet-body">%s<p class="back"><a href="#%s" data-close>&larr; Back to the page</a></p></div></div></div>'
            % (pid, pid, back, kicker, pid, title, back, body, back))


def details(pid, label='The details'):
    return '<a class="more" href="#%s">%s <span aria-hidden="true">&rarr;</span></a>' % (pid, e(label))



# ---------------------------------------------------------------- the page

def counter(value, dec=0, unit='', prefix=''):
    shown = ('{:,.%df}' % dec).format(value)
    return ('<span class="num-big">%s<b class="count" data-to="%s" data-dec="%d">%s</b>%s</span>'
            % (('<i>%s</i>' % e(prefix)) if prefix else '', ('%.' + str(dec) + 'f') % value, dec, shown,
               ('<i>%s</i>' % e(unit)) if unit else ''))


def hero(cl):
    latest, vs_port = cl.get('latest'), cl.get('vs_port')
    pts = cl.get('points') or []
    last_t = pts[-1]['time'].astimezone(EDT).strftime('%a %-d %b, %H:%M EDT') if pts else ''
    measured = len([p for p in pts if p['unit'] != 'port final'])
    if latest is None:
        head, live, tiles = 'onCrack.', 'The first measured runs will appear on the chart below.', ''
    else:
        head = 'onCrack.'
        live = ('The same Campfire, pixel for pixel, on a server that is free to do less work. Forked from the F# port, which already beat Rust; '
                'scored on its own, against Rust and against the port. Latest: <strong>%.2f&times;</strong> Rust, <strong>%.2f&times;</strong> the port.'
                % (latest, vs_port))
        tiles = ''.join('<div class="ht">%s<span>%s</span></div>' % (a, b) for a, b in [
            (counter(latest, 2, '×'), 'of Rust, latest run'),
            (counter(vs_port, 2, '×'), 'of the F# port, latest run'),
            (counter(cl['port_level'], 2, '×'), 'the port, of Rust, where onCrack starts'),
            (counter(measured, 0, ''), 'measured run%s of onCrack so far' % ('' if measured == 1 else 's')),
        ])
    return ('<section class="hero" id="top" aria-labelledby="hero-h"><div class="glow" aria-hidden="true"></div><div class="wrap">'
            '<p class="kicker hero-in">Basecamp&#39;s ONCE Campfire &middot; the F# port, unchained</p>'
            '<h1 id="hero-h" class="hero-in">%s</h1><p class="lede hero-in">%s</p>'
            '<div class="htiles hero-in">%s</div>'
            '<figure class="climb hero-in" id="climb" aria-labelledby="climb-cap">%s'
            '<figcaption id="climb-cap"><span><b>The climb.</b> onCrack&#39;s throughput as a share of Rust&#39;s, one dot per version '
            '(geometric mean of the five workloads, 16 connections), starting from the F# port&#39;s final result (the dotted line). Hover, tap or tab to a dot '
            'for its numbers beside Rust&#39;s, the port&#39;s and Rails&#39;. Latest: %s.</span>%s</figcaption></figure>'
            '<p class="btw" id="btw"><a href="#p-port-era">The port&#39;s own climb</a> <span>The dots that came before, kept off this line.</span></p>'
            '</div></section>' % (head, live, tiles, cl['chart'], e(last_t), details('p-climb', 'How to read it')))


def rules():
    items = [('p-rules', 'Same pixels', 'Every parity screenshot equals Rails&#39;, in every seed. Server HTML, the DOM and Cable frames may differ.'),
             ('p-rules', 'Always correct', 'No stale read after a write, no data in the wrong user&#39;s response. Every cache states its invalidation rule and has tests that try to break it.'),
             ('p-rules', 'Durability is opt-in', 'Anything that weakens it is measured both ways, documented, and ships behind a setting that defaults to Rails&#39; durability.'),
             ('p-scoring', 'Scored twice', 'Every ratio is against Rust and against the F# port, from the same harness, seed and pinned CPUs, and never called a port result.')]
    tiles = ''.join('<a class="nt reveal" href="#%s" style="--i:%d"><b>%s</b><p>%s</p></a>' % (pid, i, t, d) for i, (pid, t, d) in enumerate(items))
    return ('<section class="rules" id="rules" aria-label="The rules"><div class="wrap"><p class="kicker reveal">The rules</p>'
            '<div class="ntiles">%s</div></div></section>' % tiles)


def more_row():
    links = [('p-climb', 'Every run'), ('p-scoring', 'How it is scored'), ('p-rules', 'The rules'), ('p-port-era', 'The port&#39;s climb')]
    return ('<section class="more-row" id="more" aria-label="Everything else"><div class="wrap reveal"><p class="kicker">Everything else</p>'
            '<p class="links">%s</p></div></section>' % ''.join('<a class="more" href="#%s">%s <span aria-hidden="true">&rarr;</span></a>' % (p, l) for p, l in links))


# ---------------------------------------------------------------- panels

def p_climb(cl):
    pts = cl.get('points') or []
    rows = []
    for p in pts:
        rows.append('<tr%s><th scope="row">%s</th><td>%s</td><td>%s</td><td class="num">%.2f&times;</td><td>%s</td></tr>'
                    % ('' if p['kept'] else ' class="dropped"', e(p['time'].astimezone(EDT).strftime('%-d %b %H:%M')), e(p['unit'] or ''),
                       e(p['change']), p['ratio'], 'kept' if p['kept'] else 'reverted'))
    tbl = ('<div class="tw"><table><caption>Every dot, oldest first</caption><thead><tr><th scope="col">EDT</th><th scope="col">Unit</th>'
           '<th scope="col">Change</th><th scope="col" class="num">&times; Rust</th><th scope="col">Kept</th></tr></thead><tbody>%s</tbody></table></div>' % ''.join(rows))
    body = ''.join([
        '<p class="lead">The line is the geometric mean of onCrack&#39;s throughput over Rust&#39;s across the five benchmarked workloads '
        '(room page, messages page, sidebar, search, post a message) at 16 connections. Dots are spaced evenly in the order they ran, '
        'not by the clock. A dot that measured only some workloads carries the rest from the last kept run; its card greys them. '
        'The dotted line is the F# port&#39;s own ratio, where onCrack starts.</p>',
        '<h3>Read with care</h3><ul class="caveats">'
        '<li><b>The first dot is not onCrack.</b> It is the F# port&#39;s final result (<code>bench/results/phase7-final</code>, 3 reps), the starting point the fork is scored from.</li>'
        '<li><b>Most dots are provisional.</b> Tier 2 runs are one rep of only the workloads a change touches, on a published build mounted into a container. '
        'The number that counts is tier 3: a rebuilt image, three reps, all five workloads at 1 and 16 connections.</li>'
        '<li><b>Rust, the port and Rails are stored.</b> Their medians come from one session, <code>bench/results/phase7-final/</code>; onCrack is measured alone against them '
        'with the same warm-up, seed and pinned CPUs, not re-measured beside them each time.</li>'
        '<li><b>Rails is in the cards only.</b> At 1 to 2%% of Rust&#39;s throughput it would sit flat on the floor of the chart.</li>'
        '</ul>',
        tbl,
        '<p class="src">Source: <code>bench/results/oncrack-log.jsonl</code>, <code>bench/progress/history.json</code>, drawn by <code>bench/progress/climb.py</code>.</p>',
    ])
    return climb_panel('p-climb', 'The climb', 'How to read the chart', body, 'climb')


def climb_panel(pid, kicker, title, body, back):
    return panel(pid, kicker, title, body, back)


def p_scoring():
    body = ''.join([
        '<p class="lead">Same harness as the port&#39;s Phase 7: <code>bench/run</code> and <code>bench/quick</code> inside colima, the server pinned to CPUs 0-3 and the load generator to 4-7, '
        'host networking, the seed <code>parity/.seed/default</code> copied fresh for every run, every route warmed until flat, every response checked, every post&#39;s row counted.</p>',
        '<h3>Three tiers</h3><ul class="caveats">'
        '<li><b>Tier 1</b>, in process: <code>bench/db-micro</code> and the other micro projects, A/B on one change.</li>'
        '<li><b>Tier 2</b>, mounted: <code>bin/publish-mounted</code> builds the app, <code>bench/quick --mounted</code> runs it over <code>campfire-oncrack:app</code>; one rep of the workloads the change touches.</li>'
        '<li><b>Tier 3</b>, the rebuilt image: all five workloads at 1 and 16 connections, 3 reps. This is a dot&#39;s number.</li></ul>',
        '<h3>The references</h3><p>Stored medians of <code>bench/results/phase7-final/</code>: Rust, the F# port (<code>campfire-fsharp:app</code>, left untouched) and Rails, '
        'measured in one session. <code>bench/quick compare DIR</code> prints an onCrack run against Rust and against the port; every run is logged with '
        '<code>bench/quick log</code> and appears here. A session can also measure all four at once: <code>bench/run --apps reference,rust,fsharp,oncrack</code>.</p>',
        '<h3>Pixels</h3><p><code>bin/pixel-parity</code> runs the parity harness against Rails and reports only the screenshot layer, per seed. It is the one-command check of &ldquo;the UI is identical&rdquo;.</p>',
    ])
    return panel('p-scoring', 'Scoring', 'How onCrack is scored', body, 'more')


def p_rules():
    body = ''.join([
        '<p class="lead">From <code>plans/oncrack.md</code>: &ldquo;Make the UI exactly the same, but go unhinged with Datastar, caching, or any other improvements we can do.&rdquo; '
        'The port matched the Rust port&#39;s work per request and beat it 1.18-1.41&times;. onCrack drops that constraint, and nothing else.</p>',
        '<ol class="caveats">'
        '<li><b>The UI is identical.</b> Every parity screen&#39;s pixels match Rails&#39; (the harness&#39;s screenshot layer, lean matrix, all seeds) and every interaction behaves the same for a person using it. '
        'Server HTML, the live DOM, network requests and Cable frames may differ.</li>'
        '<li><b>Correct, always.</b> No stale reads after a write, no data from one user in another&#39;s response, no lost messages. Every cache states its invalidation rule and has tests that try to break it '
        '(concurrent writers, two users with different memberships, bans, deletes, edits).</li>'
        '<li><b>Durability is a disclosed choice.</b> Group commit windows and <code>synchronous=NORMAL</code> are measured both ways, documented, and shipped only behind a setting whose default is Rails-equivalent durability.</li>'
        '<li><b>Scored separately.</b> Same harness, same seed and pinned CPUs; every ratio against the Rust port and against the F# port, never presented as a like-for-like port result. The image is <code>campfire-oncrack:app</code>.</li>'
        '<li><b>Same discipline.</b> Measure before and after, one change at a time, log every run to the climb chart, never manufacture a win.</li></ol>',
    ])
    return panel('p-rules', 'The rules', 'What onCrack may and may not do', body, 'rules')


def p_port_era():
    hist = climb_chart.history()
    era = climb_chart.climb(climb_chart.PORT_ERA)
    pts = era.get('points') or []
    rows = []
    for p in pts:
        rows.append('<tr%s><th scope="row">%s</th><td>%s</td><td>%s</td><td class="num">%.2f&times;</td><td>%s</td></tr>'
                    % ('' if p['kept'] else ' class="dropped"', e(p['time'].astimezone(EDT).strftime('%-d %b %H:%M')), e(p['unit'] or ''),
                       e(p['change']), p['ratio'], 'kept' if p['kept'] else 'reverted'))
    tbl = ('<div class="tw"><table><caption>Every dot of the port&#39;s climb, oldest first (F# port over Rust, 16 connections)</caption><thead><tr><th scope="col">EDT</th><th scope="col">Unit</th>'
           '<th scope="col">Change</th><th scope="col" class="num">&times; Rust</th><th scope="col">Kept</th></tr></thead><tbody>%s</tbody></table></div>' % ''.join(rows))
    body = ''.join([
        '<p class="lead">onCrack was forked from the F# port, a faithful translation of the Rust port that matched Rust&#39;s work per request. The port&#39;s Phase 7 tuning climbed from %.2f&times; '
        'to %.2f&times; of Rust; these dots are kept off onCrack&#39;s line because they measured a different rule (the same work as Rust) and a stored Rust baseline from an earlier session. '
        'The port itself is at <a href="%s">%s</a>.</p>' % (era.get('start') or 0, era.get('latest') or 0, PORT_REPO, e(PORT_REPO.replace('https://', ''))),
        tbl,
        '<p class="era-note">Source: <code>bench/results/phase7-log.jsonl</code> and <code>bench/progress/history.json</code> (<code>port_era</code>); the port&#39;s full story, token ledger and prompts are in its repository.</p>',
        climb_chart.prelude(hist),
    ])
    return panel('p-port-era', 'Before onCrack', 'The F# port&#39;s climb', body, 'btw')



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
.tw .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
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

JS = r"""
(function(){
  var root=document.documentElement;
  var btn=document.querySelector('.theme');
  function current(){var t=root.getAttribute('data-theme');if(t)return t;return matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
  function label(){if(btn){var c=current();btn.textContent=c==='dark'?'☀':'☾';btn.setAttribute('aria-label','Switch to '+(c==='dark'?'light':'dark')+' theme');}}
  if(btn){btn.addEventListener('click',function(){var next=current()==='dark'?'light':'dark';root.setAttribute('data-theme',next);try{localStorage.setItem('theme',next);}catch(e){}label();});label();}
  var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  // counters: the HTML holds the final value; count up to it when it scrolls into view
  function fmt(v,dec){return v.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});}
  function count(el){var to=parseFloat(el.getAttribute('data-to')),dec=+el.getAttribute('data-dec')||0;if(reduce||!isFinite(to))return;
    var t0=null,d=1400;function step(t){if(!t0)t0=t;var k=Math.min((t-t0)/d,1),q=1-Math.pow(1-k,3);el.textContent=fmt(to*q,dec);if(k<1)requestAnimationFrame(step);else el.textContent=fmt(to,dec);}
    el.textContent=fmt(0,dec);requestAnimationFrame(step);}
  var els=[].slice.call(document.querySelectorAll('.reveal,.hero-in'));
  function show(el){el.classList.add('in');[].forEach.call(el.querySelectorAll('.count'),count);}
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){show(en.target);io.unobserve(en.target);}});},{rootMargin:'0px 0px -10% 0px',threshold:0.08});
    els.forEach(function(el){io.observe(el);});
  }else{els.forEach(show);}
  // on a phone the chart scrolls sideways: start at the latest run
  var sc=document.querySelector('.climb .cc-scroll');if(sc&&sc.scrollWidth>sc.clientWidth)sc.scrollLeft=sc.scrollWidth;
  // draw the climb line once
  var pl=document.querySelector('.climb .cc-climb');
  if(pl&&pl.getTotalLength&&!reduce){try{var L=pl.getTotalLength();pl.style.strokeDasharray=L;pl.style.strokeDashoffset=L;pl.getBoundingClientRect();
    pl.style.transition='stroke-dashoffset 1.8s cubic-bezier(.6,0,.2,1) .5s';pl.style.strokeDashoffset=0;}catch(e){}}
  // side panels: :target drawers without JS; with it, opened by class so Esc, click-outside and focus all work
  var mainEl=document.getElementById('main'),barEl=document.querySelector('.bar'),footEl=document.querySelector('footer.site');
  var openP=null,opener=null;
  function isPanel(el){return el&&el.classList&&el.classList.contains('panel');}
  function setInert(on){[mainEl,barEl,footEl].forEach(function(x){if(x){if(on)x.setAttribute('inert','');else x.removeAttribute('inert');}});}
  function openPanel(p,from,push){
    if(openP===p)return;if(openP)closePanel(true,true);
    openP=p;opener=from||null;p.classList.add('open');root.classList.add('locked');setInert(true);
    if(push)history.pushState({panel:p.id},'','#'+p.id);
    var s=p.querySelector('.sheet');s.scrollTop=0;setTimeout(function(){s.focus({preventScroll:true});},40);
  }
  function closePanel(silent,keepFocus){
    if(!openP)return;var p=openP;openP=null;p.classList.remove('open');root.classList.remove('locked');setInert(false);
    if(!silent){if(history.state&&history.state.panel===p.id){history.back();}else if(location.hash==='#'+p.id){history.replaceState(null,'',location.pathname+location.search);}}
    if(!keepFocus){var back=opener;if(!back){var c=p.querySelector('[data-close]');back=c&&document.getElementById(c.getAttribute('href').slice(1));}
      if(back){if(!back.matches('a[href],button,input,[tabindex]'))back.setAttribute('tabindex','-1');back.focus({preventScroll:!!opener});}}
  }
  document.addEventListener('click',function(ev){
    var a=ev.target.closest&&ev.target.closest('a');if(!a)return;
    if(a.hasAttribute('data-close')){ev.preventDefault();closePanel(false);return;}
    var h=a.getAttribute('href')||'';
    if(h.charAt(0)==='#'){var t=document.getElementById(h.slice(1));
      if(isPanel(t)){ev.preventDefault();openPanel(t,openP?opener:a,true);}
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
  window.addEventListener('popstate',function(){var id=location.hash.slice(1),t=id&&document.getElementById(id);
    if(isPanel(t))openPanel(t,null,false);else if(openP)closePanel(true);});
  var h0=location.hash.slice(1),t0=h0&&document.getElementById(h0);if(isPanel(t0))openPanel(t0,null,false);
})();
"""



def build():
    cl = climb_chart.climb()
    nav = ''.join('<li><a href="%s">%s</a></li>' % h for h in
                  [('#climb', 'Climb'), ('#rules', 'Rules'), ('#more', 'More')])
    panels = [p_climb(cl), p_scoring(), p_rules(), p_port_era()]
    body = ''.join([
        '<a class="skip" href="#main">Skip to content</a>',
        '<header class="bar"><div class="wrap"><a class="brand" href="#top">on<span>Crack</span></a>'
        '<nav aria-label="Sections"><ol>%s</ol></nav><button class="theme" type="button" aria-label="Switch theme"></button></div></header>' % nav,
        '<main id="main">', hero(cl), rules(), more_row(), '</main>',
        '<footer class="site"><div class="wrap"><p><b>Sources.</b> <a href="plans/oncrack.md">plans/oncrack.md</a>, <a href="AGENTS.md">AGENTS.md</a>, '
        '<code>bench/results/</code> (the climb is <code>oncrack-log.jsonl</code>; Rust, the F# port and Rails are <code>phase7-final/</code>), the git history of <code>crack</code>.</p>'
        '<p>onCrack is a fork of the F# port of Basecamp&#39;s ONCE Campfire. Campfire, the Rust port, its parity harness and vectors are &copy; 37signals, LLC, MIT. '
        'Generated from the logs by <code>site/build.py</code>.</p></div></footer>',
        '<div class="panels">%s</div>' % ''.join(panels),
    ])
    page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>onCrack</title><meta name="description" content="%s">'
            '<meta name="color-scheme" content="light dark">'
            '<script>document.documentElement.className+=" js";try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}</script>'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap">'
            '<style>%s%s</style></head><body>%s<script>%s</script></body></html>\n'
            % (e('onCrack: the same Campfire, pixel for pixel, on a server free to do less work. Scored against Rust and against the F# port it was forked from.'),
               climb_chart.CSS.strip(), CSS.strip(), body, JS.strip()))
    out = os.path.join(REPO, 'index.html')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('wrote %s (%s bytes)' % (out, format(len(page.encode('utf-8')), ',')))


if __name__ == '__main__':
    build()
