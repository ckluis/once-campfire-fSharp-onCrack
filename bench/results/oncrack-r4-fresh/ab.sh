#!/usr/bin/env bash
# ab.sh OUT.jsonl PHASES LABEL=IMAGE[,ENVJSON]... : runs INSIDE colima. One review.py (round 2's hand re-run; room page / mixed / post at 16
# clients, server CPU from the cgroup) per variant in the order given, appending to OUT.jsonl, with the host's load sampled before each.
# A variant is LABEL@IMAGE@ENV-JSON; CAMPFIRE_RESPONSE_CACHE_MB=64 is added to every environment (upstream's setting).
out=$1; phases=$2; shift 2
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r2-final
for v in "$@"; do
  IFS=@ read -r label image env <<<"$v"
  env=$(python3 -c 'import json,sys; e=json.loads(sys.argv[1] or "{}"); e.setdefault("CAMPFIRE_RESPONSE_CACHE_MB","64"); print(json.dumps(e))' "$env")
  echo "== $label $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"
  python3 $R/review.py oncrack "$image" "$out" --env "$env" --tag "$label" --phases "$phases" --secs 10 --warmup 15 | python3 -c '
import sys,json
for l in sys.stdin:
    d=json.loads(l)
    if d.get("kind")=="window": print("  %-10s %-10s rps %8.0f  cpu %.1f us/req  cores %.2f p50 %.3f"%(d["tag"],d["phase"],d["rps"],d["server_cpu_us_per_req"],d["server_cores_busy"],d["p50_ms"]))
    else: print("  audit ok" if d.get("ok") else "  "+l[:300])
' || echo "FAILED $label"
  docker ps -aq --filter name=cf-review | xargs -r docker rm -f >/dev/null
done
