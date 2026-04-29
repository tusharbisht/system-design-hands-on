# Rubric — design/06-vector-database

## Test types

### `smoke`

Field/status correctness on a single endpoint. 10 on full match; 0 on schema violation; -2 per missing field.

### `lifecycle`

Multi-step scenarios (index → search; index → delete → confirm gone). Every step must succeed at the right status.

| Outcome | Score |
| --- | --- |
| All steps succeed, top-doc matches expected | **10** |
| Steps succeed but top-doc is at rank 2 (close) | 7 |
| Steps succeed but top-doc not in top-3 | 4 |
| Any step errored | 0 |

For `index-and-recall`, the search test is on QUERY-RELEVANCE: the right doc should be ranked first. Expected docs (d1, d2) are clearly best matches for their queries; ranking them lower than 1st means the embedding/retrieval is misaligned.

### `filter`

Tests metadata filtering correctness:

**filter-restricts-results** — strictest test. Score 10 only when results contain ZERO docs that don't match the filter. Even one wrong category-doc in the results = score 4 (most likely a post-filter implementation bug). Empty results when valid matches exist = score 0 (filter blocks everything — wrong implementation).

**filter-empty-no-match** — filter matches no docs. MUST return `200 {results: []}`, not 404.
| Outcome | Score |
| --- | --- |
| 200 + empty results | **10** |
| 404 | 3 (technically wrong shape but functional signal) |
| 200 + non-empty results (filter ignored!) | 0 |

**filter-empty-or-missing-equals-no-filter** — `filter: {}` should behave like no filter.
| Outcome | Score |
| --- | --- |
| Returns full unfiltered ranking, top doc d2 | **10** |
| Returns 0 results (treated empty filter as "match nothing") | 0 |
| Treats {} as filter and applies category=null match | 3 |

### `upsert` — the critical test

Same `doc_id` indexed twice with different text. `total_docs` must NOT increase between the two; `GET /docs/<id>` must return the LATEST text.

| Outcome | Score |
| --- | --- |
| total_docs unchanged AND latest text returned | **10** |
| total_docs unchanged but old text returned (storage updated, retrieval index didn't) | 5 |
| total_docs grew by 1 (a duplicate vector was added — naïve insert) | **0** |
| total_docs grew + latest text returned | 2 |

Critique should report the actual numbers: `"total_docs went from 4 to 5 — duplicate insert detected"`.

### `delete` (delete-durable)

Multi-check: GET 404 + search must not return deleted doc.

| Outcome | Score |
| --- | --- |
| Both checks pass | **10** |
| GET 404 but search still returns deleted doc | 4 |
| GET still returns 200 (delete didn't take) | 0 |

### `bulk` — atomicity

**bulk-atomicity** — a batch with one bad doc must fail entirely; first valid doc must NOT be inserted.

| Outcome | Score |
| --- | --- |
| 400 returned AND `b_ok` is 404 | **10** |
| 400 returned BUT `b_ok` was inserted | 4 (caught the error but inserted anyway) |
| 200 returned (both inserted) | 0 |
| 207 / partial success | 2 |

**bulk-success** — all valid docs in batch get inserted.

| Outcome | Score |
| --- | --- |
| 200 + indexed_count: 2 + both retrievable | **10** |
| 200 + indexed_count: 1 (one not actually inserted) | 4 |
| 500 / 400 | 0 |

### `latency`

p95 across all `/search` and `/index` calls. SLO: index 500ms, search 300ms.

| Outcome | Score |
| --- | --- |
| Under SLO | **10** |
| 1.5× SLO | 6 |
| 3× SLO or > 5% timeouts | **0** |

## Pre-flight gate

`GET /health` returns 200 within 10s. Total score 0 otherwise.

## Overall scoring

Pass: ≥60%. The exercise weights the four "real database operation" axes (recall, filter, upsert, bulk) at ~75% combined — getting these right is the lesson.

## Strictness notes

- **Quote actual results lists** when grading the filter test. "filter={category:'database'} returned [d2, d3] — both retrieval, no database docs at all → filter is broken or inverted".
- **Quote total_docs before/after** for the upsert test. "before: 4, after: 5 — naïve insert, not upsert".
- **Quote the exact text returned by GET /docs/up1**. "expected 'NEW version', got 'old version' → storage didn't update".
- **Be lenient on score scaling** — different vector DBs return cosine [0,1] vs distance vs raw dot product. Don't dock for the absolute score number, only for ranking.
