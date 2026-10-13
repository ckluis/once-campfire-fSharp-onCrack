# once-campfire-fSharp-onCrack

Status: started 2026-10-07. Branch `crack`, forked from the published F# port (`0ae3436`, PR
ckluis/once-campfire-fSharp#1).

## The brief (Chris)

"Make the UI exactly the same, but go unhinged with Datastar, caching, or any other improvements we can
do to completely shift this into the stratosphere." The F# port matched the Rust port's work per
request and beat it 1.22-1.40x. onCrack drops that constraint.

## Rules

1. **The UI is identical.** Every parity screen's pixels must match Rails' (the harness's screenshot
   layer, lean matrix, all seeds), and every interaction behaves the same for a person using it. Server
   HTML, the live DOM, network requests and Cable frames may differ.
2. **Correct, always.** No stale reads after a write, no data from one user in another's response, no
   lost messages. Every cache states its invalidation rule and has tests that try to break it
   (concurrent writers, two users with different memberships, bans, deletes, edits).
3. **Durability is a disclosed choice.** Anything that weakens durability (group commit windows,
   `synchronous=NORMAL`) is measured both ways, documented, and shipped only behind a setting whose
   default is Rails-equivalent durability.
4. **Scored separately.** Same harness (`bench/run`, `bench/quick`), same seed and pinned CPUs. Every
   ratio is stated against the Rust port and against the F# port (`bench/results/phase7-final/`), and
   never presented as a like-for-like port result. The image is `campfire-oncrack:app`
   (`FSHARP_IMAGE=campfire-oncrack:app` for `bench/run` and `bench/quick`), so the port's image stays
   available for comparison.
5. **Same discipline:** measure before and after, one change at a time, log every run to the climb
   chart, never manufacture a win.

## Ideas, by expected gain on the five workloads

| Idea | Workloads | Expected | Risk |
|---|---|---|---|
| Versioned read cache: per-room and per-user version counters bumped inside write transactions; cache finished page parts and whole responses keyed by the versions they depend on, so an unchanged room serves without SQL | room, messages, sidebar, search | 2-5x on reads | stale or leaked data; memory |
| Group commit for posts: coalesce concurrent posts into one transaction and one fsync; precompute the post response and broadcast | post | 2-4x on posts at c=16 | durability window (rule 3) |
| Search: cached result pages per (query, version); FTS tuning | search | 2x+ | invalidation on edits and deletes |
| Native AOT, trimming, smaller heaps | cold start, memory, c=1 | 3-10x cold start, 2-4x memory | reflection in dependencies |
| Lighter HTTP: preassembled header blocks, fewer syscalls per response, response bodies from pinned buffers | all | 5-15% | Kestrel internals |
| Datastar frontend: SSE patches instead of Turbo and Action Cable; much less JS; cheaper fan-out | Cable fan-out, browser | large for fan-out | pixel parity of every interaction |
