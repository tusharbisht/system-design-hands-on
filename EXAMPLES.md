# EXAMPLES — design/06-vector-database

## E1 — index a doc

```http
POST /index
{ "doc_id": "p1",
  "text": "Postgres uses MVCC for concurrency.",
  "metadata": {"category": "database", "year": 2024} }
```

→ `201 { "doc_id": "p1", "indexed_at": "..." }`

## E2 — upsert (same doc_id, new text)

```http
POST /index
{ "doc_id": "p1",
  "text": "Postgres uses Multi-Version Concurrency Control to allow non-blocking reads.",
  "metadata": {"category": "database", "year": 2024} }
```

→ `200` (replaced — same doc_id existed). `GET /docs/p1` now returns the NEW text.

## E3 — bulk index

```http
POST /index/bulk
{ "documents": [
    {"doc_id": "r1", "text": "BM25 is term-frequency...",
     "metadata": {"category": "retrieval", "year": 2024}},
    {"doc_id": "r2", "text": "RRF combines ranked lists...",
     "metadata": {"category": "retrieval", "year": 2025}}
  ]
}
```

→ `200 { "indexed_count": 2, "doc_ids": ["r1", "r2"] }`

## E4 — search without filter (whole collection)

```http
POST /search
{ "query": "what does VACUUM do", "k": 3 }
```

→ `200`

```json
{ "query": "what does VACUUM do",
  "results": [
    {"doc_id": "p1", "score": 0.91, "text": "Postgres uses MVCC...", "metadata": {...}},
    ...
  ]
}
```

## E5 — search with filter (only retrieval docs)

```http
POST /search
{ "query": "what is BM25", "k": 5, "filter": {"category": "retrieval"} }
```

→ `200` with results restricted to docs where `metadata.category == "retrieval"`. Even if a database doc has a higher cosine score, it's excluded.

## E6 — filter with no matches

```http
POST /search
{ "query": "anything", "filter": {"category": "nonexistent"} }
```

→ `200 { "results": [] }` — empty array, NOT a 404.

## E7 — filter on numeric field

```http
POST /search
{ "query": "retrieval", "filter": {"year": 2024} }
```

→ Results restricted to docs with `metadata.year == 2024` (numeric equality).

## E8 — delete

```http
DELETE /docs/p1
```

→ `204`. Subsequent `POST /search` will not return p1.

## E9 — stats

```http
GET /stats
```

→

```json
{ "total_docs": 3, "categories": {"database": 0, "retrieval": 3} }
```

## E10 — bulk fails atomically

```http
POST /index/bulk
{ "documents": [
    {"doc_id": "ok1", "text": "good doc", "metadata": {...}},
    {"doc_id": "bad", "text": "", "metadata": {...}}      # text empty
  ]
}
```

→ `400 { "error": "doc_id 'bad' has empty text" }`. Crucially: the FIRST doc (`ok1`) is NOT inserted — the whole batch failed atomically.

## E11 — health

```http
GET /health
```

→ `200 {"ok": true}`
