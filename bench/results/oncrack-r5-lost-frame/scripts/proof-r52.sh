#!/usr/bin/env bash
# Unit R5.2's proof of the fix, inside colima, detached, from this checkout (its seed and load generator, as R5.1's hunt), the build measured mounted:
#   proof-r52.sh "NAME|bench/cable/loop arguments" ...
# Block after block, each bench/cable/loop's evidence in $OUTROOT/NAME/ (default /var/tmp/r52-proof), the onCrack build mounted from
# $ONCRACK_MOUNT (bin/publish-mounted of the fix). Same machine settings as R5.1's hunt (scripts/block.sh). Writes $OUTROOT/proof.done at
# the end; stops before a block when the VM's /var/tmp has under 4 GB free.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work
export RUST_IMAGE=${RUST_IMAGE:-campfire-rust-upstream:f9dca47}
export ONCRACK_MOUNT=${ONCRACK_MOUNT:-/var/tmp/campfire-r52}
export HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=120
OUTROOT=${OUTROOT:-/var/tmp/r52-proof}
mkdir -p "$OUTROOT"; rm -f "$OUTROOT/proof.done"
for spec in "$@"; do
  name=${spec%%|*}; args=${spec#*|}
  free=$(df -k /var/tmp | awk 'NR==2 {printf "%d", $4/1024/1024}')
  if [ "$free" -lt 4 ]; then echo "STOP: /var/tmp has ${free} GB free before $name" >> "$OUTROOT/proof.log"; break; fi
  # $OUTROOT/stop pauses before the next block (a disk guard sets it under the floor and clears it after), $OUTROOT/quit ends it.
  while [ -f "$OUTROOT/stop" ] && [ ! -f "$OUTROOT/quit" ]; do sleep 10; done
  [ -f "$OUTROOT/quit" ] && { echo "QUIT before $name" >> "$OUTROOT/proof.log"; break; }
  echo "$(date +%T) block $name start" >> "$OUTROOT/proof.log"
  out=$OUTROOT/$name; rm -rf "$out"; mkdir -p "$out"
  eval "bench/cable/loop --out \"\$out\" $args" > "$out.log" 2>&1
  echo "exit $?" >> "$out.log"
  echo "$(date +%T) block $name end" >> "$OUTROOT/proof.log"
done
touch "$OUTROOT/proof.done"
