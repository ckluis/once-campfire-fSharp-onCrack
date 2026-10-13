#!/usr/bin/env bash
# A control of R2.0 (bench/results/oncrack-r2-bench.md): onCrack, one rep, some realistic workloads, with extra environment, inside colima:
#   bench/results/oncrack-r2-bench/review/control.sh NAME ROUTES [K=V ...]      -> bench/results/oncrack-r2-bench/controls/NAME/
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
name=$1 routes=$2; shift 2
export SERVER_CPUS=${SERVER_CPUS:-0-3} LOADGEN_CPUS=${LOADGEN_CPUS:-4-7} WORK=/var/tmp/campfire-bench-work LOAD_WAIT_SECS=240 ONCRACK_EXTRA_ENV="$*"
bench/quick --routes "$routes" --apps oncrack --reps 1 --out "bench/results/oncrack-r2-bench/controls/$name" 2>&1 \
  | grep -E 'load before|host probe before|rps p50|done ->|ERROR|rror' | cut -c1-400 || true
