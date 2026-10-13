#!/usr/bin/env bash
# Seventh part. The verify build showed the arrays MOVING before sendmsg returned (so the pins did not hold), only in the first phase after
# a container start and only with collections made frequent (gather off: nothing). The image's app is ReadyToRun code, which tiered
# compilation replaces with JIT code after a while: so the first phase is the R2R version of Sendmsg.pin. Two controls under the same
# collection pressure: TieredCompilation off (R2R code is kept for good: if R2R is the cause, every phase shows it) and ReadyToRun off (all
# JIT: if R2R is the cause, none does). Starts when hunt6 is done.
cd "$(dirname "$0")/../../../.."
until [ -f /var/tmp/r5-lost-frame/hunt.done ]; do sleep 5; done
export ONCRACK_MOUNT=/var/tmp/campfire-r5-verify
exec bench/results/oncrack-r5-lost-frame/scripts/hunt.sh \
 "y1-verify-gc4mb-tc-off|--app oncrack --runs 6 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 DOTNET_TieredCompilation=0'" \
 "y2-verify-gc4mb-r2r-off|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 DOTNET_ReadyToRun=0'" \
 "y3-verify-gc4mb-fresh|--app oncrack --runs 6 --fresh 1 --clients 500 --server-trace 0 --env 'CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000'"
