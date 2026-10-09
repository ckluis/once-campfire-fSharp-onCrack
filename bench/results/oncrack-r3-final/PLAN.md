# R3 final run: measurement plan, fixed 2026-10-09 before the first upstream session ran

Sessions (all with `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7`, apps
`rails,rust,c,fsharp,oncrack,oncrack-cached`, in one VM boot, from images listed in the report):
- `normal`: routes `room_show,messages_page,sidebar,search,post_message`.
- `mixed`: `--mixed-write-rate 10`, routes `room_show,messages_page,sidebar,search`.

Rules, set now so no session can be chosen by its result:
1. Host load is sampled every 10 s for the whole session (`host-load-NAME.txt`: the sum of non-VM CPU, the top four processes, the load
   average). A session starts when the non-VM sum has been under 100% for three samples in a row, or after 10 minutes of waiting
   (then it says so in its file).
2. A session is NOISY if, during it, more than 25% of the host samples show a non-VM CPU sum of 150% or more. A noisy session is run one
   more time (`-2`); a profile has at most two sessions. Both are reported in full.
3. The headline for a profile is the median of each cell over all the rounds of its sessions (three rounds if one session, six if two),
   as R3.2 pooled. No session is dropped. A session the guard stops (under 12 GB free on the Mac) is reported as incomplete and not
   pooled; it is rerun once.
4. The hand re-runs (`review.py`) are the cross-check, not the headline: room page, mixed and post for onCrack (fresh, headline),
   onCrack cached, Rust and C, run in alternation, forward then reversed, with the server's CPU per request from the cgroup.
5. Headline mode for onCrack is fresh authorization (the default). The cached decision is shown beside it, labelled opt-in.
6. Nothing is adjusted after the fact. If a session shows something wrong (an error, an invalid response, a failed audit), it is reported
   and not pooled, and the cause is stated.
