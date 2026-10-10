# onCrack R4.5 Reliability baseline

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
