# Design 03 — TinyURL: scale matters

**Type:** system-design — build, host, submit a URL
**Estimated time:** 4–6h with Claude Code
**Auto-graded:** idempotency, collision avoidance, custom alias semantics, round-trip 302, 404 handling, code shape

## The problem

The classic shortener. Long URL in → short code out. Same URL twice → same code (idempotent). 1,000 distinct URLs → 1,000 distinct codes (no collisions). The redirect must round-trip.

It looks trivial. It isn't — the bugs hide in:

- **Idempotency**: do you actually deduplicate, or do you generate a fresh code on every POST?
- **Collisions**: a naive 5-char MD5 prefix collides at ~3% by 50,000 entries. The judge tries 50 random URLs; expect to design for a billion.
- **Custom aliases**: when a learner-supplied `alias` clashes with one you already have for a *different* URL, do you 409? Or silently overwrite the previous mapping? (One is a feature; one is a bug.)
- **404 vs default**: do unknown codes 404, or do they redirect to a generic landing page? The spec is clear; the judge checks.

## What you're building

`POST /shorten`, `GET /<short_code>`, `GET /api/expand/<short_code>`, `GET /stats`, `GET /health`. Full contract in [`SPEC.md`](SPEC.md), examples in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

- Service running publicly on a URL the judge can hit
- Pre-flight passes: `/health` returns 200
- 5 repeated calls with the same `long_url` return the same `short_code`
- 50 random distinct URLs return 50 distinct codes
- `GET /<short_code>` returns `302` with the right `Location` header
- Custom alias on a free name is accepted; same alias on a different URL → 409
- `GET /<unknown_code>` → 404
- All response shapes match `SPEC.md`

Pass: ≥60% weighted. Strong pass: ≥80% with 0/0 collisions and clean alias semantics.

## Why this is the right place to start on system-design classics

Most "design TinyURL" interview answers wave at sharding, Redis, ZooKeeper. The judge here doesn't care about your architecture diagram — it cares whether your *running service* round-trips correctly under specified inputs. Build small, ship, and check whether your idempotency story actually holds.

## Constraints

- Any language/framework
- Any storage (in-memory is fine for v1; the SLO permits it)
- Any code-generation strategy
- The corpus is only your own — the judge generates random URLs at probe time

## Hints

<details><summary>Hint 1 — idempotency wants a (long_url → short_code) index</summary>

Naive: store `short_code → long_url` only. On every POST, generate a fresh code and store. Two calls with the same long URL produce two codes — fail.

Right shape: TWO maps (or a single row indexed both ways). On POST, look up `long_url → short_code`. If found, return it. If not, generate, insert both directions atomically, return.

In SQL: `INSERT … ON CONFLICT (long_url) DO UPDATE SET … RETURNING short_code` is the cleanest one-statement upsert.

</details>

<details><summary>Hint 2 — base62 of a monotonic counter beats hash-prefix</summary>

A 5-char base62 code has 916M possibilities. Easy.

A 5-char MD5 hex prefix has 1M possibilities — birthday-paradox collisions hit at ~1,000 entries.

If you must hash, take 8+ chars OR use base62-of-a-counter. The latter has zero collisions by construction.

</details>

<details><summary>Hint 3 — alias precedence rules</summary>

Three cases for `POST /shorten {long_url: X, alias: A}`:

1. `A` is not in the store → use it. Return `{short_code: A}` with `201`.
2. `A` is in the store and maps to `X` → idempotent. Return `{short_code: A}` with `200`.
3. `A` is in the store but maps to `Y ≠ X` → return `409`.

The third is where most first-pass implementations break (they overwrite or 500). Code defensively.

</details>

<details><summary>Hint 4 — `GET /<code>` must NOT be the same path as `POST /shorten`</summary>

If your server uses `GET /` for `/shorten`, you'll have a path conflict — `/shorten`, `/health`, `/stats`, `/api/expand/...` all need their own paths. Reserve a *short* set of paths for system endpoints (e.g., everything starting with `_` or `api/`); everything else is a redirect target.

A practical layout: routes for `POST /shorten`, `GET /health`, `GET /stats`, `GET /api/expand/<code>` are exact matches. The catch-all `GET /<code>` matches anything else.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-03-tinyurl/](grading/design-03-tinyurl/)
