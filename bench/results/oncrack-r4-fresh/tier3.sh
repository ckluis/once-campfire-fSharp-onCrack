#!/usr/bin/env bash
# tier3.sh OUTDIR ORDER...: runs INSIDE colima. Tier 3 (bench/quick's full-length measure: 30 s warm-up per route and concurrency, 8 s windows,
# c=1 and c=16, the image, a fresh container and seed copy) of the room page and the messages page with CAMPFIRE_FRESH_HOLD on and off, one rep per
# ORDER word (hold, nohold or cached), in the order given so that drift cancels. The host's load is printed before each.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
out=$1; shift
n=0
for v in "$@"; do
  n=$((n+1))
  case $v in hold) e="CAMPFIRE_FRESH_HOLD=1" ;; nohold) e="CAMPFIRE_FRESH_HOLD=0" ;; cached) e="CAMPFIRE_FRESH_AUTH=0" ;; esac
  echo "== $n $v $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"
  ONCRACK_MOUNT="" ONCRACK_EXTRA_ENV="$e" "$ROOT/bench/quick" --reps 1 --routes room_show,messages_page --out "$out/$n-$v" > "$out-$n-$v.log" 2>&1 || echo "FAILED $v"
  grep -E "rep 1:" "$out-$n-$v.log" | sed -E 's/.*oncrack rep 1: ([a-z_]+ c=[0-9]+) ([0-9.]+) rps; server ([0-9.]+) us\/req.*/   \1 \2 rps \3 us/'
done
echo TIER3 DONE
