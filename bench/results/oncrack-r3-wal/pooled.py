#!/usr/bin/env python3
"""Unit R3.4: the tier 3 runs (t3-VARIANT-REP) pooled by variant: posts/s per rep, median, CPU per post and slowest answer.

  python3 bench/results/oncrack-r3-wal/pooled.py
"""
import glob, json, os, re, statistics
here = os.path.dirname(os.path.abspath(__file__))
rows = {}
for d in sorted(glob.glob(os.path.join(here, "t3-*-[0-9]"))):
    variant, rep = re.match(r"t3-(.+)-(\d+)$", os.path.basename(d)).groups()
    for f in glob.glob(os.path.join(d, "oncrack-*.json")):
        for h in json.load(open(f))["http"]:
            if h["route"] == "post_message":
                rows.setdefault((variant, h["conc"]), []).append((int(rep), h["rps"], h["cost"]["server_cpu_us_per_req"], h["latency"]["max_ms"]))
names = {"r22": "R2.2 restart (default)", "defer": "deferred, 40,000 ceiling", "ceiling": "deferred, 150,000 ceiling"}
for (variant, conc) in sorted(rows, key=lambda k: (k[1], list(names).index(k[0]))):
    rs = sorted(rows[(variant, conc)])
    print(f"| {names[variant]} | {conc} | {', '.join(f'{r[1]:,.0f}' for r in rs)} | **{statistics.median(r[1] for r in rs):,.0f}** | "
          f"{statistics.median(r[2] for r in rs):.0f} | {', '.join(f'{r[3]:,.0f}' for r in rs)} |")
