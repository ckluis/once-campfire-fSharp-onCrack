#!/usr/bin/env bash
# run-fg.sh NAME [bin/benchmark args...]: runs INSIDE colima, in the foreground: one harness session, output in /mnt/cfv/out/NAME (log NAME.log),
# with guard.sh beside it on the load generator's CPUs (stops the session under 12 GB free on the Mac, trims after it). Returns the session's status.
name=$1; shift
S=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/scripts
source "$S/env-r5f.sh"
umask 002
$BENCH --output /mnt/cfv/out/$name "$@" > /mnt/cfv/out/$name.log 2>&1 < /dev/null &
pid=$!
echo $pid > /mnt/cfv/out/$name.pid
taskset -c 4-7 "$S/guard.sh" $pid > /dev/null 2>&1 < /dev/null &
g=$!
wait $pid; rc=$?
wait $g
echo "session $name exit $rc"
exit $rc
