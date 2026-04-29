# SPEC — design/06-vector-database

A vector database service backed by **Pinecone, Weaviate, Qdrant, Chroma, pgvector, or any other real vector DB**. The contract: documents have arbitrary `metadata`, search supports metadata-filtering at query time, and upserts replace existing records cleanly.

This is design/01 evolved: instead of a fixed corpus + cosine, you operate a *dynamic* collection that supports inserts, updates, deletes, and metadata-filtered retrieval.

## Endpoints

### `POST /index`

Upsert a document. If `doc_id` exists → replace.

```http
POST /index
{ "doc_id": "d101",
  "text": "Postgres uses MVCC for concurrency...",
  "metadata": {"category": "database", "year": 2024, "tags": ["postgres", "mvcc"]} }
```

→ `201` (created) or `200` (replaced)

```json
{ "doc_id": "d101", "indexed_at": "2026-04-29T..." }
```

### `POST /index/bulk`

Bulk version. Body: `{"documents": [...]}`. Atomic-ish: either ALL succeed or none (any per-doc validation failure → 400 for the whole batch, no partial inserts).

→ `200 { "indexed_count": int, "doc_ids": [...] }`
→ `400` if validation fails on any doc

### `POST /search`

Top-K with optional metadata filter.

```http
POST /search
{ "query": "what causes table bloat",
  "k": 5,
  "filter": { "category": "database" } }
```

→ `200`

```json
{ "query": "what causes table bloat",
  "results": [
    {"doc_id": "d101", "score": 0.87,
     "text": "Postgres uses MVCC...", "metadata": {...}}
  ]
}
```

The `filter` is **AND of equality matches on top-level metadata fields**. If `filter` is missing or empty, no filtering — pure vector search across everything.

### `GET /docs/{doc_id}` → 200 (record) or 404

### `DELETE /docs/{doc_id}` → 204 or 404

### `GET /stats`

```json
{ "total_docs": int,
  "categories": {"database": 12, "retrieval": 8} }
```

The `categories` aggregation lets the judge verify your filter implementation actually filters.

### `GET /health` → `200 {"ok": true}`

## SLOs

```yaml
write_p95_ms: 500          # /index (embedding + DB write)
read_p95_ms: 300           # /search at k=5
error_rate_pct: 1.0
sustained_rps: 30
```

## Correctness invariants

1. **Upsert semantics**: indexing the same `doc_id` twice with different text replaces the first. After two upserts, `total_docs` increased by 1 (not 2). `GET /docs/<id>` returns the latest text.
2. **Filter is exact-equality on metadata fields.** `filter: {"category": "database"}` returns only docs where `metadata.category == "database"`. Numeric/string both supported.
3. **Empty filter == no filter.** Missing `filter` field, `filter: {}`, or `filter: null` all behave identically: pure vector search across the entire collection.
4. **Filter intersects with top-K, not before.** Don't return 5 results that match the filter from a candidate pool of only 5 — search the whole space, then filter, then top-K. (Different DBs make this easier or harder; document your approach.)
5. **Delete is durable.** After `DELETE /docs/<id>`, `GET /docs/<id>` → 404 AND that doc no longer appears in any `POST /search`.
6. **404 distinguishes from empty.** `POST /search` with a filter that matches nothing returns `200 {"results": []}` — NOT 404.
7. **Bulk atomicity.** A bulk insert with one bad record (e.g., missing `text`) fails the entire batch with 400 — no partial inserts.

## What you're being graded on

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, `/index` p95 < 500ms, `/search` p95 < 300ms |
| Schema | 10% | fields present, types right |
| Vector recall | 25% | top-1 retrieval correctness on labeled queries |
| Metadata filter | 25% | filter narrows results correctly; intersects with top-K |
| Upsert semantics | 15% | duplicate doc_id replaces, doesn't append |
| Delete durability | 10% | deleted docs disappear from search + GET |
| Bulk atomicity | 10% | bad doc in batch = whole batch fails |
| Empty-filter behaviour | 5% | missing/empty filter = no filtering |

## Constraints

- **Real vector DB required.** TF-IDF / NumPy / Python dict don't count for this exercise — the point is to use Pinecone / Weaviate / Qdrant / Chroma / pgvector. The judge can't tell you what you used; the rubric rewards correct *behaviour*. But the SLOs are tuned so an in-memory cosine WILL pass them; you'd be missing the point of the lesson, not the score.
- **Embeddings**: any. OpenAI ada-002, Cohere, sentence-transformers, Voyage — the API. Pre-compute on `/index`, query at `/search` time.
- **Hosting**: any reachable URL.

## Authoring tip

The two failure modes most submissions hit:

1. **Filter applied to top-K, not pre-filter or post-filter.** The naïve flow is "vector search top-5, then drop those that don't match the filter". If only 1 of the top-5 matches your filter, you return 1 result — even if there were 10 matching docs ranked 6th–20th. Either pre-filter (search within the filtered subset) or post-filter (search wider, then filter, then take K). Pre-filter is faster; post-filter is what most vector DBs default to with a filter clause.

2. **Upsert vs insert.** `POST /index {doc_id: "d1", text: "v1"}` then `POST /index {doc_id: "d1", text: "v2"}` should leave you with ONE document with text "v2". Many learners append a new vector each time, leaving the OLD vector in the index too — total_docs goes from 0→2, GET /docs/d1 returns v1 (the older one) randomly.

See [`EXAMPLES.md`](EXAMPLES.md) for sample requests.
