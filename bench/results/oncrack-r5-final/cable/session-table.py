#!/usr/bin/env python3
"""The tables of bench/results/oncrack-r5-final.md, from the raw results beside this script (every number there comes from here).

  python3 bench/results/oncrack-r5-final/cable/session-table.py [--json]

- t3/{rust,fsharp,oncrack}-{1,2,3}.json: the cable suite alone, one session, 3 reps, 100/500/1,000/2,000 clients, 15 s saturated.
- sends/{...}-1.json: one more rep of each, 8 s saturated, with perf stat counting the app's send syscalls over 3 s of the saturated phase
  (the tracepoints cost the app a few percent, so these runs give sends per delivery and nothing else).
"""
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.environ.get("CABLE_RES") or HERE
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "lib"))
import quicklog  # noqa: E402

APPS = [("rust", "Rust f9dca47"), ("fsharp", "F# port"), ("oncrack", "onCrack")]
COUNTS = (100, 500, 1000, 2000)


def load(directory, app):
    return quicklog.load(os.path.join(RES, directory), app)


def med(v):
    return st.median(v) if v else None


def rng(v):
    return f" [{min(v):,.0f}-{max(v):,.0f}]" if len(v) > 1 else ""


def per_run(runs, n, getter):
    out = []
    for r in runs:
        for c in r["cable"]:
            if c["clients"] == n:
                try:
                    v = getter(c)
                except (KeyError, TypeError):
                    v = None
                if v is not None:
                    out.append(v)
    return out


def checks(runs):
    """(phases, ready == clients, every posted message complete, failed connects, closed mid-run, window stalls) over every cable phase."""
    n = ok_ready = ok_complete = failed = closed = stalls = 0
    for r in runs:
        for c in r["cable"]:
            n += 1
            ok_ready += c["ready"] == c["clients"]
            t = c["throughput"]
            ok_complete += t["complete"] == t["posted"] and c["latency"]["complete"] == c["latency"]["messages"]
            failed += c["failed"]
            closed += c.get("client", {}).get("closed_midrun", 0)
            stalls += t.get("window_stalls", 0)
    return n, ok_ready, ok_complete, failed, closed, stalls


def main():
    runs = {a: load("t3", a) for a, _ in APPS}
    sends = {a: load("sends", a) for a, _ in APPS}
    cells = {a: quicklog.cable_cells(runs[a]) for a, _ in APPS}
    data = {}
    print("### Validation, every cable phase of the session\n")
    print("| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |")
    print("|---|---|---|---|---|---|---|")
    for a, label in APPS:
        n, r_, c_, f_, cl, s_ = checks(runs[a] + sends[a])
        print(f"| {label} | {n} | {r_}/{n} | {c_}/{n} | {f_} | {cl} | {s_} |")
    print("\n### Delivered messages per second (each message to every client), median of 3 and the reps in run order\n")
    print("| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |")
    print("|---|---|---|---|---|---|---|---|")
    for n in COUNTS:
        m = {a: med(cells[a][n]["msgs"]) for a, _ in APPS}
        reps = " / ".join(",".join(f"{x:,.0f}" for x in cells[a][n]["msgs"]) for a, _ in APPS)
        print(f"| {n:,} | {m['rust']:,.0f}{rng(cells['rust'][n]['msgs'])} | {m['fsharp']:,.0f}{rng(cells['fsharp'][n]['msgs'])} | "
              f"**{m['oncrack']:,.0f}**{rng(cells['oncrack'][n]['msgs'])} | **{m['oncrack'] / m['rust']:.2f}x** | **{m['oncrack'] / m['fsharp']:.2f}x** | "
              f"{m['fsharp'] / m['rust']:.2f}x | {reps} |")
        d = data.setdefault(n, {})
        for a, _ in APPS:
            sd = quicklog.cable_cells(sends[a]).get(n, {})
            sp = per_run(sends[a], n, lambda c: c["sends_per_delivery"])
            d[a] = {
                "msgs_per_sec": m[a], "msgs_per_sec_reps": cells[a][n]["msgs"],
                "server_cpu_us_per_delivery": med(cells[a][n]["cpu_us"]), "server_cores": med(cells[a][n]["srv_cores"]),
                "loadgen_cores": med(cells[a][n]["lg_cores"]),
                "loadgen_cpu_us_per_delivery": (med(cells[a][n]["lg_cores"]) * 1e6 / (m[a] * n)) if m[a] else None,
                "sends_per_delivery": med(sp),
                "pss_idle_mb": med(cells[a][n]["pss_idle"]), "pss_saturated_mb": med(cells[a][n]["pss_sat"]),
                "paced_all_p50_ms": med(per_run(runs[a], n, lambda c: c["latency"]["all_clients"]["p50_ms"])),
                "paced_all_p99_ms": med(per_run(runs[a], n, lambda c: c["latency"]["all_clients"]["p99_ms"])),
                "paced_client_p50_ms": med(per_run(runs[a], n, lambda c: c["latency"]["per_client"]["p50_ms"])),
                "paced_client_p99_ms": med(per_run(runs[a], n, lambda c: c["latency"]["per_client"]["p99_ms"])),
                "saturated_all_p50_ms": med(per_run(runs[a], n, lambda c: c["throughput"]["all_clients"]["p50_ms"])),
                "saturated_all_p99_ms": med(per_run(runs[a], n, lambda c: c["throughput"]["all_clients"]["p99_ms"])),
                "posts_per_sec": med(per_run(runs[a], n, lambda c: c["throughput"]["posts_per_sec"])),
            }
    print("\n### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores")
    print("(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client")
    print("subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.\n")
    print("| clients | | Rust | F# port | onCrack | onCrack / Rust |")
    print("|---|---|---|---|---|---|")
    rows = [("server CPU us / delivery", "server_cpu_us_per_delivery", 2), ("server cores busy", "server_cores", 2),
            ("load generator cores busy", "loadgen_cores", 2), ("load generator CPU us / delivery", "loadgen_cpu_us_per_delivery", 2), ("sends / delivery", "sends_per_delivery", 3),
            ("Pss idle (MB)", "pss_idle_mb", 0), ("Pss saturated (MB)", "pss_saturated_mb", 0)]
    for n in COUNTS:
        d = data[n]
        for label, key, digits in rows:
            vals = [d[a][key] for a, _ in APPS]
            cells_ = [f"{v:,.{digits}f}" if v is not None else "-" for v in vals]
            ratio = f"{d['oncrack'][key] / d['rust'][key]:.2f}x" if d["rust"][key] and d["oncrack"][key] is not None else ""
            print(f"| {n:,} | {label} | {' | '.join(cells_)} | {ratio} |")
        for label, p50, p99 in [("paced post -> last client p50 / p99", "paced_all_p50_ms", "paced_all_p99_ms"),
                                ("paced post -> a client p50 / p99", "paced_client_p50_ms", "paced_client_p99_ms"),
                                ("saturated post -> last client p50 / p99", "saturated_all_p50_ms", "saturated_all_p99_ms")]:
            cells_ = [f"{d[a][p50]:.1f} / {d[a][p99]:.1f}" for a, _ in APPS]
            ratio = f"{d['oncrack'][p50] / d['rust'][p50]:.2f}x" if d["rust"][p50] else ""
            print(f"| {n:,} | {label} | {' | '.join(cells_)} | {ratio} |")
    return data


if __name__ == "__main__":
    summary = main()
    if "--json" in sys.argv:
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1, default=str)
