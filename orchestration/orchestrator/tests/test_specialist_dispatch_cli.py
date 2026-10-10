"""CLI entrypoint tests for the live specialist dispatch path."""
from __future__ import annotations

import json
from pathlib import Path

from app import specialist_dispatch_cli


def test_cli_dry_run_routes_through_control_plane_and_attests_profile(tmp_path: Path, capsys) -> None:
    payload = {
        "title": "architecture route",
        "intent": "Design an MCP/Hermes profile contract for a new memory agent",
        "acceptance_criteria": ["selected specialist is explicit"],
        "verification": {"method": "launcher_attestation"},
        "idempotency_key": "cli:architecture-route",
        "dry_run": True,
    }
    input_path = tmp_path / "task.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    ledger = tmp_path / "tasks.jsonl"
    events = tmp_path / "events.jsonl"

    exit_code = specialist_dispatch_cli.main([
        "--input", str(input_path),
        "--ledger", str(ledger),
        "--events", str(events),
    ])

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is True
    assert result["selected_agent"] == "noesis-architect"
    assert result["requested_profile_id"] == "noesis-architect"
    assert result["loaded_profile_id"] == "noesis-architect"
    assert result["fallback_reason"] is None
    event = json.loads(events.read_text(encoding="utf-8").splitlines()[-1])
    assert event["selected_agent"] == "noesis-architect"
    assert event["loaded_profile_id"] == "noesis-architect"


def test_cli_blocks_missing_runtime_without_default_or_parent_fallback(tmp_path: Path, capsys) -> None:
    payload = {
        "title": "research route",
        "intent": "Research market signals and produce citations",
        "acceptance_criteria": ["blocked explicitly when runtime missing"],
        "verification": {"method": "launcher_attestation"},
        "idempotency_key": "cli:missing-runtime",
        "dry_run": True,
        "available_profiles": [],
    }
    input_path = tmp_path / "task.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = specialist_dispatch_cli.main([
        "--input", str(input_path),
        "--ledger", str(tmp_path / "tasks.jsonl"),
        "--events", str(tmp_path / "events.jsonl"),
    ])

    assert exit_code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is False
    assert result["code"] == "no_eligible_specialist"
    text = json.dumps(result)
    assert "profile_not_installed" in text
    assert "noesis-orchestrator" not in result.get("selected_agent", "")
    assert "default" not in result.get("selected_agent", "")
    assert "coder" not in result.get("selected_agent", "")
