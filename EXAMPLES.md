# EXAMPLES — design/07-mcp-server

All examples assume the server is running and reachable. Send all requests to `POST /mcp` with `Content-Type: application/json`.

## E1 — initialize handshake

Request:

```json
{ "jsonrpc": "2.0", "id": 1, "method": "initialize",
  "params": { "protocolVersion": "2025-06-18",
              "capabilities": { "roots": { "listChanged": true } },
              "clientInfo": { "name": "judge-client", "version": "0.1" } } }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 1,
  "result": { "protocolVersion": "2025-06-18",
              "capabilities": { "tools": { "listChanged": false } },
              "serverInfo": { "name": "my-mcp-server", "version": "1.0.0" } } }
```

## E2 — list tools

```json
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 2,
  "result": { "tools": [
    { "name": "echo",
      "description": "Return the provided text and its length",
      "inputSchema": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
      } },
    { "name": "add",
      "description": "Sum two numbers a + b",
      "inputSchema": {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"]
      } },
    { "name": "now",
      "description": "Return the current UTC timestamp in ISO 8601",
      "inputSchema": {"type": "object", "properties": {}}
    }
  ] } }
```

## E3 — call `echo`

Request:

```json
{ "jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": {"name": "echo", "arguments": {"text": "hello world"}} }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 3,
  "result": { "content": [{"type": "text", "text": "{\"echoed\": \"hello world\", \"length\": 11}"}],
              "isError": false } }
```

(Tool returns its result as JSON-encoded text inside `content[0].text` — that's the MCP convention.)

## E4 — call `add`

Request:

```json
{ "jsonrpc": "2.0", "id": 4, "method": "tools/call",
  "params": {"name": "add", "arguments": {"a": 3, "b": 4}} }
```

Response (`result.content[0].text` parsed):

```json
{"sum": 7}
```

## E5 — call `now`

Request:

```json
{ "jsonrpc": "2.0", "id": 5, "method": "tools/call",
  "params": {"name": "now", "arguments": {}} }
```

Response (`result.content[0].text` parsed):

```json
{"now_utc": "2026-04-29T08:00:00Z"}
```

(Format: ISO 8601, UTC, with "Z" suffix or "+00:00".)

## E6 — call unknown tool → `isError: true`

```json
{ "jsonrpc": "2.0", "id": 6, "method": "tools/call",
  "params": {"name": "foo", "arguments": {}} }
```

Response (200 OK at HTTP level; error inside the `result`):

```json
{ "jsonrpc": "2.0", "id": 6,
  "result": { "content": [{"type": "text", "text": "tool 'foo' is not defined"}],
              "isError": true } }
```

NOT the top-level JSON-RPC `error` field — that's reserved for protocol-level problems (parse errors, missing methods).

## E7 — unknown method → top-level error

```json
{ "jsonrpc": "2.0", "id": 7, "method": "tools/foo", "params": {} }
```

Response:

```json
{ "jsonrpc": "2.0", "id": 7,
  "error": { "code": -32601, "message": "Method not found: tools/foo" } }
```

## E8 — invalid JSON → parse error

Request body: `{not valid json`

Response:

```json
{ "jsonrpc": "2.0", "id": null,
  "error": { "code": -32700, "message": "Parse error" } }
```

## E9 — `id` echo (string id)

Request `id: "abc-123"` → response `id: "abc-123"` (echoed exactly, including type — strings stay strings, integers stay integers).

## E10 — health

```http
GET /health
```

→ `200 {"ok": true}`
