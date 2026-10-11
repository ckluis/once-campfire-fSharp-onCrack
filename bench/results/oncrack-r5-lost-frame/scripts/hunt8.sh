#!/usr/bin/env bash
# Eighth part: do the switches change anything by default? Round 4's final image (no switch in it) against the build with the switches
# (trace, verify; both off), alternating, the load generator without --trace-dir (as every earlier cable result was measured): the same
# 500-client phase, 8 each, twice over, in one session. Starts when hunt7 is done.
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/hunt.done ]; do sleep 5; done
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "ab1-r4-image|--app oncrack --runs 8 --clients 500 --server-trace 0 --client-trace 0" \
 "ab2-new-build|--app oncrack --runs 8 --clients 500 --server-trace 0 --client-trace 0" \
 "ab3-r4-image|--app oncrack --runs 8 --clients 500 --server-trace 0 --client-trace 0" \
 "ab4-new-build|--app oncrack --runs 8 --clients 500 --server-trace 0 --client-trace 0"
