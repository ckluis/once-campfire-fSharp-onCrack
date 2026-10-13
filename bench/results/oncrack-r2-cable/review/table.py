#!/usr/bin/env python3
"""The tables of bench/results/oncrack-r2-cable.md, from the raw results beside this script (every number there comes from here).

  python3 bench/results/oncrack-r2-cable/review/table.py [--json]

- tier 3: t3/{rust,fsharp,oncrack}-{1,2,3}.json, the cable suite alone on the rebuilt image, one session, 3 reps.
- tier 2: the t2-* runs, one rep each, in the order they were made (mounted builds of the unit's steps, and Rust's controls).
- post: t3-post (onCrack), t3-post-control (the F# port), and the post_message A/B against round 1's source (t2-post-*).
"""
import glob
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(RES, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "lib"))
import quicklog  # noqa: E402

APPS = [("rust", "Rust"), ("fsharp", "F# port"), ("oncrack", "onCrack")]


def load(directory, app):
    return quicklog.load(os.path.join(RES, directory), app)


def med(v):
    return st.median(v) if v else None


def rng(v):
    return f" [{min(v):,.0f}-{max(v):,.0f}]" if len(v) > 1 else ""


def latency(runs, n, path):
    out = []
    for r in runs:
        for c in r["cable"]:
            if c["clients"] == n:
                v = c
                for k in path:
                    v = v.get(k, {}) if isinstance(v, dict) else {}
                if isinstance(v, (int, float)):
                    out.append(v)
    return out


def tier3():
    cells = {a: quicklog.cable_cells(load("t3", a)) for a, _ in APPS}
    runs = {a: load("t3", a) for a, _ in APPS}
    data = {}
    print("### Tier 3: cable suite, rebuilt image, 3 reps, one session\n")
    print("| clients | Rust msgs/s | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust |")
    print("|---|---|---|---|---|---|---|")
    for n in (100, 500, 1000):
        m = {a: med(cells[a][n]["msgs"]) for a, _ in APPS}
        print(f"| {n:,} | {m['rust']:,.0f}{rng(cells['rust'][n]['msgs'])} | {m['fsharp']:,.0f}{rng(cells['fsharp'][n]['msgs'])} | "
              f"**{m['oncrack']:,.0f}**{rng(cells['oncrack'][n]['msgs'])} | **{m['oncrack'] / m['rust']:.2f}x** | **{m['oncrack'] / m['fsharp']:.2f}x** | "
              f"{m['fsharp'] / m['rust']:.2f}x |")
        data[n] = {a: {"msgs_per_sec": m[a], "msgs_per_sec_reps": cells[a][n]["msgs"],
                       "server_cpu_us_per_delivery": med(cells[a][n]["cpu_us"]), "server_cores": med(cells[a][n]["srv_cores"]),
                       "loadgen_cores": med(cells[a][n]["lg_cores"]), "pss_idle_mb": med(cells[a][n]["pss_idle"]),
                       "pss_saturated_mb": med(cells[a][n]["pss_sat"]),
                       "paced_all_p50_ms": med(latency(runs[a], n, ["latency", "all_clients", "p50_ms"])),
                       "paced_all_p99_ms": med(latency(runs[a], n, ["latency", "all_clients", "p99_ms"])),
                       "saturated_all_p50_ms": med(latency(runs[a], n, ["throughput", "all_clients", "p50_ms"])),
                       "saturated_post_p50_ms": med(latency(runs[a], n, ["throughput", "post", "p50_ms"]))} for a, _ in APPS}
    print("\nServer CPU per delivery (us, the container's cpu.stat over the saturated phase / messages x clients), cores busy, the load")
    print("generator's cores (of 4), and the app process's peak Pss (MB) with every client subscribed and idle / saturated:\n")
    print("| clients | | Rust | F# port | onCrack | onCrack / Rust |")
    print("|---|---|---|---|---|---|")
    for n in (100, 500, 1000):
        d = data[n]
        rows = [("server CPU us / delivery", "server_cpu_us_per_delivery", 2), ("server cores busy", "server_cores", 2),
                ("load generator cores busy", "loadgen_cores", 2), ("Pss idle (MB)", "pss_idle_mb", 0), ("Pss saturated (MB)", "pss_saturated_mb", 0),
                ("paced post -> all p50 / p99 (ms)", None, 1), ("saturated post -> all p50 (ms)", "saturated_all_p50_ms", 1),
                ("saturated POST p50 (ms)", "saturated_post_p50_ms", 2)]
        for label, key, digits in rows:
            if key is None:
                cells_ = [f"{d[a]['paced_all_p50_ms']:.1f} / {d[a]['paced_all_p99_ms']:.1f}" for a, _ in APPS]
                ratio = ""
            else:
                cells_ = [f"{d[a][key]:,.{digits}f}" for a, _ in APPS]
                ratio = f"{d['oncrack'][key] / d['rust'][key]:.2f}x" if d["rust"][key] else ""
            print(f"| {n:,} | {label} | {' | '.join(cells_)} | {ratio} |")
    return data


