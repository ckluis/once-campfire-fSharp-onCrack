#!/usr/bin/env bash
# Runs inside a debian:trixie build container: fetch pinned deps (not Fil-C), build them with clang, build the bench binary.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends clang make cmake perl autoconf automake libtool pkg-config zlib1g-dev libltdl-dev git curl unzip python3 ca-certificates xz-utils bzip2 file >/dev/null
cp -a /repo /src && cd /src
rm -rf build vendor/build vendor/src
for s in vendor/scripts/*.sh; do
  case "$s" in *filc.sh) continue ;; esac
  echo "== $s"; bash "$s"
done
make deps-build MODE=bench -j4
make MODE=bench build-app -j4
ls -la build/bench/campfire
mkdir -p /repo/build/bench && cp build/bench/campfire /repo/build/bench/campfire
sha256sum /repo/build/bench/campfire
clang --version | head -1
ldd /repo/build/bench/campfire
