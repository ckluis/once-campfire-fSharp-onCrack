#!/usr/bin/env bash
# Inside colima: cable/session.sh with guard.sh beside it (stops the session under 12 GB free on the Mac). Log cable/session.log, exit cable/session.exit.
cd "$(dirname "$0")/../../../.."
R=bench/results/oncrack-r5-final
umask 002
$R/cable/session.sh > $R/cable/session.log 2>&1 < /dev/null &
pid=$!
taskset -c 4-7 $R/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
wait $pid; rc=$?
echo $rc > $R/cable/session.exit