T2 = [("t2-base-0", "oncrack", "round 1's image (control; harness with CPU per delivery, old cable client)"),
      ("t2-rust-0", "rust", "Rust (control, old cable client)"),
      ("t2-direct-1", "oncrack", "+ direct socket writes after the probe (old cable client)"),
      ("t2-rust-lg2", "rust", "Rust, cheaper cable client"),
      ("t2-direct-lg2", "oncrack", "direct writes, cheaper cable client"),
      ("t2-batch-1", "oncrack", "+ WakeBatch (a post's broadcasts wake once)"),
      ("t2-yield1", "oncrack", "rejected: + one yield before draining"),
      ("t2-hold1000", "oncrack", "+ the line holds wakes up to 1 ms (no yield)"),
      ("t2-compact", "oncrack", "+ compact Turbo Stream JSON")]


def tier2():
    print("\n### Tier 2: one rep each, in the order made\n")
    print("| run | build | 100: msgs/s (us/delivery) | 500 | 1,000 | 1,000: server / loadgen cores | Pss saturated at 1,000 (MB) |")
    print("|---|---|---|---|---|---|---|")
    out = []
    for d, app, label in T2:
        c = quicklog.cable_cells(load(d, app))
        cell = lambda n: f"{c[n]['msgs'][0]:,.0f} ({c[n]['cpu_us'][0]:.2f})" if c[n]["cpu_us"] else f"{c[n]['msgs'][0]:,.0f}"
        print(f"| `{d}` | {label} | {cell(100)} | {cell(500)} | {cell(1000)} | {c[1000]['srv_cores'][0]:.2f} / {c[1000]['lg_cores'][0]:.2f} | {c[1000]['pss_sat'][0]:,.0f} |")
        out.append({"run": d, "app": app, "label": label, **{str(n): {"msgs_per_sec": c[n]["msgs"][0], "server_cpu_us_per_delivery": c[n]["cpu_us"][0],
                                                                    "server_cores": c[n]["srv_cores"][0], "loadgen_cores": c[n]["lg_cores"][0],
                                                                    "pss_saturated_mb": c[n]["pss_sat"][0]} for n in (100, 500, 1000)}})
    return out


def post():
    print("\n### post_message (the change touches the post's broadcast path)\n")
    print("| run | build | c | req/s | CPU us/req | warm-up |")
    print("|---|---|---|---|---|---|")
    out = []
    for d, app, label in [("t3-post", "oncrack", "R2.1 image"), ("t3-post-control", "fsharp", "the F# port (control)"),
                          ("t2-post-base", "oncrack", "round 1's source, mounted"), ("t2-post-new", "oncrack", "R2.1 image"),
                          ("t2-post-base90", "oncrack", "round 1's source, 90 s warm-up"), ("t2-post-new90", "oncrack", "R2.1 image, 90 s warm-up")]:
        for r in load(d, app):
            for h in r["http"]:
                w = h["warmup"]
                print(f"| `{d}` | {label} | {h['conc']} | {h['rps']:,.0f} | {h['cost']['server_cpu_us_per_req']:.1f} | {w['secs']:.0f} s, {w['reason']} |")
                out.append({"run": d, "label": label, "conc": h["conc"], "rps": h["rps"], "cpu_us": h["cost"]["server_cpu_us_per_req"],
                            "warmup_secs": w["secs"], "warmup": w["reason"], "warmup_windows_rps": w.get("windows_rps")})
    return out


if __name__ == "__main__":
    summary = {"tier3": tier3(), "tier2": tier2(), "post": post()}
    if "--json" in sys.argv:
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1, default=str)
