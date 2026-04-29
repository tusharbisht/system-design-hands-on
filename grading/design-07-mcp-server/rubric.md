# Rubric — design/07-mcp-server

## Test types

### `smoke`

Field/status correctness on a single endpoint. 10 on full match; 0 on mismatch.

### `rpc` — JSON-RPC envelope tests

Each test sends a JSON-RPC message and checks the response envelope + content.

**Common envelope checks (apply to every rpc test):**
- HTTP 200 (unless test explicitly expects another status — none do for v1)
- `jsonrpc: "2.0"` field present at top level
- `id` field echoed verbatim from request (with type preserved)
- Either `result` OR `error` at top level (never both, never neither)

If any of these is wrong on any test, dock 2 points from that test's score and call it out in critique.

**`initialize-handshake`** — The full handshake.
| Outcome | Score |
| --- | --- |
| All required fields present (protocolVersion, capabilities, serverInfo) with correct types | **10** |
| serverInfo missing or empty | 6 |
| protocolVersion wrong (e.g., echoed something else) | 4 |
| Returns top-level error or empty result | 0 |

**`tools-list-shape`** — three required tools listed with valid schema.
| Outcome | Score |
| --- | --- |
| All three tools present (echo, add, now); each has name+description+inputSchema | **10** |
| All three present, but some inputSchema is missing/empty | 6 |
| Two present | 4 |
| One present | 2 |
| Wrong shape entirely | 0 |

**`tools-call-echo` / `tools-call-add` / `tools-call-now-iso8601`** — happy paths.

The judge parses `result.content[0].text` as JSON and checks the parsed body contains expected fields.

| Outcome | Score |
| --- | --- |
| Right output, content[0].type='text', isError=false, fields match | **10** |
| Right output but content[0].type missing or wrong | 7 |
| Right output but isError missing or true | 5 |
| Output structurally there but values wrong (e.g., echoed wrong text, sum wrong) | 3 |
| Returns object directly in result instead of via content array | 2 |
| 5xx or top-level error | 0 |

For `tools-call-now-iso8601`: the timestamp must match `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$` AND be within ±5 minutes of the grading wall clock.

| now timestamp | Score |
| --- | --- |
| ISO 8601 UTC, within ±5 min | **10** |
| ISO 8601 but with local timezone | 5 |
| Pythonic str(datetime) (e.g., "2026-04-29 08:00:00+00:00") | 4 |
| Numeric epoch seconds | 2 |
| Wrong format entirely | 0 |

**`tools-call-unknown`** — THE most common grading pitfall.

| Outcome | Score |
| --- | --- |
| `result.isError=true` with content explaining; NO top-level `error` field | **10** |
| `result.isError=true` AND a top-level `error` field (both present) | 4 |
| Top-level `error` with code -32602 or similar (treated as protocol error) | 0 |
| 5xx | 0 |
| 404 / 500 from the tool itself | 1 |

**`unknown-method`** — protocol error.

| Outcome | Score |
| --- | --- |
| Top-level `error.code` = -32601 (Method not found) | **10** |
| Top-level `error` with different code (-32600, -32603) | 6 |
| `result.isError=true` (wrong category) | 2 |
| 5xx | 0 |

**`id-echo-string` / `id-echo-int`** — type preservation.

| Outcome | Score |
| --- | --- |
| id matches exactly with type | **10** |
| id matches as a string but request was int | 5 |
| id missing or null | 0 |

**`jsonrpc-version-present`** — top-level `jsonrpc: "2.0"`.

| Outcome | Score |
| --- | --- |
| Field present, value `"2.0"` | **10** |
| Field present, value `"1.0"` or other | 4 |
| Field missing | 0 |

### `latency`

p95 across all `/mcp` calls. SLO: 200ms.

| Outcome | Score |
| --- | --- |
| Under SLO | **10** |
| 1.5× | 6 |
| 3× | 0 |

## Pre-flight gate

`GET /health` 200 within 10s. Total score 0 otherwise.

## Overall scoring

Pass: ≥60%. The two highest-weight axes are `tools-list-shape` (3.0) and `tools-call-unknown` (3.0) — the latter especially because mixing tool errors with protocol errors is the canonical implementation bug here.

## Strictness notes

- **Quote the exact response body** when grading. "Got `{jsonrpc: '2.0', id: 6, error: {code: -32601, message: '...'}}` — that's a top-level error for an unknown TOOL. Per MCP spec, this should have been `result: {isError: true, content: [...]}`."
- **Test `id` echo with both types.** Both tests run; both must match.
- **Be lenient on `serverInfo.name`/`version` strings** — any reasonable values are OK.
- **Be strict on `protocolVersion`.** It must match the spec version `2025-06-18` (or whichever the request sent if the implementation echoes).
- **A response with BOTH `result` AND `error` is malformed.** Score the offending test 0 even if the visible content otherwise looked fine.
