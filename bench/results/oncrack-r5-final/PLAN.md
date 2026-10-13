# R5 final run: measurement plan, fixed 2026-10-12 before the first execution

Derived from `bench/results/oncrack-r4-final/PLAN.md`. Changes from round 4: two sessions per upstream-harness profile (normal and mixed) so no
headline is single-session; the PR #6 reliability session at 3 rounds for every app; the cable suite in one uninterrupted session. The noise and
pooling rules are unchanged. Results under `bench/results/oncrack-r5-final/`, with the host-load file beside each session.

Execution steps (each a foreground command, or a detached session waited on in chunks under ten minutes):

1. **Write PLAN.md** (this file, before any session) and commit it.
2. **Rebuild the images**: the onCrack image from HEAD into the clean measured worktree (`/Users/clank/Desktop/projects/oncrack-measured`,
   moved to HEAD; `CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build`), and the parity wrapper and reference images round 4 deleted.
3. **Full pixel gate** on the final code: `bin/pixel-parity` on every seed, the full lean matrix (round 2's 940-screenshot gate; rounds 3-4 ran
   targeted slices), with the core-dump guard and disk checks, `bin/clean-docker` and `bin/clean-parity` between slices.
4. **`bin/verify`** with `CAMPFIRE_REQUIRE_SEED=1`.
5. **KLOC** by upstream's rules (`docs/performance-review.md`, its cloc method) for Rails 0aa339d, Rust f9dca47, C cd0cbe4, the port and onCrack.
6. **Cable suite**: `bench/run --apps rust,fsharp,oncrack --suites cable --clients 100 500 1000 2000 --reps 3`, **one uninterrupted session**
   (one start, one host-load file, no stop and resume; a session the guard or a failure interrupts is reported incomplete and re-run whole once).
7. **Upstream harness, normal and mixed profiles**: `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7`, apps
   `rails,rust,c,fsharp,oncrack,oncrack-cached`; **two sessions per profile** (normal-1, normal-2, mixed-1, mixed-2; mixed adds
   `--mixed-write-rate 10`), in alternating order (normal-1, mixed-1, normal-2, mixed-2).
8. **PR #6 reliability** (`bench/reliability/run`, profiles overload and cable, with cable_heavy following cable): **3 rounds for every app**
   (Rails 0aa339d, Rust f9dca47, C cd0cbe4, onCrack fresh, oncrack-cached; the F# port's cable profiles alone, as the port cannot take overload's
   contracts; onCrack before R4.5 as the control).
9. **Hand re-runs**: `review.py` for room page, mixed and post, onCrack fresh, onCrack cached, Rust and C, in alternation.

Rules for the sessions (6-9), as round 4's, with the pooling changed only in that every headline now has two sessions:

1. **Host load sampling**: every 10 s during the run (`host-load-NAME.txt`: non-VM CPU %, top four processes, load average). A session starts when
   non-VM CPU has been under 100% for three consecutive samples, or after 10 minutes waiting.
2. **Noise gate**: a session is NOISY if more than 25% of its host samples show non-VM CPU >= 150%. A NOISY session is re-run once; a profile has
   at most three sessions then, all reported in full.
3. **Headline for a profile**: median of each cell over all rounds of its sessions (6 for two sessions), as R3.2 pooled. No session is dropped. A
   session the guard stops (Mac free space < 12 GB) is reported incomplete and not pooled; re-run it once.
4. **Hand re-runs**: cross-check, not headline. Forward then reversed, with server CPU per request from the cgroup.
5. **Headline mode**: fresh authorization (onCrack default). Cached decision shown beside, labelled opt-in.
6. **Nothing adjusted after the fact.** A session that shows errors, invalid responses or failed audits is reported and not pooled; cause stated.
7. **No source fixes in a runner.** A gate failure is recorded with its cause and reported, not patched in `src/`.

Disk guard: `bin/clean-docker` and `bin/clean-parity` between steps; stop under 12 GB free on the Mac (`go clean -cache` only if another
project's Go build cache is what pushed it under and no go process is running).

## What this runner covers

This unit (the final GATES runner) executes steps 1-5. Steps 6-9 are the measurement sessions this plan fixes; they are recorded as not started
unless the run log says otherwise.
