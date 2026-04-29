# EXAMPLES — design/01-semantic-search

Sample request/response pairs the judge will probe variations of.

## E1 — exact-topic query

```http
POST /search
{ "query": "what is BM25", "k": 3 }
```

→

```json
{
  "query": "what is BM25",
  "results": [
    {"doc_id": "d003", "score": 0.93, "title": "BM25 explained", "text": "BM25 is a bag-of-words ranking..."},
    {"doc_id": "d004", "score": 0.71, "title": "Hybrid retrieval with RRF", "text": "..."},
    {"doc_id": "d011", "score": 0.45, "title": "LangChain at a glance", "text": "..."}
  ]
}
```

## E2 — paraphrased query

```http
POST /search
{ "query": "how do approximate nearest neighbor indexes trade off speed and recall", "k": 2 }
```

→ top result MUST be `d006`. Score should be high.

## E3 — out-of-corpus query

```http
POST /search
{ "query": "what is the airspeed velocity of an unladen swallow", "k": 5 }
```

→ valid response, but the top score should be relatively LOW (e.g. < 0.5 cosine). Don't fake high scores.

## E4 — k bound

```http
POST /search
{ "query": "vacuum", "k": 100 }
```

→ either return at most 15 results (corpus size) and a `400` (k out of range) is also acceptable since the spec caps k at 20. Be consistent.

## E5 — empty query

```http
POST /search
{ "query": "", "k": 5 }
```

→ `400` with a body like `{"error": "query must be non-empty"}`.

## E6 — fetch a doc by id

```http
GET /docs/d004
```

→

```json
{ "doc_id": "d004", "title": "Hybrid retrieval with RRF", "text": "Reciprocal Rank Fusion..." }
```

## E7 — unknown doc id

```http
GET /docs/zzz
```

→ `404 {"error": "no such doc_id"}`.

## E8 — health probe

```http
GET /health
```

→ `200 {"ok": true}` (or your own minimal shape; the LMS pre-flight only checks status code).
