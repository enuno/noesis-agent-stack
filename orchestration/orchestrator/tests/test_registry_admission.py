"""Regression tests for registry admission of execution lanes.

Defect (deployment-verification-2026-10-06): the orchestrator admitted only
profiles/noesis-roster.yaml identities, so the deployed `coder` profile and
the `claude-code-worker` bridge lane were rejected as unknown_profile. These
tests pin the lane-admission behavior and its fail-closed edges.
"""

import pytest
import yaml

from app import registry
from app.control_plane import Orchestrator
from app.models import Verification
from app.policy import PolicyViolation


def _task(orch, key, profile, capability="implement"):
    return orch.propose(
        title=f"lane admission {key}",
        intent="bounded synthetic task",
        assignee_profile=profile,
        required_capability=capability,
        acceptance_criteria=["done"],
        verification=Verification(method="manual"),
        idempotency_key=key,
        risk_tier="r1",
    )


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_registry_cache()
    yield
    registry.reset_registry_cache()


def _write_isolated_registry(tmp_path, agents, lanes, aliases=None, roster_extra=None):
    """Point the registry at isolated roster/agent-registry files."""
    roster = {"version": "test", "profiles": roster_extra or {}}
    (tmp_path / "roster.yaml").write_text(yaml.safe_dump(roster))
    reg = {
        "version": "test",
        "orchestration_lanes": lanes,
        "aliases": aliases or {},
        "agents": agents,
    }
    (tmp_path / "agent-registry.yaml").write_text(yaml.safe_dump(reg))


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "ROSTER_PATH", tmp_path / "roster.yaml")
    monkeypatch.setattr(registry, "AGENT_REGISTRY_PATH", tmp_path / "agent-registry.yaml")


CODER = {
    "coder": {
        "agent_id": "coder",
        "enabled": True,
        "runtime": "hermes",
        "role": "builder",
        "capabilities": ["plan_draft", "implement", "self_verify"],
    }
}

BRIDGE = {
    "claude-code-worker": {
        "agent_id": "claude-code-worker",
        "enabled": True,
        "runtime": "claude-code",
        "role": "builder",
        "capabilities": ["implement", "review", "test"],
    }
}


def test_coder_lane_admitted_with_declared_capability(tmp_path, monkeypatch):
    _write_isolated_registry(tmp_path, CODER, lanes=["coder"])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    task = _task(orch, "coder-001", "coder", capability="implement")
    orch.approve(task.task_id, operator="main-hermes")
    orch.enqueue(task.task_id)
    assert orch.claim(task.task_id, claimed_by="coder").state == "claimed"


def test_claude_code_worker_lane_admitted(tmp_path, monkeypatch):
    _write_isolated_registry(tmp_path, BRIDGE, lanes=["claude-code-worker"])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    task = _task(orch, "bridge-001", "claude-code-worker", capability="review")
    assert task.assignee_profile == "claude-code-worker"


def test_lane_wrong_capability_rejected(tmp_path, monkeypatch):
    _write_isolated_registry(tmp_path, CODER, lanes=["coder"])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    with pytest.raises(PolicyViolation, match="capability_mismatch"):
        _task(orch, "coder-badcap-001", "coder", capability="code_gen")


def test_registered_but_not_allowlisted_is_unknown(tmp_path, monkeypatch):
    # Registration alone must not activate: enabled agent, empty lanes list.
    _write_isolated_registry(tmp_path, CODER, lanes=[])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    with pytest.raises(PolicyViolation, match="unknown_profile"):
        _task(orch, "coder-nolane-001", "coder")


def test_disabled_lane_not_activated(tmp_path, monkeypatch):
    disabled = {"coder": {**CODER["coder"], "enabled": False}}
    _write_isolated_registry(tmp_path, disabled, lanes=["coder"])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    with pytest.raises(PolicyViolation, match="lane_not_activated"):
        _task(orch, "coder-disabled-001", "coder")


def test_alias_resolves_to_canonical_identity(tmp_path, monkeypatch):
    _write_isolated_registry(
        tmp_path, BRIDGE, lanes=["claude-code-worker"], aliases={"bridge": "claude-code-worker"}
    )
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    task = _task(orch, "alias-001", "bridge", capability="review")
    assert registry.get_profile("bridge").name == "claude-code-worker"
    assert task.assignee_profile == "bridge"  # contract keeps the name as written


def test_alias_shadowing_identity_fails_closed(tmp_path, monkeypatch):
    _write_isolated_registry(
        tmp_path, CODER, lanes=["coder"], aliases={"coder": "claude-code-worker"}
    )
    _patch_paths(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="shadows an existing identity"):
        registry.load_registry()


def test_alias_to_unknown_target_fails_closed(tmp_path, monkeypatch):
    _write_isolated_registry(tmp_path, CODER, lanes=["coder"], aliases={"ghost": "nobody"})
    _patch_paths(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="unknown identity"):
        registry.load_registry()


def test_lane_roster_name_collision_fails_closed(tmp_path, monkeypatch):
    roster_extra = {
        "coder": {"name": "Coder", "role": "builder", "tier": "worker", "wave": 1}
    }
    _write_isolated_registry(tmp_path, CODER, lanes=["coder"], roster_extra=roster_extra)
    _patch_paths(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="identity conflict"):
        registry.load_registry()


def test_supervisor_role_lane_cannot_execute(tmp_path, monkeypatch):
    sup = {"main-hermes": {
        "agent_id": "main-hermes", "enabled": True, "runtime": "hermes",
        "role": "supervisor", "capabilities": ["approve", "delegate"],
    }}
    _write_isolated_registry(tmp_path, sup, lanes=["main-hermes"])
    _patch_paths(monkeypatch, tmp_path)
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    with pytest.raises(PolicyViolation, match="supervisor_cannot_execute"):
        _task(orch, "sup-001", "main-hermes", capability="approve")


def test_repo_default_registry_admits_repo_lanes(tmp_path):
    """The real repository config (no monkeypatching) admits coder + bridge."""
    orch = Orchestrator(tmp_path / "tasks.jsonl")
    task = _task(orch, "repo-coder-001", "coder", capability="implement")
    orch.approve(task.task_id, operator="main-hermes")
    orch.enqueue(task.task_id)
    assert orch.claim(task.task_id, claimed_by="coder").state == "claimed"

    task2 = _task(orch, "repo-bridge-001", "claude-code-worker", capability="review")
    assert task2.state == "proposed"
