# onCrack R3.4, sourced inside the colima VM before bin/benchmark: as env-r33.sh, but the oncrack-cached slot is reused for the
# opt-in WAL policy (fresh authorization on, as the shipped default): CAMPFIRE_WAL_DEFER with a 150,000-frame ceiling.
source /Users/clank/Desktop/projects/upstream-campfire/scripts/env-r33.sh
export ONCRACK_CACHED_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_WAL_DEFER":"on","CAMPFIRE_WAL_CEILING_PAGES":"150000"}'
