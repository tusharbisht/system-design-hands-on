# Design 05 — LangChain agent

**Type:** system-design — build, host, submit a URL
**Estimated time:** 8–12h with Claude Code
**Auto-graded:** tool selection accuracy + chaining + no over-tooling + final-answer correctness

## The problem

You've built retrieval (design/01) and grounded QA (design/02). Now: a query might need NO tool, ONE tool, or MULTIPLE tools in sequence. The agent has to *decide*.

Example: *"What is BM25, and what's 15 * 7?"* — needs both `search` (for BM25) and `arithmetic` (for 15 * 7), then synthesises one answer. Tool selection is the agent's hardest property to get right.

## What you're building

A LangChain (or equivalent) agent exposing:
- `POST /agent` — accepts a query, returns answer + tool_calls + citations
- `GET /tools` — enumerates the three tools you've registered
- `GET /health`

Three tools must be implemented and registered:
1. **search** — semantic search (reuse design/01)
2. **arithmetic** — eval of arithmetic expressions
3. **summarise** — given a `doc_id`, return a 1-sentence summary

Full contract in [`SPEC.md`](SPEC.md), examples in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

The judge probes 10–12 queries. For each, it checks:
- Was the right tool selected?
- For multi-step queries, was the order correct?
- For zero-tool queries (greeting, meta), did the agent NOT call tools needlessly?
- Is the final answer correct AND grounded?

Pass: ≥60%. Strong pass: ≥80%, including the multi-step chaining tests.

## Why this is harder than design/02

Tool selection is *under-determined*. The same query can be answered multiple ways:
- *"What's 100?"* — math? Or a question about the number 100? (Probably no tool — just say "100".)
- *"Summarise BM25"* — `search` then `summarise`? Or just `search`? (The first is more literal; both are defensible.)

The judge tests cases where there IS a clearly correct choice. But your agent will face ambiguous cases too. Build it to be conservative: only call a tool when needed.

## Constraints

- Use LangChain's agent framework (or LlamaIndex / Haystack). The point is to learn the framework, not bypass it.
- Reuse design/01's retriever as the `search` tool's backend (or build a fresh one — your call).
- Underlying LLM: any.
- The arithmetic tool can use `eval()` (sandboxed!) or a proper expression parser. Don't ship a service that runs arbitrary Python.

## Hints

<details><summary>Hint 1 — start with LangChain's `create_react_agent`</summary>

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search the corpus for documents matching the query. Returns top-3 docs with their IDs."""
    return httpx.post(SEARCH_URL, json={"query": query, "k": 3}).json()

@tool
def arithmetic(expression: str) -> str:
    """Evaluate an arithmetic expression. Supports +, -, *, /, **, parentheses."""
    return str(eval(expression, {"__builtins__": {}}, {}))

@tool
def summarise(doc_id: str) -> str:
    """Return a 1-sentence summary of a document by id."""
    doc = httpx.get(f"{SEARCH_URL}/docs/{doc_id}").json()
    # use a small LLM call here, or a deterministic first-sentence heuristic
    ...

llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)
agent = create_react_agent(llm, [search, arithmetic, summarise], prompt=...)
executor = AgentExecutor(agent=agent, tools=[...], return_intermediate_steps=True)
```

`return_intermediate_steps=True` gives you the tool_calls list to surface in the response.

</details>

<details><summary>Hint 2 — strong tool descriptions are 80% of selection accuracy</summary>

LangChain agents pick tools based on the docstring. *"Search the corpus"* is too vague. *"Use this when the user asks a factual question about databases, retrieval, or LLM frameworks. Returns the top-3 most relevant document IDs and their text. Do NOT use this for arithmetic or general greetings."* is much better.

The "do NOT use this for X" sentence is the secret — explicit negative examples in tool descriptions slash false positives.

</details>

<details><summary>Hint 3 — over-tooling is your most likely failure mode</summary>

Default agents call a tool for almost every query. Add to your prompt: *"If you can answer the user's question without any tools, do so directly. Don't call a tool just to look busy."*

Test it: send `"hi"`, `"thanks"`, `"what tools do you have?"`. Each should produce zero tool calls.

</details>

<details><summary>Hint 4 — chaining requires the LLM to know about the previous tool's output</summary>

*"Summarise the doc about BM25"* requires:
1. `search("BM25")` → returns `[{"doc_id": "d003", ...}]`
2. The LLM reads the search output and sees `d003`
3. `summarise("d003")` → returns the summary

LangChain handles this via the ReAct loop automatically — but only if your `search` tool's output includes the doc_id clearly. Don't return just text; return structured JSON the LLM can pluck IDs from.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-05-langchain-agent/](grading/design-05-langchain-agent/)
