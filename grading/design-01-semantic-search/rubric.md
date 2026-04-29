# Rubric — design/01-semantic-search

The judge runs the tests in `judge.json` and asks an LLM to score each one 0–10 against this rubric. The score is weighted by each test's `weight` field.

## Test types

### `smoke`

A basic shape/HTTP correctness check. Score 10 if the response matches the expected fields/status; 0 if it 500s, returns the wrong shape, or violates the `k` bound. Partial credit: deduct 2 for each missing or mistyped field.

### `ranking`

A retrieval recall check. Score by whether the doc(s) listed in `expected.top_doc_ids_must_include` actually appear in the response's top-K (where K = the request's `k`).

| Outcome | Score |
| --- | --- |
| Expected doc is rank 1 | **10** |
| Expected doc is rank 2 | 9 |
| Expected doc is rank 3 | 8 |
| Expected doc is in top-5 | 6 |
| Expected doc is in the response but past top-5 | 3 |
| Expected doc not in the response at all | **0** |

Two notes:
- If the response 500s or returns malformed JSON, score 0.
- If the response shape is right but `score` field is missing, that's a smoke failure too — score 0.

### `refusal`

An out-of-corpus query. The service should still respond `200`, but the **top score should be visibly lower** than the in-corpus queries. Specifically: if the embedding model produces normalized cosine similarities, the top score should be below `expected.low_threshold_cosine` (typically 0.5).

| Outcome | Score |
| --- | --- |
| Top score < threshold (clean refusal signal) | **10** |
| Top score 0.5–0.6 (borderline) | 6 |
| Top score 0.6–0.75 (suspicious — looks like the embedding is fooling itself) | 3 |
| Top score > 0.75 (the model is faking confidence on garbage input) | **0** |

If the service rejects with 4xx instead of returning low scores, that's also acceptable — score 8 (marginally worse than the right-shape low-score response, since the SPEC says return low scores rather than 4xx).

### `latency`

Read latency p95 across all `/search` calls in the test suite (including non-latency tests). Compare to SLO `read_p95_ms: 500`.

| Outcome | Score |
| --- | --- |
| p95 < 250ms | **10** |
| p95 250–500ms | 8 |
| p95 500–800ms | 5 |
| p95 800–1500ms | 2 |
| p95 > 1500ms or service times out on > 10% of calls | **0** |

## Determinism check

`determinism-01` runs the same input as `smoke-01`. Score 10 if the response is byte-identical (or differs only in floating-point noise < 1e-6 on scores); score 5 if results are the same docs in the same order but with subtly different scores; score 0 if order or docs differ.

## Pre-flight gate (not in tests)

Before tests run, the judge calls `GET /health`. If non-200 within 10s, the entire submission scores 0 with critique = "service unreachable". This is the gate, not a graded axis.

## Overall scoring

`weighted_total = sum(weight × score)` across all tests, divided by `sum(weight × 10)` for the percent.

Pass threshold: **60%**. The LMS shows pass/fail + percent + per-test critique.

## A note on strictness

Be strict. Generic reasoning ("looks fine") gets docked. Cite the actual `observed.body` fields in your reasoning. If the service returned `score: 0.93` for an OOC query, your critique should literally quote that number.

If the response status was 500, your reasoning should be: `"500 with body: ..."`. Don't be polite — the learner needs the specific failure to fix it.
