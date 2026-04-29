# EXAMPLES — design/04-booking-concurrency

## E1 — reset inventory

```http
POST /reset
{ "slots": [
    {"slot_id": "s1", "label": "9 AM yoga"},
    {"slot_id": "s2", "label": "10 AM yoga"}
  ]
}
```

→ `204` (no body)

## E2 — list slots after reset

```http
GET /slots
```

→ `200`

```json
{ "slots": [
    {"slot_id": "s1", "label": "9 AM yoga", "is_booked": false},
    {"slot_id": "s2", "label": "10 AM yoga", "is_booked": false}
  ]
}
```

## E3 — successful booking

```http
POST /bookings
{ "slot_id": "s1", "user_id": "alice" }
```

→ `201`

```json
{ "booking_id": "b_a1b2c3", "slot_id": "s1", "user_id": "alice", "created_at": "..." }
```

## E4 — same slot, different user → 409

```http
POST /bookings
{ "slot_id": "s1", "user_id": "bob" }
```

→ `409`

```json
{ "error": "slot 's1' is already booked", "booking_id_existing": "b_a1b2c3" }
```

## E5 — race scenario (the heart of the test)

20 simultaneous calls:

```http
POST /bookings { "slot_id": "s2", "user_id": "user_<i>" }    # i = 0..19
```

Expected aggregate: **exactly 1** response with `201`, **19** with `409`. Total `2xx + 4xx == 20`. NEVER 2 successes.

## E6 — cancel + re-book

```http
DELETE /bookings/b_a1b2c3       # alice cancels
```

→ `204`. Then `GET /slots` shows `s1.is_booked == false`.

```http
POST /bookings { "slot_id": "s1", "user_id": "carol" }
```

→ `201` (slot is free again).

## E7 — cancellation by wrong user

```http
DELETE /bookings/b_a1b2c3
# (sent by user 'bob' who didn't create this booking)
```

If your design has any user-identity mechanism (header, body field, query param), bob's DELETE → `409` (or `403`). Alice's DELETE → `204`.

(For v1 the simplest design: pass `?user_id=alice` as a query param on DELETE; the server compares.)

## E8 — book a non-existent slot

```http
POST /bookings { "slot_id": "ghost", "user_id": "alice" }
```

→ `404 { "error": "slot 'ghost' does not exist" }`

## E9 — health

```http
GET /health
```

→ `200 {"ok": true}`
