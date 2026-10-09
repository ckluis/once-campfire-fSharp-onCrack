#!/usr/bin/env python3
"""Memory outside the caches' budgets: a signed-in user requests M distinct long URLs of a cached page, each twice (stored, then offered
to the fast path), from 8 connections. Reports the container's anon memory before and after (cgroup memory.stat)."""
import json, subprocess, sys, threading, time
from lib import *
app, port = sys.argv[1], int(sys.argv[2]); env = [e for e in sys.argv[3].split(",") if e]; M = int(sys.argv[4]); PAD = int(sys.argv[5])
def anon(name):
    cid = subprocess.run(["docker", "inspect", "-f", "{{.Id}}", f"vfy-{name}"], capture_output=True, text=True).stdout.strip()
    for path in (f"/sys/fs/cgroup/system.slice/docker-{cid}.scope/memory.stat", f"/sys/fs/cgroup/docker/{cid}/memory.stat"):
        try:
            for l in open(path):
                if l.startswith("anon "): return int(l.split()[1]) // (1024 * 1024)
        except FileNotFoundError: pass
    return None
with App("mf", app, port, env=env) as a:
    c = Client(port); c.sign_in(EMAILS[DAVID])
    for _ in range(5): c.get(f"/rooms/{ALL_TALK}")
    time.sleep(1); m0 = anon("mf")
    pad = "x" * PAD; errs = []
    def run(w):
        cl = Client(port); cl.cookies = dict(c.cookies)
        for k in range(w, M, 8):
            for _ in range(2):
                r = cl.get(f"/rooms/{ALL_TALK}?i={k}&pad={pad}")
                if r.status != 200: errs.append(r.status)
    ts = [threading.Thread(target=run, args=(w,)) for w in range(8)]
    t0 = time.time()
    for t in ts: t.start()
    for t in ts: t.join()
    time.sleep(2); m1 = anon("mf")
    # Still answering, and the page itself still served from cache.
    r = c.get(f"/rooms/{ALL_TALK}")
    print(json.dumps({"group": "memory", "app": app, "env": env, "urls": M, "pad": PAD, "requests": 2 * M, "secs": round(time.time() - t0, 1),
                      "anon_mb_before": m0, "anon_mb_after": m1, "non200": len(errs), "statuses": sorted(set(errs))[:5], "after": r.status}), flush=True)
