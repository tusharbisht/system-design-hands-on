# Design 01 — Semantic search

**Type:** system-design — build, host, submit a URL
**Estimated time:** 4–6h with Claude Code
**Auto-graded:** recall@5 on 10 labeled queries + p95 latency + result-shape invariants

## The problem

You're shipping a small "search this docs site" feature. The corpus is 15 short documents on database internals, retrieval, and LLM frameworks (`corpus/docs.json` on `main`). You need a service that takes a natural-language query and returns the most semantically similar documents.

This is the simplest piece of a RAG stack — get it right before moving on.

## What you're building

A service exposing `POST /search`, `GET /docs/{id}`, `GET /health`. Full contract in [`SPEC.md`](SPEC.md). Sample requests in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

1. Service running publicly on a URL the judge can hit
2. `/health` returns 200
3. The 10 labeled queries (judge holds these privately — see [`grading/design-01-semantic-search/judge.json`](grading/design-01-semantic-search/judge.json) for the public version) get the right top-5
4. p95 latency under 500ms on `/search` (k=5)
5. Result shape exactly matches SPEC

When all of those are true, the judge gives you ≥ 60/100 — passing.

## Constraints

- Use `corpus/docs.json` from `main` unchanged (15 documents)
- Pick any embedding model and vector store
- Pick any language/framework
- No new corpus, no synthetic data — the judge tests on the published corpus

## What's deliberately left to you

- **Embedding model**: OpenAI ada-002 (cheap, fine), Cohere embed-english-v3, sentence-transformers (local, free), Voyage — your call. The judge doesn't care which.
- **Vector store**: pgvector / Qdrant / Chroma / FAISS / numpy in memory / scipy cosine. For 15 docs, brute-force in numpy is fine and fastest to ship.
- **Hosting**: Render / Fly / Railway free tiers are sufficient. Cold-start delay > 30s will fail the pre-flight; warm your service before submitting.

## How you're graded

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight | gate | `/health` 200; `/search` round-trip works |
| Result shape | 20% | fields present, k bound respected |
| Recall@5 | 50% | did the right doc come up for labeled queries |
| Order + determinism | 15% | descending sort; same input → same output |
| OOC handling | 15% | weird queries get low scores; don't fake confidence |

## Hints

<details><summary>Hint 1 — start with brute-force cosine, not a vector DB</summary>

You have 15 documents. A vector DB is over-engineering. On startup, embed the 15 docs once, hold them in memory as a numpy array. `/search` embeds the query, computes 15 cosine scores, sorts, returns top-k. This will easily make the latency SLO and is ~30 lines of Python. Add a vector DB only if you intentionally want to learn the ops; the judge doesn't reward complexity.

</details>

<details><summary>Hint 2 — normalize embeddings once, then use dot product</summary>

If your embeddings are unit-length (most APIs return normalized; verify with `np.linalg.norm`), `cosine(a, b) == dot(a, b)`. Dot product is faster and trivially batchable as `corpus_matrix @ query_vec`. Saves a divide per pair.

</details>

<details><summary>Hint 3 — pre-flight = a /health endpoint AND a warm cache</summary>

The LMS judge does `GET /health` before testing. If `/health` returns 200 instantly but `/search` takes 30 seconds because you embed-on-first-call, your latency SLO will fail. Pre-load on startup. Render/Fly cold-start can also kick you out — hit your service once with a warm-up curl right before submitting.

</details>

## Why this exercise exists

Most RAG bugs in production are *retrieval* bugs, not *generation* bugs. If your retriever can't find the right doc, no amount of GPT-4 will save the answer. This branch isolates retrieval so you can feel where it breaks (paraphrasing, OOC, k bounds, determinism) before adding the LLM in design/02.

## See also

- [SPEC.md](SPEC.md) — full API contract and SLOs
- [EXAMPLES.md](EXAMPLES.md) — sample request/response
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md) — recommended Claude Code workflow
- [grading/design-01-semantic-search/](grading/design-01-semantic-search/) — public judge.json + rubric.md
