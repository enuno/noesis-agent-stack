#!/usr/bin/env python3
"""Full MCP tools/list discovery: name + description + inputSchema + annotations."""
from __future__ import annotations
import datetime, json, os, sys, urllib.error, urllib.request

PROTOCOL_VERSION = "2025-06-18"
MAX_PAGES = 500

def read_conf(key):
    path = os.path.expanduser("~/.mcpjungle.conf")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(key + ":"):
                return line.split(":", 1)[1].strip() or None
    return None

def parse_sse(raw):
    if not (raw.startswith("event:") or raw.startswith("data:")):
        return raw
    payloads = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                payloads.append(line[5:].strip())
    return payloads[-1] if payloads else ""

class McpSession:
    def __init__(self, url, token):
        self.url, self.token, self.session_id = url, token, None
    def post(self, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("MCP-Protocol-Version", PROTOCOL_VERSION)
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                sid = resp.headers.get("mcp-session-id") or resp.headers.get("Mcp-Session-Id")
                if sid: self.session_id = sid
                status = resp.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()[:300]
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        raw = parse_sse(raw)
        if not raw.strip():
            return {"_http_status": status, "_empty": True}
        return json.loads(raw)
    def list_tools_full(self):
        tools, cursor, pages = [], None, 0
        while True:
            params = {"cursor": cursor} if cursor else {}
            reply = self.post({"jsonrpc": "2.0", "id": 10 + pages, "method": "tools/list", "params": params})
            if "_http_status" in reply: raise RuntimeError(f"tools/list failed: {reply}")
            if "error" in reply: raise RuntimeError(f"tools/list error: {reply['error']}")
            result = reply.get("result", {})
            tools.extend(result.get("tools", []))
            pages += 1
            cursor = result.get("nextCursor")
            if not cursor: return tools, pages
            if pages >= MAX_PAGES: raise RuntimeError("page cap reached")

def main():
    registry = read_conf("registry_url")
    token = read_conf("access_token")
    mcp_url = registry.rstrip("/") + "/mcp"
    session = McpSession(mcp_url, token)
    session.post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                             "clientInfo": {"name": "discover_full", "version": "1.0"}}})
    try:
        session.post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    except RuntimeError:
        pass
    tools, pages = session.list_tools_full()
    print(f"pages={pages} tools={len(tools)}", file=sys.stderr)
    out = {
        "discovered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "endpoint": mcp_url,
        "tools": tools,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)

if __name__ == "__main__":
    main()
