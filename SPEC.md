# SPEC — design/04-booking-concurrency

A reservation service. Pre-seeded inventory of bookable slots (rooms, classes, anything fixed). When two users race for the same slot, **exactly one wins**, the loser gets a clean 409. No silent double-bookings. No lost confirmations.

## Endpoints

### `POST /reset`

Reset the inventory. The judge calls this at the start of a probe to put your service into a known state.

```http
POST /reset HTTP/1.1
Content-Type: application/json

{ "slots": [
    {"slot_id": "s1", "label": "9 AM yoga - room A"},
    {"slot_id": "s2", "label": "10 AM yoga - room A"},
    {"slot_id": "s3", "label": "11 AM yoga - room A"}
  ]
}
```

→ `204` (no body). Drops all existing bookings; re-creates the inventory with the supplied list.

### `GET /slots`

```http
GET /slots
```

→ `200`

```json
{
  "slots": [
    {"slot_id": "s1", "label": "9 AM yoga - room A", "is_booked": false},
    {"slot_id": "s2", "label": "10 AM yoga - room A", "is_booked": true},
    {"slot_id": "s3", "label": "11 AM yoga - room A", "is_booked": false}
  ]
}
```

### `POST /bookings`

```http
POST /bookings
{ "slot_id": "s1", "user_id": "alice" }
```

→ `201` (newly booked)

```json
{
  "booking_id": "b_aB3xY7",
  "slot_id": "s1",
  "user_id": "alice",
  "created_at": "2026-04-29T08:00:00Z"
}
```

If the slot is already booked (by anyone, including the same user):
→ `409 { "error": "slot 's1' is already booked", "booking_id_existing": "b_..." }`

If `slot_id` doesn't exist:
→ `404`

If `slot_id` or `user_id` missing/empty:
→ `400`

### `DELETE /bookings/{booking_id}`

Cancel a booking. The slot becomes available again.

→ `204` on success
→ `404` if no such booking
→ `409` if booking exists but was created by a different user (only the owner can cancel)

### `GET /bookings/{booking_id}`

→ `200` with the booking record, or `404`.

### `GET /health` → `200 {"ok": true}`

## SLOs

```yaml
read_p95_ms: 100
write_p95_ms: 200
error_rate_pct: 0.5
sustained_rps: 100
concurrent_clients: 50      # this matters here — see correctness invariants
```

## Correctness invariants — the heart of this exercise

1. **At most one booking per slot.** Even under concurrent load. If 50 clients race to `POST /bookings {slot_id: "s1", ...}`, exactly ONE returns `201`. The other 49 return `409`. NEVER two `201`s for the same slot.
2. **Conflict response is honest.** When a 409 is returned, the slot really IS booked (the racing winner). Subsequent `GET /slots` confirms `is_booked: true` for that slot.
3. **Cancellation re-opens the slot.** `DELETE /bookings/<id>` followed by `POST /bookings {slot_id: same}` works (returns 201).
4. **Owner-only cancellation.** `DELETE /bookings/<id>` from a user other than the booking creator returns `409`, not `204`. (The judge tests this.)
5. **Idempotent reset.** `POST /reset` always succeeds and replaces inventory.
6. **No phantom bookings.** A 409 doesn't create a record (no half-states; the judge cross-checks `GET /bookings/<id>` for any booking_id in error responses).
7. **`is_booked` reflects truth.** The `is_booked: true/false` field on `GET /slots` is *always consistent* with the actual booking state. No stale flags.

## What you're being graded on

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, latencies under SLO |
| Single-booking correctness | 20% | `POST /bookings` 201; second POST same slot → 409 |
| Race-condition (concurrent) | 35% | 20 concurrent POSTs to same slot → exactly one 201 |
| Cancellation + re-book | 15% | DELETE → slot re-bookable |
| Owner-only DELETE | 15% | other-user DELETE → 409, not 204 |
| Schema + state consistency | 15% | `is_booked` matches actual state; no orphans |

## Constraints

- Any storage. SQLite/Postgres with proper transactions is the obvious path; a `UNIQUE` constraint on `(slot_id)` of the bookings table is the cleanest enforcement.
- Any concurrency model. Single-process async, threadpool, multi-worker — your call. **The graded behaviour is correctness under concurrent inputs**, not speed.
- The judge calls `POST /reset` at the start of every test scenario. So your service can't accumulate state across tests.

## Authoring tips

The two failure modes most submissions hit:

1. **Read-modify-write races.** "Check if slot is free → if yes, insert booking" performed in two SQL statements (or two Python lines) is a TOCTOU race. Two threads both pass the check; both insert. Two `201`s for the same slot. Mitigate with a `UNIQUE` index on `slot_id` + `INSERT … ON CONFLICT` (Postgres) or `INSERT OR FAIL` + try/except (SQLite). Use the database as the lock.
2. **Phantom bookings on 409.** Some implementations create a partial record (e.g., `INSERT booking; check uniqueness; if fail, leave booking in DB`). The judge cross-checks any `booking_id_existing` against `GET /bookings/<id>` to catch this.

See [`EXAMPLES.md`](EXAMPLES.md) for sample request/response pairs.
