# Solving Design 05 with Claude Code — faster and better

Tool selection is the agent's hardest property — and it's *graded*. Spend your time on tool descriptions and the over-tooling guard, not on perfect prompts.

## Recommended workflow

### 1. Read the rubric BEFORE the framework

> "Read `SPEC.md`, `EXAMPLES.md`, and `grading/design-05-langchain-agent/rubric.md`. List the 7 axes the judge will score. For each, give me one specific failure case I should defend against."

The rubric is your spec. The single biggest mistake on this branch is to start coding the agent before knowing what the judge cares about.

### 2. Stub the API + tool registry first

> "Scaffold a LangChain agent with three tools (`search`, `arithmetic`, `summarise`), each returning a hardcoded fixture. Wire `POST /agent` to invoke the agent. Wire `GET /tools` to list the three tools. Don't build out the tools yet — let me see the agent reasoning loop fire on a fake input first."

Get the LangChain machinery moving with fake tools. Verify ReAct's Thought→Action→Observation loop works in your env. Then plug in real tools one at a time.

### 3. Write tool descriptions like negative examples matter

> "Critique these three tool docstrings. Each should make the agent's selection decision unambiguous. Add a `Do NOT use this when:` clause to each. Don't rewrite — just add."

Most agent failures trace to tool docstrings being too positive ("use this for searching") without negatives ("do NOT use this for arithmetic, greetings, or meta-questions about the agent itself"). The negative sentence is what kills false positives.

### 4. Probe the four quadrants

```python
single_tool = [
  ("What is BM25?", ["search"]),
  ("What's 234 * 17?", ["arithmetic"]),
]
multi_tool_chained = [
  ("Summarise the doc about BM25", ["search", "summarise"]),
  ("What is BM25 and how many parameters times 10?", ["search", "arithmetic"]),
]
zero_tool = [
  ("hi", []),
  ("what tools do you have?", []),
  ("thanks!", []),
]
ambiguous = [
  ("tell me about retrieval", ["search"]),  # one tool is fine
]

for q, expected_tools in single_tool + multi_tool_chained + zero_tool + ambiguous:
    r = httpx.post(URL + "/agent", json={"query": q}).json()
    actual = [tc["tool"] for tc in r["tool_calls"]]
    print(f"Q: {q}\n  expected: {expected_tools}\n  actual:   {actual}\n  answer:   {r['answer'][:80]}")
```

The third column (zero_tool) is where you'll fail first. Every default LangChain setup over-tools on greetings. Fix this before submitting.

### 5. Set temperature to 0 — full stop

Agents are non-deterministic by default. The judge runs the same query multiple times in some test paths. Set temperature=0 on the agent's LLM. Tool selection becomes reliable; the small fluency loss is irrelevant for this graded behavior.

### 6. Read the judge's per-test critique carefully

The critique is your debug log. If it says:

> "expected tool sequence ['search', 'summarise'] for 'summarise the doc about hybrid retrieval'; actual was ['search'] only — agent retrieved the doc but didn't invoke summarise on the doc_id"

That tells you exactly: your `search` tool isn't returning the doc_id in a form the LLM picks up. Fix the search tool's output structure (return `{"doc_id": "d004", "title": "...", "snippet": "..."}` not just `"d004: Hybrid retrieval..."`).

## Claude Code techniques that pay off here

| Technique | Why it matters here |
| --- | --- |
| **Read rubric.md first, code second** | the judge grades 7 axes; missing one is a 10–20% loss |
| **Strong negative tool descriptions** | the single biggest lever on selection accuracy |
| **Four-quadrant probe (single / multi / zero / ambiguous)** | finds over-tooling and under-tooling separately |
| **temperature=0** | agents need to be deterministic to debug |
| **Read the judge's "expected vs actual tool sequence"** | maps directly to what you change |

## What NOT to do

- **Don't bypass LangChain with hand-rolled routing.** The exercise is to feel agent abstractions; rolling your own switch statement misses the lesson.
- **Don't add tools the rubric doesn't ask for.** Adding a `weather` tool because "it might be useful" pollutes the selection space.
- **Don't ship `eval()` un-sandboxed.** `arithmetic("__import__('os').system('rm -rf /')")` is the obvious risk. Use `ast.literal_eval` for simple cases or a proper math parser. The judge does NOT test injection — but you should care.
- **Don't return raw search-result text from the search tool** — the LLM can't reliably extract doc_ids from prose. Return JSON with explicit `doc_id` fields.
- **Don't print the entire tool_call's intermediate output in `tool_calls.output_summary`.** Keep it short — 1-line. The judge only needs to verify the right tool was called; full output dumps blow up response sizes.

## When you're stuck

> "The judge says 'agent over-tools on `hi` — invoked search'. Show me the prompt I'm passing to `create_react_agent` and add a constraint that says 'if the user input is a greeting, courtesy, or meta-question about the agent, respond directly without calling any tool'. Then re-test."

(The fix is usually 1 line in the system prompt + 1 negative example in the search tool's description.)

## After this exercise

You've now built: pure retrieval (01), grounded QA (02), and tool-routed agent (05). The skills compose: a production RAG-with-tools system at a real company looks roughly like the union of these three. The hardest thing in production is calibration — knowing when retrieval is enough, when an agent helps, and when both are over-engineering. That comes with the practice this course gives you.
