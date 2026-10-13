# Sourced inside the colima VM before bin/benchmark. CPUs: upstream's 8-11 (server) and 12-15 (client) map to this VM's 0-3 and 4-7.
export ONCRACK_IMAGE=campfire-oncrack:app
export ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'
export FSHARP_IMAGE=campfire-fsharp:app
export RUST_IMAGE=campfire-rust-upstream:f9dca47
export C_IMAGE=campfire-c-upstream:cd0cbe4
export RAILS_IMAGE=campfire-rails-upstream:0aa339d
export RAILS_BENCH_ENV='{"WEB_CONCURRENCY":"4","RAILS_MAX_THREADS":"1","RAILS_MIN_THREADS":"1"}'
export TMPDIR=/mnt/cfv
cd /mnt/cfv/once-campfire-verification
BENCH="ruby bin/benchmark --workspace /mnt/cfv/ws --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7"
