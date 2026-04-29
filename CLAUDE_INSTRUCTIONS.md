# Solving Design 04 with Claude Code — faster and better

The trap: this looks like a CRUD exercise but isn't. Skip the concurrency thinking and the 35%-weighted race test eats you.

## Recommended workflow

### 1. Write the contract test FIRST, in your own terms

> "Read SPEC.md and grading/design-04-booking-concurrency/rubric.md. Without writing code yet, write `probe.py` (using httpx + asyncio) that exercises every test type the judge will run. The probe should fire 20 concurrent POSTs to the same slot and assert {201: 1, 409: 19}."

Run the probe against an empty FastAPI shell that returns hardcoded fixtures. You'll see your probe is correct. Then implement the service to make the probe pass.

### 2. Pick the locking strategy in plan mode

> "Plan the concurrency design. Compare:
> (a) Python-level lock (asyncio.Lock or threading.Lock)
> (b) Database UNIQUE constraint + INSERT … RETURNING / ON CONFLICT
> (c) Redis SET NX
>
> For each: how does it survive multi-worker processes? How does it survive a restart? Recommend ONE for this exercise."

The right answer for this exercise is (b). It's correct under any worker model, survives restarts, and is ~10 lines of code. (a) breaks the moment uvicorn runs more than one worker. (c) requires another service.

### 3. Implement with the database as the lock

> "Use SQLite with `UNIQUE(slot_id)` on the bookings table. On POST: try INSERT, catch IntegrityError, on conflict fetch the existing booking and return 409 with `booking_id_existing`. Don't add an `is_booked` column to slots — derive it via LEFT JOIN at GET /slots time."

Single source of truth. No phantom states. Show the diff before applying.

### 4. Probe yourself with the 20-way concurrent test

```python
# Add to probe.py
async def race_test(c):
    await c.post("/reset", json={"slots": [{"slot_id": "race", "label": "T"}]})
    coros = [c.post("/bookings", json={"slot_id": "race", "user_id": f"u{i}"}) for i in range(20)]
    rs = await asyncio.gather(*coros)
    by_status = {}
    for r in rs:
        by_status[r.status_code] = by_status.get(r.status_code, 0) + 1
    print(f"  race result: {by_status}")
    assert by_status.get(201, 0) == 1, f"expected 1 201, got {by_status}"
    assert by_status.get(409, 0) == 19, f"expected 19 409, got {by_status}"
```

If this prints `{201: 1, 409: 19}` you're done with the hard part.

If it prints `{201: 4, 409: 16}` your "lock" isn't atomic. Go back to step 3.

### 5. Probe cancel + re-book

```python
await c.post("/reset", json={"slots": [{"slot_id": "x", "label": "X"}]})
r1 = await c.post("/bookings", json={"slot_id": "x", "user_id": "alice"})
bid = r1.json()["booking_id"]
r2 = await c.delete(f"/bookings/{bid}?user_id=alice")
assert r2.status_code == 204
r3 = await c.post("/bookings", json={"slot_id": "x", "user_id": "bob"})
assert r3.status_code == 201
```

### 6. Probe owner-only DELETE

```python
r1 = await c.post("/bookings", json={"slot_id": "x2", "user_id": "alice"})
bid = r1.json()["booking_id"]
r_wrong = await c.delete(f"/bookings/{bid}?user_id=mallory")
assert r_wrong.status_code in (409, 403), f"expected 409/403 from wrong user, got {r_wrong.status_code}"
r_right = await c.delete(f"/bookings/{bid}?user_id=alice")
assert r_right.status_code == 204
```

### 7. Submit, read the critique

The critique tells you exactly which axis lost points. Common first failures:

- **race-condition test fails**: your service double-booked. Fix the locking (see Hint 1 in EXERCISE.md).
- **owner-only-DELETE fails**: you let any user delete. Add the user_id check.
- **schema-state-consistency fails**: your `is_booked` flag drifted. Derive instead of store.

## Claude Code techniques that pay off here

| Technique | Why it matters |
| --- | --- |
| **Probe-first development** | concurrency bugs are invisible without a real concurrent probe |
| **Plan mode for locking strategy** | three legitimate choices — pick before writing code |
| **Database as the lock** | single best practice; fights everything else you might try |
| **Derive `is_booked` from JOIN, don't store** | eliminates a second source of truth that can drift |
| **Run probe.py 5x in a row** | concurrency bugs sometimes pass once and fail later |

## What NOT to do

- **Don't use asyncio.Lock.** Single-process. Loses to multi-worker uvicorn (which is the deployment default).
- **Don't store `is_booked` on the slot row.** Derive it. You'll thank yourself when you later add cancellation.
- **Don't 500 on a duplicate.** Catch the IntegrityError, return 409 with the existing booking_id. The judge cross-checks.
- **Don't pre-seed inventory in your code.** The judge calls `POST /reset` at the start of every scenario; respect the inventory it gives you.
- **Don't do a "check then insert" without the unique constraint.** That's the canonical TOCTOU bug. Always rely on the DB-level uniqueness.

## When you're stuck

> "The race-test got {201: 3, 409: 17} — I'm double-booking 3 times out of 20. Show me my POST /bookings handler. Walk through what happens when two requests arrive in the same async tick. Is the uniqueness check inside a single SQL statement, or split across two?"

(Common cause: you're checking `SELECT … FROM bookings WHERE slot_id=?` and then `INSERT INTO bookings …` as two statements. Replace with one `INSERT … ON CONFLICT (slot_id) DO NOTHING RETURNING …` or with a single `INSERT` whose IntegrityError you catch.)

## After this exercise

Race-condition handling under real concurrent load is the most production-relevant skill on this whole course. Carry the pattern forward: the same DB-level constraint trick handles "one user one wishlist", "one device one fcm-token", "one cart per session" and every other invariant your future production system will have.
