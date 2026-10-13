#!/usr/bin/env bash
# Rebuilds the comparison images the earlier cleanup removed (C, F# port, Rails, Rust), serially, inside colima.
set -x
U=/Users/clank/Desktop/projects/upstream-campfire
docker build -f $U/once-campfire-c/bench/image/Dockerfile.c -t campfire-c-upstream:cd0cbe4 $U/ctx
( cd /Users/clank/Desktop/projects/once-campfire-fsharp && docker build -t campfire-fsharp:app . )
docker build -t campfire-rails-upstream:0aa339d --build-arg APP_VERSION=0aa339d --build-arg GIT_REVISION=$(git -C $U/once-campfire rev-parse HEAD) $U/once-campfire
git -C $U/once-campfire-rust submodule status
docker build -t campfire-rust-upstream:f9dca47 $U/once-campfire-rust
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}'
