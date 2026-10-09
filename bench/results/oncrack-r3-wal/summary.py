#!/usr/bin/env python3
"""Unit R3.4: posts/s, CPU per post, cores busy, p99 and slowest answer per rep and concurrency, for each tier 2/3 directory given,
with the warm-up's last windows (the stall shows there as dips) and the median of the reps.

  python3 bench/results/oncrack-r3-wal/summary.py DIR...
"""
import glob, json, os, statistics, sys

for d in sys.argv[1:]:
    rows = {}
    for f in sorted(glob.glob(os.path.join(d, "oncrack-*.json"))):
        j = json.load(open(f))
        for h in j["http"]:
            if h["route"] != "post_message":
                continue
            c = h["cost"]
            rows.setdefault(h["conc"], []).append((j["rep"], h["rps"], c["server_cpu_us_per_req"], c["server_cores_busy"],
                                                   h["latency"]["p99_ms"], h["latency"]["max_ms"], h["warmup"]))
    print(f"== {d}")
    for conc in sorted(rows):
        for rep, rps, cpu, cores, p99, mx, w in rows[conc]:
            tail = " ".join(f"{x / 1000:.1f}" for x in w["windows_rps"][-8:])
            print(f"  c={conc:<3} rep {rep}: {rps:8.0f}/s  {cpu:6.1f} us  {cores:4.2f} cores  p99 {p99:7.2f} ms  max {mx:7.1f} ms"
                  f"  warm-up {w['secs']:.0f}s {'settled' if w['settled'] else 'max'}, last windows k/s: {tail}")
        rs = [r[1] for r in rows[conc]]
        print(f"  c={conc:<3} median {statistics.median(rs):8.0f}/s [{min(rs):.0f}-{max(rs):.0f}] over {len(rs)} reps")
