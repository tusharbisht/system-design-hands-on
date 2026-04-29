# SPEC — design/07-mcp-server

A **Model Context Protocol (MCP)** server that LLM clients (Claude Desktop, the Anthropic SDK's MCP client, custom agent harnesses) can connect to and call tools on. Implements the MCP **Streamable HTTP transport** with the three core methods: `initialize`, `tools/list`, `tools/call`.

> Reference: [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-06-18) — particularly the JSON-RPC 2.0 message format and the Streamable HTTP transport.

## What you must implement

### Transport: HTTP-with-JSON-RPC at `POST /mcp`

ALL MCP messages go to a single endpoint, `POST /mcp`. The body is a JSON-RPC 2.0 request. The response is a JSON-RPC 2.0 response. Content-Type: `application/json`.

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json

{ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...} }
```

→ `200 application/json`

```json
{ "jsonrpc": "2.0", "id": 1, "result": {...} }
```

(Skipping SSE / batching for v1 — single-message request/response only.)

### Required tools

You implement and expose **at least these three** tools:

1. **`echo`** — returns its input. Trivial. `{"text": "hello"}` → `{"echoed": "hello", "length": 5}`.
2. **`add`** — sums two numbers. `{"a": 3, "b": 4}` → `{"sum": 7}`. Reject non-numbers with a JSON-RPC error.
3. **`now`** — returns current ISO 8601 UTC timestamp. No arguments. `{}` → `{"now_utc": "2026-04-29T08:00:00Z"}`.

You may add more tools; the judge only tests the three above.

## JSON-RPC methods

### `initialize`

Sent by the client first, before any other method.

Request:

```json
{ "jsonrpc": "2.0", "id": 1, "method": "initialize",
  "params": { "protocolVersion": "2025-06-18",
              "capabilities": { "roots": { "listChanged": true } },
              "clientInfo": { "name": "test-client", "version": "1.0" } } }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 1, "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "tools": { "listChanged": false } },
    "serverInfo": { "name": "your-server-name", "version": "1.0.0" } } }
```

`protocolVersion` MUST equal `"2025-06-18"` (echo the client's value if you want forward-compat). `capabilities.tools` MUST be present (signals tool support). `serverInfo.name` and `version` are required strings.

### `tools/list`

Returns the list of tools the server exposes.

```json
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 2, "result": {
    "tools": [
      { "name": "echo",
        "description": "Echo the provided text back",
        "inputSchema": { "type": "object",
          "properties": {"text": {"type": "string"}}, "required": ["text"] } },
      { "name": "add",  "description": "...", "inputSchema": {...} },
      { "name": "now",  "description": "...", "inputSchema": {...} }
    ]
  }
}
```

The judge checks that `tools` contains exactly the three required tools by name, with valid JSON Schema for `inputSchema`.

### `tools/call`

Invoke a tool.

```json
{ "jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": { "name": "add", "arguments": {"a": 3, "b": 4} } }
```

Response (success):

```json
{ "jsonrpc": "2.0", "id": 3, "result": {
    "content": [{"type": "text", "text": "{\"sum\": 7}"}],
    "isError": false
  }
}
```

Response (error — e.g., unknown tool name, or a tool that itself failed):

```json
{ "jsonrpc": "2.0", "id": 3, "result": {
    "content": [{"type": "text", "text": "tool 'foo' is not defined"}],
    "isError": true
  }
}
```

Note: per MCP spec, **tool errors return as `isError: true` inside `result`** — NOT as a JSON-RPC `error` field at the top level. The top-level `error` is reserved for JSON-RPC protocol errors (parse errors, missing method, etc.).

## JSON-RPC error responses

For PROTOCOL errors (not tool errors), use the JSON-RPC 2.0 standard `error` field:

```json
{ "jsonrpc": "2.0", "id": 4, "error": {
    "code": -32601, "message": "Method not found: foo/bar"
  }
}
```

Standard codes (from JSON-RPC 2.0):
- `-32700` Parse error
- `-32600` Invalid Request
- `-32601` Method not found
- `-32602` Invalid params
- `-32603` Internal error

## Auxiliary endpoint

### `GET /health` → `200 {"ok": true}`

Used for the LMS pre-flight check.

## SLOs

```yaml
read_p95_ms: 200      # tools/list and most tools/call invocations
error_rate_pct: 1.0
sustained_rps: 50
```

## Correctness invariants

1. **JSON-RPC envelope is mandatory.** Every `POST /mcp` response must have `"jsonrpc": "2.0"` and either `result` OR `error` (never both, never neither).
2. **The `id` field is echoed.** The response's `id` matches the request's `id` exactly. The judge sends both integer and string `id`s and checks both are echoed correctly.
3. **All three tools work.** Echo round-trips, add sums correctly, now returns a valid ISO-8601 UTC timestamp.
4. **Unknown tool returns `isError: true`** in the `tools/call` result — NOT a top-level JSON-RPC error. Two distinct error categories.
5. **Unknown method returns top-level `error`** with code `-32601`.
6. **Invalid JSON in request body** returns top-level `error` with code `-32700`.
7. **`initialize` is callable repeatedly.** Multiple `initialize` calls should all succeed (the spec allows re-initialization).
8. **`tools/list` returns the tools BY NAME**, not just descriptions — names must match exactly: `echo`, `add`, `now`.

## What you're being graded on

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight | gate | `/health` 200 |
| `initialize` handshake | 15% | required fields present; protocolVersion correct |
| `tools/list` shape | 20% | three tools listed with valid inputSchema |
| `tools/call` happy paths | 30% | echo / add / now all work |
| Tool-error handling | 15% | unknown tool → isError:true in result |
| JSON-RPC errors | 10% | unknown method → -32601; bad JSON → -32700 |
| `id` echo + envelope | 10% | id round-trips; jsonrpc version present |

## Constraints

- **Any language/framework.** Python with FastAPI, Node with Express, Go with chi — all fine. The MCP **Python SDK** (`mcp` package) does most of the work for you if you're in Python.
- **Streamable HTTP transport only.** Don't worry about stdio / SSE for this exercise.
- **No auth required.** Real MCP servers may have auth; this exercise treats the endpoint as open.

## Authoring tip — use the official SDK if you can

The `mcp` Python SDK + `mcp-server-streamable-http` (or equivalent in your language) handles the JSON-RPC framing for you. You write tool definitions; the SDK wires `initialize`, `tools/list`, `tools/call`, and the error envelopes correctly.

If you roll your own (good learning exercise but more work), the JSON-RPC envelope is straightforward:

```python
@app.post("/mcp")
async def mcp(req: Request):
    raw = await req.body()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"}}

    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":     return ok(msg_id, handle_initialize(params))
    if method == "tools/list":     return ok(msg_id, {"tools": TOOLS_DEF})
    if method == "tools/call":     return ok(msg_id, handle_tools_call(params))
    return err(msg_id, -32601, f"Method not found: {method}")
```

See [`EXAMPLES.md`](EXAMPLES.md) for sample request/response pairs.
