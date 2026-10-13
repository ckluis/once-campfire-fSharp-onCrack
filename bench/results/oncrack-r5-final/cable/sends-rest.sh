#!/usr/bin/env bash
# The rest of session 2's sends pass, inside colima, detached (the disk guard stopped session.sh at 02:34 during "sends fsharp", Mac free 11.9 GiB,
# another project's go test run had grown its build cache; the orphaned fsharp part was killed and its partial files removed): sends fsharp, sends oncrack.
# Exit status in cable/sends-rest.exit; guard.sh beside it as in run-guarded.sh.
cd "$(dirname "$0")/../../../.."
R=bench/results/oncrack-r5-final
rm -f $R/cable/sends-rest.exit
( for app in fsharp oncrack; do echo "== sends $app $(date +%T)"; $R/cable/part.sh $app 1 sends; done; echo SENDS DONE ) > $R/cable/sends-rest.log 2>&1 &
pid=$!
taskset -c 4-7 $R/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
wait $pid; echo $? > $R/cable/sends-rest.exit
