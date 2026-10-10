#!/usr/bin/env bash
# One tier 2 run of unit R4.2's A/B, inside colima:  pair.sh LABEL "ENV=VAL ..." [CLIENTS]
# The cable suite of the mounted onCrack build (bin/publish-mounted) at 1,000 and 2,000 clients, raw client, window 128, one rep,
# into bench/results/oncrack-r4-fanout/pairs/LABEL, with the host's load average before and after in LABEL/load.txt.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
label=$1 extra=${2-} clients=${3:-1000 2000}
out=bench/results/oncrack-r4-fanout/pairs/$label
mkdir -p "$out"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work
export ONCRACK_MOUNT=/var/tmp/campfire-mounted ONCRACK_EXTRA_ENV="$extra" CABLE_CLIENTS="$clients"
w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
echo "before $(cat /proc/loadavg)" > "$out/load.txt"
MERGE_PART=1 HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=300 \
  bench/run --apps oncrack --reps 1 --out "$out" 2>&1 | grep -E 'load before|cable|done ->|ERROR|rror' || true
echo "after $(cat /proc/loadavg)" >> "$out/load.txt"
