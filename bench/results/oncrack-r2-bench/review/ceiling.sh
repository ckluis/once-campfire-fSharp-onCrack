#!/usr/bin/env bash
# R2.0 item 2: is onCrack's top rate the server's or the load generator's? onCrack, one rep, room page and sidebar at c=16 and c=64
# (bench/quick, the classic workloads on the default seed), with the server and the load generator on the CPUs given, inside colima:
#   bench/results/oncrack-r2-bench/review/ceiling.sh NAME SERVER_CPUS LOADGEN_CPUS   -> bench/results/oncrack-r2-bench/ceiling/NAME/
# APP=rust (or fsharp) measures that app instead, the same way.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
name=$1 app=${APP:-oncrack}
export SERVER_CPUS=$2 LOADGEN_CPUS=$3 WORK=/var/tmp/campfire-bench-work LOAD_WAIT_SECS=240
bench/quick --routes room_show,sidebar --concs "16 64" --apps "$app" --reps 1 --out "bench/results/oncrack-r2-bench/ceiling/$name" 2>&1 \
  | grep -E 'load before|host probe before|rps p50|done ->|ERROR|rror' | cut -c1-300 || true
python3 - "bench/results/oncrack-r2-bench/ceiling/$name/$app-1.json" "$name" "$2" "$3" "$(nproc)" "$app" <<'PY' | tee -a bench/results/oncrack-r2-bench/ceiling/ceiling.jsonl
import json, sys
f, name, s, l, n, app = sys.argv[1:]
for h in json.load(open(f))["http"]:
    c = h["cost"]
    print(json.dumps({"app": app, "config": name, "vm_cpus": int(n), "server_cpus": s, "loadgen_cpus": l, "route": h["route"], "conc": h["conc"], "rps": h["rps"],
                      "p50_ms": h["latency"]["p50_ms"], "p99_ms": h["latency"]["p99_ms"], "server_cpu_us_per_req": c["server_cpu_us_per_req"],
                      "server_cores_busy": c["server_cores_busy"], "loadgen_cpu_us_per_req": c["loadgen_cpu_us_per_req"], "loadgen_cores_busy": c["loadgen_cores_busy"],
                      "statuses": h["statuses"], "errors": h["errors"], "host_probe_after": h["host_probe_after"]["ratio"], "warmup_settled": h["warmup"]["settled"]}))
PY
