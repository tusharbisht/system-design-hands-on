# SPEC — design/03-tinyurl

A URL shortener. Same long URL → same short code (idempotent). Different long URLs → different short codes (no silent collisions). Short codes resolve via 302 redirect.

## Endpoints

### `POST /shorten`

```http
POST /shorten HTTP/1.1
Content-Type: application/json

{ "long_url": "https://example.com/some/long/path?with=query" }
```

→ `200` (idempotent) or `201` (newly created)

```json
{ "long_url": "https://example.com/some/long/path?with=query",
  "short_code": "aB3xY7", "short_url": "https://your-host/aB3xY7" }
```

Errors:
- `400` if `long_url` missing, empty, or not a valid http(s) URL.

With an optional **custom alias**:

```http
POST /shorten
{ "long_url": "https://my.example.com", "alias": "my-link" }
```

→ `201` `{ "long_url": "...", "short_code": "my-link", "short_url": "..." }`

If `alias` is already taken (and points to a *different* `long_url`):
→ `409` `{ "error": "alias 'my-link' is already taken" }`

If `alias` is taken AND points to the *same* `long_url`: idempotent `200`.

### `GET /{short_code}`

→ `302` with `Location: <long_url>`. The body is irrelevant (browsers follow the header). Most HTTP clients can be configured to either follow or not follow.

If `short_code` doesn't exist:
→ `404 {"error": "no such short code"}`

### `GET /api/expand/{short_code}`

A non-redirecting variant for programmatic access:

→ `200 { "short_code": "aB3xY7", "long_url": "https://...", "created_at": "2026-04-29T..." }`
→ `404` if not found

### `GET /health`

→ `200 {"ok": true}`

### `GET /stats`

→ `200 { "total_links": int, "total_redirects": int }` — used by the judge to verify scale.

## SLOs

```yaml
read_p95_ms: 100        # GET /<short_code>
write_p95_ms: 200       # POST /shorten
error_rate_pct: 0.5
sustained_rps: 200
```

## Correctness invariants

1. **Idempotent shortening**: `POST /shorten` with the same `long_url` (no alias) returns the SAME `short_code` every time, across processes and restarts (your storage choice must enforce this).
2. **No collisions**: 1,000 distinct `long_url` values must produce 1,000 distinct `short_code` values. The judge generates random URLs to test this.
3. **Custom alias precedence**: when an alias is supplied AND not taken, the server uses that alias (not its own generated code).
4. **Alias conflict detection**: a custom alias already mapped to a different long URL returns `409`, not `200` with a silent overwrite.
5. **Round-trip**: `POST /shorten {long_url: X}` → `GET /<short_code>` → 302 with `Location: X`.
6. **404 on missing code**: `GET /xyz123` (a code never created) returns 404 — NOT a redirect to a default page.
7. **Code shape**: short codes are at least 5 chars, URL-safe (alphanumeric + `-` + `_`), no spaces.
8. **Stats consistency**: `total_links` from `/stats` equals the number of distinct short codes in your store.

## Constraints

- **Storage engine**: any (in-memory / Redis / Postgres / SQLite / DynamoDB). For idempotency you'll likely want a `(long_url → short_code)` index — design accordingly.
- **Hash strategy**: any. base62 of an autoincrement counter, MD5 prefix, hand-chosen — your call. Just produce valid short codes.
- **Hosting**: any reachable URL.

## What you're being graded on

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, `/shorten` p95 < 200ms, `/<code>` p95 < 100ms |
| Idempotency | 25% | same long URL → same short code (5+ repeated calls verified) |
| Collision avoidance | 20% | 50 distinct URLs → 50 distinct codes |
| Round-trip + 302 | 20% | shorten then GET → 302 with right `Location` |
| Custom alias | 15% | alias used when free; 409 on conflict; idempotent on same URL |
| 404 on missing | 10% | unknown code returns 404, not a default redirect |
| Code shape + schema | 10% | codes are URL-safe, ≥ 5 chars; response fields match spec |

## Examples

See [`EXAMPLES.md`](EXAMPLES.md).

## Authoring tip

You will fail collision avoidance if your code generator is "first 5 chars of MD5" — at scale, MD5 prefixes collide. Either: (a) base62-encode a monotonic ID; (b) use a longer prefix; (c) check-and-retry on collision. The judge fires 50 distinct URLs — easily enough to surface a 5-char-MD5 collision.
