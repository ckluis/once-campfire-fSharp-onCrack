#!/usr/bin/env bash
# (First attempt, kept in aborted-session-1/: all seven apps in one run stopped at the F# port's contract preparation, 'search: differs from seed SQL',
# the port's pre-R3.3 search order; the harness prepares contracts for the overload profile only. So the port runs the cable profiles alone, after.)
# The R4 final PR #6 reliability session, run INSIDE colima, detached (exit status to reliability/session.exit): 3 rounds of overload and cable
# (cable_heavy follows cable) for Rails 0aa339d, Rust f9dca47, C cd0cbe4, the F# port, onCrack HEAD (fresh authorization), oncrack-cached and
# onCrack before R4.5 (oncrack-prev: the image built from 21791e2). Output: reliability/session/. guard.sh stops it under 12 GB free on the Mac.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r4-final/reliability
cd $R
rm -f $D/session.exit
export CFV=/mnt/cfv/rel
export RUST_IMAGE=campfire-rust-upstream:f9dca47 C_IMAGE=campfire-c-upstream:cd0cbe4 RAILS_IMAGE=campfire-rails-upstream:0aa339d FSHARP_IMAGE=campfire-fsharp:app
export RAILS_BENCH_ENV='{"WEB_CONCURRENCY":"4","RAILS_MAX_THREADS":"1","RAILS_MIN_THREADS":"1"}'
export ONCRACK_IMAGE=campfire-oncrack:app ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export ONCRACK_CACHED_IMAGE=campfire-oncrack:app ONCRACK_CACHED_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}'
export ONCRACK_PREV_IMAGE=campfire-oncrack:r45-before ONCRACK_PREV_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export TMPDIR=/mnt/cfv
# Second attempt (the first, aborted-session-2/, stopped at oncrack-prev: its source worktree's copied submodule had a dangling .git file). The port's
# cable run, session-fsharp/, finished in the first attempt and is kept: PORT_DONE=1 skips it.
rm -rf $D/session
[ -n "$PORT_DONE" ] || rm -rf $D/session-fsharp
# bench/reliability/run was written for the Mac and calls `colima ssh -- CMD`; inside the VM a shim runs CMD directly.
mkdir -p /var/tmp/shim && printf '#!/bin/bash\nshift 2\nexec "$@"\n' > /var/tmp/shim/colima && chmod +x /var/tmp/shim/colima
export PATH=/var/tmp/shim:$PATH
( bench/reliability/run $D/session --apps rails,rust,c,oncrack,oncrack-cached,oncrack-prev --profiles overload,cable --rounds 3
  [ -n "$PORT_DONE" ] || bench/reliability/run $D/session-fsharp --apps fsharp --profiles cable --rounds 3 ) &
pid=$!
mkdir -p /mnt/cfv/out
taskset -c 4-7 $R/bench/results/oncrack-r4-final/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
wait $pid; rc=$?
echo $rc > $D/session.exit
