#!/usr/bin/env python3
"""Summarise `perf script` output of futex syscalls: wakes per request by thread name and managed call chain (onCrack R2.4)."""
import collections, json, re, sys

script, lg, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
rps = json.load(open(lg))["rps"]
reqs = rps * secs
events = []
cur = None
for line in open(script, errors="replace"):
    if not line.strip():
        if cur: events.append(cur)
        cur = None
        continue
    if line[0] not in " \t":
        cur = {"head": line.strip(), "frames": []}
    elif cur is not None:
        m = re.match(r"\s*[0-9a-f]+\s+(.*)", line)
        if m: cur["frames"].append(m.group(1).split(" (")[0])
if cur: events.append(cur)
print(f"{len(events)} futex calls in {secs:.0f} s, {reqs:.0f} requests: {len(events) / reqs:.2f} per request")
by_thread = collections.Counter()
by_stack = collections.Counter()
for e in events:
    comm = e["head"].split()[0] if e["head"] else "?"
    by_thread[comm] += 1
    managed = [f for f in e["frames"] if "::" in f and not f.startswith("[")]
    def short(m):
        m = re.sub(r"\[[A-Za-z.\-]*\]", "", m)          # [Assembly]
        m = re.sub(r"`\d+<[^()]*>", "", m)
        m = re.sub(r"\(.*", "", m)                           # arguments
        return m.split(" ")[-1].replace("::", ".")
    key = " <- ".join(short(m) for m in managed[:6])
    by_stack[(comm, key)] += 1
for c, n in by_thread.most_common(): print(f"  {c:20s} {n / reqs:.2f}/req")
print("top stacks:")
for (c, k), n in by_stack.most_common(14): print(f"  {n / reqs:5.2f}/req  {c}: {k}")
