#!/usr/bin/env python3
"""onCrack R2.3 (front server fast path): the tier 3 medians of bench/results/oncrack-r2-front/tier3 (the five workloads, c=1 and 16)
against Rust and the F# port as round 1's four-way session measured them (bench/results/oncrack-round1-final, same harness, same seed),
and against onCrack there; the realistic workloads of tier3-real against the same-session baseline of bench/results/oncrack-r2-bench and
R2.2's tier 3 (bench/results/oncrack-r2-post/tier3-real). Run from the repo root:
python3 bench/results/oncrack-r2-front/review/table.py"""
import glob, json, math, statistics
ROUTES = ["room_show", "messages_page", "sidebar", "search", "post_message"]
NAMES = {"room_show": "room page", "messages_page": "messages page", "sidebar": "sidebar", "search": "search", "post_message": "post a message"}

def load(pattern):
    cells = {}
    for f in sorted(glob.glob(pattern)):
        for r in json.load(open(f)).get("http", []):
            cells.setdefault((r["route"], r["conc"]), []).append((r["rps"], r["cost"]["server_cpu_us_per_req"], r["latency"]["p99_ms"]))
    return {k: tuple(statistics.median(x[i] for x in v) for i in range(3)) + (len(v),) for k, v in cells.items()}

R1 = "bench/results/oncrack-round1-final"
base = {a: load(f"{R1}/{a}-*.json") for a in ("rust", "fsharp", "oncrack")}
new = load("bench/results/oncrack-r2-front/tier3/oncrack-*.json")
print("| Workload | c | Rust | F# port | onCrack round 1 | **onCrack R2.3** | **/ Rust** | **/ port** | / round 1 | p99 ms (round 1) |")
print("|---|---|---|---|---|---|---|---|---|---|")
geo = {}
for route in ROUTES:
    for c in (1, 16):
        r, f, o1 = (base[a][(route, c)] for a in ("rust", "fsharp", "oncrack"))
        o = new[(route, c)]
        cell = lambda x: f"{x[0]:,.0f} ({x[1]:,.1f})"
        print(f"| {NAMES[route]} | {c} | {cell(r)} | {cell(f)} | {cell(o1)} | **{cell(o)}** | **{o[0]/r[0]:.2f}x** (CPU {o[1]/r[1]:.2f}x) | "
              f"**{o[0]/f[0]:.2f}x** (CPU {o[1]/f[1]:.2f}x) | {o[0]/o1[0]:.2f}x | {o[2]:.2f} ({o1[2]:.2f}) |")
        for k, v in (("r", o[0]/r[0]), ("f", o[0]/f[0]), ("o1", o[0]/o1[0])):
            geo.setdefault((k, c), []).append(v)
print()
for c in (1, 16):
    g = {k: math.exp(sum(map(math.log, geo[(k, c)])) / 5) for k in ("r", "f", "o1")}
    print(f"c={c} geometric mean of the five: onCrack/Rust {g['r']:.2f}x, onCrack/port {g['f']:.2f}x, R2.3/round 1 {g['o1']:.2f}x")

def real(dirpath):
    cells = {}
    for f in sorted(glob.glob(f"{dirpath}/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        app = d.get("app") or f.split("/")[-1].split("-")[0]
        for r in d.get("http", []):
            lanes = r.get("lanes")
            if not lanes:
                continue
            for lane, v in lanes.items():
                cells.setdefault((app, r["route"], lane), []).append(v["rps"])
    return {k: statistics.median(v) for k, v in cells.items()}

print()
b = real("bench/results/oncrack-r2-bench")
r22 = real("bench/results/oncrack-r2-post/tier3-real")
n = real("bench/results/oncrack-r2-front/tier3-real")
print("| Workload | lane | Rust | F# port | onCrack R2.0 | onCrack R2.2 | **onCrack R2.3** | **/ Rust** | **/ port** |")
print("|---|---|---|---|---|---|---|---|---|")
for w in ("mixed", "spread", "spread_mixed", "search_spread"):
    for lane in ("reads", "posts"):
        key = ("oncrack", w, lane)
        if key not in n:
            continue
        rr, ff, o0 = b.get(("rust", w, lane)), b.get(("fsharp", w, lane)), b.get(key)
        o2 = r22.get(key)
        fmt = lambda x: "-" if x is None else f"{x:,.0f}"
        print(f"| {w} | {lane} | {fmt(rr)} | {fmt(ff)} | {fmt(o0)} | {fmt(o2)} | **{n[key]:,.0f}** | **{n[key]/rr:.2f}x** | **{n[key]/ff:.2f}x** |")
