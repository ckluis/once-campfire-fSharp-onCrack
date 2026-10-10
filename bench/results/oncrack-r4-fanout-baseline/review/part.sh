#!/usr/bin/env bash
# One part of unit R4.1's baseline session (bench/results/oncrack-r4-fanout-baseline.md), run inside colima:
#   bench/results/oncrack-r4-fanout-baseline/review/part.sh APP REP [OUTDIR] [EXTRA ENV...]
# The cable suite alone (fresh container; 100/500/1,000/2,000 clients; 15 s saturated, window 128, the raw client), Rust (upstream
# f9dca47's image), the F# port and onCrack in one session, the order alternating between reps as bench/run schedules it.
# OUTDIR is t3 for the measured reps and sends for the one-rep pass that counts send syscalls (CABLE_SENDS=1, 8 s saturated).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
app=$1 rep=$2 out=${3:-t3}
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work
export RUST_IMAGE=${RUST_IMAGE:-campfire-rust-upstream:f9dca47}
export CABLE_CLIENTS="100 500 1000 2000"
if [ "$out" = sends ]; then export CABLE_SENDS=1 CABLE_TPUT_SECS=8; fi
w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 300 ]; do sleep 10; w=$((w+10)); done
MERGE_PART=1 HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=300 \
  bench/run --apps rust,fsharp,oncrack --reps 3 --only "$app:$rep" --out bench/results/oncrack-r4-fanout-baseline/$out 2>&1 \
  | grep -E 'load before|host probe before|cable|cold|done ->|ERROR|rror' || true
