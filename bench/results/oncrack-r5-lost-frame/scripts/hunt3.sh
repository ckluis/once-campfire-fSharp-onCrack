#!/usr/bin/env bash
# Third part of the hunt, inside colima, detached; starts when hunt2 is done. Round 4's phase differed from the loops in having the
# memory sampler beside it (bench/lib/procmem.py reading the server's smaps_rollup every 250 ms from CPU 0) and a server-wide idle
# gap of 1.8 s in the posting window, which the first loops (no sampler) did not show as a message lost, but did show as gaps of
# 0.4-0.9 s between publishes (the database's "WAL restart took N ms"). So: the sampler on, and provoked freezes (docker pause).
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/hunt.done ]; do sleep 5; done
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "j-procmem-fresh500|--app oncrack --runs 12 --fresh 1 --prefix 100 --clients 500 --procmem 1" \
 "j-procmem-warm500|--app oncrack --runs 20 --clients 500 --procmem 1" \
 "h1-freeze1500|--app oncrack --runs 12 --clients 500 --freeze-ms 1500" \
 "h2-freeze600|--app oncrack --runs 8 --clients 500 --freeze-ms 600" \
 "h3-freeze3000|--app oncrack --runs 6 --clients 500 --freeze-ms 3000"
