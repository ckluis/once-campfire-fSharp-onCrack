#!/usr/bin/env bash
# Unit R5.2: one bench/run cable rep per arm (raw client, window 128), arms rotated, inside colima, detached:
#   OUT=DIR arms-r52.sh ROUNDS CLIENTS "NAME|MOUNT|ENV" ...
# MOUNT is a bin/publish-mounted directory ("" for the image's own build), ENV the app's extra environment. The order turns by one each
# round. Each run in $OUT/rROUND-NAME with the VM's load before and after; ../../oncrack-r4-fanout/table.py prints them. $OUT/stop stops
# it between runs; $OUT/arms.done is written at the end.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
rounds=$1 clients=$2; shift 2
arms=("$@"); n=${#arms[@]}
OUT=${OUT:?OUT=DIR}
mkdir -p "$OUT"; rm -f "$OUT/arms.done"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work CABLE_CLIENTS="$clients"
for r in $(seq 1 "$rounds"); do
  for k in $(seq 0 $((n - 1))); do
    spec=${arms[$(( (k + r - 1) % n ))]}
    name=${spec%%|*}; rest=${spec#*|}; mount=${rest%%|*}; env=${rest#*|}
    while [ -f "$OUT/stop" ]; do sleep 10; [ -f "$OUT/quit" ] && break 3; done
    d=$OUT/r$r-$name; mkdir -p "$d"
    w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
    echo "before $(cat /proc/loadavg)" > "$d/load.txt"
    echo "$(date +%T) round $r $name start" >> "$OUT/arms.log"
    ONCRACK_MOUNT="$mount" ONCRACK_EXTRA_ENV="$env" MERGE_PART=1 HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=300 \
      bench/run --apps oncrack --reps 1 --out "$d" > "$d/run.log" 2>&1
    s=$?
    echo "after $(cat /proc/loadavg)" >> "$d/load.txt"
    echo "$(date +%T) round $r $name end ($s)" >> "$OUT/arms.log"
  done
done
touch "$OUT/arms.done"
