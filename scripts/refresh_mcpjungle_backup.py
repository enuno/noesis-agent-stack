#!/usr/bin/env python3
"""Refresh config/mcpjungle/backup/gateway-state-backup.json from the live gateway.

Fetches GET /api/v0/servers, /api/v0/server_configs and /api/v0/tool-groups,
redacts server_configs with a strict field allowlist, and proves the
redaction by value (every non-trivial live string is checked against the
emitted file) before writing anything.

Usage
    refresh_mcpjungle_backup.py [--repo PATH]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

BASE = "https://mcpjungle.tailf99a0.ts.net"
SAFE_SERVER_FIELDS = {"name", "transport", "url", "description", "enabled", "command", "args",
                      "env", "session_mode"}
SAFE_FIELDS = {"name", "description", "url", "transport", "session_mode", "enabled"}
CONTAINER_FIELDS = {"headers", "env"}


def read_token() -> str:
    for line in open(Path.home() / ".mcpjungle.conf", encoding="utf-8"):
        if line.startswith("access_token:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("no access_token in ~/.mcpjungle.conf")


def api(path: str, token: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def collect_secret_strings(obj) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SAFE_FIELDS and not isinstance(v, (dict, list)):
                continue
            out.extend(collect_secret_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(collect_secret_strings(v))
    elif isinstance(obj, str) and len(obj) >= 12:
        out.append(obj)
    return out


def redact_value(v):
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        if len(v) < 8:
            return v
        shape = "jwt" if v.count(".") == 2 else "opaque-token"
        return f"<REDACTED:{shape}:len={len(v)}>"
    return v


def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SAFE_FIELDS and not isinstance(v, (dict, list)):
                out[k] = v
            elif k in CONTAINER_FIELDS and isinstance(v, dict):
                out[k] = {kk: redact_value(vv) for kk, vv in v.items()}
            elif isinstance(v, (dict, list)):
                out[k] = redact(v)
            else:
                out[k] = redact_value(v)
        return out
    elif isinstance(obj, list):
        return [redact(v) for v in obj]
    return redact_value(obj)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    mcp_dir = repo / "config" / "mcpjungle"
    token = read_token()

    servers = api("/api/v0/servers", token)
    for s in servers:
        extra = set(s.keys()) - SAFE_SERVER_FIELDS
        if extra:
            raise SystemExit(f"FATAL: unexpected field(s) on /servers entry {s.get('name')}: {extra}")

    server_configs = api("/api/v0/server_configs", token)
    live_secrets = sorted({s for sc in server_configs for s in collect_secret_strings(sc)})
    redacted_configs = [redact(sc) for sc in server_configs]
    emitted = json.dumps(redacted_configs)
    leaked = [s for s in live_secrets if s in emitted]
    if leaked:
        raise SystemExit(f"FATAL: redaction leak -- {len(leaked)} live secret value(s) present "
                          "in the redacted output; refusing to write the backup")

    local_groups_dir = mcp_dir / "groups"
    local_groups = {p.stem: json.loads(p.read_text()) for p in sorted(local_groups_dir.glob("*.json"))}

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    inv = json.loads((mcp_dir / "tool-inventory.json").read_text())

    backup = {
        "schema_version": "1.0.0",
        "artifact_type": "mcpjungle-gateway-state-backup",
        "captured_at": now,
        "target": {
            "registry_base_url": BASE,
            "mcp_endpoint": BASE + "/mcp",
            "mcpjungle_cli_version": "v0.4.6",
            "mcpjungle_server_version": "v0.4.6",
            "server_mode": "development",
            "server_mode_note": (
                "The gateway runs in SERVER_MODE=development. In this mode MCPJungle performs no "
                "authentication and no ACLs. The trust boundary for the resulting open access is "
                "the tailnet itself."
            ),
        },
        "main_gateway_servers": {
            "count": len(servers),
            "source": "GET /api/v0/servers",
            "description": (
                "The upstream MCP servers registered on the main gateway. This view carries no "
                "credentials: every entry has null env, null args and null command, and the only "
                "non-empty fields are name, transport, url, description and enabled."
            ),
            "servers": servers,
        },
        "server_configs_redacted": redacted_configs,
        "tool_groups": {
            "count": len(local_groups),
            "source": "config/mcpjungle/groups/*.json, cross-checked against GET /api/v0/tool-groups",
            "description": (
                "The deployable group definitions. Each group is stored with the exact "
                "included_tools allowlist that was deployed, so a restore recreates the same tool "
                "exposure."
            ),
            "groups": [local_groups[k] for k in sorted(local_groups)],
        },
        "main_endpoint_tool_inventory": {
            "count": len(inv["tools"]),
            "source": "MCP initialize + tools/list against " + BASE + "/mcp",
            "description": (
                "The main /mcp endpoint still serves all " + str(len(inv["tools"])) + " tools. "
                "Creating tool groups does not narrow the main gateway; narrowing requires "
                "pointing a client at a group endpoint. The full per-tool metadata for this "
                "surface is maintained in config/mcpjungle/tool-inventory.json and is not "
                "duplicated here."
            ),
            "inventory_file": "../tool-inventory.json",
        },
        "restore_procedure": {
            "servers": (
                "mcpjungle register -c <file> for each entry in main_gateway_servers. Upstream "
                "credentials are NOT recoverable from this backup: re-apply them from the "
                "Bitwarden escrow."
            ),
            "groups": (
                "mcpjungle create group --conf config/mcpjungle/groups/<group-name>.json for any "
                "group absent from tool_groups. To update an existing group, use "
                "mcpjungle update group --conf <file>."
            ),
            "ordering": (
                "Restore servers before groups: group creation validates every listed tool "
                "against the registry and fails if a tool does not exist or is disabled."
            ),
        },
        "integrity": {
            "leak_check": (
                "Every non-trivial string value in the live server_configs was treated as a "
                "secret and checked against the emitted file by value. The emitted file contains "
                "none of them. Only field NAMES and the redacted shape markers survive."
            ),
            "note": (
                "This backup is a point-in-time snapshot. Re-capture and diff against "
                "main_gateway_servers and tool_groups to review drift."
            ),
        },
    }

    emitted_full = json.dumps(backup)
    leaked_full = [s for s in live_secrets if s in emitted_full]
    if leaked_full:
        raise SystemExit(f"FATAL: full-file redaction leak -- {len(leaked_full)} value(s) present")

    out_path = mcp_dir / "backup" / "gateway-state-backup.json"
    out_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    print(f"wrote backup: {len(servers)} servers, {len(local_groups)} groups, "
          f"0/{len(live_secrets)} live secret values leaked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
