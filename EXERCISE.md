# Design 07 — MCP server (Streamable HTTP transport)

**Type:** system-design — build, host, submit a URL
**Estimated time:** 4–6h with Claude Code
**Auto-graded:** JSON-RPC envelope correctness, three required tools, error-handling for tool-vs-protocol failures, `id` echo, schema for `tools/list`

## The problem

You're building a **Model Context Protocol (MCP)** server. MCP is the open protocol Claude Desktop, the Anthropic SDK's MCP client, and a growing list of agent harnesses use to talk to external tools. You'll implement the **Streamable HTTP transport** (HTTP request → JSON-RPC response) — the most common transport for hosted MCP servers.

Three tools exposed by your server: `echo`, `add`, `now`. That's it. The lesson is **the protocol, not the tools**: get the JSON-RPC envelope right, get `tools/list` and `tools/call` right, distinguish protocol errors from tool errors.

## What you're building

A single endpoint: `POST /mcp` accepting JSON-RPC 2.0 messages, plus `GET /health`. Full contract in [`SPEC.md`](SPEC.md), 10 sample messages in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

- `/health` returns 200
- `initialize` returns protocolVersion `2025-06-18` and a `serverInfo` block
- `tools/list` returns the three tools (`echo`, `add`, `now`) each with valid `inputSchema`
- `tools/call` succeeds for all three tools on valid input
- `tools/call` for an UNKNOWN tool returns `isError: true` inside `result` — NOT a top-level JSON-RPC error
- An unknown METHOD returns a top-level JSON-RPC error with code `-32601`
- Invalid JSON returns code `-32700`
- The `id` from the request is echoed in the response, type-preserved (int → int, string → string)

Pass: ≥60%. Strong pass: ≥80% with the protocol-error-vs-tool-error distinction handled correctly (this is where most submissions trip).

## Why this exercise exists

Every coding agent ecosystem in 2025 will have to talk MCP. As an engineer building integrations, you'll either be the *server* exposing tools to LLMs, or the *client* calling third-party servers. Knowing the wire protocol — what `initialize` looks like, what envelope `tools/list` returns, how a tool error differs from a transport error — is now table-stakes infrastructure literacy.

## Constraints

- Any language. Python with `mcp` SDK is the easiest. Node, Go, Rust all viable.
- **Streamable HTTP transport only** for v1. The MCP spec also defines stdio + SSE; ignore them.
- The judge sends single-message request/response pairs. You don't need to implement batching.
- No auth.

## Hints

<details><summary>Hint 1 — try the SDK first; roll your own only if you must</summary>

Python: `pip install mcp`. The SDK provides FastMCP and the JSON-RPC framing — you write `@mcp.tool()` decorators on your three functions and you're 80% done.

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("my-server")

@mcp.tool()
def echo(text: str) -> dict:
    return {"echoed": text, "length": len(text)}

@mcp.tool()
def add(a: float, b: float) -> dict:
    return {"sum": a + b}

@mcp.tool()
def now() -> dict:
    from datetime import datetime, timezone
    return {"now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
```

Then mount it on a streamable HTTP transport. The SDK + a small FastAPI bridge is ~30 lines.

(If the SDK is hard to install or limiting, roll your own JSON-RPC handler — it's ~100 lines. The judge tests the WIRE behavior, not which library.)

</details>

<details><summary>Hint 2 — the two error categories</summary>

```
                        ┌─ JSON-RPC `error` field (top level)
                        │  Code -32700: Parse error (bad JSON)
                        │  Code -32601: Method not found (unknown method)
PROTOCOL ERRORS  ───────┤  Code -32602: Invalid params
                        │  Code -32603: Internal server error

                        ┌─ `result.isError = true` with content
TOOL ERRORS  ───────────┤  Tool name unknown: "tool 'foo' is not defined"
                        │  Tool argument invalid: "expected number for 'a'"
                        │  Tool internal failure: "...stack trace..."
```

Mixing them up is the #1 grading pitfall. `tools/call` with an unknown tool name is NOT a "method not found" — `tools/call` IS the method, and it ran successfully; the tool inside it failed.

</details>

<details><summary>Hint 3 — `id` echo, with types preserved</summary>

The judge sends both integer and string IDs:

```
{"id": 1, ...}    →  response must have "id": 1     (integer)
{"id": "x-7", ...} → response must have "id": "x-7" (string)
```

Don't coerce to string. Don't generate your own. Echo verbatim.

</details>

<details><summary>Hint 4 — `tools/call` result shape</summary>

The MCP spec says tool results go in `content` as an array of typed parts. For text-returning tools (which is most), use:

```json
{"content": [{"type": "text", "text": "<JSON-encoded-string-of-the-tool-output>"}],
 "isError": false}
```

The `content[0].text` is itself a STRING (typically containing JSON, but it's a text block as far as MCP is concerned). Clients parse it.

Don't put the tool's structured output directly in `result` — the MCP spec mandates the content/isError envelope.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-07-mcp-server/](grading/design-07-mcp-server/)
- [MCP Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
