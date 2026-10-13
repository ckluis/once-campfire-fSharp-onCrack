# R3.2 measurement plan, fixed at 08:41 on 2026-10-09, before the second normal session ran

The first complete normal session (`upstream-normal-noisy/`, 08:24-08:38) ran while other work on the Mac (a Go build, Spotlight)
took host cores: every app's cells have wide ranges (C's room page 48,918-75,012, the port's 19,629-36,410, onCrack fresh
51,762-119,221). The VM's vCPUs are not pinned, so a busy host moves them to efficiency cores. The hand re-run between sessions
(`review-room.jsonl`, room page, 15 s warm-up, 10 s window, server CPU from the cgroup) was steady: onCrack fresh 134,170 and 129,470
req/s at 24.0 and 25.1 us of CPU per request, cached 169,145 at 18.8, Rust 45,835 at 62.1, C 68,622 at 48.1.

Rule for the headline, set now so no session can be chosen by its result:
- One more normal session runs after the mixed one, same images, seed, harness and settings (`upstream-normal-2/`).
- The normal-profile headline is the median of each cell over both sessions' six rounds (pooled). Neither session is dropped, and
  both are reported in full, with their own medians and ranges.
- The mixed profile is one session (`upstream-mixed/`), as asked.
- If the Mac goes under 12 GB free, the guard stops the session and whatever completed is reported as such.
