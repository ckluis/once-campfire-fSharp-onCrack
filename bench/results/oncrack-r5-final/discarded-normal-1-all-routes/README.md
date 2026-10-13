# Discarded (not pooled): the first normal session, run by mistake with all eight routes

Started 2026-10-12 21:40 EDT as `normal-1`. Two faults, either enough to keep it out of the headline:

1. **Wrong route set.** I omitted `--routes room_show,messages_page,sidebar,search,post_message`, which every earlier round used for the normal profile
   (rounds 2-4; `oncrack-r4-final/normal-1/summary.json` lists those five). The harness default is eight routes (adds avatar, static_css, up), so
   each round ran 8 route pairs per app and the headline columns were measured in a different interleaving from round 4's.
2. **NOISY** by PLAN rule 2: 48% of the session's host samples show non-VM CPU >= 150% (max 702%): another project's Erlang VMs (`beam.smp`, 100-490% each)
   and Spotlight indexing ran for the first 25 minutes of it. `noise.txt`.

Kept in full (not deleted, not pooled): `table.md` is the harness table, exit 0, every response validated. The three extra routes are the only
information not in the other sessions. Do not quote its headline cells; room page 150k vs Rust 36k is not a clean reading.
The re-run is `normal-1` (five routes), which is a fresh session, not a second use of the noisy-rerun allowance.
