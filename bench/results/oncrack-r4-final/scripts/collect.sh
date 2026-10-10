#!/usr/bin/env bash
# collect.sh NAME: copies a finished session's harness output (and log, guard log) out of the VM's tmpfs into this directory.
n=$1; R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-final
colima ssh -- bash -c "rm -rf $R/$n; cp -r /mnt/cfv/out/$n $R/$n; cp /mnt/cfv/out/$n.log $R/$n/console.log; cp /mnt/cfv/out/guard-*.log $R/$n/ 2>/dev/null; rm -f /mnt/cfv/out/guard-*.log"
