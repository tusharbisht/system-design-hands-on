# Rubric — design/04-booking-concurrency

The 35%-weighted axis is the concurrent race-condition test. A submission that nails everything else but fails that one is a fail. Conversely, a submission that handles concurrency but is sloppy on edge-case error codes can still pass.

## Test types

### `smoke`

Schema/HTTP correctness — fields present, types right, status code matches. Score 10 on full match; 0 on schema violation; -2 per missing field.

### `booking_basic` / `booking_conflict`

Sequential POST scenarios. Score against the explicit `step_N_status` in the test instructions.

| Outcome | Score |
| --- | --- |
| Status matches; body has all required fields | **10** |
| Status matches but body missing field | 7 |
| Status off by one (e.g., 200 instead of 201 on a fresh booking) | 6 |
| Status code wrong but operation succeeded | 4 |
| 5xx | **0** |

For `booking_conflict`: the second POST MUST return 409. A 200 (silent overwrite) is **0 — this is a double-booking bug**.

### `concurrency` — the heart of the exercise

The judge fires `concurrency` POSTs concurrently to the same `slot_id`. Aggregates status codes.

| Outcome | Score |
| --- | --- |
| Exactly 1 × 201 and N-1 × 409 (perfect — no double-bookings) | **10** |
| 1 × 201 and N-1 × 409 with 0 5xx errors but slow (>1s p95) | 9 |
| 2-3 × 201 (some double-bookings) | 3 |
| ≥ 4 × 201 (race condition is wide open) | **0** |
| Service errored on > 20% of concurrent calls | 0 |
| All 200/409 returned but no booking actually persisted | 1 |

Critique should report the actual status counts, e.g., `{201: 3, 409: 17, 500: 0}` — and name the likely cause (TOCTOU race in handler, in-process lock that doesn't span workers, etc.).

### `lifecycle`

Multi-step sequences (book → cancel → rebook). Score 10 only when EVERY step succeeds with the right status. Partial credit (5–8) for "first 2 of 3 steps work".

### `permission`

Owner-only DELETE. The judge does the wrong-user DELETE first, then the right-user DELETE.

| Outcome | Score |
| --- | --- |
| Wrong-user gets 409/403 AND right-user gets 204 | **10** |
| Wrong-user gets 200/204 (anyone can cancel — security bug) | **0** |
| Both get 204 | 0 |
| Wrong-user gets 500 instead of 409 | 4 |

### `consistency`

Cross-endpoint state coherence:

- `is-booked-consistency`: `GET /slots` flags match the real bookings table.
- `no-phantom-on-409`: a 409 response must not create a record. `GET /bookings/<id>` for any bogus id from the failed POST returns 404.

Score 10 if both endpoints agree; 0 if they don't.

### `latency`

p95 across all calls. SLO 100ms read, 200ms write.

| Outcome | Score |
| --- | --- |
| Under SLO | **10** |
| 1.5× SLO | 6 |
| 3× SLO or > 5% timeouts | **0** |

## Pre-flight gate

`GET /health` 200 within 10s. Total score 0 if not reachable.

## Overall scoring

Weighted percent. Pass: ≥60%.

The race-condition test alone is 5.0 weight (out of ~22 total). Failing it (score 0) drops the maximum achievable to ~77%. So a learner who completely whiffs concurrency CAN still pass if they nail every other axis perfectly — but they're at the edge. This matches reality: a system that double-books occasionally but handles every other case is broken in production but might pass a code review.

## Strictness notes

- **Quote the actual status counts** on concurrency tests. "Got {201: 1, 409: 19} → perfect" or "{201: 4, 409: 16} → 4 double-bookings".
- **Quote booking_id values** when checking `no-phantom-on-409`. "After 409 from bob's attempt, GET /bookings/b_X returned 404 → no phantom record ✓".
- **Be specific on permission failures.** "DELETE /bookings/<id>?user_id=mallory returned 204 — anyone can cancel anyone's booking, security bug".
- **Be lenient on 200 vs 201** unless the spec explicitly demanded one. But be strict on 200 vs 409 — those mean very different things.
