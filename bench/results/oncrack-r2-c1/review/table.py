#!/usr/bin/env python3
"""onCrack R2.4 (one connection): every table of bench/results/oncrack-r2-c1.md, from the raw runs beside this script. Run from the repo root:
python3 bench/results/oncrack-r2-c1/review/table.py

- tier3/: the five workloads at c=1 and 16 on the rebuilt image, 3 reps; compared with round 1's same-session Rust and port medians
  (bench/results/oncrack-round1-final) and with R2.3's tier 3 (bench/results/oncrack-r2-front/tier3).
- tier3-extra/: /up, avatar, the CSS file and posts at c=1, 16, 64, one rep.
- tier3-real/: the realistic workloads, 3 reps; baseline R2.0's same-session Rust and port, R2.3's tier 3.
- t2-*: tier 2 runs, one rep each (mounted builds; the names say the setting).
"""
import glob, json, math, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(RES, "..", "..", ".."))
ROUTES = ["room_show", "messages_page", "sidebar", "search", "post_message"]
NAMES = {"room_show": "room page", "messages_page": "messages page", "sidebar": "sidebar", "search": "search", "post_message": "post a message",
         "up": "/up", "avatar": "avatar", "static_css": "CSS file"}


def load(pattern):
    cells = {}
    for f in sorted(glob.glob(pattern)):
        for r in json.load(open(f)).get("http", []):
            if not r.get("gzip", True):
                continue
            cost = r["cost"]
            cells.setdefault((r["route"], r["conc"]), []).append(
                (r["rps"], cost["server_cpu_us_per_req"], r["latency"]["p99_ms"], r["latency"]["p50_ms"], cost["server_cores_busy"]))
    return {k: tuple(statistics.median(x[i] for x in v) for i in range(5)) + (len(v),) for k, v in cells.items()}


