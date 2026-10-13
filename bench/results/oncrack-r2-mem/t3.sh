#!/usr/bin/env bash
# R2.5 tier 3, realistic workloads: ONE rep of one image, into DIR.  t3.sh new|old REP
# Run inside colima from the repo root. new = campfire-oncrack:app (64a714d), old = campfire-oncrack:r24 (R2.4's image, 4e12ec8).
set -euo pipefail
which=$1 rep=$2
case "$which" in
  new) export ONCRACK_IMAGE=campfire-oncrack:app ;;
  old) export ONCRACK_IMAGE=campfire-oncrack:r24 ;;
esac
bench/quick --real --reps 3 --only "oncrack:$rep" --out "bench/results/oncrack-r2-mem/t3-real-$which"
