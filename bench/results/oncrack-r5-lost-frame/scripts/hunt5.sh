#!/usr/bin/env bash
# Fifth part. Round 5's first reproduction was a frame whose bytes on the wire were other memory (zeros, pointers, a 16-byte header
# overwritten) and it came 12-13 s into three phases of a fresh container, when the first big garbage collections happen. So: make
# collections far more frequent (DOTNET_GCgen0MaxBudget, hex bytes) and see whether the loss follows. Starts when hunt4's block k3 is done
# (hunt4 itself is stopped after it).
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/k3-direct-off/loop.exit ]; do sleep 5; done
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "m1-gc16mb|--app oncrack --runs 12 --clients 500 --server-trace 0 --env DOTNET_GCgen0MaxBudget=1000000" \
 "m2-gc4mb|--app oncrack --runs 12 --clients 500 --server-trace 0 --env DOTNET_GCgen0MaxBudget=400000"
