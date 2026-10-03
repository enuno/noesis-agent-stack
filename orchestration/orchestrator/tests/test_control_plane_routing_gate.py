"""Integration tests: inference-routing gate wired into Orchestrator.dispatchable."""

from __future__ import annotations

from pathlib import Path

from app.control_plane import Orchestrator
from app.inference_routing import EnforcerConfig, InferenceRoutingEnforcer, REPO_ROOT
from app.models import TaskContract, Verification


def _enforcer(tmp_path: Path, mode: str) -> InferenceRoutingEnforcer:
    cfg = EnforcerConfig(
        mode=mode,
        fail_closed=True,
        policy_path=REPO_ROOT / "platform/inference-routing.yaml",
        reconciliation_path=REPO_ROOT / "platform/runtime-reconciliation.yaml",
        models_path=REPO_ROOT / "shared/models.yaml",
        aliases_path=REPO_ROOT / "shared/model-aliases.yaml",
        provider_policy_path=REPO_ROOT / "shared/provider-policies.yaml",
        risk_tiers_path=REPO_ROOT / "platform/risk-tiers.yaml",
        decision_log_path=tmp_path / "routing-decisions.jsonl",
        reload_seconds=60,
        allowlist=(),
        emergency_disable=False,
    )
    return InferenceRoutingEnforcer(cfg)


def _propose(orch: Orchestrator, **overrides) -> TaskContract:
    base = dict(
        title="integration probe",
        intent="probe routing gate",
        assignee_profile="noesis-signal",
        required_capability="deep_research",
        acceptance_criteria=["probe complete"],
        verification=Verification(method="probe"),
        idempotency_key="probe-1",
        risk_tier="r0",
        labels=["research"],
    )
    base.update(overrides)
    return orch.propose(**base)


def _override_signal(orch: Orchestrator) -> None:
    """Model a reconciled aligned profile so the gate isolates routing policy."""
    orch.inference_enforcer.set_profile_overrides(
        "noesis-signal",
        {
            "observed_runtime": {
                "source": "policy_fixture",
                "provider_lane": "KIMI_CODE",
                "model_alias_or_id": "kimi-k2.7-code",
                "evidence": "integration-test fixture",
            },
            "repo_declared": {
                "provider_lane": "KIMI_CODE",
                "model_alias_or_id": "kimi-k2.7-code",
                "evidence": "integration-test fixture",
            },
            "resolution": {
                "state": "aligned",
                "rationale": "integration fixture",
                "required_gates": [],
            },
        },
    )


class TestRoutingGateInDispatchable:
    def test_enforce_mode_blocks_dispatch_for_blocked_profile(self, tmp_path):
        orch = Orchestrator(tmp_path / "ledger.jsonl", inference_enforcer=_enforcer(tmp_path, "enforce"))
        task = _propose(orch)
        orch.enqueue(task.task_id)
        decision = orch.dispatchable(task.task_id)
        assert decision.allowed is False
        assert "inference routing denied" in decision.reason
        orch.inference_enforcer.clear_profile_overrides()

    def test_enforce_mode_allows_reconciled_baseline_route(self, tmp_path):
        orch = Orchestrator(tmp_path / "ledger.jsonl", inference_enforcer=_enforcer(tmp_path, "enforce"))
        _override_signal(orch)
        task = _propose(orch)
        orch.enqueue(task.task_id)
        decision = orch.dispatchable(task.task_id)
        assert decision.allowed is True
        orch.inference_enforcer.clear_profile_overrides()

    def test_observe_mode_preserves_dispatch_but_records_decision(self, tmp_path):
        enforcer = _enforcer(tmp_path, "observe")
        orch = Orchestrator(tmp_path / "ledger.jsonl", inference_enforcer=enforcer)
        # Blocked profile would be denied under enforce; observe must not block.
        task = _propose(orch)
        orch.enqueue(task.task_id)
        decision = orch.dispatchable(task.task_id)
        assert decision.allowed is True
        log = tmp_path / "routing-decisions.jsonl"
        assert log.exists()
        assert "observe_deny" in log.read_text()
        orch.inference_enforcer.clear_profile_overrides()

    def test_no_enforcer_preserves_existing_dispatch_semantics(self, tmp_path):
        orch = Orchestrator(tmp_path / "ledger.jsonl")
        task = _propose(orch)
        orch.enqueue(task.task_id)
        decision = orch.dispatchable(task.task_id)
        assert decision.allowed is True

    def test_enforce_denies_secret_data_before_dispatch(self, tmp_path):
        orch = Orchestrator(tmp_path / "ledger.jsonl", inference_enforcer=_enforcer(tmp_path, "enforce"))
        _override_signal(orch)
        task = _propose(orch)
        orch.enqueue(task.task_id)
        orch._inference_routing_context[str(task.task_id)] = {
            "data_classification": "secret",
        }
        decision = orch.dispatchable(task.task_id)
        assert decision.allowed is False
        assert "data_classification_denied" in decision.reason
        orch.inference_enforcer.clear_profile_overrides()
