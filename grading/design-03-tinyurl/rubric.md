# Rubric — design/03-tinyurl

## Test types

### `smoke`

Schema/HTTP correctness — fields present, types right, status code matches `expected.status`/`status_in`. Score 10 on full match; 0 on schema violation; -2 per missing field.

### `idempotency`

The test instructions describe how to issue `repeat` copies of the same `POST /shorten` and check that the `short_code` is identical across all returned bodies.

| Outcome | Score |
| --- | --- |
| All `repeat` calls returned identical short_codes; status was 201 on call 1 and 200 on subsequent calls (or all 200) | **10** |
| All identical short_codes but status was always 201 (the server doesn't differentiate "new" from "exists") | 8 |
| 4 of 5 identical, 1 different | 4 |
| 3+ different codes across the 5 calls — fundamentally non-idempotent | **0** |

Critique should quote the exact returned codes, e.g., "calls returned ['aB3xY7', 'aB3xY7', 'aB3xY7', 'aB3xY7', 'aB3xY7'] — perfect idempotency".

### `uniqueness`

Issue 50 POST calls with distinct random long URLs. Collect short_codes; check the set size is 50.

| Outcome | Score |
| --- | --- |
| 50 distinct codes across 50 distinct URLs | **10** |
| 49 distinct (one collision) | 5 |
| ≤ 48 distinct | **0** |
| Service errors out > 5% of calls | 0 |

Critique should report the actual count, e.g., "47 distinct codes from 50 URLs — 3 collisions detected on a 5-char hash prefix".

### `roundtrip`

Step 1: shorten a known long URL → capture code. Step 2: `GET /<code>` with `follow_redirects=False`. Check `status==302` AND `headers['location']` matches the original `long_url` *exactly* (case-sensitive, including query string and trailing slash).

| Outcome | Score |
| --- | --- |
| 302 + Location matches exactly | **10** |
| 302 + Location matches up to trailing slash | 8 |
| 301 instead of 302 | 5 (technically wrong per spec but functional) |
| 200 (returned the URL in body, didn't redirect) | 2 |
| 404 (lost the mapping) | 0 |

### `redirect` — 302 not 301

The judge specifically distinguishes: 301 is "moved permanently"; 302 is "found/temporary". Spec mandates 302.

| Outcome | Score |
| --- | --- |
| 302 | **10** |
| 301 | 5 |
| Other | 0 |

### `alias`

Three sub-cases (see `judge.json` test instructions). Score against the specific scenario:

**alias-fresh**: alias not yet in store → server uses it. Score 10 if `short_code == alias`. Score 0 if server ignored the alias and generated its own.

**alias-conflict**: alias maps to a DIFFERENT URL → step 2 must return 409.
- 409 + helpful message → 10
- 409 + empty body → 8
- 200 (silent overwrite!) → **0** — this is a security bug
- 500 → 3

**alias-idempotent**: alias maps to SAME URL → idempotent.
- 200/201 + correct short_code → 10
- 409 (over-strict) → 4
- 500 → 0

### `latency`

p95 across all `/shorten` and `/<code>` calls. SLO: write 200ms, read 100ms.

| Outcome | Score |
| --- | --- |
| Both well under SLO | **10** |
| One axis 1.5× over SLO | 5 |
| > 5% timeouts | **0** |

## Pre-flight gate

`GET /health` 200 within 10s. Total score 0 if not reachable.

## Overall scoring

Pass: ≥60%. The rubric weights idempotency (3.0) + collision avoidance (3.0) + roundtrip (2.5) heaviest because they're foundational. A learner with weak alias semantics but rock-solid idempotency can still pass.

## Strictness notes

- **Quote evidence.** "POST /shorten returned `{short_code: 'aB3xY7'}`; second call returned `{short_code: 'cM9pQ2'}` — non-idempotent." Don't say "looks broken" without naming the codes.
- **Cite exact status codes.** "Got 200 instead of 302" not "wrong status".
- **Be strict on alias-conflict.** Silently overwriting a previous alias is a real-world security bug — score 0 even if the rest of the system is solid.
- **Be lenient on first-write status.** 200 vs 201 on the FIRST shortening is a minor distinction — don't dock heavily either way unless the rubric for the specific test demands it.
