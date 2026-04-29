# EXAMPLES — design/05-langchain-agent

## E1 — pure arithmetic

```http
POST /agent
{ "query": "What's 234 * 17?" }
```

→ `tool_calls: [{ tool: "arithmetic", input: "234 * 17" }]`, `answer: "234 * 17 = 3978"`, `citations: []`.

## E2 — pure retrieval QA

```http
POST /agent
{ "query": "What is BM25?" }
```

→ `tool_calls: [{ tool: "search", input: "BM25" }]`, `answer: "BM25 is a bag-of-words..."`, `citations: ["d003"]`.

## E3 — mixed

```http
POST /agent
{ "query": "What is BM25, and how many tunable parameters does it have multiplied by 10?" }
```

→ both tools. `answer` mentions BM25 explanation + `2 * 10 = 20`. `citations: ["d003"]`.

## E4 — chain: summarise the doc about X

```http
POST /agent
{ "query": "Give me a one-sentence summary of the doc about hybrid retrieval." }
```

→ `tool_calls: [{ tool: "search", ... }, { tool: "summarise", input: "d004" }]`, summary text in `answer`.

## E5 — over-tooling trap (greeting)

```http
POST /agent
{ "query": "hi" }
```

→ `tool_calls: []`, `answer: "Hello! ..."`. Calling `search` on this is a deduction.

## E6 — over-tooling trap (meta question)

```http
POST /agent
{ "query": "What tools do you have available?" }
```

→ Either `tool_calls: []` with a direct answer ("I have search, arithmetic, summarise"), OR a single self-introspection tool call. NOT a `search` call against the corpus.

## E7 — ambiguous (acceptable to ask for clarification)

```http
POST /agent
{ "query": "tell me more" }
```

→ Either a clarifying question in `answer`, or a graceful default. The judge accepts both as long as the agent doesn't fabricate context.

## E8 — `/tools` introspection

```http
GET /tools
```

→ `200 {"tools": [{"name": "search", "description": "..."}, {"name": "arithmetic", "description": "..."}, {"name": "summarise", "description": "..."}]}`. Three entries, names exactly match.
