#!/usr/bin/env bash
# Sixth part: the build with CAMPFIRE_CABLE_VERIFY (the probe of each published array checked around the sendmsg that reads it, and the
# address the kernel was given against the array's), at 4d6f89c in /var/tmp/campfire-r5-verify, under collections made very frequent
# (the one loss that frequent collections gave, the frame's 10,298 bytes were 8,864 NULs and pointers: other objects' memory).
cd "$(dirname "$0")/../../../.."
export ONCRACK_MOUNT=/var/tmp/campfire-r5-verify
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "v1-verify-gc1mb|--app oncrack --runs 12 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0size=0x100000 DOTNET_GCgen0MaxBudget=100000'" \
 "w1-verify-gc1mb-gather-off|--app oncrack --runs 12 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 CAMPFIRE_CABLE_GATHER=off DOTNET_GCgen0size=0x100000 DOTNET_GCgen0MaxBudget=100000'" \
 "v2-verify-gc4mb|--app oncrack --runs 12 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000'" \
 "v3-verify-default|--app oncrack --runs 12 --clients 500 --server-trace 0 --env CAMPFIRE_CABLE_VERIFY=1"
