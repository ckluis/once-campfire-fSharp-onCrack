#!/usr/bin/env bash
# R2.5 tier 2: the realistic workloads once per read cache size, on the mounted build (inside colima, from the repo root).
set -uo pipefail
for rc in "$@"; do
  echo "##### read cache $rc MB $(date +%T)"
  ONCRACK_EXTRA_ENV="CAMPFIRE_READ_CACHE_MB=$rc" bench/quick --real --reps 1 --mounted /var/tmp/campfire-r25-b4 --only oncrack:1 --out bench/results/oncrack-r2-mem/rc-$rc 2>&1 | grep -E "oncrack rep 1|rror" | cut -c1-230
done
echo "##### done"
