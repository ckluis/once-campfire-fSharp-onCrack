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
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOG = os.path.join(ROOT, "bench/results/oncrack-log.jsonl")
STORED = os.path.join(ROOT, "bench/results/phase7-final")   # Rust, the F# port and Rails, one session, 3 reps each
HISTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
WORKLOADS = [("room_show", "Room page"), ("messages_page", "Messages page"), ("sidebar", "Sidebar"),
             ("search", "Search"), ("post_message", "Post a message")]
CONCS = [("c16", 16), ("c1", 1)]
e = html.escape

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


def entries(hist, era=ONCRACK):
    if era is PORT_ERA:
        rows = [dict(h) for h in hist["port_era"]["comparable"]] + [port_start_entry(hist)]
    else:
        rows = [start_entry(hist)]
    return rows + read_log(era["log"])


def commits_between(a, b):
    """Subjects of the commits after a up to b that change the app itself (not the bench, docs or this page)."""
    try:
        out = subprocess.run(["git", "-C", ROOT, "log", "--reverse", "--format=%h %s", f"{a}..{b}", "--",
                              "src", "Dockerfile", "Directory.Build.props", "Directory.Packages.props"],
                             capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l for l in out.splitlines() if l and not l.split(" ", 1)[1].startswith("bench: log")]


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


def card(era, r, view, measured, rust, port, ov, rails):
    """The hover card of one dot. `port` is the stored F# port (a column and a ratio in onCrack's chart, None in the port era's)."""
    name = era["name"]
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
            % (e(t.astimezone().strftime("%a %-d %b, %H:%M %Z") if t else "?"), e(str(r.get("unit", ""))), e(str(r.get("tier", ""))),
               "" if kept else " · reverted", e(str(r.get("change", ""))), e(str(r.get("commit", ""))),
               e(str(r.get("build", ""))[:30]), (" · overall %.2f× of Rust" % ov) if ov else "", span, span, sub_head, "".join(rows), done(r),
               foot, name))


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
                       % (X(r), H - B + 20, t.astimezone().strftime("%H:%M"), X(r), H - B + 36, t.astimezone().strftime("%a %-d %b")))
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
