#!/usr/bin/env python3
"""Per-thread CPU of a process, by thread name (onCrack R2.4: where a request's CPU is spent when the server is nearly idle).

  threadcpu.py snap PID FILE          save every thread's utime+stime (clock ticks) and switches
  threadcpu.py diff PID FILE REQUESTS print the threads' CPU per request since the snapshot, grouped by name
"""
import json, os, re, sys

TICK = os.sysconf("SC_CLK_TCK")


def read(pid):
    out = {}
    base = f"/proc/{pid}/task"
    for tid in os.listdir(base):
        try:
            name = open(f"{base}/{tid}/comm").read().strip()
            stat = open(f"{base}/{tid}/stat").read()
            status = open(f"{base}/{tid}/status").read()
        except OSError:
            continue
        f = stat[stat.rindex(")") + 2:].split()
        ticks = int(f[11]) + int(f[12])
        vol = int(re.search(r"voluntary_ctxt_switches:\s+(\d+)", status).group(1))
        nonvol = int(re.search(r"nonvoluntary_ctxt_switches:\s+(\d+)", status).group(1))
        out[tid] = {"name": name, "ticks": ticks, "vol": vol, "nonvol": nonvol}
    return out


mode, pid, path = sys.argv[1:4]
if mode == "snap":
    json.dump(read(pid), open(path, "w"))
else:
    before = json.load(open(path))
    after = read(pid)
    n = max(int(sys.argv[4]), 1)
    groups = {}
    for tid, a in after.items():
        b = before.get(tid, {"ticks": 0, "vol": 0, "nonvol": 0})
        g = groups.setdefault(a["name"], [0, 0, 0, 0])
        g[0] += a["ticks"] - b["ticks"]
        g[1] += a["vol"] - b["vol"]
        g[2] += a["nonvol"] - b["nonvol"]
        g[3] += 1
    total = sum(g[0] for g in groups.values())
    print("    thread CPU per request (clock-tick resolution), switches per request:")
    for name, g in sorted(groups.items(), key=lambda x: -x[1][0]):
        if g[0] == 0 and g[1] < n * 0.01:
            continue
        print("      %-18s x%-3d %7.1f us  vol %.2f nonvol %.2f /req" % (name, g[3], g[0] * 1e6 / TICK / n, g[1] / n, g[2] / n))
    print("      %-18s      %7.1f us" % ("total", total * 1e6 / TICK / n))
