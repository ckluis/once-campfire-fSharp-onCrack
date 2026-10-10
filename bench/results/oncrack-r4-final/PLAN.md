# R4 final run: measurement plan, fixed 2026-10-10 before the first execution

Execution steps (each a foreground command, results under `bench/results/oncrack-r4-final/` with host-load file beside):

1. **Write PLAN.md** (this file, before any session) — commit it.
2. **Rebuild the onCrack image** from HEAD into the clean measured worktree (`oncrack-measured`).
3. **Pixel gate**: `bin/pixel-parity --fast --only realtime search` on the default seed.
4. **Cable suite**: `bench/run --apps rust,fsharp,oncrack --suites cable --clients 100 500 1000 2000 --reps 3`, one session.
5. **Upstream harness, normal and mixed profiles**: `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7`, apps `rails,rust,c,fsharp,oncrack,oncrack-cached`, two sessions (normal, mixed).
6. **Hand re-runs**: `review.py` for room page, mixed and post, against onCrack fresh, onCrack cached, Rust and C, in alternation.

Sessions (5 and 6) follow R3's rules, set now:

1. **Host load sampling**: every 10 s during the run (`host-load-NAME.txt`: non-VM CPU %, top four processes, load average). A session starts when non-VM CPU has been under 100% for three consecutive samples, or after 10 minutes waiting.
2. **Noise gate**: a session is NOISY if more than 25% of its host samples show non-VM CPU ≥ 150%. A NOISY session is re-run once; a profile has at most two sessions. Both are reported in full.
3. **Headline for a profile**: median of each cell over all rounds of its sessions (3 if one, 6 if two), as R3.2 pooled. No session is dropped. A session the guard stops (Mac free space < 12 GB) is reported incomplete and not pooled; re-run it once.
4. **Hand re-runs**: cross-check, not headline. Room page, mixed, post: onCrack fresh (headline), onCrack cached, Rust, C, in alternation (forward then reversed), with server CPU per request from cgroup.
5. **Headline mode**: fresh authorization (onCrack default). Cached decision shown beside, labelled opt-in.
6. **Nothing adjusted after the fact.** If a session shows errors, invalid responses, or failed audits, it is reported and not pooled; cause stated.

Disk guard: `bin/clean-docker` and `bin/clean-parity` between steps; stop under 12 GB free on Mac.
