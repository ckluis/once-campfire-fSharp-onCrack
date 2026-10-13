#!/usr/bin/env bash
# setup-r32.sh: rebuild the harness's tmpfs after a VM restart (run inside colima). A 3 GiB tmpfs at /mnt/cfv; the verification
# checkout (branch oncrack-adapter) cloned there; upstream's load generator (Rust 1.98.1, static, kept on the Mac in
# tools/loadgen-1.98.1-static/) in its default path; the seed built with the pinned Rails 90b3300 image and made group-writable;
# a workspace of symlinks to the measured checkouts (onCrack's is the clean worktree ~/Desktop/projects/oncrack-measured).
set -euo pipefail
U=/Users/clank/Desktop/projects/upstream-campfire
sudo mkdir -p /mnt/cfv
mountpoint -q /mnt/cfv || sudo mount -t tmpfs -o size=3g,mode=0775 tmpfs /mnt/cfv
sudo chown "$(id -u)":1000 /mnt/cfv
cd /mnt/cfv
rm -rf once-campfire-verification ws
git clone -q /Users/clank/Desktop/projects/once-campfire-verification once-campfire-verification
cd once-campfire-verification
git checkout -q oncrack-adapter
mkdir -p loadgen/target/release
cp "$U/tools/loadgen-1.98.1-static/loadgen" loadgen/target/release/loadgen
ruby bin/seed --image campfire-reference:app > /dev/null 2>&1
chmod -R g+w fixtures/default/db fixtures/default/storage
mkdir -p /mnt/cfv/ws /mnt/cfv/out
ln -sfn /Users/clank/Desktop/projects/oncrack-measured /mnt/cfv/ws/once-campfire-oncrack
ln -sfn "$U/once-campfire-rust" /mnt/cfv/ws/once-campfire-rust
ln -sfn "$U/once-campfire-c" /mnt/cfv/ws/once-campfire-c
ln -sfn /Users/clank/Desktop/projects/once-campfire-fsharp /mnt/cfv/ws/once-campfire-fsharp
echo "harness $(git log --oneline -1)"
echo "loadgen $(sha256sum loadgen/target/release/loadgen | cut -c1-16)"
echo "seed    $(sha256sum fixtures/default/db/production.sqlite3 | cut -c1-16)"
for d in /mnt/cfv/ws/*; do echo "$(basename "$d") $(git -C "$d" rev-parse --short HEAD) dirty=$(git -C "$d" status --porcelain --untracked-files=no | wc -l)"; done
