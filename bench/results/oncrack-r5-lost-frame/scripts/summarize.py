#!/usr/bin/env python3
"""Prints the hunt's table from data/*/phases.jsonl and data/*/env.txt: per block its configuration, phases at the target client count,
phases in which a message did not reach every client, phases with something else flagged (a freeze, a WAL warning, a verify failure)."""
import glob, json, os, re, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
rows = []
for d in sorted(glob.glob(root + "/*/")):
    name = os.path.basename(d.rstrip("/"))
    pj = d + "phases.jsonl"
    if not os.path.exists(pj):
        continue
    ph = [json.loads(l) for l in open(pj)]
    env = open(d + "env.txt").read() if os.path.exists(d + "env.txt") else ""
    app = re.search(r"^app: (\w+), clients: (\d+), prefix: (\S+), runs: (\d+), fresh: (\d)", env, re.M)
    appenv = re.search(r"^app env: (.*)$", env, re.M)
    lg = re.search(r"^loadgen args: (.*)$", env, re.M)
    st = re.search(r"^server trace: (\d)", env, re.M)
    tgt = [p for p in ph if p["shape"] == "target"]
    lost = [p for p in tgt if any("did not reach every client" in x for x in p["problems"])]
    other = [p for p in ph if p["miss"] and p not in lost and not all("WAL" in x or "ERROR/WARN" in x for x in p["problems"])]
    benign = [p for p in ph if p["miss"] and p not in lost and p not in other]
    rows.append((name, app.group(1) if app else "?", app.group(2) if app else "?", ("fresh" if app and app.group(5) == "1" else "warm"),
                 (appenv.group(1).strip() if appenv else "").replace("CAMPFIRE_CABLE_TRACE=/trace/cable.jsonl", "server trace").strip(),
                 (lg.group(1) if lg else "").replace("(client trace 1)", "").strip(), len(tgt), len(lost), len(other), len(benign),
                 sorted(p["msgs_per_sec"] for p in tgt)[len(tgt) // 2] if tgt else None))
print("| block | app | clients | containers | app environment (beyond the image's) | load generator | target phases | phases with a message not delivered to every client | other flagged (freeze, verify, error) | flagged for a database warning only | median msg/s |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(str(x) if x != "" else "-" for x in r) + " |")
tot_t = sum(r[6] for r in rows); tot_l = sum(r[7] for r in rows)
print(f"\nTotal target phases: {tot_t}; with a message not delivered to every client: {tot_l}")
