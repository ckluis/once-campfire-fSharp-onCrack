# onCrack R3.3, sourced inside the colima VM before bin/benchmark. CPUs: upstream's 8-11 (server) and 12-15 (client) map to this VM's 0-3 and 4-7.
# oncrack is the shipped default (fresh authorization on every cache hit); oncrack-cached is the same image with CAMPFIRE_FRESH_AUTH=0.
export ONCRACK_IMAGE=campfire-oncrack:app
export ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export ONCRACK_CACHED_IMAGE=campfire-oncrack:app
export ONCRACK_CACHED_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}'
export FSHARP_IMAGE=campfire-fsharp:app
export RUST_IMAGE=campfire-rust-upstream:f9dca47
export C_IMAGE=campfire-c-upstream:cd0cbe4
export TMPDIR=/mnt/cfv
cd /mnt/cfv/once-campfire-verification
BENCH="ruby bin/benchmark --workspace /mnt/cfv/ws --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7"
# R3.3: oncrack lists search by message id (image built from the clean worktree at the label's commit); oncrack-prev is onCrack as of R3.2's code (87c1ad1), which listed search by created_at.
export ONCRACK_PREV_IMAGE=campfire-oncrack:prev
export ONCRACK_PREV_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
