# Design 06 — Vector database (Pinecone / Weaviate / Qdrant / pgvector)

**Type:** system-design — build, host, submit a URL
**Estimated time:** 6–10h with Claude Code
**Auto-graded:** vector recall, metadata-filter correctness, upsert semantics, delete durability, bulk atomicity

## The problem

design/01 was a *fixed* corpus + cosine similarity. Real RAG systems work with *dynamic* collections: docs come in, get updated, get deleted. Production retrieval lives behind a real vector database — Pinecone, Weaviate, Qdrant, Chroma, pgvector — and the API contract gets harder once you add: bulk inserts that need atomicity, metadata filtering at query time, upsert semantics.

This branch is design/01 with operating realism added.

## What you're building

`POST /index`, `POST /index/bulk`, `POST /search`, `GET /docs/<id>`, `DELETE /docs/<id>`, `GET /stats`, `GET /health`. Full contract in [`SPEC.md`](SPEC.md). Sample requests in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

- Service running publicly. `/health` returns 200.
- A real vector DB behind it (Pinecone managed, or Weaviate/Qdrant/Chroma containerized, or pgvector on Postgres). Not a Python dict.
- Vector search recalls expected docs on labeled queries (similar to design/01 but on docs the *judge inserts at probe time*).
- Metadata filter narrows results AND intersects correctly with top-K.
- Upsert (same doc_id, new text) replaces the old vector, not appends.
- Delete is durable.
- Bulk insert with one bad doc fails atomically — no partial inserts.

Pass: ≥60%. Strong pass: ≥80% with all four invariants (filter / upsert / delete / bulk-atomicity) scoring 10/10.

## Why this is harder than design/01

- **The judge inserts the corpus at probe time.** It calls `POST /index` (or `/bulk`) with documents *it* generates, then queries them. Your service has to handle a stream of indexes correctly — there's no pre-baked TF-IDF matrix.
- **Filters intersect with top-K.** Naïve approach: vector search top-5, then drop those that don't match the filter. Wrong: you might return 1 result when 10 valid ones exist past rank 5.
- **Upsert is not insert.** This is where most learners break. `POST /index {doc_id: 'd1', text: 'v1'}` then `POST /index {doc_id: 'd1', text: 'v2'}` should leave you with ONE vector indexed under d1, with the v2 content.

## Constraints

- **Use a real vector DB.** Pinecone (managed, free tier exists), Weaviate (Docker), Qdrant (Docker), Chroma (Docker or in-process), pgvector (Postgres extension). Pick one — the judge can't tell which but the rubric rewards correct *behaviour*, which non-trivial DBs make easier.
- **Embeddings**: any. Pre-compute on `/index`, query at `/search` time.
- **Metadata storage**: store the metadata as JSONB / object alongside the vector. Pinecone/Qdrant/Weaviate all support this natively. pgvector + a Postgres JSONB column works.

## Hints

<details><summary>Hint 1 — pick a DB you can install in 30 minutes</summary>

For first-time learners:
- **Pinecone**: managed, free tier sufficient. ~10 min: signup → API key → first index. SDK works in any language.
- **Qdrant**: Docker one-liner: `docker run -p 6333:6333 qdrant/qdrant`. Has a Python SDK.
- **Chroma**: `pip install chromadb`. In-process or as a server. Fastest to ship; least production-realistic.
- **pgvector**: if you're already using Postgres, add the extension. The most "real-database" feel.

Don't try Weaviate or Milvus first time — they have heavier learning curves.

</details>

<details><summary>Hint 2 — upsert atomically</summary>

Most vector DBs distinguish `insert` (fails on duplicate) from `upsert` (replaces). Use upsert from day one. If the SDK only has insert, the recipe is: `delete(doc_id); insert(doc_id, vec, metadata)` — but this isn't atomic. Use the SDK's upsert API where it exists.

```python
# Pinecone
index.upsert([(doc_id, embedding, {"text": text, **metadata})])

# Qdrant
client.upsert(collection_name="docs", points=[{
    "id": doc_id, "vector": embedding,
    "payload": {"text": text, **metadata}
}])
```

</details>

<details><summary>Hint 3 — filter + top-K is database-supported</summary>

Don't post-filter. Every modern vector DB supports filter-clauses inside the query itself:

```python
# Pinecone
index.query(vector=q, top_k=5, filter={"category": "database"})

# Qdrant
client.search(collection_name="docs", query_vector=q, limit=5,
              query_filter={"must": [{"key": "category", "match": {"value": "database"}}]})

# pgvector (raw SQL)
SELECT doc_id, text, embedding <=> %s AS distance
  FROM documents
 WHERE metadata->>'category' = 'database'
 ORDER BY distance LIMIT 5
```

Use the DB's filter — it's faster AND correct (it considers the entire filtered subset, not just top-K).

</details>

<details><summary>Hint 4 — bulk atomicity</summary>

If your DB doesn't have transactional bulk insert (Pinecone doesn't), validate the entire batch FIRST, then insert. Validation should check: doc_id non-empty, text non-empty, metadata is a JSON object, no duplicate doc_ids in the batch. If all pass, upsert. If any fail, return 400 without writing anything.

For pgvector + a single transaction: just BEGIN; INSERT each; COMMIT or ROLLBACK on first error.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-06-vector-database/](grading/design-06-vector-database/)
