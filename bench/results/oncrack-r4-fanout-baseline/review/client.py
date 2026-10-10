#!/usr/bin/env python3
"""The load generator comparison of bench/results/oncrack-r4-fanout-baseline.md, from the runs beside this script (client/*/).

  python3 bench/results/oncrack-r4-fanout-baseline/review/client.py

Each directory is one `bench/cable/ab` session: one app in one container, the variants alternating. The file name says app, clients,
variant (`raw_3` is the raw client with 3 loops, `raw_3_--window,0` adds arguments) and rep.
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(os.path.dirname(HERE), "client")
NOTE = {
    "r41-smoke-2000-fd-limit": "2,000 clients, descriptor limit 1,024 (bench/run raises it now)",
    "r41-ab1": "first raw client (whole-frame search, no window), host busy (spin probe 5x the quiet baseline)",
    "r41-ab2-oncrack": "raw client, whole-frame search, no window, 2 reps",
    "r41-ab2-rust": "raw client, whole-frame search, no window, 2 reps",
    "r41-ab3": "raw client, tail-window search, no window, 5 reps, host busy",
    "r41-ab4": "window 32 against none (and tungstenite with window 32), 3 reps",
    "r41-ab5": "window sweep 32/64/128/192, 2 reps",
    "r41-ab6-rust": "window 128, raw:3",
    "r41-ab6-fsharp": "window 128, raw:3",
    "r41-ab7": "tail-window search against whole-frame search, window 128, 4 reps",
}


def main():
    for d in sorted(glob.glob(os.path.join(CLIENT, "*"))):
        name = os.path.basename(d)
        print(f"\n#### {name}: {NOTE.get(name, '')}\n")
        print("| run | app | variant | msgs/s | posted / complete | closed mid-run | server cores | server us/del | loadgen cores | loadgen us/del | paced p50 / p99 (ms) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            if f.endswith(".phases.json"):
                continue
            base = os.path.basename(f)[:-5]
            c = json.load(open(f))
            c = c["cable"][0] if "cable" in c else c
            m = re.match(r"(\w+)-(\d+)-(.+)-(\d+)$", base)
            app, variant, rep = (m.group(1), m.group(3), m.group(4)) if m else ("", base, "")
            ph = f[:-5] + ".phases.json"
            t = c["throughput"]
            if os.path.exists(ph):
                s = json.load(open(ph))["saturated"]
                sat = [json.load(open(ph)).get(x, {}) for x in ("saturated", "saturated_posted")]
            else:
                sat = [(c.get("process_memory") or {}).get(x, {}) for x in ("saturated", "saturated_posted")]
            n = t["posted"] * c["ready"]
            srv = sum(w.get("server_cpu_ms", 0) for w in sat)
            lg = sum(w.get("loadgen_cpu_ms", 0) for w in sat)
            win = sum(w.get("window_ms", 0) for w in sat) or 1
            lwin = sum(w.get("loadgen_window_ms", 0) for w in sat) or 1
            lat = c["latency"]["all_clients"]
            print(f"| {rep} | {app} | {variant} | {t['delivered_msgs_per_sec']:,.0f} | {t['posted']:,} / {t['complete']:,} | {c.get('client', {}).get('closed_midrun', '-')} | "
                  f"{srv / win:.2f} | {srv * 1000 / max(n, 1):.2f} | {lg / lwin:.2f} | {lg * 1000 / max(n, 1):.2f} | {lat.get('p50_ms')} / {lat.get('p99_ms')} |")


if __name__ == "__main__":
    main()
