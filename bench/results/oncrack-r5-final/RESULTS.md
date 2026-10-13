# R5 final: upstream-harness sessions and hand re-runs, 2026-10-12/13

Images: `campfire-oncrack:app` (label `ee5a2e91795e`, `src/` identical to `6abc183`), Rust `f9dca47`, C `cd0cbe4`, Rails `0aa339d`, F# port `9954ad0`. Harness `a05b344` (branch
`oncrack-adapter`), upstream's load generator `351a66af`, seed `34f66576` (built fresh by `scripts/setup.sh`; round 4's seed digest differed, the content is the same
fixtures). `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7` from the tmpfs at `/mnt/cfv`, apps `rails,rust,c,fsharp,oncrack,oncrack-cached`,
**with `--routes room_show,messages_page,sidebar,search,post_message` (normal) or `...,search` plus `--mixed-write-rate 10` (mixed)** as rounds 2-4 ran them; PLAN.md's command
line omitted `--routes` (see Deviations). Every session exit 0, **0 errors or invalid responses in 224,402,307 timed responses, 2,762,229 acknowledged writes audited**.

## Headline (PLAN rule 3: median of every round of every session; none dropped)

`pooled.md` has the tables. Geometric mean over the profile's routes, ratio of medians:

| Profile | sessions | onCrack (fresh) / Rust | onCrack (fresh) / C | onCrack / F# port | onCrack / Rails | fresh / cached |
|---|---|---:|---:|---:|---:|---:|
| Normal | 3 (9 rounds) | **3.76x** | **2.40x** | 5.25x | 35.7x | 0.90x |
| Mixed (reads, 10 posts/s writer) | 3 (9 rounds) | **3.76x** | **2.26x** | 6.78x | 56.4x | 0.83x |

Round 4 (one session each): normal 3.29x Rust and 2.40x C; the C ratio is unchanged and the Rust ratio is inside the spread below.

**The spread behind it (do not quote the headline without this).** `totals.md`: each session's own geometric mean, fresh/Rust 2.11x, 3.28x, 4.74x (normal) and 6.33x, 3.12x,
3.00x (mixed); fresh/C 1.46x, 2.99x, 1.41x (normal) and 2.38x, 1.48x, 3.81x (mixed). Only normal-1 and mixed-1 passed the noise rule; normal-2, normal-3, mixed-2 and mixed-3 were
NOISY (55-65% of host samples at >= 150% non-VM CPU, see below). The noise is not symmetric: onCrack's cells fall further under host load than C's or Rust's in some
sessions (room page 9,787 to 163,603 across mixed rounds; its 160k req/s needs ~2.5 of the 4 client cores) and the post path (disk) falls 10x under another project's
fsyncs (normal-1 onCrack post 1,975 to 12,449). A quiet host is what round 4 had for its one session; this round did not get one, so the honest reading is
"between 2x and 5x Rust, between 1.4x and 3.8x C, ahead in every cell at its median", not a point value.

**Post path.** onCrack pooled post 8,726 req/s (fresh; 12,289 cached) against Rust 5,001 and C 3,517: ahead at the median, but the wide min-max (850-13,732) says the
write path is the one most exposed to a shared disk. The hand re-runs' quiet sets (below) show 15,395 req/s at 194.9 us of server CPU per post for fresh.

## Sessions

| Session | Started (EDT) | Host samples >= 150% | Rule 2 | Notes |
|---|---|---:|---|---|
| normal-1 | 10-12 22:07 | 22% | ok | |
| mixed-1 | 10-12 22:42 | 24% | ok | |
| normal-2 | 10-12 22:43 | 56% of the sampled 55% | NOISY | host sampler lost 22:52-23:00 (my wait was moved to the background by the tool timeout); sampled part was NOISY |
| mixed-2 | 10-12 23:09 | 54% | NOISY | |
| normal-3 | 10-12 23:26 | 65% | NOISY | the one re-run of normal-2, pooled with the others |
| mixed-3 | 10-12 23:57 | 65% | NOISY | the one re-run of mixed-2, pooled with the others |
| discarded-normal-1-all-routes | 10-12 21:40 | 48% | NOISY | wrong route set; not pooled; kept in full (`discarded-normal-1-all-routes/README.md`) |

A profile's budget is three sessions; it is spent. The loads were another project's Erlang VMs (`beam.smp`, 100-490% each), its Go test binaries, Python workers and Spotlight; nothing of
this project's ran beside a session (`host-load-*.txt` name the top four processes every 10 s).

## Hand re-runs (`review.py`, 16 clients, 15 s warm-up + 10 s window, server CPU from the cgroup)

Seven sets of four apps (fresh, cached, Rust, C): forward, reversed, forward, reversed, then one re-run of each NOISY set. **84 timed windows all valid, 28 database audits all ok
(4,474,566 acknowledged posts: rich-text rows equal, 0 search-index rows missing).** Sets rev, rev2-b and fwd2-b were not NOISY (18%); fwd, fwd2, rev2 and fwd-b were (65-88%): `review-noise.txt`.

Server CPU per request (cgroup), ratio Rust or C over onCrack (fresh):

| | room page | mixed reads | post |
|---|---:|---:|---:|
| all seven sets, Rust / fresh | 3.79x | 4.78x | 3.14x |
| all seven sets, C / fresh | 2.93x | 2.57x | 3.32x |
| the three non-NOISY sets, Rust / fresh | 3.75x | 4.15x | 2.69x |
| the three non-NOISY sets, C / fresh | 2.68x | 2.47x | 3.24x |

Round 4 said 3.25x Rust and 2.02x C for the room page. Both are higher now (3.75-3.79x and 2.68-2.93x); CPU per request is the more host-robust number (it is the container's own CPU),
and it moved the way the harness's pooled ratios did. I do not attribute the change to a code change (`src/` is unchanged since round 4's last commit but one, `git diff 6abc183 HEAD -- src` empty): the
likelier cause is that round 4's Rust and C room-page CPU was read on a quieter host. The quiet sets (`review-quiet-sets.md`) are a cross-check chosen by the pre-fixed rule, not a headline.

Fresh against cached: 20.2 vs 19.2 us per room-page request in the quiet sets, 194.9 vs 217.2 us per post. The default pays nothing measurable for re-checking authorization.

## Deviations, stated

1. **Routes.** PLAN.md step 7 and the runner task omit `--routes`; the harness default is eight routes (avatar, static_css, up added). Rounds 2-4 passed the five (four mixed). I ran the first normal
   session on the default eight by mistake, saw it in the table, set it aside and re-ran with the five. Not an adjustment after the fact to flatter anything: the aside is kept whole and shows
   onCrack ahead of Rust, C and the port on the three extra routes too.
2. **normal-2's sampler gap** (above): rule 1 asks for samples every 10 s, 45% of that session has none.
3. **NOISY sessions pooled.** Rule 3 says every session is pooled, so the headline carries four NOISY sessions out of six. It is the rule, not a choice; the per-session table is the check on it.
