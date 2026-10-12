#!/usr/bin/env bash
# Unit R5.2: what the fix costs, inside colima, detached (from this checkout; the fix measured as a mounted build):  cost-r52.sh ROUNDS [CLIENTS]
# Rotates three arms, one bench/run cable rep each (raw client, window 128), ROUNDS times, at CLIENTS (1000):
#   fix-on   the fix's build (ONCRACK_MOUNT, default /var/tmp/campfire-r52), gathered writes on (the default)
#   fix-off  the same build with CAMPFIRE_CABLE_GATHER=off (every batch copied into a pooled buffer: no gathered write at all)
#   r4       campfire-oncrack:app's own build (round 4 as shipped: the gathered write whose payloads were not all pinned), for reference only
# The arm order turns by one each round, so no arm always follows another. Each run in $OUT/ROUND-ARM (bench/run's --out), with the VM's
# load before and after in load.txt; table.py of oncrack-r4-fanout prints them. Writes $OUT/cost.done at the end.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
rounds=${1:-4} clients=${2:-1000}
OUT=${OUT:-/var/tmp/r52-cost}
FIX=${FIX:-/var/tmp/campfire-r52}
mkdir -p "$OUT"; rm -f "$OUT/cost.done"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work CABLE_CLIENTS="$clients"
arms=(fix-on fix-off r4)
for r in $(seq 1 "$rounds"); do
  for k in 0 1 2; do
    arm=${arms[$(( (k + r - 1) % 3 ))]}
    [ -f "$OUT/stop" ] && break 2
    case $arm in
      fix-on) mount=$FIX env="" ;;
      fix-off) mount=$FIX env="CAMPFIRE_CABLE_GATHER=off" ;;
      r4) mount="" env="" ;;
    esac
    d=$OUT/r$r-$arm; mkdir -p "$d"
    w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
    echo "before $(cat /proc/loadavg)" > "$d/load.txt"
    echo "$(date +%T) round $r $arm start" >> "$OUT/cost.log"
    ONCRACK_MOUNT="$mount" ONCRACK_EXTRA_ENV="$env" MERGE_PART=1 HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=300 \
      bench/run --apps oncrack --reps 1 --out "$d" > "$d/run.log" 2>&1
    echo "after $(cat /proc/loadavg)" >> "$d/load.txt"
    echo "$(date +%T) round $r $arm end ($?)" >> "$OUT/cost.log"
  done
done
touch "$OUT/cost.done"
