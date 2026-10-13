#!/usr/bin/env bash
# wait.sh NAME: one chunk (at most 540 s) of waiting for a detached session; prints state.
n=$1; R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final
$R/scripts/hostload-wait.sh $n $R/logs/session-$n.exit 540
if [ -f $R/logs/session-$n.exit ]; then echo "FINISHED exit $(cat $R/logs/session-$n.exit)"; else echo "RUNNING: $(colima ssh -- tail -1 /mnt/cfv/out/$n.log 2>/dev/null)"; fi
date +%T
