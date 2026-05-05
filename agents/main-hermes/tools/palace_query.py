#!/usr/bin/env python3
"""Hermes palace query tool — CLI interface to MemPalace for search, KG, and diary.

Usage:
    python palace_query.py search "job timeout patterns" --wing broker --limit 5
    python palace_query.py kg-query --entity "noesis-agent-stack" --direction both
    python palace_query.py diary-read --agent main-hermes --last-n 10
    python palace_query.py traverse --start-room job-receipts --max-hops 3
    python palace_query.py status
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


MCP_SERVER = "mempalace"


def _mcp_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool via the Hermes CLI and return parsed JSON.

    In a real deployment this would use the native MCP client library.
    For Phase 1.5 we shell out to `hermes tools call` as a bridge.
    """
    # Fallback: if hermes CLI isn't available, print what we would do
    cmd = ["hermes", "tools", "call", f"{MCP_SERVER}:{tool}"]
    for key, value in args.items():
        cmd.extend([f"--{key}", str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "command": " ".join(cmd)}
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {
            "error": "hermes CLI not found; this tool requires the Hermes agent runtime.",
            "command": " ".join(cmd),
            "note": "Run this script from within a Hermes session where MCP tools are natively available.",
        }
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON from MCP tool: {exc}", "raw": result.stdout}


def cmd_search(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {"query": args.query, "limit": args.limit}
    if args.wing:
        payload["wing"] = args.wing
    if args.room:
        payload["room"] = args.room
    result = _mcp_call("mempalace_search", payload)
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def cmd_kg_query(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "entity": args.entity,
        "direction": args.direction,
    }
    if args.as_of:
        payload["as_of"] = args.as_of
    result = _mcp_call("mempalace_kg_query", payload)
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def cmd_diary_read(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "agent_name": args.agent,
        "last_n": args.last_n,
    }
    result = _mcp_call("mempalace_diary_read", payload)
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def cmd_traverse(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "start_room": args.start_room,
        "max_hops": args.max_hops,
    }
    result = _mcp_call("mempalace_traverse", payload)
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def cmd_status(_args: argparse.Namespace) -> int:
    result = _mcp_call("mempalace_status", {})
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes MemPalace query tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser("search", help="Semantic search across drawers")
    p_search.add_argument("query", help="Search query (max 250 chars)")
    p_search.add_argument("--wing", default=None, help="Filter by wing")
    p_search.add_argument("--room", default=None, help="Filter by room")
    p_search.add_argument("--limit", type=int, default=5, help="Max results")
    p_search.set_defaults(func=cmd_search)

    p_kg = subparsers.add_parser("kg-query", help="Query the knowledge graph")
    p_kg.add_argument("--entity", required=True, help="Entity to query")
    p_kg.add_argument("--direction", default="both", choices=["outgoing", "incoming", "both"])
    p_kg.add_argument("--as-of", default=None, help="Date filter YYYY-MM-DD")
    p_kg.set_defaults(func=cmd_kg_query)

    p_diary = subparsers.add_parser("diary-read", help="Read agent diary entries")
    p_diary.add_argument("--agent", required=True, help="Agent name")
    p_diary.add_argument("--last-n", type=int, default=10, help="Recent entries to fetch")
    p_diary.set_defaults(func=cmd_diary_read)

    p_trav = subparsers.add_parser("traverse", help="Traverse palace graph from a room")
    p_trav.add_argument("--start-room", required=True, help="Starting room name")
    p_trav.add_argument("--max-hops", type=int, default=2, help="Connection depth")
    p_trav.set_defaults(func=cmd_traverse)

    p_status = subparsers.add_parser("status", help="Palace overview status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
