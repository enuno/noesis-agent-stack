#!/usr/bin/env python3
"""Deploy the MCPJungle tool groups and verify them in two layers.

Layer 1 — definition match: the live definition equals the source file.
Layer 2 — served-tools match: the group's own MCP endpoint serves exactly the
          declared included_tools.

Usage:
  python3 deploy_groups.py --plan          show what would change
  python3 deploy_groups.py --apply         create/update the groups
  python3 deploy_groups.py --verify        verify the deployed groups
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MCP = R / "config" / "mcpjungle"
BASE = "https://mcpjungle.tailf99a0.ts.net"
REGISTRY = "mcpjungle"


def token() -> str:
    for line in open("/home/elvis/.mcpjungle.conf", encoding="utf-8"):
        if "access_token" in line:
            return line.split(":", 1)[1].strip()
    raise SystemExit("no token")


TOK = token()


def api(path: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOK})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def mcp_session(endpoint: str):
    """Open an MCP session and return (session_id, tools)."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "verify", "version": "1"}}}
    req = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json, text/event-stream",
                                          "Authorization": "Bearer " + TOK})
    with urllib.request.urlopen(req, timeout=120) as r:
        sid = r.headers.get("mcp-session-id")
        raw = r.read().decode()
    parse(raw)

    body = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    req = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json, text/event-stream",
                                          "Authorization": "Bearer " + TOK,
                                          "mcp-session-id": sid})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode()
    res = parse(raw)
    return [t["name"] for t in res["result"]["tools"]]


def parse(raw: str):
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw) if raw.strip() else None


def local_groups():
    out = {}
    for p in sorted((MCP / "groups").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["name"]] = d
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    local = local_groups()
    live_raw = api("/api/v0/tool-groups")
    live = {g["name"]: g for g in (live_raw if isinstance(live_raw, list)
                                    else live_raw.get("tool_groups", live_raw.get("groups", [])))}

    create = [n for n in sorted(local) if n not in live]
    update = [n for n in sorted(local) if n in live
              and set(live[n].get("included_tools") or []) != set(local[n]["included_tools"])]
    unchanged = [n for n in sorted(local) if n in live and n not in update]
    orphan = [n for n in sorted(live) if n not in local]

    print(f"local groups: {len(local)}   live groups: {len(live)}")
    print(f"  to create: {len(create)}   to update: {len(update)}   unchanged: {len(unchanged)}")
    if orphan:
        print(f"  live-only (not in the repo): {orphan}")

    if args.plan:
        for n in create:
            print(f"  CREATE {n} ({len(local[n]['included_tools'])} tools)")
        for n in update:
            print(f"  UPDATE {n} ({len(local[n]['included_tools'])} tools)")
        return 0

    if args.apply:
        failures = []
        for n in create + update:
            cmd = [REGISTRY, "create" if n in create else "update", "group",
                   "--conf", str(MCP / "groups" / f"{n}.json"), "--registry", BASE]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                failures.append((n, proc.stderr.strip()[:300]))
                print(f"  FAIL  {n}: {proc.stderr.strip()[:300]}")
            else:
                print(f"  OK    {n} ({'created' if n in create else 'updated'})")
        if failures:
            print(f"\n{len(failures)} failure(s)")
            return 1
        print(f"\n{len(create)} created, {len(update)} updated, 0 failed")
        return 0

    if args.verify:
        # layer 1: definition match
        live_raw = api("/api/v0/tool-groups")
        live = {g["name"]: g for g in (live_raw if isinstance(live_raw, list)
                                        else live_raw.get("tool_groups", live_raw.get("groups", [])))}
        def_fail = []
        for n, d in sorted(local.items()):
            L = live.get(n)
            if L is None:
                def_fail.append(f"{n}: absent from the registry")
                continue
            if (L.get("name") != d["name"] or L.get("description") != d["description"]
                    or set(L.get("included_tools") or []) != set(d["included_tools"])):
                def_fail.append(f"{n}: live definition differs from the source file")
        print(f"layer 1 — definition match: {len(local) - len(def_fail)}/{len(local)} ok")
        for f in def_fail:
            print(f"  MISMATCH {f}")

        # layer 2: served-tools match
        srv_fail = []
        for n, d in sorted(local.items()):
            endpoint = f"{BASE}/v0/groups/{n}/mcp"
            try:
                served = set(mcp_session(endpoint))
            except Exception as exc:
                srv_fail.append(f"{n}: endpoint probe failed: {exc}")
                continue
            declared = set(d["included_tools"])
            if served != declared:
                missing = declared - served
                extra = served - declared
                srv_fail.append(f"{n}: served != declared (missing {sorted(missing)[:5]}, "
                                f"extra {sorted(extra)[:5]})")
        print(f"layer 2 — served-tools match: {len(local) - len(srv_fail)}/{len(local)} ok")
        for f in srv_fail:
            print(f"  MISMATCH {f}")

        if def_fail or srv_fail:
            print(f"\nFAIL: {len(def_fail)} definition + {len(srv_fail)} served-tools mismatches")
            return 1
        print(f"\nPASS: {len(local)}/{len(local)} groups match on both layers")
        return 0

    ap.error("choose --plan, --apply or --verify")
    return 2


if __name__ == "__main__":
    sys.exit(main())
