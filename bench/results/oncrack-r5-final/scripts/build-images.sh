#!/usr/bin/env bash
# Inside colima, detached: step 2 of PLAN.md. onCrack image from the clean measured worktree at HEAD, then the reference and parity images from the main checkout.
M=/Users/clank/Desktop/projects/oncrack-measured; R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack; L=$R/bench/results/oncrack-r5-final/logs
rm -f $L/build.exit
export PARITY_NET_DIR=/tmp/parity-net; mkdir -p /tmp/parity-net
( cd $M && CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build ) > $L/build-oncrack.log 2>&1; rc1=$?
( cd $R && parity/bin/reference build ) > $L/build-reference.log 2>&1; rc2=$?
echo "oncrack=$rc1 reference=$rc2" > $L/build.exit
