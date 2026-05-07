"""Palace query interface for Hermes supervisor.

Provides semantic search, knowledge graph lookups, and diary reads
from MemPalace before significant approval or delegation decisions.

When running inside the Hermes agent runtime, these functions invoke
the native MCP tools (mcp_mempalace_search, mcp_mempalace_kg_query,
mcp_mempalace_diary_read). When running standalone, they return
graceful no-ops with diagnostic messages.

Usage in hermes_cycle.py:
    from tools.palace_query import palace_search, palace_kg_query, palace_diary_read
    findings = palace_search("bitcoin mining energy efficiency", limit=5)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def _is_agent_runtime() -> bool:
    """Detect whether we are inside the Hermes agent runtime (MCP available)."""
    return os.environ.get("HERMES_AGENT_RUNTIME", "0") == "1"


def _noop_result(tool_name: str, query: str) -> Dict[str, Any]:
    return {
        "tool": tool_name,
        "query": query,
        "status": "noop",
        "note": "MCP tools require HERMES_AGENT_RUNTIME=1. Run from agent context.",
        "results": [],
    }


def palace_search(
    query: str,
    limit: int = 5,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    context: str = "",
) -> Dict[str, Any]:
    """Semantic search across MemPalace wings/rooms.

    Returns verbatim drawer content with similarity scores.
    """
    if not _is_agent_runtime():
        return _noop_result("mcp_mempalace_search", query)

    # In agent runtime, this is replaced by the actual MCP call
    # via the hermes gateway. The payload below is the contract.
    return {
        "tool": "mcp_mempalace_search",
        "query": query,
        "limit": limit,
        "wing": wing,
        "room": room,
        "context": context,
        "status": "pending_runtime",
        "results": [],
    }


def palace_kg_query(
    entity: str,
    direction: str = "both",
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Query the MemPalace knowledge graph for an entity's relationships.

    Args:
        entity: Entity to query (e.g. 'bitcoin-mining', 'Alice')
        direction: outgoing | incoming | both
        as_of: YYYY-MM-DD filter for temporal validity
    """
    if not _is_agent_runtime():
        return _noop_result("mcp_mempalace_kg_query", entity)

    return {
        "tool": "mcp_mempalace_kg_query",
        "entity": entity,
        "direction": direction,
        "as_of": as_of,
        "status": "pending_runtime",
        "results": [],
    }


def palace_diary_read(
    agent_name: str = "hermes",
    last_n: int = 10,
    wing: Optional[str] = None,
) -> Dict[str, Any]:
    """Read recent diary entries for context continuity.

    Args:
        agent_name: Agent whose diary to read (default 'hermes')
        last_n: Number of recent entries
        wing: Optional target wing (defaults to wing_{agent_name})
    """
    if not _is_agent_runtime():
        return _noop_result("mcp_mempalace_diary_read", agent_name)

    return {
        "tool": "mcp_mempalace_diary_read",
        "agent_name": agent_name,
        "last_n": last_n,
        "wing": wing,
        "status": "pending_runtime",
        "results": [],
    }


def enrich_signal_with_palace(signal_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-flight palace query before a significant dispatch decision.

    Attaches palace context to the signal payload so the approval
    engine and routing table can use it. Non-destructive.
    """
    topic = signal_payload.get("topic", signal_payload.get("objective", ""))
    if not topic:
        return signal_payload

    findings = palace_search(topic, limit=3)
    if findings.get("results"):
        signal_payload["_palace_context"] = {
            "query": topic,
            "findings_count": len(findings["results"]),
            "top_finding": findings["results"][0] if findings["results"] else None,
        }
    return signal_payload
