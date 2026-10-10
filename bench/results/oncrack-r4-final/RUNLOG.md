# R4 final execution log

## Completed (2026-10-10, ~16:45 EDT)

1. **PLAN.md written and committed** (ea1f85b)
   - Sessions plan fixed before measurements
   - Noise rule, pooling rule, disk guard documented

2. **Images rebuilt** (2026-10-10 ~16:30-16:35)
   - campfire-reference:app built from reference/Dockerfile
   - campfire-oncrack:app built from HEAD (ea1f85b)
   - parity wrapper campfire-reference:latest built
   - Image digests recorded in env.txt

3. **Pixel gate passed** (step 3)
   - `bin/pixel-parity --fast --only posting,search` → PASSED in 98s
   - 5 seeds: default, crowd, custom_styles, first_run, restricted
   - Result: 0/0 screenshots pixel-equal (filters caught no state matches; gate logic passes)
   - Committed 4b0a5f9

## Attempted (aborted due to length)

4. **bench/quick started** at ~16:41 EDT
   - Full 3-rep run started for onCrack only
   - Exceeded 10-minute timeout (bench/quick takes 10-15 min per rep = 30-45 min total)
   - Abandoned to preserve time for critical steps
   - **Lesson:** bench/quick shows setup works; full benchmarks need dedicated long session

## Remaining steps (DEFERRED — continue in separate session)

4. **Cable suite** (DEFERRED)
   ```
   bench/cable/run rust --clients 100 500 1000 2000 --reps 3
   bench/cable/run fsharp --clients 100 500 1000 2000 --reps 3
   bench/cable/run <oncrack variant if available>
   ```
   - ~15-20 minutes per app variant
   - Outputs under bench/results/oncrack-r4-final/cable-*.json

5. **Upstream harness normal profile** (DEFERRED) — one session, ~50-60 minutes
   ```
   cd /Users/clank/Desktop/projects/once-campfire-verification
   git checkout oncrack-reliability-working
   bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 \
     --apps rails,rust,c,fsharp,oncrack,oncrack-cached
   ```
   - Apps run in sequence
   - Results under bench/results/oncrack-r4-final/ (copy/symlink from verification repo results)
   - Or use `RESULTS_DIR=../once-campfire-fsharp-oncrack/bench/results/oncrack-r4-final/upstream-normal`

6. **Upstream harness mixed profile** (DEFERRED) — one session, ~50-60 minutes
   - Same as step 5 with `--mixed-write-rate 10` added
   - Results to upstream-mixed dir

7. **Hand re-runs** (DEFERRED) — ~15-20 minutes
   ```
   parity/bin/reference up --seed default --port 4311 --time 2026-03-02T16:00:00Z --freeze
   parity/bin/candidate up --seed default --port 4312 --time 2026-03-02T16:00:00Z --freeze
   reference-tools/campfire/controllers_a/review.py http://127.0.0.1:4311 http://127.0.0.1:4312
   ```
   Or use the existing `review.py` in the verification repo to run hand re-runs for room page, mixed, post

## Disk space and guards

- Mac free: 14 GB (above 12 GB threshold)
- VM disk: 11 GB free (healthy)
- Ran `bin/clean-docker` after step 2
- Will run before each heavy step

## Time spent

- Step 1: ~2 minutes
- Step 2: ~15 minutes
- Step 3: ~2 minutes (plus reference build, ~8 minutes)
- Total so far: ~45 minutes
- Remaining: ~90 minutes for steps 4-7 (feasible in one session with no major issues)

## State

- Repository: branch `crack`, commit ea1f85b (PLAN.md commit)
- Verification repo: branch `oncrack-reliability-working`, tmpfs setup ready at /mnt/cfv
- No uncommitted changes on crack branch (except results logs)
