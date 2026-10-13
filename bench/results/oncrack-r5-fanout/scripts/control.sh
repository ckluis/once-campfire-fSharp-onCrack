#!/usr/bin/env bash
# Unit R5.3: Rust f9dca47 beside onCrack in one session, bench/run's cable suite (raw client, window 128) at 1,000 and 2,000 clients, rounds alternating
# which goes first, inside colima, detached:  OUT=DIR control.sh ROUNDS   ($OUT/control.done at the end; rN-rust, rN-oncrack under $OUT)
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.."
OUT=${OUT:?}; rounds=${1:-3}
mkdir -p "$OUT"; rm -f "$OUT/control.done"
while [ -n "${AFTER:-}" ] && [ ! -f "$AFTER" ]; do sleep 5; done
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work CABLE_CLIENTS="1000 2000" RUST_IMAGE=${RUST_IMAGE:-campfire-rust-upstream:f9dca47}
for r in $(seq 1 "$rounds"); do
  if [ $((r % 2)) -eq 1 ]; then order="rust oncrack"; else order="oncrack rust"; fi
  for app in $order; do
    d=$OUT/r$r-$app; mkdir -p "$d"
    echo "$(date +%T) round $r $app start" >> "$OUT/control.log"
    echo "before $(cat /proc/loadavg)" > "$d/load.txt"
    if [ "$app" = oncrack ]; then export ONCRACK_MOUNT=/var/tmp/campfire-r53; else unset ONCRACK_MOUNT; fi
    MERGE_PART=1 HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=120 bench/run --apps "$app" --reps 1 --out "$d" > "$d/run.log" 2>&1
    echo "after $(cat /proc/loadavg)" >> "$d/load.txt"
    echo "$(date +%T) round $r $app end ($?)" >> "$OUT/control.log"
  done
done
touch "$OUT/control.done"
