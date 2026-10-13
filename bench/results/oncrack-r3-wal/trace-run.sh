#!/usr/bin/env bash
# Unit R3.4: one tier 2 rep of post_message at the given concurrencies with the WAL trace on, and the VM's dirty and
# writeback memory sampled every 250 ms beside it (the trace's clock and the sampler's are the VM's).
#
#   colima ssh -- bash -c "cd REPO && bench/results/oncrack-r3-wal/trace-run.sh NAME 'CONCS' 'EXTRA ENV' [WARMUP]"
#
# Writes bench/results/oncrack-r3-wal/NAME/ (the rep's results, wal.log, vm.log).
set -euo pipefail
name=$1 concs=$2 extra=$3 warm=${4:-60}
out=bench/results/oncrack-r3-wal/$name
mkdir -p "$out"
trace=/var/tmp/r34-trace-$name
rm -rf "$trace"
( while :; do
    printf '%s %s %s\n' "$(date -u +%H:%M:%S.%3N)" "$(awk '/^Dirty:/{d=$2}/^Writeback:/{w=$2}END{print d, w}' /proc/meminfo)" \
      "$(awk '$3=="vda"{print $8, $10, $11}' /proc/diskstats)"
    sleep 0.25
  done > "$out/vm.log" ) &
sampler=$!
trap 'kill $sampler 2>/dev/null || true' EXIT
TRACE_DIR=$trace ONCRACK_EXTRA_ENV="CAMPFIRE_WAL_TRACE=/trace/wal.log $extra" \
  bench/quick --mounted /var/tmp/campfire-mounted --routes post_message --concs "$concs" --reps 1 \
  --warmup "$warm" --warmup-max "$warm" --secs 8 --out "$out" >"$out/quick.txt" 2>&1 || { tail -20 "$out/quick.txt"; exit 1; }
cp "$trace/wal.log" "$out/wal.log"
rm -rf "$trace"
tail -3 "$out/quick.txt"
