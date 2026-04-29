# System Design Hands-On — RAG + LangChain

A hands-on system-design course where you **build and host a small distributed-systems primitive end-to-end**, then submit a public URL. An LMS-side LLM judge probes your service with adversarial questions and grades answers against a rubric.

> This is a system-design teaching repo. Each branch is one system to design. The deliverable is **a running service at a URL**, not a passing test suite. See [`CLAUDE.md`](CLAUDE.md) for authoring conventions.

## Course map

### Retrieval / RAG / agents

| Branch | What you build | Time | Auto-graded |
| --- | --- | --- | --- |
| [`tour/workflow`](../../tree/tour/workflow) | how the course works, demo URL submission | 15 min | — |
| [`design/01-semantic-search`](../../tree/design/01-semantic-search) | `POST /search` semantic search over a fixed corpus | 4–6h | recall@K, latency p95 |
| [`design/02-rag-qa`](../../tree/design/02-rag-qa) | `POST /ask` — retrieve + answer with citations | 6–8h | answer faithfulness, citation accuracy, OOC refusal |
| [`design/05-langchain-agent`](../../tree/design/05-langchain-agent) | LangChain agent: router + tools (search, arithmetic, summarise) | 8–12h | tool selection accuracy, multi-step reasoning |
| [`design/06-vector-database`](../../tree/design/06-vector-database) | real vector DB (Pinecone / Weaviate / Qdrant / pgvector) with metadata filters, upserts, bulk atomicity | 6–10h | recall, filter correctness, upsert vs insert, delete durability |
| [`design/07-mcp-server`](../../tree/design/07-mcp-server) | MCP server (Streamable HTTP transport): `initialize` / `tools/list` / `tools/call` | 4–6h | JSON-RPC envelope, three required tools, protocol-vs-tool error distinction |

### Classic system-design — scale + concurrency

| Branch | What you build | Time | Auto-graded |
| --- | --- | --- | --- |
| [`design/03-tinyurl`](../../tree/design/03-tinyurl) | URL shortener with idempotent shortening, custom aliases, 302 round-trip | 4–6h | idempotency, no collisions on 50 distinct URLs, alias semantics |
| [`design/04-booking-concurrency`](../../tree/design/04-booking-concurrency) | reservation service — 20 concurrent users race for one slot, exactly one wins | 6–8h | race-condition correctness (40% weight), cancel + re-book, owner-only DELETE |

Recommended order for the curious: tour → 01 → 02 → 06 → 03 → 04 → 05 → 07.

## Submission flow

1. Build the service — any language, any framework
2. Host it publicly (Render / Fly / Railway / your own VPS)
3. Submit the URL on the module's slide-3
4. The LMS hits the URL with the branch's adversarial probe set + LLM judge
5. You see your score (correctness / faithfulness / latency) and a written critique

There's no fork. There's no PR. **The URL is the artifact.**

## Why this format

System design isn't whiteboard arrows. The bugs are in the joints — chunking strategy hidden behind a beautiful retriever, citation accuracy degrading in multi-turn, agent tool-selection drifting on edge cases. **You only find them by running real adversarial probes against a real service.**

This course gives you:
- A spec strict enough that you can't fudge the contract
- An adversarial probe set the judge actually uses
- A rubric that scores faithfulness + correctness, not just "did the API respond 200"

## Quick start

```bash
git clone https://github.com/tusharbisht/system-design-hands-on.git
cd system-design-hands-on
git checkout design/01-semantic-search
cat EXERCISE.md            # framing
cat SPEC.md                # API contract
cat EXAMPLES.md            # sample requests
```

Build, host, submit on the LMS at `https://<lms-host>/courses/tusharbisht-system-design-hands-on`.

## What you'll need

- An LLM API key (OpenAI / Anthropic / OpenRouter / a local model — your choice)
- An embedding source (OpenAI ada-002, Cohere, sentence-transformers, etc.)
- A vector store (pgvector / Qdrant / Chroma / Pinecone / your own — your choice)
- A hosting provider where the URL is reachable from the public internet

Free tiers across these are sufficient for a single learner running through the course.

## What's NOT graded

- Your code style
- Whether you used FastAPI vs Express vs Spring Boot
- Whether you used pgvector vs Qdrant vs in-memory cosine
- How you chose to chunk

What IS graded: **what your service returns when probed.** Pick the stack you want to learn; the judge doesn't care.

## Course metadata

- **Format**: 7 system-design branches + 1 walkthrough
- **Total time**: 38–58 hours of focused work
- **Prereqs**: comfortable with HTTP APIs, JSON, and *one* programming language
- **Output**: a portfolio of hosted services demonstrating retrieval, agents, classic system design, and protocol design
