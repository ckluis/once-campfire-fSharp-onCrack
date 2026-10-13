"""The Phase 7 climb chart: F#'s throughput as a share of Rust's, one dot per logged run.

The hero of the project page (site/build.py, rebuilt after each logged run by bench/progress/build.py). climb() returns
the chart's HTML (SVG, dots and a CSS-only hover/focus/tap card per dot), the "before the port" strip, the scoped CSS
they need, and the numbers behind them.

Everything the component draws is under one root class (.cc) and every class it uses starts with cc-, so the page's
styles can't reach into it nor its styles out. Colours are custom properties on .cc (--cc-*) with light and dark values;
a host page may override them on .cc to match its palette.

Rust's numbers are the stored medians of bench/results/phase7-start/rust-*.json; the start point is F#'s own medians
from the same directory. Rails is the 5b baseline (bench/results/baseline-20261006).
"""
import glob
import html
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOG = os.path.join(ROOT, "bench/results/oncrack-log.jsonl")
STORED = os.path.join(ROOT, "bench/results/phase7-final")   # Rust, the F# port and Rails, one session, 3 reps each
HISTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
WORKLOADS = [("room_show", "Room page"), ("messages_page", "Messages page"), ("sidebar", "Sidebar"),
             ("search", "Search"), ("post_message", "Post a message")]
CONCS = [("c16", 16), ("c1", 1)]
e = html.escape
EDT = timezone(timedelta(hours=-4), "EDT")   # the work was run in US Eastern; a fixed zone so the page does not depend on the machine that builds it

# The two eras the page draws. onCrack's is the line (onCrack over the stored Rust medians, starting from the F# port's final
# result); the port's is the Phase 7 history of the app onCrack was forked from, drawn in a panel apart from the line.
ONCRACK = {"name": "onCrack", "log": LOG, "rust": STORED, "rails": STORED, "port_col": True, "axis": "nice"}
PORT_ERA = {"name": "F#", "log": os.path.join(ROOT, "bench/results/phase7-log.jsonl"), "rust": os.path.join(ROOT, "bench/results/phase7-start"),
            "rails": os.path.join(ROOT, "bench/results/baseline-20261006"), "port_col": False, "axis": "port"}


def medians(app, where=None):
    """Median req/s and CPU µs/req per (workload, concurrency) over an app's reps (the stored phase7-final session by default)."""
    reps = {}
    for p in sorted(glob.glob(os.path.join(where or STORED, f"{app}-[0-9].json"))):
        with open(p) as f:
            for run in json.load(f)["http"]:
                if run.get("gzip"):
                    key = (run["route"], run["conc"])
                    reps.setdefault(key, {"rps": [], "cpu_us": []})["rps"].append(run["rps"])
                    cpu = (run.get("cost") or {}).get("server_cpu_us_per_req")
                    if cpu:
                        reps[key]["cpu_us"].append(cpu)
    out = {}
    for w, _ in WORKLOADS:
        for key, c in CONCS:
            v = reps.get((w, c))
            if v and v["rps"]:
                out.setdefault(w, {})[key] = {"rps": statistics.median(v["rps"]),
                                              "cpu_us": statistics.median(v["cpu_us"]) if v["cpu_us"] else None}
    return out


def history():
    with open(HISTORY) as f:
        return json.load(f)


def start_entry(hist):
    """onCrack's starting point: the F# port's final result (history.json "oncrack_start", numbers from bench/results/phase7-final)."""
    st = dict(hist["oncrack_start"])
    st.setdefault("kept", True)
    st["workloads"] = medians("fsharp")
    st["rust"] = medians("rust")
    return st


def port_start_entry(hist):
    # history.json records the time (a checkout resets file times); the file's mtime is the fallback.
    pe = hist["port_era"]
    t = pe.get("start_time")
    p = os.path.join(PORT_ERA["rust"], "fsharp-3.json")
    if not t:
        t = "2026-10-06T14:00:00Z"
        if os.path.exists(p):
            t = datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"time": t, "unit": "phase 7 start", "tier": 3, "change": "Phase 7 starting point: the trustworthy harness, before any tuning",
            "description": pe.get("start_description", ""), "commit": "5cc5ba4", "build": "image, 3 reps", "kept": True,
            "workloads": medians("fsharp", PORT_ERA["rust"])}


def read_log(path, mode=None):
    """The log's rows. Round 5 added "mode" (fresh | cached) to the project-suite rows; a row without it is cached (rounds 1-2). The chart
    draws one mode's line: CLIMB_MODE (default cached, which is every row logged before round 5 and keeps the chart as it was)."""
    mode = mode or os.environ.get("CLIMB_MODE", "cached")
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if r.get("mode", "cached") == mode:
                        rows.append(r)
    return rows


def entries(hist, era=ONCRACK, mode=None):
    if era is PORT_ERA:
        rows = [dict(h) for h in hist["port_era"]["comparable"]] + [port_start_entry(hist)]
        mode = "cached"   # the port's log has no modes; its rows read as the one default
    else:
        rows = [start_entry(hist)]
    return rows + read_log(era["log"], mode)


def commits_between(a, b):
    """Subjects of the commits after a up to b that change the app itself (not the bench, docs or this page)."""
    try:
        out = subprocess.run(["git", "-C", ROOT, "log", "--reverse", "--format=%h %s", f"{a}..{b}", "--",
                              "src", "Dockerfile", "Directory.Build.props", "Directory.Packages.props"],
                             capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l for l in out.splitlines() if l and not l.split(" ", 1)[1].startswith("bench: log")]


def _clip(text, n):
    """text cut at a word boundary within n characters, with an ellipsis."""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(" ,;(") + "…"


def describe(rows):
    """What was done for each dot, and which runs are dots at all.

    A run is a version (a dot) when it has its own description (earlier versions, the Phase 7 start), is a
    unit's tier 3 confirmation, or follows an app commit since the previous version. Re-measurements of
    unchanged code and runtime knobs tried without a commit are measurement-only: they stay in
    bench/results/phase7-log.jsonl but are not drawn and never move the line or the carried values."""
    prev, out = None, []
    for r in rows:
        if not r.get("description") and prev and r.get("commit"):
            r["commits"] = commits_between(prev, r["commit"])
        r["version"] = bool(r.get("description")) or str(r.get("tier")) == "3" or bool(r.get("commits"))
        if r["version"] and r.get("commit") and r.get("kept", True):
            prev = r["commit"]
    return rows


