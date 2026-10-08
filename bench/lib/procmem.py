#!/usr/bin/env python3
"""Per-process memory of a container, by role, while a cable run goes on (bench/run).

  procmem.py sample CGROUP_DIR OUT.jsonl        # every 250 ms until killed or the cgroup goes
  procmem.py phases OUT.jsonl LOADGEN.stderr    # peak per role within each loadgen PHASE window

Roles, from each process's command line: `campfire` (the Rust app: one process, its own front
server included), `puma` (the Rails app: Puma's master and workers, which also serve Action Cable),
`thrust` (Thruster), `redis` (the reference's cable pub/sub and Resque queue), `jobs` (resque-pool
and its workers), `other`. Each sample sums, per role, Pss (proportional set size, so pages the
forked Puma workers share with their master count once) and RssAnon (anonymous resident memory,
counted in every process that maps it), both from /proc/PID/smaps_rollup, in MB. Each sample also carries the cgroup's
CPU so far (cpu.stat usage_usec), and `phases` gives each window's server CPU (`server_cpu_ms`) and, when the load
generator's PHASE lines carry its own CPU (a third number, ms), the load generator's (`loadgen_cpu_ms`).
"""
import json, os, re, sys, time


def role(cmdline):
    if "campfire" in cmdline:
        return "campfire"
    if "puma" in cmdline:
        return "puma"
    if "thrust" in cmdline:
        return "thrust"
    if "redis-server" in cmdline:
        return "redis"
    if "resque" in cmdline:
        return "jobs"
    return "other"


def rollup(pid):
    out = {}
    with open(f"/proc/{pid}/smaps_rollup") as f:
        for line in f:
            k, _, v = line.partition(":")
            if k in ("Pss", "Anonymous"):
                out[k] = int(v.split()[0]) / 1024
    return out


def sample(cgroup, path):
    with open(path, "w") as out:
        while os.path.isdir(cgroup):
            roles = {}
            try:
                pids = open(f"{cgroup}/cgroup.procs").read().split()
            except OSError:
                break
            for pid in pids:
                try:
                    cmd = open(f"/proc/{pid}/cmdline").read().replace("\0", " ")
                    m = rollup(pid)
                except OSError:
                    continue
                r = roles.setdefault(role(cmd), {"pss_mb": 0.0, "anon_mb": 0.0, "procs": 0})
                r["pss_mb"] += m.get("Pss", 0)
                r["anon_mb"] += m.get("Anonymous", 0)
                r["procs"] += 1
            cpu = None
            try:
                for line in open(f"{cgroup}/cpu.stat"):
                    if line.startswith("usage_usec "):
                        cpu = int(line.split()[1])
            except OSError:
                pass
            out.write(json.dumps({"t": int(time.time() * 1000), "roles": roles, "cpu_us": cpu}) + "\n")
            out.flush()
            time.sleep(0.25)


def phases(path, stderr_path):
    samples = [json.loads(l) for l in open(path) if l.strip()]
    found = list(re.finditer(r"PHASE (\w+) (\d+)(?: (\d+))?", open(stderr_path).read()))
    marks = [(m.group(1), int(m.group(2))) for m in found]
    lg_cpu = {m.group(1): int(m.group(3)) for m in found if m.group(3)}
    bounds = marks + [("after", 10**15)]
    result = {}
    for (name, t0), (nxt, t1) in zip(bounds, bounds[1:]):
        window = [s for s in samples if s["t"] < t0][-1:] + [s for s in samples if t0 <= s["t"] < t1]
        if not window:
            continue
        roles = {}
        for s in window:
            for r, v in s["roles"].items():
                cur = roles.setdefault(r, {"peak_pss_mb": 0.0, "peak_anon_mb": 0.0})
                cur["peak_pss_mb"] = round(max(cur["peak_pss_mb"], v["pss_mb"]), 1)
                cur["peak_anon_mb"] = round(max(cur["peak_anon_mb"], v["anon_mb"]), 1)
                cur["procs"] = v["procs"]
        total = max(sum(v["pss_mb"] for v in s["roles"].values()) for s in window)
        result[name] = {"roles": roles, "peak_total_pss_mb": round(total, 1)}
        # Server CPU over the window: the last sample at or before its end against the last one before its start.
        before = [s for s in samples if s["t"] <= t0 and s.get("cpu_us") is not None][-1:]
        upto = [s for s in samples if s["t"] <= t1 and s.get("cpu_us") is not None][-1:]
        if before and upto and t1 < 10**15:
            result[name]["server_cpu_ms"] = round((upto[0]["cpu_us"] - before[0]["cpu_us"]) / 1000, 1)
            result[name]["window_ms"] = upto[0]["t"] - before[0]["t"]
        if name in lg_cpu and nxt in lg_cpu:
            result[name]["loadgen_cpu_ms"] = lg_cpu[nxt] - lg_cpu[name]
            result[name]["loadgen_window_ms"] = t1 - t0
    return result


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "phases":
        print(json.dumps(phases(sys.argv[2], sys.argv[3])))
    else:
        sys.exit(__doc__)
