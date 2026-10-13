#!/usr/bin/env bash
# One part of unit R2.1's tier 3 (bench/results/oncrack-r2-cable.md), run inside colima:
#   bench/results/oncrack-r2-cable/review/part.sh APP REP [SUITES] [ROUTES]
# Default: the cable suite alone (fresh container, 100/500/1,000 clients), Rust, the F# port and onCrack in one session, the
# order alternating between reps as bench/run schedules it. Each part waits for the VM's load to settle first.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
app=$1 rep=$2 suites=${3:-cable} routes=${4:-up}
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work
w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
MERGE_PART=1 HTTP_ROUTES="$routes" SUITES="$suites" LOAD_WAIT_SECS=120 \
  bench/run --apps rust,fsharp,oncrack --reps 3 --only "$app:$rep" --out bench/results/oncrack-r2-cable/t3 2>&1 \
  | grep -E 'load before|host probe before|cable|cold|done ->|ERROR|rror' || true
