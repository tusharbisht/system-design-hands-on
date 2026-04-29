# Solving Design 07 with Claude Code — faster and better

The trap: thinking this is "build three tools". It's "implement a JSON-RPC envelope correctly". The tool work is trivial; the protocol work is where mistakes hide.

## Recommended workflow

### 1. Read the SPEC + RFC link in detail before any code

> "Read SPEC.md, EXAMPLES.md, and grading/design-07-mcp-server/rubric.md. Then fetch the MCP Streamable HTTP transport spec at https://modelcontextprotocol.io/specification/2025-06-18 and the JSON-RPC 2.0 spec at https://www.jsonrpc.org/specification. List for me: (a) the exact shape of an `initialize` response, (b) the exact shape of a successful `tools/call` result, (c) the exact shape of a tool-error vs a protocol-error response."

The spec has the answers. Reading it first saves an hour of submitted-and-corrected.

### 2. Pick: SDK or roll-your-own

Plan mode (Shift+Tab):

> "Plan the implementation. Compare two approaches:
> (a) Use the `mcp` Python SDK with FastMCP — `@mcp.tool()` decorators wire everything.
> (b) Roll my own JSON-RPC handler in FastAPI — full control, ~100 lines.
> For each: setup time, control over error envelopes, debuggability. Recommend ONE for shipping in a half-day."

If the SDK installs cleanly, it's the right call. If you hit version-skew issues (the SDK has been moving), roll your own — the wire protocol is small.

### 3. Implement the JSON-RPC dispatcher first

If rolling your own:

```python
@app.post("/mcp")
async def mcp(req: Request):
    raw = await req.body()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return jsonrpc_error(None, -32700, "Parse error")

    msg_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        return jsonrpc_ok(msg_id, do_initialize(params))
    if method == "tools/list":
        return jsonrpc_ok(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        return jsonrpc_ok(msg_id, do_tools_call(params))
    return jsonrpc_error(msg_id, -32601, f"Method not found: {method}")
```

Three helpers (`jsonrpc_ok`, `jsonrpc_error`) that wrap the envelope. The dispatcher is 20 lines.

### 4. Implement the three tools

```python
def tool_echo(args):
    text = args["text"]
    return {"echoed": text, "length": len(text)}

def tool_add(args):
    a = args["a"]; b = args["b"]
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("a and b must be numbers")
    return {"sum": a + b}

def tool_now(args):
    return {"now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

TOOLS_REGISTRY = {"echo": tool_echo, "add": tool_add, "now": tool_now}

def do_tools_call(params):
    name = params.get("name")
    args = params.get("arguments") or {}
    fn = TOOLS_REGISTRY.get(name)
    if fn is None:
        # TOOL error — NOT protocol error
        return {"content": [{"type": "text", "text": f"tool '{name}' is not defined"}],
                "isError": True}
    try:
        out = fn(args)
        return {"content": [{"type": "text", "text": json.dumps(out)}],
                "isError": False}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                "isError": True}
```

### 5. Probe yourself

```python
import httpx, json
URL = "http://localhost:8000/mcp"

def call(method, params=None, msg_id=1):
    body = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
    r = httpx.post(URL, json=body)
    return r.json()

# 1. initialize
r = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
assert "result" in r and r["result"]["protocolVersion"] == "2025-06-18"
print("✓ initialize")

# 2. tools/list
r = call("tools/list", {}, msg_id=2)
names = [t["name"] for t in r["result"]["tools"]]
assert sorted(names) == ["add", "echo", "now"], names
print("✓ tools/list:", names)

# 3. tools/call echo
r = call("tools/call", {"name": "echo", "arguments": {"text": "hi"}}, msg_id=3)
assert r["result"]["isError"] is False
out = json.loads(r["result"]["content"][0]["text"])
assert out["echoed"] == "hi" and out["length"] == 2
print("✓ echo")

# 4. tools/call add
r = call("tools/call", {"name": "add", "arguments": {"a": 3, "b": 4}}, msg_id=4)
out = json.loads(r["result"]["content"][0]["text"])
assert out["sum"] == 7
print("✓ add")

# 5. tools/call unknown -> isError true (NOT top-level error)
r = call("tools/call", {"name": "foo", "arguments": {}}, msg_id=5)
assert r["result"]["isError"] is True
assert "error" not in r        # NOT top-level error
print("✓ unknown tool → isError")

# 6. unknown method -> top-level error -32601
r = call("foo/bar", {}, msg_id=6)
assert r["error"]["code"] == -32601
print("✓ unknown method → -32601")

# 7. id echo: string
r = call("initialize", {}, msg_id="abc-7")
assert r["id"] == "abc-7"      # string preserved
print("✓ id echo (string)")

# 8. invalid JSON
r = httpx.post(URL, content=b"{not json").json()
assert r["error"]["code"] == -32700
print("✓ parse error → -32700")
```

If all eight print, you're done.

### 6. Submit and read the critique

The judge runs essentially these eight probes. Common first failures:

- **`isError` test fails**: you returned a top-level `error` for an unknown tool. Move to `result.isError`.
- **`id` echo fails**: you used `int(msg.get("id"))` somewhere, breaking string IDs. Just preserve `msg.get("id")` verbatim.
- **`tools/list` shape fails**: missing `inputSchema`, or schema isn't valid JSON Schema. Each tool MUST have `inputSchema`.
- **timestamp format fails on `now`**: returned `2026-04-29 08:00:00.123456` (Python default). Use ISO 8601 with `Z` suffix or `+00:00`.

## Claude Code techniques that pay off here

| Technique | Why it matters |
| --- | --- |
| **Read the actual MCP + JSON-RPC specs first** | the wire protocol is precise — guesswork costs submissions |
| **Plan-mode SDK vs roll-your-own** | each has trade-offs; pick before installing |
| **Probe-yourself with 8 distinct messages** | the judge runs 8 cases; cover them locally first |
| **Validate `id` echo for both int and string** | a common bug; also a rubric axis |
| **Distinguish `result.isError` from top-level `error`** | this distinction is THE recurring grading axis |

## What NOT to do

- **Don't return `result.isError: true` for an unknown METHOD.** That's a protocol error → top-level `error: {-32601, ...}`.
- **Don't return top-level `error` for an unknown TOOL inside `tools/call`.** The method `tools/call` ran successfully; the tool inside it failed → `result.isError: true`.
- **Don't add tools the judge isn't testing.** It only checks the three required ones. More tools = more surface for schema/wire-format bugs.
- **Don't return raw JSON object in `result.content[0]`.** It must be `{"type": "text", "text": "<json-string>"}`. Clients parse the JSON inside the string.
- **Don't fabricate `protocolVersion` strings.** Echo `"2025-06-18"` (or whatever the request sent, if matching).

## When you're stuck

> "The judge says my unknown-tool test fails: I returned `{error: {code: -32601, ...}}` but it expected `{result: {isError: true, content: [...]}}`. Walk me through the MCP spec section on tool errors vs JSON-RPC method errors, then fix my `do_tools_call` handler."

(The fix is structural: when the tool name isn't in the registry, return a `result.isError` envelope, not a top-level error.)

## After this exercise

You've now implemented the wire side of MCP. The skill carries: tomorrow you might be writing an MCP CLIENT that talks to a third-party server, and knowing what envelopes to expect makes that two hours instead of two days.
