#!/usr/bin/env bash
# kt.sh NAME PORT KILL_AFTER [K=V ...]: one kill -9 durability run of the round 2 verifier's killtest.py against campfire-oncrack:app (inside colima).
set -u
n=$1; port=$2; ka=$3; shift 3
cd /var/tmp/vfy/ev
./app.sh up "$n" oncrack "$port" default "$@" >/dev/null || exit 2
python3 killtest.py "$port" "/var/tmp/vfy/inst/$n/db/production.sqlite3" "vfy-$n" "$ka"; rc=$?
echo "exit=$rc"
./app.sh down "$n"
