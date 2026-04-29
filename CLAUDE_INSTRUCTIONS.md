# Solving Design 01 with Claude Code — faster and better

This is the simplest module in the course but the most important to do well — every later module reuses retrieval. Get the foundation tight.

## Recommended workflow

### 1. Scaffold tightly, ship before you embed

> "Read SPEC.md and EXAMPLES.md. Scaffold a Python FastAPI service with the three endpoints (`POST /search`, `GET /docs/{id}`, `GET /health`) returning hardcoded fixture responses that match the SPEC shape exactly. No embedding logic yet. Then we'll deploy."

Why: ship a *responding* service before you ship a *correct* one. The hardest single task on this branch is getting your hosting working — Render cold-starts, Fly volume mounts, Railway port binding. Discover that with a hello-world response, not a 30-line retriever.

### 2. Add the retriever in plan mode

Press `Shift+Tab`:

> "Plan the retrieval implementation. Use brute-force cosine in numpy over the 15 docs in `corpus/docs.json`. Keep the entire index in memory. Embed on startup, not per-request. Compare two embedding sources: OpenAI ada-002 (paid) vs sentence-transformers/all-MiniLM-L6-v2 (free, local). Recommend one for this exercise."

The `all-MiniLM-L6-v2` recommendation is the right one for this size of corpus — free, fast, no API keys. ada-002 is also fine and a few percentage points better on recall.

### 3. Probe yourself before the judge does

> "Write a small test script `probe.py` that hits my deployed URL with these 5 queries and prints the top-3 results. Save under `tests/probe.py`."

```python
queries = [
  "what is BM25",
  "how does cosine differ from dot product",
  "why does my Postgres table get bloated",
  "what is the airspeed velocity of an unladen swallow",  # OOC
  "vacuum",  # short keyword
]
```

If your probe shows the wrong doc on top for any of the first three, the judge will dock you. Fix the retriever, not the probe.

### 4. Test the boundary conditions

The judge probes:
- empty query (your service should return 400)
- `k=0`, `k=1`, `k=20`, `k=21`
- a doc-id that doesn't exist
- the same query called twice (same response — determinism)
- an OOC query (your top score should be visibly lower than the in-corpus queries)

> "For each of those boundary cases, run a curl against my deployed URL and tell me what the response was. Fix anything that looks wrong, but don't change the spec — change the implementation."

### 5. Latency check before submitting

> "Hit my deployed URL with 50 sequential `/search` calls of varying queries. Report p50, p95, p99 in milliseconds. If p95 > 400ms, find out why."

Common p95 culprits:
- Embedding the corpus per-request (should be once, on startup)
- Cold-start of the embedding model (warm up by embedding a dummy query on startup)
- Synchronous network calls to a remote embedding API (the round-trip alone is 200-500ms; cache or use local embeddings)

### 6. Submit and read the critique

```
LMS slide-3 → paste your URL → Submit
```

The judge writes a per-test score + an overall critique. Read the critique. If you got 50/100 and the critique says "results were good but k=20 returned 21 entries" — that's a 5-line fix away from passing. Don't re-architect in response to small criticisms.

## Claude Code techniques that pay off here

| Technique | Why it matters here |
| --- | --- |
| **Ship the API shell first** | hosting bugs are 60% of why the first submission fails — debug those before logic |
| **Plan-mode the retriever** | embedding choice is the single biggest knob; let Claude lay out the trade-offs |
| **Probe yourself with curl/httpx** | the judge runs ~10 probes; you should run 10-20 of your own first |
| **Read the rubric.md** | it's public on this repo; your tests should map 1:1 to its axes |

## What NOT to do

- **Don't reach for a vector DB.** 15 documents, brute-force numpy. A vector DB is the right answer when you have ~100k+ vectors.
- **Don't use GPT-4 for the retrieval itself.** This branch is *embedding* search — no LLM in the loop. (The next branch adds the LLM.)
- **Don't randomize anything.** Determinism is graded. If you add temperature or sampling anywhere, you've broken the contract.
- **Don't stuff in tools you "might need later".** Save LangChain for design/05; save reranking for design/03. This branch is one model + one numpy array.
- **Don't fake high scores on OOC queries** to make your service "look confident". The judge tests this; you'll dock 15%.

## When you're stuck

> "I deployed to Render and the judge says it can't reach my URL. Show me my service's recent logs (you can access them via Render's CLI), and check whether my service is binding to 0.0.0.0:$PORT or just 127.0.0.1:8000."

(Render expects `0.0.0.0:$PORT` — `$PORT` is set in the env. Common first deployment bug.)

## After this exercise

You have a working semantic-search service. Next branch (design/02) adds the LLM that *answers* questions using your retrieval. The judge there is harsher: it checks not only that you retrieve the right docs, but that the LLM's answer cites them faithfully and refuses to invent facts.
