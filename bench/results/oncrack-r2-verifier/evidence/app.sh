#!/usr/bin/env bash
# app.sh up NAME APP PORT SEED [K=V ...] | down NAME | dir NAME
# Runs an app image on a VM-local (ext4) copy of a parity seed, so a foreign SQLite connection in the VM shares the WAL index.
set -euo pipefail
ROOT=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
BASE=/var/tmp/vfy/inst
cmd=$1; name=$2
case $cmd in
  down) docker rm -f "vfy-$name" >/dev/null 2>&1 || true; rm -rf "$BASE/$name"; exit 0 ;;
  dir) echo "$BASE/$name"; exit 0 ;;
esac
app=$3; port=$4; seed=$5; shift 5
case $app in
  oncrack) image=campfire-oncrack:app ;;
  fsharp) image=campfire-fsharp:app ;;
  rust) image=campfire-rust:app ;;
  reference) image=campfire-reference ;;
  *) image=$app ;;
esac
docker rm -f "vfy-$name" >/dev/null 2>&1 || true
if [ -n "${FROM_DIR:-}" ]; then dir=$FROM_DIR; else
dir=$BASE/$name; rm -rf "$dir"; mkdir -p "$dir/db" "$dir/storage"
cp -a "$ROOT/parity/.seed/$seed/db/." "$dir/db/"; cp -a "$ROOT/parity/.seed/$seed/storage/." "$dir/storage/"; fi
env=(); for e in "$@"; do env+=(-e "$e"); done
extra=(); [ "$app" = reference ] && extra=(-v "$ROOT:/work:ro"); [ -n "${MOUNT:-}" ] && extra+=(-v "$MOUNT:/opt/campfire:ro")
docker run -d --name "vfy-$name" --cpus 2 --log-driver json-file --log-opt max-size=10m --log-opt max-file=2 \
  --user "$(id -u):$(id -g)" -p "127.0.0.1:$port:80" --env-file "$ROOT/parity/.env.reference" "${env[@]+"${env[@]}"}" \
  -v "$dir/db:/rails/storage/db" -v "$dir/storage:/rails/storage/files" "${extra[@]+"${extra[@]}"}" "$image" >/dev/null
for _ in $(seq 1 480); do
  curl -fsS -o /dev/null "http://127.0.0.1:$port/up" 2>/dev/null && { echo "up $name $app :$port $dir"; exit 0; }
  sleep 0.25
done
docker logs "vfy-$name" 2>&1 | tail -30; exit 1
