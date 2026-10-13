#!/usr/bin/env bash
# ab-quick.sh OUTDIR ROUTES ORDER...: runs INSIDE colima. CPU per request (bench/quick cpu, a mounted build, the cgroup's cpu.stat) of the same build
# with CAMPFIRE_FRESH_HOLD on and off, one fresh container per run, in the order given (e.g. hold nohold nohold hold); the host's load is
# printed before each. ORDER words: hold, nohold, cached (CAMPFIRE_FRESH_AUTH=0).
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
out=$1 routes=$2; shift 2
n=0
for v in "$@"; do
  n=$((n+1))
  case $v in
    hold) env_="CAMPFIRE_FRESH_HOLD=1" ;;
    nohold) env_="CAMPFIRE_FRESH_HOLD=0" ;;
    cached) env_="CAMPFIRE_FRESH_AUTH=0" ;;
    *) echo "unknown variant $v" >&2; exit 2 ;;
  esac
  echo "== run $n $v $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"
  ONCRACK_EXTRA_ENV="$env_" "$ROOT/bench/quick" cpu --mounted "${MOUNTED:-/var/tmp/campfire-mounted}" --routes "$routes" --secs "${SECS:-6}" --warmup "${WARMUP:-20}" --warmup-max "${WARMUP:-20}" --out "$out/$n-$v" > "$out-$n-$v.log" 2>&1 || { echo "FAILED $v"; tail -5 "$out-$n-$v.log"; }
  grep -E "room_show|messages_page" "$out/$n-$v/report.md" 2>/dev/null | head -6 || true
done
