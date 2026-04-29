# SPEC — design/01-semantic-search

A semantic search service over a fixed corpus of 15 documents (`corpus/docs.json` on `main`).

## Endpoints

### `POST /search`

```http
POST /search HTTP/1.1
Content-Type: application/json

{ "query": "how does cosine differ from dot product?", "k": 5 }
```

→ `200 OK`

```json
{
  "query": "how does cosine differ from dot product?",
  "results": [
    { "doc_id": "d002", "score": 0.91, "title": "Cosine similarity vs dot product", "text": "Cosine similarity measures..." },
    { "doc_id": "d006", "score": 0.62, "title": "Vector index ANN tradeoffs", "text": "..." }
  ]
}
```

Errors:
- `400` if `query` missing/empty or `k` not in `1..20`
- `500` if your service fails internally (judge will dock heavily)

### `GET /docs/{doc_id}`

```http
GET /docs/d002 HTTP/1.1
```

→ `200`

```json
{ "doc_id": "d002", "title": "Cosine similarity vs dot product", "text": "Cosine similarity..." }
```

Errors:
- `404` if `doc_id` is not in your indexed corpus.

### `GET /health`

→ `200 {"ok": true}` — used by the LMS pre-flight check before judging.

## SLOs

```yaml
read_p95_ms: 500           # /search at k=5 over the seeded corpus
write_p95_ms: n/a
error_rate_pct: 1.0
sustained_rps: 20          # the judge probes serially; bursts to 5 concurrent
```

## Correctness invariants

Verified by the judge:

1. **Result count**: `len(results) <= k`. If the corpus has fewer than `k` documents, return what's there.
2. **Field shape**: every result has `doc_id`, `score`, `title`, `text`. Missing fields → 0 score on that test.
3. **Order**: results sorted by `score` descending. No ties broken arbitrarily across calls (deterministic).
4. **Score range**: `score` is a real number; cosine similarities should be in `[-1, 1]`, dot products in any range. No NaN, no null.
5. **doc_id is real**: every `doc_id` returned matches a doc in `corpus/docs.json`.
6. **Recall@5 on labeled queries**: at least 8 of 10 labeled queries return their ground-truth doc within the top-5. (See `grading/design-01-semantic-search/judge.json`.)
7. **OOC robustness**: a query like "what is the meaning of life" (no relevant doc) should return *low* scores — judge checks the top score is below your strong-match threshold.
8. **Same-query determinism**: two calls with the same `{query, k}` return the same `results` (modulo serialization noise). No randomness without a seed.

## Constraints

- **Corpus**: use `corpus/docs.json` from `main` *unchanged*. Index it, however you like, on startup.
- **Embedding model**: any. OpenAI ada-002, Cohere, sentence-transformers (local), Voyage — your call.
- **Vector store**: any. pgvector, Qdrant, Chroma, in-memory cosine — your call.
- **Language/framework**: any.
- **API key handling**: if your embedding requires a key, set it via env on your hosting provider. Don't commit it.

## What you're being graded on (rubric.md preview)

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, `/search` p95 < 500ms |
| Result shape | 20% | every field present, types correct, k-bound respected |
| Recall@5 | 50% | does the right doc come up for labeled queries |
| Order + determinism | 15% | sorted descending; same input → same output |
| OOC handling | 15% | low-relevance queries get low scores (don't fake high scores) |

## Examples

See [`EXAMPLES.md`](EXAMPLES.md).

## Authoring tip

The judge runs 10 labeled queries against your service. Pre-compute embeddings on startup; don't embed the corpus on every `/search` call (you will lose the latency SLO). Cache the corpus index in memory or a vector store; the corpus is small and fits.