def versions(rows):
    """The dots: one per commit. Every logged run with the same commit measured the same build (a unit may log
    a control first, A/B variants, or several workloads in separate runs, and may log them in one batch,
    interleaved), so all of a commit's runs form one group wherever they sit in the log. The dot merges the
    group's kept runs (later measurements override earlier ones per workload; different workloads combine) and
    takes its label from the kept run that measured the most. Reverted runs in a group with kept runs are
    absorbed; a group with only reverted runs is a single hollow dot (a code experiment that was undone).
    Earlier versions and the Phase 7 start (rows with their own description) are always their own dots."""
    groups, order = {}, []
    for i, r in enumerate(rows):
        key = ("own", i) if r.get("description") or not r.get("commit") else ("commit", r["commit"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)
    out = []
    for key in order:
        group = groups[key]
        if not any(g.get("version") for g in group):
            continue
        kept = [g for g in group if g.get("kept", True)]
        use = kept or group
        merged_w = {}
        for g in use:
            for w, cs in g.get("workloads", {}).items():
                merged_w.setdefault(w, {}).update({c: dict(v) for c, v in cs.items()})
        label = max(enumerate(use), key=lambda iv: (len(iv[1].get("workloads", {})), iv[0]))[1]
        out.append(dict(label, workloads=merged_w, version=True, kept=bool(kept),
                        commits=next((g.get("commits") for g in group if g.get("commits")), label.get("commits") or []),
                        time=use[-1].get("time", label.get("time"))))
    return out


def when(r):
    try:
        return datetime.fromisoformat(str(r["time"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None


def carry(rows):
    """Kept runs with every workload they didn't measure filled in from the latest earlier kept run that did.
    Each value remembers whether it was measured in that run. Reverted runs are filled from the same state but
    don't change it."""
    state, out = {}, []
    for r in rows:
        measured = {(w, c) for w, v in r.get("workloads", {}).items() for c in v}
        view = {w: {c: dict(v) for c, v in cs.items()} for w, cs in state.items()}
        for w, cs in r.get("workloads", {}).items():
            for c, v in cs.items():
                view.setdefault(w, {})[c] = dict(v)
        if r.get("kept", True):
            state = {w: {c: dict(v) for c, v in cs.items()} for w, cs in view.items()}
        out.append((r, view, measured))
    return out


def ratio(view, rust, w, c):
    try:
        return view[w][c]["rps"] / rust[w][c]["rps"]
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def overall(view, rust, c="c16"):
    qs = [ratio(view, rust, w, c) for w, _ in WORKLOADS]
    if any(q is None for q in qs):
        return None
    prod = 1.0
    for q in qs:
        prod *= q
    return prod ** (1 / len(qs))


def num(v, fmt="{:,.0f}"):
    return fmt.format(v) if isinstance(v, (int, float)) else "–"


def done(r):
    """The card's "What was done" section."""
    if r.get("description"):
        return '<div class="cc-done"><h4>What was done</h4><p>%s</p></div>' % e(r["description"])
    cs = r.get("commits") or []
    if cs:
        items = "".join('<li><code>%s</code> %s</li>' % (e(c.split(" ", 1)[0]), e(c.split(" ", 1)[1] if " " in c else "")) for c in cs[:8])
        more = '<li class="cc-more">and %d more</li>' % (len(cs) - 8) if len(cs) > 8 else ""
        return '<div class="cc-done"><h4>What was done</h4><ul>%s%s</ul></div>' % (items, more)
    return '<div class="cc-done"><h4>What was done</h4><p>No code change since the previous dot (a measurement only).</p></div>'


def prelude(hist):
    """Before the port: the Muse-era numbers, shown apart from the line because they weren't like for like."""
    cards = []
    for p in hist["port_era"].get("prelude", []):
        ratios = "".join("<li><span>%s</span><b>%s</b></li>" % (e(k), e(v)) for k, v in p["ratios"].items())
        cards.append('<div class="cc-pre"><p class="cc-pre-label">%s</p><p class="cc-pre-claim">%s</p><ul>%s</ul><p class="cc-pre-why">%s</p></div>'
                     % (e(p["label"]), e(p["claim"]), ratios, e(p["why"])))
    return ('<section class="cc cc-prelude"><h2>Before the port</h2><p class="cc-sub">Claimed F#/Rust ratios from the challenge app. '
            'They are off the chart on purpose: the pages weren&#39;t identical to Rust&#39;s, so they don&#39;t measure the same work.</p>'
            '<div class="cc-pre-grid">%s</div></section>' % "".join(cards))


def card(era, r, view, measured, rust, port, ov, rails, series=None):
    """The hover card of one dot. `port` is the stored F# port (a column and a ratio in onCrack's chart, None in the port era's)."""
    name = era["name"] if not series else series
    t = when(r)
    rows = []
    for w, label in WORKLOADS:
        cells = []
        for c, _ in CONCS:
            v = view.get(w, {}).get(c, {})
            ru = rust.get(w, {}).get(c, {})
            q = ratio(view, rust, w, c)
            cls = "cc-win" if q and q >= 1 else ("cc-close" if q and q >= 0.9 else "")
            carried = "cc-carried" if (w, c) not in measured and v else ""
            ra = rails.get(w, {}).get(c, {}).get("rps")
            pc = (port or {}).get(w, {}).get(c, {})
            if port is not None:
                sub = ("%.2f× F# port" % (v["rps"] / pc["rps"])) if pc.get("rps") and v.get("rps") else ""
            else:
                sub = ("%.0f× Rails" % (v["rps"] / ra)) if ra and v.get("rps") else ""
            port_cell = ('<td class="cc-pt">%s<small>%s µs</small></td>' % (num(pc.get("rps")), num(pc.get("cpu_us")))) if port is not None else ""
            cells.append('<td class="cc-fs %s">%s<small>%s µs</small></td>%s<td class="cc-rs">%s<small>%s µs</small></td>'
                         '<td class="cc-ra">%s</td><td class="cc-q %s">%s<small>%s</small></td>'
                         % (carried, num(v.get("rps")), num(v.get("cpu_us")), port_cell, num(ru.get("rps")), num(ru.get("cpu_us")),
                            num(ra), cls, ("%.2f×" % q) if q else "–", sub))
        rows.append("<tr><th>%s</th>%s</tr>" % (e(label), "".join(cells)))
    kept = r.get("kept", True)
    span = 5 if port is not None else 4
    sub_head = "".join("<th>%s</th>" % h for h in ([name] + (["F# port"] if port is not None else []) + ["Rust", "Rails", "%s/Rust" % name])) * 2
    if port is not None:
        foot = ("Rust, the F# port and Rails are the stored medians of bench/results/phase7-final (one session, 3 reps each); "
                "onCrack's own runs are against them, never re-measured side by side.")
    else:
        foot = ("Rust was measured in the same run." if r.get("rust") else "Rust is the stored Phase 7 starting point.") \
            + " Rails is the 5b baseline (3 reps), the last time it ran; it doesn't change."
    return ('<span class="cc-card" role="tooltip"><span class="cc-when">%s · %s · tier %s%s</span><span class="cc-what">%s</span>'
            '<span class="cc-meta">commit <code>%s</code> · %s build%s</span>'
            '<table><tr class="cc-grp"><th></th><th colspan="%d">16 connections</th><th colspan="%d">1 connection</th></tr>'
            '<tr class="cc-sub"><th></th>%s</tr>%s</table>'
            '%s<span class="cc-foot">Requests per second, CPU µs per request beneath. %s Greyed %s values were carried from an earlier run.</span></span>'
            % (e(t.astimezone(EDT).strftime("%a %-d %b, %H:%M %Z") if t else "?"), e(str(r.get("unit", ""))), e(str(r.get("tier", ""))),
               "" if kept else " · reverted", e(str(r.get("change", ""))), e(str(r.get("commit", ""))),
               e(_clip(str(r.get("build", "")), 44)), (" · overall %.2f× of Rust" % ov) if ov else "", span, span, sub_head, "".join(rows), done(r),
               foot, era["name"]))


CSS = """
.cc{--cc-card:#fff;--cc-ink:#1c1a17;--cc-mute:#6d675d;--cc-line:#e3ded3;--cc-acc:#c2410c;--cc-win:#15803d;--cc-close:#b45309;--cc-drop:#a8a29e;
  font-family:-apple-system,system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .cc{--cc-card:#221e19;--cc-ink:#f1ede5;--cc-mute:#a29c90;--cc-line:#36312a;--cc-acc:#fb923c;--cc-win:#4ade80;--cc-close:#fbbf24;--cc-drop:#78716c}}
:root[data-theme="dark"] .cc{--cc-card:#221e19;--cc-ink:#f1ede5;--cc-mute:#a29c90;--cc-line:#36312a;--cc-acc:#fb923c;--cc-win:#4ade80;--cc-close:#fbbf24;--cc-drop:#78716c}
.cc *{box-sizing:border-box}
.cc-sub{color:var(--cc-mute);margin:4px 0 18px}
.cc-scroll{position:relative}
.cc-chart{position:relative;background:var(--cc-card);border:1px solid var(--cc-line);border-radius:14px;aspect-ratio:1000/440;color:var(--cc-ink)}
.cc-chart svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.cc-grid{stroke:var(--cc-line)} .cc-axis,.cc-tick{fill:var(--cc-mute);font-size:12px} .cc-day{fill:var(--cc-mute);font-size:10.5px;opacity:.75}
.cc-rust{stroke:var(--cc-ink);stroke-width:2;stroke-dasharray:8 6;opacity:.7} .cc-rustlabel{fill:var(--cc-ink);font-weight:700;font-size:15px}
.cc-port{stroke:var(--cc-mute);stroke-width:1.5;stroke-dasharray:2 5;opacity:.9} .cc-portlabel{fill:var(--cc-mute);font-weight:650;font-size:13px}
.cc-climb{fill:none;stroke:var(--cc-acc);stroke-width:4;stroke-linejoin:round;stroke-linecap:round} .cc-area{fill:var(--cc-acc);opacity:.1}
.cc-dot{display:block;position:absolute;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;border:3px solid var(--cc-acc);background:var(--cc-card);padding:0;cursor:pointer;outline-offset:3px}
.cc-dot.cc-last{background:var(--cc-acc);width:20px;height:20px;margin:-10px 0 0 -10px} .cc-dot.cc-dropped{border-color:var(--cc-drop);width:11px;height:11px;margin:-5.5px 0 0 -5.5px;border-width:2px}
.cc-dot .cc-card{display:none;position:absolute;left:18px;top:-12px;z-index:5;width:780px;max-width:92vw;text-align:left;background:var(--cc-card);color:var(--cc-ink);
  border:1px solid var(--cc-line);border-radius:12px;padding:12px 14px;box-shadow:0 12px 32px rgba(0,0,0,.18);font:13px/1.4 -apple-system,system-ui,sans-serif;cursor:default;white-space:normal}
.cc-dot.cc-flip .cc-card{left:auto;right:18px} .cc-dot:hover .cc-card,.cc-dot:focus .cc-card,.cc-dot:focus-within .cc-card{display:block}
.cc-card>span{display:block;margin:0 0 4px} .cc-when{color:var(--cc-mute);font-size:12px} .cc-what{font-weight:650;font-size:14px} .cc-meta{color:var(--cc-mute);font-size:12px}
.cc-card code{font:11px ui-monospace,Menlo,monospace;background:none;padding:0;color:inherit}
.cc-card table{width:100%;border-collapse:collapse;margin:8px 0 0;font-variant-numeric:tabular-nums;font-size:13px;background:none;border:0}
.cc-card th,.cc-card td{padding:5px 4px;border:0;border-top:1px solid var(--cc-line);text-align:right;vertical-align:top;font-size:inherit;text-transform:none;letter-spacing:normal;white-space:normal;color:inherit}
.cc-card th:first-child{text-align:left;font-weight:600}
.cc-card .cc-carried{opacity:.45} .cc-card small{display:block;color:var(--cc-mute);font-size:10.5px} .cc-card .cc-rs{color:var(--cc-mute)} .cc-card .cc-ra{color:var(--cc-mute);opacity:.8;font-size:11.5px}
.cc-card .cc-q{font-weight:700;font-size:13.5px;vertical-align:middle} .cc-card tr.cc-grp th{text-align:center;border-top:0;color:var(--cc-ink)} .cc-card tr.cc-sub th{font-size:11px;color:var(--cc-mute);font-weight:600;border-top:0}
.cc-card td.cc-fs{border-left:1px solid var(--cc-line)} .cc-win{color:var(--cc-win)} .cc-close{color:var(--cc-close)} .cc-foot{color:var(--cc-mute);font-size:11px;margin-top:8px!important}
.cc-done{display:block;margin-top:10px;border-top:1px solid var(--cc-line);padding-top:8px} .cc-done h4{margin:0 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--cc-mute)}
.cc-done p{margin:0} .cc-done ul{margin:0;padding-left:16px} .cc-done li{margin:2px 0} .cc-done code{color:var(--cc-mute)}
.cc-prelude{margin:6px 0 16px} .cc-prelude h2{font-size:15px;margin:0;text-transform:uppercase;letter-spacing:.06em;color:var(--cc-mute)}
.cc-pre-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px} .cc-pre{background:var(--cc-card);border:1px dashed var(--cc-line);border-radius:12px;padding:12px 14px;opacity:.85}
.cc-pre-label{margin:0;font-weight:650} .cc-pre-claim{margin:0 0 6px;color:var(--cc-mute);font-size:13px} .cc-pre ul{list-style:none;padding:0;margin:0 0 6px;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px}
.cc-pre li span{color:var(--cc-mute);margin-right:4px} .cc-pre li b{text-decoration:line-through;text-decoration-color:var(--cc-mute)} .cc-pre-why{margin:0;font-size:12.5px;color:var(--cc-mute)}
@media (max-width:640px){
  .cc-pre-grid{grid-template-columns:1fr}
  /* On a phone the chart keeps its shape and scrolls sideways inside its box; a dot's card becomes a sheet at the bottom of the screen. */
  .cc-scroll{overflow-x:auto;overscroll-behavior-x:contain;margin:0 -16px;padding:0 16px 6px}
  .cc-chart{min-width:640px}
  .cc-dot .cc-card,.cc-dot.cc-flip .cc-card{position:fixed;left:8px;right:8px;top:auto;bottom:8px;width:auto;max-width:none;max-height:72vh;overflow:auto;z-index:50}
}
"""


def nice_ticks(lo, hi):
    """Gridlines at a step that gives about 5 to 9 of them between lo and hi."""
    step = next((st for st in (0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 5.0) if (hi - lo) / st <= 9), 5.0)
    g = (int(lo / step + 1e-9)) * step
    out = []
    while g <= hi + 1e-9:
        if g >= lo - 1e-9:
            out.append(round(g, 2))
        g += step
    return out


def climb(era=ONCRACK):
    """Everything both pages need: HTML fragments, CSS and the numbers behind them. `era` is ONCRACK (the line, from the F# port's final
    result) or PORT_ERA (the Phase 7 history of the port, drawn in a panel)."""
    name = era["name"]
    stored = medians("rust", era["rust"])
    rails = medians("reference", era["rails"])
    port = medians("fsharp") if era["port_col"] else None
    hist = history()
    rows = carry(versions(describe(entries(hist, era))))
    pts = [(when(r), overall(v, r.get("rust") or stored), r, v, m) for r, v, m in rows]
    pts = [p for p in pts if p[0] and p[1] is not None]
    kept = [p for p in pts if p[2].get("kept", True)]
    W, H, L, R, T, B = 1000, 440, 56, 80, 28, 70
    # Evenly spaced by run order, not by clock: each dot gets the same room, labelled with its time and day.
    order = {id(p[2]): i for i, p in enumerate(pts)}
    n = max(len(pts) - 1, 1)
    port_level = overall(medians("fsharp"), stored) if era["port_col"] else None
    if pts:
        vals = [p[1] for p in pts]
        if era["axis"] == "port":
            lo, hi = min(0.6, min(vals) - 0.04), max(1.15, max(vals) + 0.04)
        else:
            lo, hi = min(0.8, min(vals) - 0.1), max(1.5, max(vals) * 1.08)
    else:
        lo, hi = 0.6, 1.15
    X = lambda r: L + (W - L - R) * ((order[id(r)] / n) if len(pts) > 1 else 0.5)
    Y = lambda v: H - B - (H - T - B) * (v - lo) / (hi - lo)

    svg = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (W, H)]
    for g in nice_ticks(lo, hi):
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-grid"/><text x="10" y="%.1f" class="cc-axis">%g×</text>'
                   % (L, W - R, Y(g), Y(g), Y(g) + 4, g))
    svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-rust"/><text x="%d" y="%.1f" class="cc-rustlabel">Rust</text>'
               % (L, W - R, Y(1), Y(1), W - R + 10, Y(1) + 5))
    if port_level:
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-port"/><text x="%d" y="%.1f" class="cc-portlabel">F# port</text>'
                   % (L, W - R, Y(port_level), Y(port_level), W - R + 10, Y(port_level) + 5))
    if kept:
        line = " ".join("%.1f,%.1f" % (X(r), Y(v)) for t, v, r, *_ in kept)
        svg.append('<polygon class="cc-area" points="%.1f,%d %s %.1f,%d"/>' % (X(kept[0][2]), H - B, line, X(kept[-1][2]), H - B))
        svg.append('<polyline class="cc-climb" points="%s"/>' % line)
    step = max(1, -(-len(pts) // 24))  # label every dot until there are more than 24
    for i, (t, v, r, *_) in enumerate(pts):
        if i % step == 0 or i == len(pts) - 1:
            svg.append('<text x="%.1f" y="%d" class="cc-tick" text-anchor="middle">%s</text><text x="%.1f" y="%d" class="cc-day" text-anchor="middle">%s</text>'
                       % (X(r), H - B + 20, t.astimezone(EDT).strftime("%H:%M"), X(r), H - B + 36, t.astimezone(EDT).strftime("%a %-d %b")))
    svg.append("</svg>")

    dots = []
    for i, (t, v, r, view, measured) in enumerate(pts):
        isk = r.get("kept", True)
        last = isk and kept and r is kept[-1][2]
        left, top = X(r) / W * 100, Y(v) / H * 100
        side = "cc-flip" if left > 58 else ""
        dots.append('<span class="cc-dot %s %s %s" tabindex="0" role="button" style="left:%.2f%%;top:%.2f%%" aria-label="%s, %.2f times Rust">%s</span>'
                    % ("cc-kept" if isk else "cc-dropped", "cc-last" if last else "", side, left, top,
                       e(r.get("change", "")), v, card(era, r, view, measured, r.get("rust") or stored, port, v, rails)))

    out = {"hist": hist, "css": CSS, "prelude": prelude(hist),
           "chart": '<div class="cc"><div class="cc-scroll"><div class="cc-chart">%s%s</div></div></div>' % ("".join(svg), "".join(dots)),
           "points": [{"time": p[0], "ratio": p[1], "unit": p[2].get("unit"), "change": p[2].get("change", ""), "tier": p[2].get("tier"),
                       "kept": p[2].get("kept", True), "commit": p[2].get("commit", "")} for p in pts],
           "latest": None, "port_level": port_level}
    if kept:
        first = kept[0]
        latest = kept[-1]
        gain = (latest[1] / first[1] - 1) * 100
        hours = (latest[0] - first[0]).total_seconds() / 3600
        # Code changes since the start: dots after it that carry app commits (not confirmations of the same code).
        changes = len([p for p in kept if p[0] > first[0] and p[2].get("commits")])
        to_go = (1 / latest[1] - 1) * 100
        steps = [(b[1] / a[1] - 1) * 100 for a, b in zip(kept, kept[1:])]
        best = max(range(len(steps)), key=lambda i: steps[i]) if steps else None
        out.update(latest=latest[1], start=first[1], gain=gain, hours=hours, changes=changes, to_go=to_go,
                   kept_n=len(kept), dropped_n=len(pts) - len(kept), tuning_runs=len([p for p in pts if p[0] > first[0]]),
                   best_jump=({"gain": steps[best], "change": kept[best + 1][2].get("change", ""), "ratio": kept[best + 1][1]}
                              if best is not None else None))
        if port_level:
            out["vs_port"] = latest[1] / port_level
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# The hero chart (round 5's page rebuild): the port's climb, onCrack's two modes and the reference lines on one timeline.
#
# Lines: the F# port's own history (bench/results/phase7-log.jsonl, over the Rust of its own session, phase7-start); onCrack with the cached decision
# (the opt-in; rounds 1 and 2 only had this one) and onCrack with fresh authorization (the default since round 3), both over the stored Rust medians of
# phase7-final (bench/results/oncrack-log.jsonl, rows tagged "mode"; a row without one is cached). All three are "x Rust on this project's own suite", not
# upstream's harness: the page's table of upstream's harness is the comparable headline. Rust is 1x. Rails is the stored 5b baseline's ratio. C was never
# measured on this suite, so it has no line.
#
# The axis is the port chart's: one slot per logged version in the order they ran (every dot is labelled with its clock time, the bands with their days),
# not the clock itself, because round one logged thirteen versions in a day and round five two in a week. Iterations are bands: the slots of each band
# sit together under its label, and a round that logged nothing on this suite (round four) keeps an empty band, so the gap is visible.
# ---------------------------------------------------------------------------------------------------------------------------------

SERIES = {
    "port": {"label": "F# port's own climb", "short": "F# port", "end": "port", "cls": "cc-s-port"},
    "cached": {"label": "onCrack, cached decision (opt-in)", "short": "onCrack, cached", "end": "cached", "cls": "cc-s-cached"},
    "fresh": {"label": "onCrack, fresh authorization (default)", "short": "onCrack, fresh", "end": "fresh", "cls": "cc-s-fresh"},
}


def _points(era, mode):
    """The dots of one line, in log order, with carried values: [(time, ratio, row, view, measured)], and the era's stored Rust, Rails and port."""
    stored = medians("rust", era["rust"])
    rails = medians("reference", era["rails"])
    port = medians("fsharp") if era["port_col"] else None
    rows = carry(versions(describe(entries(history(), era, mode))))
    pts = [(when(r), overall(v, r.get("rust") or stored), r, v, m) for r, v, m in rows]
    return [p for p in pts if p[0] and p[1] is not None], stored, rails, port


def _band_of(bands, era, row):
    """Which iteration a logged run belongs to: the first band whose unit list or prefix names its unit (history.json "bands")."""
    unit = str(row.get("unit", ""))
    for b in bands:
        if b.get("empty") or b["era"] != era:
            continue
        if unit in b.get("units", []) or any(unit.startswith(x) for x in b.get("unit_prefix", [])):
            return b["key"]
    for b in bands:
        if b["era"] == era and b.get("rest"):
            return b["key"]
    raise KeyError("no band for unit %r (%s)" % (unit, era))


def hero_chart():
    """The one hero chart: HTML (SVG, legend, dots with their cards), the numbers behind it and the bands (for the beats under it)."""
    hist = history()
    bands = hist["bands"]
    port_pts, port_rust, port_rails, _ = _points(PORT_ERA, "cached")
    cached_pts, o_rust, o_rails, o_port = _points(ONCRACK, "cached")
    fresh_pts, *_ = _points(ONCRACK, "fresh")
    fork = cached_pts[0]                      # the port's final re-baseline: the fork point, on the port's line and the start of onCrack's
    cached_pts = cached_pts[1:]
    fresh_pts = [p for p in fresh_pts if p[2].get("unit") != "port final"]
    # The port's own 'final' row is the same session as the fork point (bench/results/phase7-final): one dot, at the time the port logged it.
    final_i = next(i for i, p in enumerate(port_pts) if p[2].get("unit") == "final")
    fork_t = port_pts[final_i][0]
    port_pts = port_pts[:final_i] + [(fork_t, fork[1], fork[2], fork[3], fork[4])] + port_pts[final_i + 1:]

    dots = []
    def add(series, pt, era, basis, label):
        t, v, r, view, measured = pt
        dots.append({"series": series, "t": t, "v": v, "r": r, "view": view, "m": measured, "era": era, "basis": basis, "label": label,
                     "kept": r.get("kept", True), "band": _band_of(bands, "port" if era is PORT_ERA else "oncrack", r) if r.get("unit") != "port final" else None})
    for p in port_pts:
        add("port", p, PORT_ERA, (port_rust, port_rails, None), "F# port")
    for p in cached_pts:
        add("cached", p, ONCRACK, (o_rust, o_rails, o_port), "onCrack, cached decision")
    for p in fresh_pts:
        add("fresh", p, ONCRACK, (o_rust, o_rails, o_port), "onCrack, fresh authorization")
    for d in dots:
        if d["band"] is None:                 # the fork point closes the port's tuning band
            d["band"] = next(b["key"] for b in bands if b["era"] == "port" and b.get("rest"))
    # One slot per (time, commit) for onCrack's two modes, everything else its own slot. Slots follow the order the runs were logged (the port's dots, then onCrack's):
    # the log is chronological but for a few rows logged late, and a dot's carried values depend on that order, so sorting by clock would draw a carry artifact as a dip.
    order = list(range(len(dots)))
    slot_of, slots = {}, []
    for i in order:
        d = dots[i]
        key = (d["t"], d["r"].get("commit")) if d["series"] in ("cached", "fresh") else ("own", i)
        if key not in slot_of:
            slot_of[key] = len(slots)
            slots.append({"band": d["band"], "t": d["t"], "dots": []})
        d["slot"] = slot_of[key]
        slots[d["slot"]]["dots"].append(i)
    W, H, L, R, T, B = 1000, 520, 56, 150, 66, 66
    MINW = 4.6
    layout, x = [], 0.0
    for b in bands:
        mine = [i for i, sl in enumerate(slots) if sl["band"] == b["key"]]
        w = max(len(mine) + 0.6, MINW, len(b["label"]) * 0.62) if not b.get("empty") or mine else max(MINW, len(b["label"]) * 0.62)
        layout.append({"band": b, "slots": mine, "x0": x, "w": w})
        x += w
    unit_px = (W - L - R) / x
    sx = {}
    for lb in layout:
        n = max(len(lb["slots"]), 1)
        for k, si in enumerate(lb["slots"]):
            sx[si] = L + (lb["x0"] + (k + 0.5) * lb["w"] / n) * unit_px
    vals = [d["v"] for d in dots]
    lo, hi = 0.0, max(vals) * 1.1
    rails_level = overall(medians("reference", ONCRACK["rails"]), o_rust)
    port_level = overall(medians("fsharp"), o_rust)
    Yf = lambda v: H - B - (H - T - B) * (v - lo) / (hi - lo)
    X = lambda d: sx[d["slot"]]

    svg = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (W, H)]
    for lb in layout:                          # iteration bands: a shade on alternate bands, a divider, a label that links to its beat
        b = lb["band"]
        x0, x1 = L + lb["x0"] * unit_px, L + (lb["x0"] + lb["w"]) * unit_px
        if lb["band"]["key"] in {bb["key"] for bb in bands[1::2]}:
            svg.append('<rect class="cc-band" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (x0, T - 34, x1 - x0, H - B - T + 34))
        svg.append('<line class="cc-div" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (x0, x0, T - 34, H - B))
        ds = [dots[i] for si in lb["slots"] for i in slots[si]["dots"]]
        span = ""
        if ds:
            t0, t1 = min(d["t"] for d in ds).astimezone(EDT), max(d["t"] for d in ds).astimezone(EDT)
            span = t0.strftime("%-d %b") if t0.date() == t1.date() else "%s – %s" % (t0.strftime("%-d %b"), t1.strftime("%-d %b"))
        mid = (x0 + x1) / 2
        svg.append('<a href="#beat-%s" class="cc-bandlink"><text x="%.1f" y="%d" class="cc-bandname" text-anchor="middle">%s</text>'
                   '<text x="%.1f" y="%d" class="cc-bandspan" text-anchor="middle">%s</text></a>'
                   % (b["key"], mid, T - 18, e(b["label"]), mid, T - 5, e(span if ds else b.get("empty_note", ""))))
        if b.get("empty"):
            svg.append('<text x="%.1f" y="%.1f" class="cc-none" text-anchor="middle">nothing logged</text><text x="%.1f" y="%.1f" class="cc-none" text-anchor="middle">on this suite</text>'
                       % (mid, Yf(hi * 0.5) - 4, mid, Yf(hi * 0.5) + 12))
    svg.append('<line class="cc-div" x1="%d" x2="%d" y1="%d" y2="%d"/>' % (W - R, W - R, T - 34, H - B))
    g = 1
    for g in nice_ticks(lo, hi):
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-grid"/><text x="10" y="%.1f" class="cc-axis">%g×</text>' % (L, W - R, Yf(g), Yf(g), Yf(g) + 4, g))
    svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-rust"/><text x="%d" y="%.1f" class="cc-rustlabel">Rust 1×</text>' % (L, W - R, Yf(1), Yf(1), W - R + 10, Yf(1) + 5))
    svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="cc-rails"/><text x="%d" y="%.1f" class="cc-raillabel">Rails</text>' % (L, W - R, Yf(rails_level), Yf(rails_level), W - R + 10, Yf(rails_level) + 4))

    def line(series, pts_, extra=None):
        pts_ = sorted(pts_, key=lambda d: d["slot"])
        return " ".join("%.1f,%.1f" % (X(d), Yf(d["v"])) for d in pts_ if d["kept"] and (extra is None or extra(d)))
    by = lambda s_: [d for d in dots if d["series"] == s_]
    fork_d = next(d for d in dots if d["r"].get("unit") == "port final")
    cached_line = [fork_d] + [d for d in by("cached") if d["kept"]]
    cached_kept = sorted(cached_line, key=lambda d: d["slot"])
    # onCrack's lines start at the fork point; the port's line runs through it and goes on
    port_line = sorted([d for d in by("port") if d["kept"]], key=lambda d: d["slot"])
    svg.append('<polyline class="cc-line cc-l-port" points="%s"/>' % " ".join("%.1f,%.1f" % (X(d), Yf(d["v"])) for d in port_line))
    svg.append('<polyline class="cc-line cc-l-cached" points="%s"/>' % " ".join("%.1f,%.1f" % (X(d), Yf(d["v"])) for d in cached_kept))
    fresh_kept = sorted([d for d in by("fresh") if d["kept"]], key=lambda d: d["slot"])
    branch = None
    if fresh_kept:
        before = [d for d in cached_kept if d["t"] < fresh_kept[0]["t"]]
        branch = before[-1]                    # fresh starts where the default changed: from the last cached dot before the first fresh one
        svg.append('<polyline class="cc-line cc-l-branch" points="%.1f,%.1f %.1f,%.1f"/>' % (X(branch), Yf(branch["v"]), X(fresh_kept[0]), Yf(fresh_kept[0]["v"])))
        svg.append('<polyline class="cc-line cc-l-fresh" points="%s"/>' % " ".join("%.1f,%.1f" % (X(d), Yf(d["v"])) for d in fresh_kept))
    # line-end labels, pushed apart where they would touch
    ends = []
    for s_, pts_ in (("fresh", fresh_kept), ("cached", cached_kept), ("port", port_line)):
        if pts_:
            ends.append([s_, Yf(pts_[-1]["v"]), pts_[-1]])
    port_final_y = Yf(port_level)
    ends.sort(key=lambda a: a[1])
    for i in range(1, len(ends)):
        if ends[i][1] - ends[i - 1][1] < 15:
            ends[i][1] = ends[i - 1][1] + 15
    last_slot_x = max(sx.values())
    for s_, y, d in ends:
        svg.append('<text x="%d" y="%.1f" class="cc-endlabel cc-t-%s">%s</text>' % (W - R + 10, y + 4, s_, "%s %.2f×" % (SERIES[s_]["end"], d["v"])))
    # time ticks: the first dot of each band and about every fifth after it
    ticks = []
    for lb in layout:
        for k, si in enumerate(lb["slots"]):
            if k == 0 or (k % 5 == 0 and len(lb["slots"]) - k > 2) or (len(lb["slots"]) > 1 and k == len(lb["slots"]) - 1 and k % 5 > 2):
                ticks.append(si)
    prev_day, prev_x = None, -99
    for si in ticks:
        if sx[si] - prev_x < 40:
            continue
        prev_x = sx[si]
        t = slots[si]["t"].astimezone(EDT)
        day = t.strftime("%a %-d %b")
        svg.append('<text x="%.1f" y="%d" class="cc-tick" text-anchor="middle">%s</text>' % (sx[si], H - B + 18, t.strftime("%H:%M")))
        if day != prev_day:
            svg.append('<text x="%.1f" y="%d" class="cc-day" text-anchor="middle">%s</text>' % (sx[si], H - B + 33, day))
            prev_day = day
    svg.append("</svg>")

    # dots: HTML, so each carries its own CSS-only card
    last_of = {s_: (pts_[-1] if pts_ else None) for s_, pts_ in (("fresh", fresh_kept), ("cached", cached_kept), ("port", port_line))}
    html_dots = []
    for i in sorted(range(len(dots)), key=lambda i: -dots[i]["v"]):
        d = dots[i]
        left, top = X(d) / W * 100, Yf(d["v"]) / H * 100
        stored, rails, port = d["basis"]
        isfork = d is fork_d
        cls = ["cc-dot", SERIES[d["series"]]["cls"], "cc-kept" if d["kept"] else "cc-dropped"]
        if d is last_of.get(d["series"]) and d["kept"] and d["series"] != "port":
            cls.append("cc-last")
        if isfork:
            cls.append("cc-fork")
        if left > 58:
            cls.append("cc-flip")
        label = "F# port, final re-baseline: where onCrack forked" if isfork else "%s: %s" % (d["label"], d["r"].get("change", ""))
        html_dots.append('<span class="%s" tabindex="0" role="button" style="left:%.2f%%;top:%.2f%%" aria-label="%s, %.2f times Rust">%s</span>'
                         % (" ".join(cls), left, top, e(label), d["v"],
                            card(d["era"], d["r"], d["view"], d["m"], d["r"].get("rust") or stored, port, d["v"], rails,
                                 series=("F# port" if isfork else d["label"]) if d["era"] is ONCRACK else None)))
    legend = ('<ul class="cc-legend">'
              '<li><i class="cc-sw cc-sw-fresh"></i>onCrack, fresh authorization <small>the default since round three</small></li>'
              '<li><i class="cc-sw cc-sw-cached"></i>onCrack, cached decision <small>opt-in; all there was in rounds one and two</small></li>'
              '<li><i class="cc-sw cc-sw-port"></i>the F# port\'s own climb <small>the line onCrack forked from</small></li>'
              '<li><i class="cc-sw cc-sw-rust"></i>Rust, pinned <small>1×</small></li>'
              '<li><i class="cc-sw cc-sw-rails"></i>Rails <small>stored baseline</small></li></ul>')
    chart = ('<div class="cc cc-hero">%s<div class="cc-scroll"><div class="cc-chart cc-wide">%s%s</div></div></div>' % (legend, "".join(svg), "".join(html_dots)))
    bandinfo = []
    for lb in layout:
        ds = [dots[i] for si in lb["slots"] for i in slots[si]["dots"]]
        bandinfo.append({"key": lb["band"]["key"], "label": lb["band"]["label"], "n": len(ds), "empty": bool(lb["band"].get("empty")),
                         "first": min((d["t"] for d in ds), default=None), "last": max((d["t"] for d in ds), default=None)})
    return {"chart": chart, "css": CSS_HERO, "bands": bandinfo, "hist": hist,
            "dots": [{"series": d["series"], "t": d["t"], "v": d["v"], "unit": d["r"].get("unit"), "change": d["r"].get("change", ""), "tier": d["r"].get("tier"),
                      "kept": d["kept"], "commit": d["r"].get("commit", ""), "band": d["band"]} for d in sorted(dots, key=lambda d: (d["t"], d["slot"]))],
            "latest": {s_: (pts_[-1]["v"] if pts_ else None) for s_, pts_ in (("fresh", fresh_kept), ("cached", cached_kept), ("port", port_line))},
            "port_level": port_level, "rails_level": rails_level, "fork": fork_d["v"], "branch_commit": branch["r"].get("commit") if branch else None}


CSS_HERO = """
.cc-hero{--cc-port:#5a6b94;--cc-cached:#b9570f;--cc-fresh:#0f766e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .cc-hero{--cc-port:#9fb1dc;--cc-cached:#f59e4b;--cc-fresh:#2dd4bf}}
:root[data-theme="dark"] .cc-hero{--cc-port:#9fb1dc;--cc-cached:#f59e4b;--cc-fresh:#2dd4bf}
.cc-legend{list-style:none;margin:0 0 12px;padding:0;display:flex;flex-wrap:wrap;gap:6px 22px;font-size:13px;color:var(--cc-ink)}
.cc-legend li{display:flex;align-items:center;gap:8px} .cc-legend small{color:var(--cc-mute);font-size:12px}
.cc-sw{display:inline-block;width:30px;height:0;border-top:4px solid var(--cc-fresh);border-radius:2px}
.cc-sw-cached{border-top:3px dashed var(--cc-cached)} .cc-sw-port{border-top:3px dotted var(--cc-port)}
.cc-sw-rust{border-top:2px dashed var(--cc-ink);opacity:.7} .cc-sw-rails{border-top:2px dotted var(--cc-mute)}
.cc-chart.cc-wide{aspect-ratio:1000/520}
.cc-hero .cc-band{fill:var(--cc-ink);opacity:.045} .cc-hero .cc-div{stroke:var(--cc-line);stroke-width:1}
.cc-bandlink{cursor:pointer;outline:none} .cc-bandname{fill:var(--cc-ink);font-weight:700;font-size:12.5px} .cc-bandspan{fill:var(--cc-mute);font-size:10.5px}
.cc-bandlink:hover .cc-bandname,.cc-bandlink:focus .cc-bandname{fill:var(--cc-fresh);text-decoration:underline}
.cc-none{fill:var(--cc-mute);font-size:11px;font-style:italic}
.cc-hero .cc-line{fill:none;stroke-linejoin:round;stroke-linecap:round}
.cc-l-fresh{stroke:var(--cc-fresh);stroke-width:4.5}
.cc-l-cached{stroke:var(--cc-cached);stroke-width:3;stroke-dasharray:8 6}
.cc-l-branch{stroke:var(--cc-fresh);stroke-width:2.5;stroke-dasharray:2 6;opacity:.7}
.cc-l-port{stroke:var(--cc-port);stroke-width:3;stroke-dasharray:1 6}
.cc-rails{stroke:var(--cc-mute);stroke-width:1.5;stroke-dasharray:2 5} .cc-raillabel{fill:var(--cc-mute);font-weight:650;font-size:12.5px}
.cc-endlabel{font-weight:700;font-size:12.5px} .cc-t-fresh{fill:var(--cc-fresh)} .cc-t-cached{fill:var(--cc-cached)} .cc-t-port{fill:var(--cc-port)}
.cc-hero .cc-dot{width:13px;height:13px;margin:-6.5px 0 0 -6.5px;border-width:2.5px}
.cc-hero .cc-s-fresh{border-color:var(--cc-fresh)} .cc-hero .cc-s-cached{border-color:var(--cc-cached)} .cc-hero .cc-s-port{border-color:var(--cc-port);width:10px;height:10px;margin:-5px 0 0 -5px;border-width:2px}
.cc-hero .cc-dot.cc-last{width:17px;height:17px;margin:-8.5px 0 0 -8.5px}
.cc-hero .cc-s-fresh.cc-last{background:var(--cc-fresh)} .cc-hero .cc-s-cached.cc-last{background:var(--cc-cached)}
.cc-hero .cc-dot.cc-fork{width:15px;height:15px;margin:-7.5px 0 0 -7.5px;border-color:var(--cc-ink);border-width:3px;background:var(--cc-port)}
.cc-hero .cc-dot.cc-dropped{border-color:var(--cc-drop);width:9px;height:9px;margin:-4.5px 0 0 -4.5px;border-width:2px;background:var(--cc-card)}
.cc-hero .cc-dot:hover,.cc-hero .cc-dot:focus{z-index:6}
.cc-hero .cc-dot:hover::before,.cc-hero .cc-dot:focus::before{content:"";position:absolute;inset:-5px;border-radius:50%;border:2px solid var(--cc-ink);opacity:.35}
@media (max-width:640px){.cc-hero .cc-chart.cc-wide{min-width:980px}}
"""


def check_start():
    """The embedded record of onCrack's start must be the stored F# port medians of bench/results/phase7-final: prints one line per
    workload that differs and exits 1 (python3 bench/progress/climb.py --check)."""
    bad = 0
    st = history()["oncrack_start"]
    for w, cs in (st.get("workloads") or {}).items():
        for c, v in cs.items():
            want = medians("fsharp")[w][c]
            if round(want["rps"], 1) != v["rps"] or (want["cpu_us"] and round(want["cpu_us"], 1) != v.get("cpu_us")):
                print("start differs from phase7-final: %s %s: %s vs %s" % (w, c, v, want))
                bad += 1
    print("oncrack_start matches bench/results/phase7-final" if not bad else "%d differences" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_start())
    r = climb()
    print("latest %.3fx Rust, %.3fx the F# port, %d dots" % (r["latest"], r.get("vs_port") or 0, len(r["points"])))
