#!/usr/bin/env python3
"""Every cable phase of a session directory: posted vs delivered (throughput and paced), subscribed, closed mid-run, odd frames, markers past cap,
receipts without post time, window stalls, failed connects. Prints a table and, at the end, 'FLAGGED' lines for any phase where a message did not reach
every client or a counter is nonzero. Usage: python3 cable/phases.py SESSION_DIR"""
import glob, json, os, sys
d = sys.argv[1]
flag = []
print("| file | clients | subscribed | saturated posted | saturated complete | paced messages | paced complete | closed mid-run | odd frames | markers past cap | no post time | window stalls | failed |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for sub in ("t3", "sends"):
    for f in sorted(glob.glob(os.path.join(d, sub, "*.json"))):
        j = json.load(open(f))
        for c in j["cable"]:
            t, l, cl = c["throughput"], c["latency"], c.get("client", {})
            row = (sub + "/" + os.path.basename(f)[:-5], c["clients"], f'{c["ready"]}', t["posted"], t["complete"], l["messages"], l["complete"],
                   cl.get("closed_midrun", 0), cl.get("odd_frames", 0), cl.get("markers_past_cap", 0), cl.get("receipts_without_post_time", 0), t.get("window_stalls", 0), c["failed"])
            print("| " + " | ".join(str(x) for x in row) + " |")
            if t["posted"] != t["complete"] or l["messages"] != l["complete"] or c["ready"] != c["clients"] or any(row[7:11]) or row[12]:
                flag.append(row)
for r in flag:
    print("FLAGGED", r)
print("phases flagged:", len(flag))
