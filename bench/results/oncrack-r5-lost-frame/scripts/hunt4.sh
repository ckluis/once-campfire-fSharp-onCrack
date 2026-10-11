#!/usr/bin/env bash
# Fourth part of the hunt, inside colima, detached. The first loops had the app's trace on and never lost a message (about 190 phases);
# the one block with it off (i-notrace500) lost one or two messages for ONE client in 3 of 15 phases, the client's frame for the
# message made of NULs. So everything here runs with the server trace off (the client's dumps are the evidence), and each variant of
# the app that could matter is a block of 15 phases at 500 clients: the default again, then the switches that turn a mechanism off
# (gathered writes, direct writes, the log, the publish order), the other load generator client, the port and Rust, 1,000 clients.
cd "$(dirname "$0")/../../../.."
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "k1-default-notrace|--app oncrack --runs 15 --clients 500 --server-trace 0" \
 "k2-gather-off|--app oncrack --runs 15 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_GATHER=off" \
 "k3-direct-off|--app oncrack --runs 15 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_DIRECT=off" \
 "k6-tungstenite|--app oncrack --runs 15 --clients 500 --server-trace 0 --client-trace 0 --lg-args '--client tungstenite'" \
 "k4-ring|--app oncrack --runs 15 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_LOG=ring" \
 "k5-order-stream|--app oncrack --runs 15 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_ORDER=stream" \
 "k7-port|--app fsharp --runs 15 --clients 500" \
 "k8-rust|--app rust --runs 15 --clients 500" \
 "k9-default-1000|--app oncrack --runs 10 --clients 1000 --server-trace 0" \
 "k10-default-trace-on|--app oncrack --runs 15 --clients 500 --server-trace 1"
