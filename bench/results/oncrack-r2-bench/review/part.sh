#!/usr/bin/env bash
# One app-rep of R2.0's same-session baseline of the realistic workloads (bench/results/oncrack-r2-bench.md), inside colima:
#   bench/results/oncrack-r2-bench/review/part.sh APP REP [ROUTES]
# With ROUTES (comma-separated), only those workloads, merged into the rep's file (MERGE_PART=1: they replace the rep's runs of them).
# Rails runs rep 1 only; Rust, the F# port and onCrack three reps, the order alternating as bench/run's schedule has it.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work LOAD_WAIT_SECS=240
routes=(--real); [ -z "${3:-}" ] || { routes=(--routes "$3"); export MERGE_PART=1; }
bench/quick "${routes[@]}" --apps reference,rust,fsharp,oncrack --reps 3 --only "$1:$2" --out bench/results/oncrack-r2-bench 2>&1 \
  | grep -E 'load before|host probe before|realistic workloads prepared|rps p50|done ->|ERROR|rror' | cut -c1-400 || true
