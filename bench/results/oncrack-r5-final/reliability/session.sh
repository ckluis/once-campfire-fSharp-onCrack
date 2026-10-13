#!/usr/bin/env bash
# session.sh PART: runs INSIDE colima (detached by start.sh). The R5 final PR #6 reliability session, as round 4's reliability/session.sh with the
# three setup fixes in scripts/setup-reliability.sh's output (the harness copy with .git, fixtures/default and the static aarch64 loadgen) and the fourth
# found here: the workspace needs once-campfire-oncrack-prev (a symlink to the R4.5 "before" worktree, 21791e2).
#   main    rails,rust,c,oncrack,oncrack-cached,oncrack-prev x overload,cable x 3 rounds   -> main/
#   fsharp  the F# port, cable profiles only, 3 rounds                                      -> fsharp/
#   fscheck the F# port on overload, 1 round (does its search order still fail the contract?) -> fsharp-overload-check/
# Exit status to reliability/PART.exit. guard.sh stops it under 12 GB free on the Mac.
part=$1
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r5-final/reliability
cd $R
rm -f $D/$part.exit
export CFV=/mnt/cfv/rel
export RUST_IMAGE=campfire-rust-upstream:f9dca47 C_IMAGE=campfire-c-upstream:cd0cbe4 RAILS_IMAGE=campfire-rails-upstream:0aa339d FSHARP_IMAGE=campfire-fsharp:app
export RAILS_BENCH_ENV='{"WEB_CONCURRENCY":"4","RAILS_MAX_THREADS":"1","RAILS_MIN_THREADS":"1"}'
export ONCRACK_IMAGE=campfire-oncrack:app ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export ONCRACK_CACHED_IMAGE=campfire-oncrack:app ONCRACK_CACHED_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}'
export ONCRACK_PREV_IMAGE=campfire-oncrack:r45-before ONCRACK_PREV_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export TMPDIR=/mnt/cfv
umask 002
mkdir -p /var/tmp/shim && printf '#!/bin/bash\nshift 2\nexec "$@"\n' > /var/tmp/shim/colima && chmod +x /var/tmp/shim/colima
export PATH=/var/tmp/shim:$PATH
case $part in
  main) dir=main; args="--apps rails,rust,c,oncrack,oncrack-cached,oncrack-prev --profiles overload,cable --rounds 3" ;;
  fsharp) dir=fsharp; args="--apps fsharp --profiles cable --rounds 3" ;;
  fscheck) dir=fsharp-overload-check; args="--apps fsharp --profiles overload --rounds 1" ;;
  *) echo "unknown part $part" >&2; exit 2 ;;
esac
rm -rf $D/$dir
mkdir -p /mnt/cfv/out
( bench/reliability/run $D/$dir $args ) > /mnt/cfv/out/reliability-$part.log 2>&1 &
pid=$!
taskset -c 4-7 $R/bench/results/oncrack-r5-final/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
wait $pid; rc=$?
# guard.sh kills this subshell only, and the harness (ruby bin/reliability) outlives it (met in main's first run, 2026-10-13 04:09): stop it too.
if [ $rc -ge 128 ]; then pkill -f "[r]uby bin/reliability"; sleep 2; docker ps -q --filter name=cf-native-reliability | xargs -r docker rm -f > /dev/null; fi
echo $rc > $D/$part.exit
