"""Tests for the fail-closed inference-routing enforcer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.inference_routing import (
    EnforcerConfig,
    InferenceRoutingEnforcer,
    PolicyLoadError,
    RoutingContext,
    REPO_ROOT,
)


def make_config(tmp_path: Path, mode: str = "observe", **overrides) -> EnforcerConfig:
    base = dict(
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
    base.update(overrides)
    return EnforcerConfig(**base)


def make_ctx(**overrides) -> RoutingContext:
    base = dict(
        task_id="task-1",
        profile_id="noesis-signal",
        task_class="research",
        risk_tier="r0",
        data_classification="internal_redacted",
    )
    base.update(overrides)
    return RoutingContext(**base)


@pytest.fixture
def enforcer(tmp_path):
    enforcer = InferenceRoutingEnforcer(make_config(tmp_path))
    yield enforcer
    enforcer.clear_profile_overrides()


def _override_signal_aligned(e: InferenceRoutingEnforcer, profile_id: str = "noesis-signal") -> None:
    """Model a reconciled, aligned profile backed by the observed KIMI baseline."""
    e.set_profile_overrides(
        profile_id,
        {
            "observed_runtime": {
                "source": "policy_fixture",
                "provider_lane": "KIMI_CODE",
                "model_alias_or_id": "kimi-k2.7-code",
                "evidence": "unit-test fixture",
            },
            "repo_declared": {
                "provider_lane": "KIMI_CODE",
                "model_alias_or_id": "kimi-k2.7-code",
                "evidence": "unit-test fixture",
            },
            "resolution": {
                "state": "aligned",
                "rationale": "test fixture",
                "required_gates": [],
            },
        },
    )


def _read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestFailClosed:
    def test_missing_policy_fails_closed_in_enforce_mode(self, tmp_path):
        cfg = make_config(
            tmp_path,
            mode="enforce",
            policy_path=tmp_path / "missing-policy.yaml",
        )
        with pytest.raises(PolicyLoadError):
            InferenceRoutingEnforcer(cfg)

    def test_invalid_policy_fails_closed_in_enforce_allowlist_mode(self, tmp_path):
        bad_policy = tmp_path / "bad.yaml"
        bad_policy.write_text("not_a_mapping: [", encoding="utf-8")
        cfg = make_config(tmp_path, mode="enforce_allowlist", policy_path=bad_policy)
        with pytest.raises(PolicyLoadError):
            InferenceRoutingEnforcer(cfg)

    def test_policy_reload_failure_retains_last_known_good_in_observe(self, tmp_path, monkeypatch):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path))
        assert enforcer._policy is not None

        def broken_loader(*args, **kwargs):
            raise PolicyLoadError("injected reload failure")

        monkeypatch.setattr(enforcer, "_read_yaml", broken_loader)
        loaded = enforcer.load_policy()
        assert loaded is enforcer._policy
        assert enforcer._last_error is not None

    def test_policy_reload_failure_denies_new_dispatches_in_enforce(self, tmp_path, monkeypatch):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        assert enforcer._policy is not None
        _override_signal_aligned(enforcer)

        def broken_loader(*args, **kwargs):
            raise PolicyLoadError("injected reload failure")

        monkeypatch.setattr(enforcer, "_read_yaml", broken_loader)
        enforcer.load_policy()
        decision = enforcer.evaluate(make_ctx())
        assert decision.allowed is False
        assert decision.reason_code == "policy_reload_failed"


class TestLaneEligibility:
    def test_proposed_perplexity_lane_denied_in_enforce(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(
            make_ctx(requested_lane="PERPLEXITY_API", requested_model="sonar")
        )
        assert decision.allowed is False
        assert decision.reason_code in {"lane_not_selectable", "reconciliation_freeze"}

    def test_openrouter_denied_regardless_of_requested_route(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(
            make_ctx(requested_lane="OPENROUTER_FALLBACK", requested_model="anything")
        )
        assert decision.allowed is False
        assert decision.reason_code == "openrouter_selected"

    def test_unpinned_model_denied(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(
            make_ctx(requested_lane="KIMI_CODE", requested_model="unpinned-model")
        )
        assert decision.allowed is False
        assert decision.reason_code == "model_not_allowed"


class TestProfileAndDataPolicy:
    def test_profile_missing_from_reconciliation_denied(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        decision = enforcer.evaluate(make_ctx(profile_id="unknown-profile"))
        assert decision.allowed is False
        assert decision.reason_code == "profile_missing_from_reconciliation"

    def test_secret_data_denied_before_provider_selection(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx(data_classification="secret"))
        assert decision.allowed is False
        assert decision.reason_code == "data_classification_denied"

    def test_restricted_data_denied_before_provider_selection(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx(data_classification="restricted"))
        assert decision.allowed is False
        assert decision.reason_code == "data_classification_denied"


class TestRiskGates:
    def test_r2_without_independent_review_denied(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx(risk_tier="r2"))
        assert decision.allowed is False
        assert decision.reason_code == "independent_review_required"

    def test_r3_without_approval_and_rollback_denied(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx(risk_tier="r3"))
        assert decision.allowed is False
        # r3 is denied; with no approved lane carrying max_risk r3 the
        # risk ceiling trips first, otherwise the review gate would.
        assert decision.reason_code in {
            "independent_review_required",
            "risk_tier_exceeds_lane_max",
        }

    def test_r3_with_same_family_review_denied(self, tmp_path):
        enforcer = InferenceRoutingEnforcer(make_config(tmp_path, mode="enforce"))
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(
            make_ctx(
                risk_tier="r3",
                independent_review_provider_family="kimi",
                approval_granted=True,
                approval_manifest_id="manifest-1",
                rollback_plan_present=True,
            )
        )
        # r3 is denied; same-family review is rejected when the risk ceiling
        # does not trip first.
        assert decision.allowed is False
        assert decision.reason_code in {
            "independent_review_same_provider_family",
            "risk_tier_exceeds_lane_max",
        }


class TestModes:
    def test_observe_logs_deny_but_preserves_baseline_dispatch(self, tmp_path):
        cfg = make_config(tmp_path, mode="observe")
        enforcer = InferenceRoutingEnforcer(cfg)
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx(requested_lane="OPENROUTER_FALLBACK"))
        assert decision.allowed is True
        assert decision.decision == "observe_deny"
        records = _read_log(cfg.decision_log_path)
        assert records[-1]["reason_code"] == "openrouter_selected"

    def test_shadow_deny_records_would_deny_without_blocking(self, tmp_path):
        cfg = make_config(tmp_path, mode="shadow_deny")
        enforcer = InferenceRoutingEnforcer(cfg)
        decision = enforcer.evaluate(make_ctx(profile_id="unknown-profile"))
        assert decision.allowed is True
        assert decision.decision == "observe_deny"
        records = _read_log(cfg.decision_log_path)
        assert records[-1]["reason_code"] == "profile_missing_from_reconciliation"

    def test_enforce_allowlist_denies_unlisted_tuple(self, tmp_path):
        cfg = make_config(
            tmp_path,
            mode="enforce_allowlist",
            allowlist=(("noesis-signal", "KIMI_CODE", "kimi-k2.7-code"),),
        )
        enforcer = InferenceRoutingEnforcer(cfg)
        # Use a reconciled-but-unlisted profile to isolate the allowlist gate.
        _override_signal_aligned(enforcer, profile_id="noesis-scribe")
        decision = enforcer.evaluate(make_ctx(profile_id="noesis-scribe"))
        assert decision.allowed is False
        assert decision.reason_code in {
            "profile_missing_from_reconciliation",
            "not_allowlisted",
            "reconciliation_blocked",
        }

    def test_off_mode_requires_emergency_flag(self, tmp_path):
        with pytest.raises(PolicyLoadError):
            InferenceRoutingEnforcer(make_config(tmp_path, mode="off", emergency_disable=False))


class TestDecisionMetadata:
    def test_every_decision_includes_policy_version_and_sha256(self, tmp_path):
        cfg = make_config(tmp_path, mode="observe")
        enforcer = InferenceRoutingEnforcer(cfg)
        decision = enforcer.evaluate(make_ctx())
        assert decision.policy_version
        assert decision.policy_sha256
        records = _read_log(cfg.decision_log_path)
        assert records[-1]["policy_version"] == decision.policy_version
        assert records[-1]["policy_sha256"] == decision.policy_sha256

    def test_allowlisted_r0_readonly_tuple_may_pass_only_after_approval(self, tmp_path):
        cfg = make_config(
            tmp_path,
            mode="enforce_allowlist",
            allowlist=(("noesis-signal", "KIMI_CODE", "kimi-k2.7-code"),),
        )
        enforcer = InferenceRoutingEnforcer(cfg)
        _override_signal_aligned(enforcer)
        decision = enforcer.evaluate(make_ctx())
        assert decision.allowed is True
        assert decision.decision == "allow"
        assert decision.resolved_lane == "KIMI_CODE"
        assert decision.resolved_model == "kimi-k2.7-code"
