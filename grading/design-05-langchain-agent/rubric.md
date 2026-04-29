# Rubric — design/05-langchain-agent

## Test types

### `smoke`

Shape correctness. Score 10 if all expected fields present; 0 if 500 or schema-broken; -2 per missing field.

### `tool_selection` (single tool)

The query has a clearly-correct tool. Score on whether the agent picked it.

| Outcome | Score |
| --- | --- |
| Right tool called, correct arguments, correct final answer | **10** |
| Right tool called, correct args, but final answer is slightly off | 7 |
| Right tool called, wrong/garbled args | 5 |
| Wrong tool called (e.g. search instead of arithmetic) | 2 |
| Multiple unnecessary tools called (over-tooling) | 4 |
| No tool called when one was needed | 1 |

For `arithmetic` tests, also check `answer_must_contain` — the actual number must appear in the answer text. If it does not, dock 3 even if the right tool was called (the tool returned the answer but the agent didn't surface it).

### `tool_chain` (multi-tool)

The query requires multiple tools, often in a specific order. Score 10 only when the order is correct AND both tools were used.

| Outcome | Score |
| --- | --- |
| Both tools called in correct order | **10** |
| Both tools called, wrong order (acceptable for unordered cases) | 8 |
| Both tools called but only on tagged-unordered tests; ordered tests dock | 5 |
| Only one of the required tools called | 3 |
| Neither required tool called | 0 |

For `expected.tools_called_unordered`, order doesn't matter. For `expected.tools_called_in_order`, it does.

### `no_tool`

The query should NOT trigger any tool call. Greetings, thanks, meta-questions about the agent.

| Outcome | Score |
| --- | --- |
| `tool_calls` is empty AND answer is appropriate | **10** |
| `tool_calls` is empty but answer is empty/dumb | 7 |
| 1 tool called but agent recovered (final answer is OK) | 5 |
| Multiple tools called for a greeting | **0** |

For `tools_called_max: 1` on the meta-introspection test, allow 1 self-introspection tool call (some agents are designed this way) — score 10 if the answer enumerates the three tools.

### `latency`

p95 across `/agent` calls. SLO 8000ms.

| Outcome | Score |
| --- | --- |
| p95 < 4000ms | **10** |
| p95 4000–8000ms | 8 |
| p95 8000–12000ms | 5 |
| p95 > 12000ms or > 10% timeouts | **0** |

## Pre-flight gate

`GET /health` 200 within 10s; total score 0 if not reachable.

## Endpoint override

The `tool-introspection` test uses `endpoint_override: "GET /tools"` instead of the branch's default `POST /agent`. Treat its `expected` differently: check `tools_field_min_length` and `tool_names_must_include` against the response body.

## Overall scoring

Pass: ≥60%. Strong pass: ≥80% with at least one multi-tool test scoring full credit.

## Strictness note

- For tool_calls, quote the *actual* `tools` list from `observed.body.tool_calls` in your reasoning. Saying "the wrong tool was called" without naming it is docked 1 point on critique quality.
- For arithmetic, quote both the expected value and what the answer string contained. "Expected 3978 in answer; observed answer was 'BM25 is...' (no arithmetic mentioned)."
- Be especially strict on over-tooling. A learner who over-tools on greetings is going to ship a slow, expensive production agent. Dock hard.
