# SPEC — design/05-langchain-agent

A LangChain (or equivalent agent framework) service that, given a user query, decides which tool(s) to use and answers. Tools available:

1. **search** — semantic search over the corpus (your existing `/search` from design/01 or a fresh impl)
2. **arithmetic** — evaluate an arithmetic expression like `"15 * 7 + 3"` and return the number
3. **summarise** — given a doc_id, return a 1-sentence summary of that doc

The agent must pick the right tool(s) for each query, in the right order, and produce a grounded final answer.

## Endpoints

### `POST /agent`

```http
POST /agent HTTP/1.1
Content-Type: application/json

{ "query": "What is BM25 and what's 15 * 7?" }
```

→ `200 OK`

```json
{
  "query": "What is BM25 and what's 15 * 7?",
  "answer": "BM25 is a bag-of-words ranking function based on term frequency and inverse document frequency. 15 * 7 = 105.",
  "tool_calls": [
    { "tool": "search", "input": "what is BM25", "output_summary": "found d003 (BM25 explained)" },
    { "tool": "arithmetic", "input": "15 * 7", "output_summary": "105" }
  ],
  "citations": ["d003"]
}
```

### `GET /tools`

```json
{
  "tools": [
    { "name": "search", "description": "..." },
    { "name": "arithmetic", "description": "..." },
    { "name": "summarise", "description": "..." }
  ]
}
```

### `GET /health` → `200 {"ok": true}`

## SLOs

```yaml
read_p95_ms: 8000          # /agent end-to-end (multi-step reasoning)
error_rate_pct: 1.0
sustained_rps: 3
```

## Correctness invariants

The judge verifies:

1. **Tool selection accuracy** — for a "calculate this" query, the agent uses `arithmetic`. For a "what is X" query about the corpus, the agent uses `search`. For a multi-step query, both. The judge tests with queries that have a clearly correct tool choice.
2. **Tool order matters** — for a query like "summarise the doc about BM25", the agent must `search → summarise`, not `summarise` alone (no doc_id known yet).
3. **Don't over-tool** — for a simple greeting like "hi" or a meta-question like "what tools do you have?", the agent should answer directly without invoking tools. Calling `search` for "hi" is a deduction.
4. **Citations on retrieval-backed answers** — when the agent uses `search`, the final `citations` must include the relevant doc_ids.
5. **Arithmetic correctness** — `15 * 7 = 105`, not `109` and not "I don't do math".
6. **Schema** — every `tool_call` has `tool`, `input`, `output_summary`. `tool_calls` is an array of length 0+ (length 0 is allowed for direct answers).
7. **`/tools` enumerates exactly the three tools** named above. Names must match. Descriptions can be your own wording.

## Constraints

- Use **LangChain** (or LlamaIndex / Haystack / a custom router — but the goal is to feel LangChain's agent abstractions; a direct-API rewrite misses the point)
- Underlying LLM: any. The agent's reasoning (ReAct or similar) is what's graded, not the LLM identity
- Reuse design/01's retriever via a tool wrapper, OR rebuild — your call

## What you're being graded on

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, `/agent` p95 < 8000ms |
| Tool selection | 35% | right tool(s) for each query |
| Tool order | 15% | correct sequencing on multi-step queries |
| No over-tooling | 10% | direct answer for non-tool queries |
| Final answer correctness | 25% | the answer text is correct AND grounded |
| Schema | 10% | `tool_calls` array shape, `citations` shape, `/tools` enumeration |
| Multi-step reasoning | 5% | for "summarise the doc about X" the agent chains search→summarise |

## Examples

See [`EXAMPLES.md`](EXAMPLES.md).
