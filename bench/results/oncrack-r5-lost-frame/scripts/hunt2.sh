#!/usr/bin/env bash
# Second part of the hunt (the first part ran a-warm500, a-fresh500, a-warm1000, b-ring500 with a loop that truncated the app's trace file;
# its c-stream500 was stopped for the disk). Inside colima, detached.
cd "$(dirname "$0")/../../../.."
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "c-stream500|--app oncrack --runs 15 --clients 500 --env CAMPFIRE_CABLE_ORDER=stream" \
 "d-port500|--app fsharp --runs 6 --clients 500" \
 "e-rust500|--app rust --runs 6 --clients 500" \
 "f-tail0-500|--app oncrack --runs 10 --clients 500 --lg-args '--tail-window 0'" \
 "g-warm500b|--app oncrack --runs 20 --clients 500" \
 "g-fresh500b|--app oncrack --runs 10 --fresh 1 --prefix 100 --clients 500" \
 "i-notrace500|--app oncrack --runs 15 --clients 500 --server-trace 0"
