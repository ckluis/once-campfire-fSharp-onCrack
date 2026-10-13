#!/usr/bin/env bash
# Unit R5.3: bench/cable/perf (KEEP_SCRIPT=1) for a list of "NAME|CLIENTS|ENV" runs, inside colima, detached:
#   OUT=DIR MOUNT=/var/tmp/campfire-r52c perf3.sh "default-1000|1000|" "stream-1000|1000|CAMPFIRE_CABLE_ORDER=stream" ...
# Each run in $OUT/NAME; $OUT/perf.done when finished.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
OUT=${OUT:?OUT}; MOUNT=${MOUNT:?MOUNT}
mkdir -p "$OUT"; rm -f "$OUT/perf.done"
for spec in "$@"; do
  name=${spec%%|*}; rest=${spec#*|}; clients=${rest%%|*}; env=${rest#*|}
  w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
  echo "$(date +%T) $name start (load $(cat /proc/loadavg))" >> "$OUT/perf.log"
  ONCRACK_MOUNT="$MOUNT" ONCRACK_EXTRA_ENV="$env" KEEP_SCRIPT=1 bench/cable/perf --app oncrack --clients "$clients" --secs 8 --out "$OUT/$name" > "$OUT/$name.log" 2>&1
  echo "$(date +%T) $name end ($?)" >> "$OUT/perf.log"
done
touch "$OUT/perf.done"
