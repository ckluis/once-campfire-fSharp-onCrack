# R4.0: the A7 failure was the test browser's cookie jar, not the app

Round 3 left one unexplained failure of the verifier's A7 attack test (a valid seeded session cookie answered 302 to `/session/new`, once in 18 full runs). Cause found and fixed; the app was right.

## What was done

1. **Diagnostics kept** (`bench/results/oncrack-verifier/AttackTests.fs`, `src/Campfire.App/Concerns.fs`). A7 now checks its warm-up request too, and on a failing round prints the app's captured log (`CapturingLoggers`), the database's view (session rows, the vector's session by token, David's row), the warm response's `Set-Cookie` names and the jar's `session_token`. `A7_SABOTAGE=1` deletes the sessions in round 2 to prove the printing works; `A7_ROUNDS=N` sets the round count (30). `restoreAuthentication` logs at Debug, only when a request that carried a `session_token` cookie ends up signed out: "did not verify" or "verified but names no session" (cold path, no cost on a signed-in request).
2. **Reproduced** at the default (JIT, fresh authorization) by looping A7 alone with 250 rounds a run, the harness built once: 2 failing runs in 12 (3,000 rounds), then none in 14 more runs (3,500 rounds, host busy). Both failures: warm request 200, then `first` and `second` 302 to sign-in. The app log held nothing about authentication: no "did not verify", no "names no session". The sabotage run prints both lines, so the log was live: those requests reached the app **without a `session_token` cookie**. The sessions table and David's row were intact.
3. **Cause.** The warm request is 200 and re-signs the session cookie (a seeded session is older than the hourly activity refresh). `Browser.AbsorbSetCookies` in `tests/Campfire.App.Tests/Support.fs` dropped any cookie when the lower-cased `Set-Cookie` header contained the substring `1970` anywhere (meant for `expires=Thu, 01 Jan 1970`). The signed cookie ends in a 40-hex-digit SHA1 digest; it holds those four digits about 37/16^4, one in 1,800 signatures. The jar then removed the freshly issued cookie and the next request went out signed out. That rate matches what was seen (2 in 6,500 rounds here, 1 in 540 in round 3). The app never saw the cookie; nothing about sessions, caches, `Versions.Sync`, `FreshAuth` or the connections was involved. The fronted suite and production are unaffected (a real browser reads `Expires`).
4. **Fix** (test support only). `Support.setCookieDeletes` reads the attributes: an empty value, `Max-Age` of zero or less, or an `Expires` already past. `CookieJarTests` (3 tests): a real `Cookies.sign` cookie whose header contains `1970` stays (found by stepping the expiry's milliseconds; it takes a few thousand signatures); the deleting forms leave; live cookies stay. With the old substring rule put back, 2 of the 3 fail.

## After

| Check | Result |
|---|---|
| A7 alone, fixed jar, default mode | 28 runs x 250 rounds = 7,000 rounds, 0 failures (unfixed: 2 in 6,500) |
| Full attack suite (11 tests), fresh mode | 11 of 11 |
| `bin/verify App` (251 tests, 1 skipped on macOS) | 250 passed |

Seven thousand clean rounds at a failure rate of about 1 in 1,800 would be a 2% accident without the fix; together with the mechanism and the unit test this closes it. Not run: the CPU-saturated and cached-mode loops (the cause is not timing-dependent, so they would not tell more), and the 302 on the first run after a compile (the failure never depended on it).

Files: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-a7/failure-1.log` and `failure-2.log` (the two captured failures, before the extra warm-cookie lines were added to the diagnostics).
