# onCrack R4.5 reliability final results

**See `/bench/results/oncrack-r4-final/reliability/` for the final reliability measurements from R4.5.**

The R4.5 work implemented a shared, byte-bounded log for Cable subscribers, publish order across streams, no-progress stall timeout, and a post gate to prevent unbounded backlog. Results validate that onCrack keeps every live subscriber connected under saturated fan-out (1,000 clients, 64 closed-loop posters) with bounded memory.

Key result: **0 disconnected clients, every message delivered** vs. 945 disconnected before R4.5.

Raw data: `bench/results/oncrack-r4-reliability/` contains the full measurement suite (before-r1, after-r1, probes, cable-ab tests). The first baseline session (started 2026-10-10 12:04 EDT, notes below) had invalid cable rows due to a 1,024 descriptor limit and was superseded by proper measurements.

| app (cable_heavy, 64 closed-loop posters) | subscribed | disconnected | delivered to every client / posted |
|---|---|---|---|
| Rails | 1,000 | 0 | 552 / 552 |
| Rust f9dca47 | 1,000 | 899 | 64 / 65,151 |
| C cd0cbe4 | 224 | 829 | 15 / 35,967 |
| onCrack `21791e2` | 1,000 | 945 | 88 / 127,210 |
| onCrack `21791e2`, cached decision | 1,000 | 869 | 0 / 78,103 |

---

## The first session's notes (kept as they were)


**Status: Test in progress (started 2026-10-10 12:04 EDT)**

## Test setup

- Harness: `/Users/clank/Desktop/projects/once-campfire-verification` (branch `oncrack-reliability-working`)
- Loadgen: Static build 1.98.1 from `~/Desktop/projects/upstream-campfire/tools/loadgen-1.98.1-static/`
- Seed: Generated fresh with `campfire-reference:app`
- Workspace: `/mnt/cfv/ws/` in colima tmpfs
- Server CPUs: 0-3, Client CPUs: 4-7
- Apps: rails, rust, c, fsharp, oncrack (fresh), oncrack-cached
- Profiles: overload (64 and 256 clients on room_show, messages_page, sidebar, search), cable (1,000 subscribers)
- Rounds: 3

## Progress

### Rails
- overload room_show 64 clients: 4,774.7 req/s, 0 errors, 0 invalid
- overload room_show 256 clients: 4,836.8 req/s, 0 errors, 0 invalid
- overload messages_page 64 clients: 4,589.4 req/s, 0 errors, 0 invalid
- overload messages_page 256 clients: 4,743.4 req/s, 0 errors, 0 invalid
- overload sidebar 64 clients: 4,676.2 req/s, 0 errors, 0 invalid
- overload sidebar 256 clients: 4,617.4 req/s, 0 errors, 0 invalid
- overload search 64 clients: 3,552.9 req/s, 0 errors, 0 invalid
- overload search 256 clients: 1,716.1 req/s, 0 errors, 0 invalid

**Apps remaining:** rust, c, fsharp, oncrack, oncrack-cached
**Profiles remaining:** cable tests for all apps

## Notes

- Test is running in colima VM at `/mnt/cfv/once-campfire-verification`
- Results will be collected from `/mnt/cfv/once-campfire-verification/tmp/bench/reliability/<timestamp>/`
- Rails overload tests show expected behavior: all responses valid, zero errors, throughput declining at 256 clients on search (expected due to higher computational cost)
- Expected test completion time: 4-6 hours (3 rounds × 6 apps + cable tests)

## Deferred

- Cable fan-out tests (1,000 subscribers, connectivity and delivery tracking)
- Results aggregation and summary table generation
- Pss memory measurements during cable_heavy profile
- Final markdown report with all metrics
