# R4 Final Reliability Results

These are the cable reliability measurements from R4.5, validating that onCrack keeps every live Cable subscriber with bounded memory through a shared, byte-bounded log.

## Cable Heavy (1,000 clients, 64 closed-loop posters, 60 s drain limit)

### Results

| app | subscribed | disconnected | delivered to all / posted | messages/s | p99 post to last client | Pss peak |
|---|---|---|---|---|---|---|
| Rails 0aa339d | 1,000 | 0 | 552 / 552 | 21.7 | 24,084 ms | 3,136 MB |
| Rust f9dca47 | 1,000 | 899 | 64 / 65,151 | 4.3 | 357 ms | 127 MB |
| C cd0cbe4 | 224 | 829 | 15 / 35,967 | 1.0 | 39 ms | 73 MB |
| **onCrack (after R4.5)** | **1,000 / 1,000** | **0 / 0** | **10,638 / 10,638; 10,521 / 10,521** | **574.1, 566.8** | **11,248, 12,165 ms** | **906, 963 MB** |
| onCrack, cached decision | 1,000 / 1,000 | 0 / 0 | 11,689 / 11,689; 12,520 / 12,520 | 633.2, 670.6 | 10,584, 10,387 ms | 966, 967 MB |

**Before R4.5:** onCrack disconnected 945 clients (88 delivered of 127,210 posted) due to the 256-frame fixed ring.

### Key Changes

1. **Shared, byte-bounded log** replaces the fixed 256-frame ring: chunks of 256 frames, subscribers as cursors, memory bounded at 256 MB per group, GC frees unused chunks.

2. **Publish order across streams:** hub-wide frame sequence prevents one deep stream from starving others on a connection.

3. **No-progress stall timeout:** connections cut only when truly stalled (no acknowledged bytes for 30 s), not from one slow write; a slow reader stays connected.

4. **Post gate:** `MessagesController#create` waits briefly when most subscribers are seconds behind, preventing unbounded backlog accumulation.

## Overload Profile

Both overload and cable profiles passed validation with 0 errors and 0 invalid responses at 64 and 256 clients.

## Data Locations

- `before-r1/`: Rails, Rust, C, onCrack at commit 21791e2 (cable profile, one round)
- `after-r1/`: onCrack HEAD (cable and overload profiles, 2 rounds)
- Full probe measurements and cable A/B variants in `../oncrack-r4-reliability/`

## Conclusion

The R4.5 changes successfully eliminate client disconnects under saturated fan-out (1,000 clients, 64 posters) while keeping memory bounded and delivering every posted message to every connected client.

