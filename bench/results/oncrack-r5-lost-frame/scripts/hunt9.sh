#!/usr/bin/env bash
# Ninth part: which switches matter. Every block is fresh containers (the first phase of a container is where the arrays move), the verify
# build with the throttled report (6920635, /var/tmp/campfire-r5-verify2), 500 clients; the stress is a 4 MB gen0 budget. The mechanism's
# controls: CAMPFIRE_CABLE_LOG=ring, CAMPFIRE_CABLE_ORDER=stream (the log and the order), CAMPFIRE_CABLE_GATHER=off (copying writes) and
# CAMPFIRE_CABLE_DIRECT=off (writes through Kestrel's stream); then the F# port (no gathered writes) and Rust under the same pressure, and the
# default with no pressure at all. Starts when hunt8 is done.
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/ab4-new-build/loop.exit ]; do sleep 5; done
export ONCRACK_MOUNT=/var/tmp/campfire-r5-verify2
S='CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000'
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "c0-default-nostress|--app oncrack --runs 12 --fresh 1 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_VERIFY=1" \
 "c1-default-stress|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env '$S'" \
 "c2-ring-stress|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env '$S CAMPFIRE_CABLE_LOG=ring'" \
 "c3-orderstream-stress|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env '$S CAMPFIRE_CABLE_ORDER=stream'" \
 "c4-gatheroff-stress|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env '$S CAMPFIRE_CABLE_GATHER=off'" \
 "c5-directoff-stress|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env '$S CAMPFIRE_CABLE_DIRECT=off'" \
 "p1-port-stress|--app fsharp --runs 10 --fresh 1 --clients 500 --env DOTNET_GCgen0MaxBudget=400000" \
 "r1-rust|--app rust --runs 10 --fresh 1 --clients 500"
