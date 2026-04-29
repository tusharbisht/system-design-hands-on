# EXAMPLES — design/02-rag-qa

## E1 — directly answerable from one doc

```http
POST /ask
{ "question": "What does VACUUM do in Postgres?" }
```

→

```json
{
  "question": "What does VACUUM do in Postgres?",
  "answer": "VACUUM reclaims storage from dead tuples — old row versions left behind by Postgres's MVCC concurrency model. Autovacuum handles this automatically in normal operation.",
  "citations": ["d001"],
  "retrieved_doc_ids": ["d001", "d013", "d014"]
}
```

## E2 — synthesis across two docs

```http
POST /ask
{ "question": "How do I combine BM25 and vector search results into one ranking?" }
```

→ answer should reference Reciprocal Rank Fusion; `citations` should include `d004` (and possibly `d003` for BM25 explanation).

## E3 — out-of-corpus

```http
POST /ask
{ "question": "What's the population of Tokyo?" }
```

→ `citations: []`, `answer` expresses inability ("I don't know", "not in my knowledge base", etc.). `retrieved_doc_ids` still has 1+ entries (you ran retrieval; it just returned weak matches).

## E4 — adversarial: question whose answer LOOKS like it should be in the corpus but isn't

```http
POST /ask
{ "question": "What's the recommended chunk size for embedding models trained on Tagalog?" }
```

The corpus mentions chunking strategy in general (d005) but says nothing about Tagalog. The LLM might be tempted to invent a number. **Don't.** Refuse — `citations: []`, answer says "I don't have information specific to Tagalog."

## E5 — the lazy-refusal trap

```http
POST /ask
{ "question": "What chunk size should I use for RAG?" }
```

This IS in the corpus (d005 says 256–512 tokens). The judge tests that you DON'T refuse here. A blanket "I don't know" refusal scores 0 on the non-lazy-answer axis.

## E6 — health probe

```http
GET /health
```

→ `200 {"ok": true}`
