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

## Next steps (in order)

4. **Cable suite** — `bench/cable/run rust fsharp --clients 100 500 1000 2000 --reps 3` (then onCrack; or run as part of bench/run)
   - ~15-20 minutes per app variant
   - Outputs under bench/results/oncrack-r4-final/

5. **Upstream harness normal profile** — one session
   ```
   /Users/clank/Desktop/projects/once-campfire-verification:
   bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 \
     --apps rails,rust,c,fsharp,oncrack,oncrack-cached
   ```
   - Apps in sequence (fresh, cached modes)
   - ~40-50 minutes in colima
   - Results to bench/results/oncrack-r4-final/ via symlink or copy

6. **Upstream harness mixed profile** — one session
   - Same command with `--mixed-write-rate 10`
   - ~40-50 minutes

7. **Hand re-runs** — `review.py` room page, mixed, post
   - 5 alternations (forward, reverse, forward, reverse, forward)
   - ~30 minutes

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
