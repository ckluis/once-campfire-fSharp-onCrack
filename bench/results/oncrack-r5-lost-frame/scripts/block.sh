#!/usr/bin/env bash
# One block of the R5.1 lost-frame hunt, inside colima, detached:
#   block.sh NAME [bench/cable/loop arguments...]
# Writes /var/tmp/r5-lost-frame/NAME/ (bench/cable/loop's evidence, loop.exit last). Always the same environment as the cable suite of
# round 4 (cpus 0-3 for the server, 4-7 for the load generator), onCrack as the build mounted over the image's /opt/campfire.
set -uo pipefail
name=$1; shift
ROOT=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
cd "$ROOT"
export SERVER_CPUS=0-3 LOADGEN_CPUS=4-7 WORK=/var/tmp/campfire-bench-work
export RUST_IMAGE=${RUST_IMAGE:-campfire-rust-upstream:f9dca47}
# ONCRACK_MOUNT="" runs the image's own build (round 4's final).
export ONCRACK_MOUNT=${ONCRACK_MOUNT-/var/tmp/campfire-r5-trace}
# A block named *r4-image* runs the image's own build; one named *new-build* the build with every switch (verify build), whatever the caller set.
case "$name" in *r4-image*) export ONCRACK_MOUNT="" ;; *new-build*) export ONCRACK_MOUNT=/var/tmp/campfire-r5-verify ;; esac
export HTTP_ROUTES=up SUITES=cable LOAD_WAIT_SECS=120 CABLE_CLIENTS="500"
out=/var/tmp/r5-lost-frame/$name
rm -rf "$out"; mkdir -p "$out"
bench/cable/loop --out "$out" "$@" > "$out.log" 2>&1
echo "exit $?" >> "$out.log"