def real(dirpath):
    cells = {}
    for f in sorted(glob.glob(f"{dirpath}/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        app = d.get("app") or os.path.basename(f).split("-")[0]
        for r in d.get("http", []):
            for lane, v in (r.get("lanes") or {}).items():
                cells.setdefault((app, r["route"], lane), []).append((v["rps"], v.get("p50_ms"), v.get("p99_ms")))
    return {k: tuple(statistics.median(x[i] for x in v) if all(x[i] is not None for x in v) else None for i in range(3)) for k, v in cells.items()}


def p(path):
    return os.path.join(ROOT, "bench", "results", path)


R1 = p("oncrack-round1-final")
base = {a: load(f"{R1}/{a}-*.json") for a in ("rust", "fsharp", "oncrack")}
r23 = load(p("oncrack-r2-front/tier3/oncrack-*.json"))
new = load(os.path.join(RES, "tier3/oncrack-*.json"))
print("## Five workloads, tier 3: req/s (CPU us per request, cores busy)\n")
print("| Workload | c | Rust | F# port | onCrack R2.3 | **onCrack R2.4** | **/ Rust** | **/ port** | / R2.3 | p50 / p99 ms (R2.3) |")
print("|---|---|---|---|---|---|---|---|---|---|")
geo = {}
for route in ROUTES:
    for c in (1, 16):
        r, f, o3 = base["rust"][(route, c)], base["fsharp"][(route, c)], r23[(route, c)]
        o = new[(route, c)]
        cell = lambda x: f"{x[0]:,.0f} ({x[1]:,.1f})"
        print(f"| {NAMES[route]} | {c} | {cell(r)} | {cell(f)} | {cell(o3)} | **{o[0]:,.0f} ({o[1]:,.1f}, {o[4]:.2f})** | **{o[0]/r[0]:.2f}x** (CPU {o[1]/r[1]:.2f}x) | "
              f"**{o[0]/f[0]:.2f}x** (CPU {o[1]/f[1]:.2f}x) | {o[0]/o3[0]:.2f}x | {o[3]:.2f} / {o[2]:.2f} ({o3[3]:.2f} / {o3[2]:.2f}) |")
        for k, v in (("r", o[0] / r[0]), ("f", o[0] / f[0]), ("o3", o[0] / o3[0])):
            geo.setdefault((k, c), []).append(v)
print()
for c in (1, 16):
    g = {k: math.exp(sum(map(math.log, geo[(k, c)])) / 5) for k in ("r", "f", "o3")}
    print(f"c={c} geometric mean of the five: onCrack/Rust {g['r']:.2f}x, onCrack/port {g['f']:.2f}x, R2.4/R2.3 {g['o3']:.2f}x")
print("\nCores busy (server) at c=1, Rust -> R2.3 -> R2.4:")
for route in ROUTES:
    print(f"  {NAMES[route]:15s} {base['rust'][(route,1)][4]:.2f} -> {r23[(route,1)][4]:.2f} -> {new[(route,1)][4]:.2f}   (n reps {new[(route,1)][5]})")

ex = load(os.path.join(RES, "tier3-extra/oncrack-*.json"))
if ex:
    print("\n## Other routes, tier 3 (one rep, 20-40 s warm-up): req/s (CPU us per request, cores busy), round 1 onCrack / Rust in the same layout\n")
    print("| Route | c | Rust (round 1) | onCrack round 1 | **onCrack R2.4** | / Rust | p50 / p99 ms |")
    print("|---|---|---|---|---|---|---|")
    for route in ("up", "avatar", "static_css", "post_message"):
        for c in (1, 16, 64):
            if (route, c) not in ex or (route, c) not in base["rust"]:
                continue
            r, o1, o = base["rust"][(route, c)], base["oncrack"][(route, c)], ex[(route, c)]
            cell = lambda x: f"{x[0]:,.0f} ({x[1]:,.1f}, {x[4]:.2f})"
            print(f"| {NAMES[route]} | {c} | {cell(r)} | {cell(o1)} | **{cell(o)}** | {o[0]/r[0]:.2f}x | {o[3]:.2f} / {o[2]:.2f} |")

print("\n## Realistic workloads, tier 3 (c=16 readers), req/s per lane\n")
b = real(p("oncrack-r2-bench"))
o23 = real(p("oncrack-r2-front/tier3-real"))
n = real(os.path.join(RES, "tier3-real"))
print("| Workload | lane | Rust | F# port | onCrack R2.3 | **onCrack R2.4** | / R2.3 | / Rust | / port |")
print("|---|---|---|---|---|---|---|---|---|")
for w in ("mixed", "spread", "spread_mixed", "search_spread"):
    for lane in ("reads", "posts"):
        key = ("oncrack", w, lane)
        if key not in n:
            continue
        rr, ff = b.get(("rust", w, lane)), b.get(("fsharp", w, lane))
        o3 = o23.get(key)
        fmt = lambda x: "-" if x is None else f"{x[0]:,.0f}"
        print(f"| {w} | {lane} | {fmt(rr)} | {fmt(ff)} | {fmt(o3)} | **{n[key][0]:,.0f}** | {n[key][0]/o3[0]:.2f}x | {n[key][0]/rr[0]:.2f}x | {n[key][0]/ff[0]:.2f}x |")

print("\n## Tier 2, posts: req/s (CPU us per request) by setting and concurrency (one rep each, same build, one session)\n")
sets = [("r23", "R2.3 behavior (solo off, pool spins)"), ("solo", "solo only"), ("r23-spin0", "spin 0 only"), ("solo-spin0", "solo + spin 0 (shipped)")]
print("| Setting | " + " | ".join(f"c={c}" for c in (1, 2, 4, 16, 64)) + " |")
print("|---|---|---|---|---|---|")
for key, label in sets:
    cells = load(os.path.join(RES, f"t2-postmatrix-{key}/oncrack-1.json"))
    row = []
    for c in (1, 2, 4, 16, 64):
        x = cells.get(("post_message", c))
        row.append("-" if not x else f"{x[0]:,.0f} ({x[1]:,.0f})")
    print(f"| {label} | " + " | ".join(row) + " |")
