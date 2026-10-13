#!/usr/bin/env bash
# Copies the hunt's evidence from the VM's /var/tmp/r5-lost-frame/ into bench/results/oncrack-r5-lost-frame/data/, inside colima:
# per block its env.txt, loop log, phases.jsonl and a small record of every phase that was flagged (verdict, app errors, freeze, stderr);
# the full evidence (client dumps, the server's trace of the phase, the app's log) only for a phase in which a message did not reach every
# client or a client was cut, compressed. Traces of other flagged phases (a freeze, a WAL warning) stay in the VM.
set -euo pipefail
SRC=/var/tmp/r5-lost-frame
DST=$(cd "$(dirname "$0")/.." && pwd)/data
mkdir -p "$DST"
for b in "$SRC"/*/; do
  b=${b%/}; name=$(basename "$b")
  [ -f "$b/phases.jsonl" ] || continue
  mkdir -p "$DST/$name"
  cp "$b/env.txt" "$b/phases.jsonl" "$DST/$name/" 2>/dev/null || true
  [ -f "$b.log" ] && cp "$b.log" "$DST/$name/block.log"
  [ -f "$b/misses.txt" ] && cp "$b/misses.txt" "$DST/$name/"
  python3 - "$b" "$DST/$name" <<'PY'
import json, os, shutil, subprocess, sys, tarfile
src, dst = sys.argv[1:]
for line in open(src + "/phases.jsonl"):
    v = json.loads(line)
    if not v["miss"]:
        continue
    d = src + "/" + v["dir"]
    out = dst + "/flagged/" + v["dir"]
    os.makedirs(out, exist_ok=True)
    for f in ("verdict.json", "app-errors.log", "freeze.txt", "result.json"):
        if os.path.exists(d + "/" + f):
            shutil.copy(d + "/" + f, out)
    if os.path.exists(d + "/stderr"):
        shutil.copy(d + "/stderr", out + "/stderr.txt")
    real = [p for p in v["problems"] if "did not reach every client" in p or "window stalls" in p or "clients closed" in p or "failed to connect" in p or "no usable result" in p]
    if real or os.environ.get("KEEP_ALL_FLAGGED"):
        subprocess.run(["tar", "czf", out + "/evidence.tar.gz", "-C", d, "."], check=True)
PY
done
du -sh "$DST"
