# Solving Design 03 with Claude Code — faster and better

The trap on TinyURL is *over-engineering*. The judge won't see your sharding strategy. Optimize for getting the contract right; ship; iterate.

## Recommended workflow

### 1. Read the SPEC + EXAMPLES + rubric.md before any code

> "Read SPEC.md, EXAMPLES.md, and grading/design-03-tinyurl/rubric.md. Tell me the 7 axes the judge scores. For each, list one specific bug that would lose points."

The rubric is the spec. The judge runs against it. If your mental model of the rubric isn't crisp, you'll over-build the wrong thing.

### 2. Pick the storage model in plan mode (Shift+Tab)

> "Plan storage. Compare three options for me: (a) in-memory dict + persistence on shutdown, (b) SQLite with two indexes (one per direction), (c) Postgres with `ON CONFLICT (long_url) DO NOTHING`. Recommend ONE for this exercise's scale (<1M links). Justify."

Option (a) wins for shipping fast. SQLite (b) wins if you want a 50-line implementation that survives restarts. Postgres (c) is overkill for the rubric.

### 3. Implement idempotency BEFORE collision-avoidance

> "Implement `POST /shorten` with idempotency. Storage: `Dict[long_url, short_code]` and `Dict[short_code, record]`. On POST: lookup by long_url; if hit, return existing; otherwise generate base62-of-counter code, insert both ways atomically, return. NO custom alias yet — just plain idempotency. Show me the diff before applying."

Get this single behavior right with a probe before adding aliases.

### 4. Probe yourself

```python
# probe.py
import httpx, random, string
URL = "http://localhost:8000"

# Idempotency: same URL → same code
for _ in range(5):
    r = httpx.post(f"{URL}/shorten", json={"long_url": "https://wiki.org/X"})
    print(" idempotent:", r.json()["short_code"])
# All 5 should print the same code.

# Collisions: 50 distinct URLs → 50 distinct codes
codes = set()
for _ in range(50):
    u = f"https://example.com/{''.join(random.choices(string.ascii_lowercase, k=20))}"
    r = httpx.post(f"{URL}/shorten", json={"long_url": u})
    codes.add(r.json()["short_code"])
print(" distinct:", len(codes), "(should be 50)")

# Round-trip
r = httpx.post(f"{URL}/shorten", json={"long_url": "https://wiki.org/RT"})
code = r.json()["short_code"]
r = httpx.get(f"{URL}/{code}", follow_redirects=False)
assert r.status_code == 302 and r.headers["location"] == "https://wiki.org/RT"
print(" round-trip ok")
```

If any of those don't hold locally, the judge will fail you. Fix here, not after submitting.

### 5. Add custom aliases

> "Now add the optional `alias` parameter. The three cases:
> - alias not in store → use it, 201
> - alias in store mapping to SAME long_url → idempotent 200
> - alias in store mapping to DIFFERENT long_url → 409
>
> Do NOT silently overwrite. Show the diff."

Probe each of the three cases before submitting.

### 6. Add the catch-all redirect

> "Add `GET /<short_code>` returning 302. Order routes so /shorten, /health, /stats, /api/expand/* are exact matches; the catch-all is the LAST route. For 404 on missing codes, return 404 with `{error: ...}` — NOT a redirect to a default page."

Test:

```bash
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" -L http://localhost:8000/aB3xY7
# expect: 200 https://wiki.org/X (after the redirect)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/zzzzz
# expect: 404
```

### 7. Submit and read the judge critique

The first submission is information-gathering. Read the per-test reasoning. Common first-time failures:

- **collision-01 fails**: your code generator collides under load. Switch to base62-counter or wider hash.
- **alias-conflict fails**: you returned 200 (overwrote) instead of 409.
- **roundtrip fails**: you returned 200/301 instead of 302, or `Location` header missing.
- **404-missing fails**: you redirected to `/` instead of returning 404.

## Claude Code techniques that pay off here

| Technique | Why it matters |
| --- | --- |
| **Read rubric.md before coding** | the judge cares about specific axes; over-engineering wastes time |
| **Plan storage in plan mode** | three reasonable choices; pick before writing 30 lines |
| **Idempotency probe first** | 80% of first-time failures are idempotency. Probe locally. |
| **Route ORDER matters** | catch-all `GET /<code>` must come LAST or it shadows other GETs |
| **`follow_redirects=False`** in your probe | you want to verify status 302 + Location header, not the redirect target |

## What NOT to do

- **Don't shard.** The rubric tests correctness, not throughput beyond the SLO.
- **Don't introduce a queue.** Sync-write is fine at this scale.
- **Don't forget `created_at`** in the `/api/expand` response — it's in the spec.
- **Don't return short codes < 5 chars.** Even if your counter is at "1", base62-encode and pad.
- **Don't let custom aliases collide with system paths** (`health`, `stats`, `shorten`). Validate that aliases don't equal those reserved words.

## When you're stuck

> "The judge says collision-01 fails: my service returned the same short_code 'aB3xY' for two different long_urls. Show me my code generator. Walk through how it picks codes — is it deterministic on long_url (so two different URLs WOULD always get different codes), or is it pseudo-random (so collisions are possible)?"

(Common cause: hashing the URL with a too-short hash. Switch to a counter.)

## After this exercise

Idempotency on writes + 302 round-trip is foundational. Reuse the pattern in design/04 (booking), where the same idempotency lessons apply (don't double-book a slot).
