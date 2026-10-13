#!/usr/bin/env bash
# Tenth part. Round 4's phase with the missing message also had the container using under one core for 1.8 s in the posting window (every
# other phase of the session had no such stretch), and the posters were not blocked in a request (the slowest post took 27 ms). Does the
# moved-array phenomenon come with such a stretch? The memory sampler beside each phase (--procmem 1, as in round 4) gives the container's
# CPU every 250 ms. Fresh containers, the verify build, the 4 MB gen0 budget. Starts when hunt9 is done.
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/r1-rust/loop.exit ]; do sleep 5; done
export ONCRACK_MOUNT=/var/tmp/campfire-r5-verify2
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "d1-procmem-stress|--app oncrack --runs 10 --fresh 1 --clients 500 --server-trace 0 --procmem 1 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000'" \
 "d2-procmem-default|--app oncrack --runs 10 --fresh 1 --prefix 100 --clients 500 --server-trace 0 --procmem 1"
