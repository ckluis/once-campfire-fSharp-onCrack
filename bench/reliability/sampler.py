#!/usr/bin/env python3
"""Unit R4.5: the memory of whichever container the reliability harness is running, twice a second, until killed (run as root in the VM).

  sampler.py OUT.jsonl

One line per sample: epoch seconds, the sum of Pss and of anonymous memory over the container's processes (/proc/PID/smaps_rollup,
as bench/lib/procmem.py), their count, and the cgroup's memory.current. bench/reliability/summarize gives each profile the peak
between the previous profile's last output line and its own.
"""
import glob, json, os, sys, time


def rollup(pid):
    pss = anon = 0.0
    with open(f"/proc/{pid}/smaps_rollup") as f:
        for line in f:
            k, _, v = line.partition(":")
            if k == "Pss":
                pss = int(v.split()[0]) / 1024
            elif k == "Anonymous":
                anon = int(v.split()[0]) / 1024
    return pss, anon


def main():
    out = open(sys.argv[1], "a", buffering=1)
    open(sys.argv[1].rsplit("/", 1)[0] + "/sampler.pid", "w").write(str(os.getpid()))
    while True:
        started = time.time()
        for cg in glob.glob("/sys/fs/cgroup/docker/*/") + glob.glob("/sys/fs/cgroup/system.slice/docker-*.scope/"):
            try:
                pids = open(cg + "cgroup.procs").read().split()
                current = int(open(cg + "memory.current").read()) / 1048576
            except OSError:
                continue
            pss = anon = 0.0
            n = 0
            for pid in pids:
                try:
                    p, a = rollup(pid)
                except OSError:
                    continue
                pss += p
                anon += a
                n += 1
            if n:
                out.write(json.dumps({"t": round(started, 2), "id": os.path.basename(cg.rstrip("/"))[:12], "pss_mb": round(pss, 1), "anon_mb": round(anon, 1),
                                      "procs": n, "cgroup_mb": round(current, 1)}) + "\n")
        time.sleep(max(0.0, 0.5 - (time.time() - started)))


main()
