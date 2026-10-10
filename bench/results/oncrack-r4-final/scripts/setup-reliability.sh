#!/usr/bin/env bash
# setup-reliability.sh: inside colima, after setup.sh. Puts the harness's reliability branch (oncrack-reliability-working with its local,
# uncommitted bench/reliability.rb change, as it stands on the Mac) in /mnt/cfv/rel, with the benchmark's seed and a load generator built from
# that branch's loadgen/ (rust:1.98.1-trixie, static, --locked), the one with the `disconnected` counter.
set -euo pipefail
V=/Users/clank/Desktop/projects/once-campfire-verification
rm -rf /mnt/cfv/rel; mkdir -p /mnt/cfv/rel
( cd $V && tar --exclude=./.git --exclude=./loadgen/target --exclude=./node_modules --exclude=./tmp -cf - . ) | tar -xf - -C /mnt/cfv/rel
cp -a /mnt/cfv/once-campfire-verification/fixtures /mnt/cfv/rel/fixtures
mkdir -p /mnt/cfv/rel/loadgen/target/release /mnt/cfv/rel/tmp
mkdir -p /var/tmp/lgbuild && rm -rf /var/tmp/lgbuild/loadgen && cp -a $V/loadgen /var/tmp/lgbuild/loadgen && rm -rf /var/tmp/lgbuild/loadgen/target
docker run --rm -v /var/tmp/lgbuild/loadgen:/w -w /w -e RUSTFLAGS="-C target-feature=+crt-static" rust:1.98.1-trixie cargo build --release --locked
cp /var/tmp/lgbuild/loadgen/target/release/loadgen /mnt/cfv/rel/loadgen/target/release/loadgen
git -C $V log --oneline -1
echo "loadgen $(sha256sum /mnt/cfv/rel/loadgen/target/release/loadgen | cut -c1-16)"
