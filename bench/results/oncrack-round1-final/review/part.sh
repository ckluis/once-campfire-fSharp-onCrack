#!/usr/bin/env bash
# One part of the four-way re-baseline (bench/results/oncrack-round1-final.md), run inside colima:
#   bench/results/oncrack-round1-final/review/part.sh APP REP "ROUTES" [SUITES]
# Rails and Rust run two or three routes a part; the F# port and onCrack one heavy route a part.
# Cable and upload run in each rep's last part.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
app=$1 rep=$2 routes=$3 suites=${4:-http}
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work PARITY_NET_DIR=/tmp/parity-net
mkdir -p /tmp/parity-net
MERGE_PART=1 HTTP_ROUTES="$routes" SUITES="$suites" LOAD_WAIT_SECS=240 \
  bench/run --apps reference,rust,fsharp,oncrack --reps 3 --only "$app:$rep" --out bench/results/oncrack-round1-final 2>&1 \
  | grep -E 'load before|host probe before|rps p50|cable|upload|cold|idle|done ->|rows|ERROR|rror' || true
