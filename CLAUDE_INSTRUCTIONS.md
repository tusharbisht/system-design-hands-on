# Solving Design 06 with Claude Code — faster and better

The hardest part is *not* writing the code — it's wiring up the vector DB without spending an hour on installation. Pick a stack you can ship in 30 minutes; spend the rest of the time on correctness.

## Recommended workflow

### 1. Choose the vector DB in plan mode (Shift+Tab)

> "Plan the storage. Compare four options for this exercise:
> (a) Pinecone — managed, ~10 min setup
> (b) Qdrant in Docker — local, ~5 min setup
> (c) Chroma in-process — `pip install`, ~1 min setup
> (d) pgvector on Postgres — ~15 min setup if Postgres is already there
>
> Trade-offs: setup time, cost, durability across redeploys, support for filter clauses, deletion semantics.
> Recommend ONE for shipping in a few hours."

Pick the one you can have running fastest. Chroma works for v1; the rubric tests behaviour, not which DB.

### 2. Embed once, locally

> "I'll be embedding via OpenAI ada-002 (or sentence-transformers locally — your call). Show me a function `embed(text: str) -> list[float]` that handles errors and rate limits. Keep it ~15 lines."

Don't shell out to embedding APIs on every request without caching the model client. One process-global client.

### 3. Build the API in two passes

> "Pass 1: implement /health, /index, /search WITHOUT filter, /docs/<id> GET. Show me the diff. Don't worry about bulk, delete, or filtering yet."

Get the round-trip working first.

> "Pass 2: add filter support to /search, /index/bulk with atomic validation, DELETE /docs/<id>, /stats. Show me the diff."

### 4. Probe yourself

```python
import httpx
URL = "http://localhost:8000"
c = httpx.Client(base_url=URL)

# Health
assert c.get("/health").status_code == 200

# Index
docs = [
    ("d1", "Postgres uses MVCC", {"category": "database"}),
    ("d2", "BM25 is term frequency", {"category": "retrieval"}),
    ("d3", "RRF combines ranked lists", {"category": "retrieval"}),
]
for did, text, md in docs:
    r = c.post("/index", json={"doc_id": did, "text": text, "metadata": md})
    assert r.status_code in (200, 201)

# Search without filter
r = c.post("/search", json={"query": "what does VACUUM do", "k": 3}).json()
assert r["results"][0]["doc_id"] == "d1"

# Search with filter
r = c.post("/search", json={"query": "term frequency", "k": 5, "filter": {"category": "retrieval"}}).json()
assert all(x["metadata"]["category"] == "retrieval" for x in r["results"])
assert "d1" not in [x["doc_id"] for x in r["results"]]   # database doc must not appear

# Upsert: same doc_id, new text
r1 = c.post("/index", json={"doc_id": "d1", "text": "Postgres MVCC explained", "metadata": {"category": "database"}})
assert c.get("/docs/d1").json()["text"] == "Postgres MVCC explained"
assert c.get("/stats").json()["total_docs"] == 3   # NOT 4

# Delete
c.delete("/docs/d1")
assert c.get("/docs/d1").status_code == 404
r = c.post("/search", json={"query": "Postgres", "k": 5}).json()
assert "d1" not in [x["doc_id"] for x in r["results"]]

# Bulk atomicity
r = c.post("/index/bulk", json={"documents": [
    {"doc_id": "ok", "text": "fine", "metadata": {}},
    {"doc_id": "bad", "text": "", "metadata": {}},   # empty text - should fail
]})
assert r.status_code == 400
assert c.get("/docs/ok").status_code == 404   # MUST not have been inserted

print("all probes passed")
```

If any of these don't pass locally, fix before submitting.

### 5. Submit and iterate

The judge inserts a small corpus, then probes. Read the per-test critique carefully — common first failures:

- **filter test fails**: you post-filtered top-K instead of pre-filtering. Switch to the DB's filter clause.
- **upsert test fails**: your `POST /index` always inserts a NEW vector for the same `doc_id`. Use upsert.
- **bulk-atomicity fails**: you inserted the first valid doc before validating the second. Validate ALL first, insert ONLY if all valid.
- **delete-durability fails**: you delete from a side index but not from the vector DB itself; subsequent search still returns the deleted doc.

## Claude Code techniques that pay off here

| Technique | Why it matters |
| --- | --- |
| **Plan-mode the DB choice** | each option has different setup costs; pick BEFORE installing |
| **Embed-once + cache the client** | otherwise each request re-creates clients, blowing latency budget |
| **Use the DB's filter clause** | post-filtering is the canonical wrong answer here |
| **Test upsert by checking total_docs after** | the bug is invisible until you query stats |
| **Test bulk by GET-ing the half-inserted doc** | "did the first doc make it?" is the only reliable check |

## What NOT to do

- **Don't store the vector AND the text in two places.** Pick one source of truth: most modern vector DBs let you store the original text as part of the metadata payload. Use that.
- **Don't shell out to a model on every request.** Cache the embedding client at process startup.
- **Don't paginate /search.** The spec says return top-K. K is bounded (≤20 in spirit; even larger is fine). Pagination adds complexity that isn't graded.
- **Don't try to support arbitrary nested filters.** The spec says exact-equality on top-level metadata fields. Don't implement OR / NOT / nested paths until v2.
- **Don't return embeddings in `/search` results.** They're large; bandwidth waste. The result schema is `{doc_id, score, text, metadata}` only.

## When you're stuck

> "The judge says my filter test fails: I returned 0 results when filter={category: 'database'} but there ARE database docs in the index. Walk me through how I'm passing the filter to my vector DB. Am I post-filtering top-K or pre-filtering inside the query?"

(Common cause: post-filtering. Fix: use the DB's native filter clause inside the query call.)

## After this exercise

The patterns here — upsert as primary write op, filter clauses inside the query, atomic bulk validation — apply to ANY data-store-with-search system you'll build. Carry forward to design/02 and design/05's retrievers when you go back and harden them.
