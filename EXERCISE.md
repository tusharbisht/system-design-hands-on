# Design 04 — Booking website: concurrency matters

**Type:** system-design — build, host, submit a URL
**Estimated time:** 6–8h with Claude Code
**Auto-graded:** at-most-one-booking-per-slot under concurrent load + cancellation/re-book + owner-only DELETE + schema/state consistency

## The problem

Inventory of bookable slots. 50 users hit "book this 9 AM class" within milliseconds of each other. Exactly one wins. The other 49 get a clean 409. **No silent double-bookings, ever.**

This is the canonical concurrency design problem in disguise. The whiteboard answer is "use a transaction" or "use Redis SETNX". Easy to say. The judge fires 20 concurrent `POST /bookings` calls at the same slot from your hosted URL and counts the `201`s. You lose 35% of the grade if more than one of those returns `201`.

## What you're building

`POST /reset`, `GET /slots`, `POST /bookings`, `DELETE /bookings/{id}`, `GET /bookings/{id}`, `GET /health`. Full contract in [`SPEC.md`](SPEC.md). Sample requests in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

- `/health` is reachable
- `POST /reset` puts the inventory into a known state every time
- 20 concurrent `POST /bookings` to the same slot return exactly **1** `201` and **19** `409`s
- After a `DELETE /bookings/<id>`, the slot is re-bookable
- A user other than the booking creator gets `409` (or `403`) on `DELETE`
- `GET /slots` shows `is_booked: true/false` consistent with the real booking state at all times
- All 4xx responses include a useful `error` message; no 500s under any tested input

Pass: ≥60% weighted. Strong pass: ≥80% with the race-condition test scoring 10/10 (no double-bookings on the 20-way concurrent probe).

## Why this is the most production-shaped exercise in the course

Most "build a booking system" tutorials skip concurrency. You can build a service that passes manual testing and double-books the moment two users click at once. The judge here makes the concurrency test the dominant axis (35% weight) precisely because that's what breaks in production.

The test is real concurrency: 20 simultaneous HTTP POSTs from the judge's process. If your "lock" is a Python global flag, you'll fail. If your "uniqueness check" is `if slot.is_booked: return 409 / else: slot.is_booked = True; create_booking()` in two non-atomic statements, you'll fail. The only reliable answer is to push the conflict resolution to a layer that *enforces atomicity for you*: a unique constraint on a database column, a Redis `SET NX`, a single-writer queue.

## Constraints

- Any language/framework
- Any storage (SQLite + `UNIQUE(slot_id)` is enough; Postgres with `ON CONFLICT` is cleaner; Redis SETNX is also valid)
- Any concurrency model (single-threaded async is fine if your DB enforces uniqueness)
- The judge `POST /reset` at the start of each scenario; don't accumulate state across tests
- The judge generates the inventory contents — don't pre-seed; respect what /reset says

## Hints

<details><summary>Hint 1 — let the database be the lock</summary>

Don't write your own. Don't use a Python `Lock` (won't survive across processes). Don't use file locks (slow + brittle).

Postgres / SQLite / MySQL all have a `UNIQUE` constraint primitive. Create a `bookings` table with `UNIQUE(slot_id)`. The DB will reject the second insert atomically. Wrap the insert in try/except; on `IntegrityError`/`UniqueViolation` return 409.

```python
# Postgres / asyncpg
try:
    rec = await conn.fetchrow("""
      INSERT INTO bookings (slot_id, user_id, booking_id, created_at)
      VALUES ($1, $2, $3, NOW())
      RETURNING booking_id
    """, slot_id, user_id, booking_id)
    return {"booking_id": rec["booking_id"], ...}, 201
except asyncpg.UniqueViolationError:
    existing = await conn.fetchrow("SELECT booking_id FROM bookings WHERE slot_id=$1", slot_id)
    return {"error": ..., "booking_id_existing": existing["booking_id"]}, 409
```

That's the whole locking story. ~10 lines.

</details>

<details><summary>Hint 2 — `is_booked` is a derived field; don't store it</summary>

Don't add a column `slots.is_booked` and try to keep it in sync with the bookings table. That introduces a second source of truth and a window where they disagree.

Instead: `GET /slots` joins slots LEFT JOIN bookings, deriving `is_booked = (bookings.slot_id IS NOT NULL)`. One source of truth: the bookings table.

</details>

<details><summary>Hint 3 — owner-only DELETE wants identity</summary>

The simplest design: take `?user_id=...` on the DELETE URL, compare to `bookings.user_id`. Match → 204. Mismatch → 409.

(In a real system you'd authenticate and use a session; for this exercise, query-param identity is acceptable.)

The judge does test this — it'll DELETE with the wrong user and expect 409.

</details>

<details><summary>Hint 4 — concurrent test debugging</summary>

If your service double-books, run a local probe FIRST with httpx + asyncio:

```python
import asyncio, httpx
URL = "http://localhost:8000"

async def main():
    async with httpx.AsyncClient(base_url=URL) as c:
        await c.post("/reset", json={"slots":[{"slot_id":"x","label":"X"}]})
        async def attempt(i):
            return await c.post("/bookings", json={"slot_id":"x","user_id":f"u{i}"})
        responses = await asyncio.gather(*[attempt(i) for i in range(20)])
        codes = [r.status_code for r in responses]
        print("status counts:", {c: codes.count(c) for c in set(codes)})

asyncio.run(main())
```

You want exactly: `{201: 1, 409: 19}`. If you see `{201: 17, 409: 3}` you have a TOCTOU bug.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-04-booking-concurrency/](grading/design-04-booking-concurrency/)
