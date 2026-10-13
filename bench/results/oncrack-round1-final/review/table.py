#!/usr/bin/env python3
"""onCrack round 1 four-way re-baseline: the five workloads at c=1, 16 and 64 from bench/results/oncrack-round1-final, medians of 3 reps
(req/s, server CPU us/req, p99 ms), with onCrack against Rust and the F# port re-measured in the same session, and against the stored
phase7-final medians. Run from the repo root: python3 bench/results/oncrack-round1-final/review/table.py"""
import glob, json, math, statistics
ROUTES = ["room_show", "messages_page", "sidebar", "search", "post_message"]
NAMES = {"room_show": "room page", "messages_page": "messages page", "sidebar": "sidebar", "search": "search", "post_message": "post a message"}
def load(pattern):
    cells = {}
    for f in sorted(glob.glob(pattern)):
        for r in json.load(open(f)).get("http", []):
            cells.setdefault((r["route"], r["conc"]), []).append((r["rps"], r["cost"]["server_cpu_us_per_req"], r["latency"]["p99_ms"]))
    return {k: tuple(statistics.median(x[i] for x in v) for i in range(3)) + (len(v),) for k, v in cells.items()}
D = "bench/results/oncrack-round1-final"
now = {a: load(f"{D}/{a}-*.json") for a in ("reference", "rust", "fsharp", "oncrack")}
stored = {a: load(f"bench/results/phase7-final/{a}-*.json") for a in ("rust", "fsharp")}
print("| Workload | c | Rails | Rust | F# port | onCrack | onCrack / Rust | onCrack / port | port / Rust | Rust now / stored | port now / stored |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
geo = {}
for route in ROUTES:
    for c in (1, 16, 64):
        rl, r, f, o = (now[a][(route, c)] for a in ("reference", "rust", "fsharp", "oncrack"))
        sr, sf = stored["rust"][(route, c)], stored["fsharp"][(route, c)]
        cell = lambda x: f"{x[0]:,.0f} ({x[1]:,.1f})"
        print(f"| {NAMES[route]} | {c} | {cell(rl)} | {cell(r)} | {cell(f)} | {cell(o)} | **{o[0]/r[0]:.2f}x** (CPU {o[1]/r[1]:.2f}x) | **{o[0]/f[0]:.2f}x** (CPU {o[1]/f[1]:.2f}x) | {f[0]/r[0]:.2f}x | {r[0]/sr[0]:.3f} | {f[0]/sf[0]:.3f} |")
        for k, v in (("or", o[0]/r[0]), ("of", o[0]/f[0]), ("fr", f[0]/r[0]), ("os_r", o[0]/sr[0]), ("os_f", o[0]/sf[0])):
            geo.setdefault((k, c), []).append(v)
print()
for c in (1, 16, 64):
    g = {k: math.exp(sum(map(math.log, geo[(k, c)])) / 5) for k in ("or", "of", "fr", "os_r", "os_f")}
    print(f"c={c} geometric mean of the five: onCrack/Rust {g['or']:.2f}x, onCrack/port {g['of']:.2f}x, port/Rust {g['fr']:.2f}x; "
          f"against the stored phase7-final medians: onCrack/Rust {g['os_r']:.2f}x, onCrack/port {g['os_f']:.2f}x")
