"""Tests for the Noesis managed model-routing policy.

These tests are pure: they load repository YAML or tmp_path fixtures. They do
not call providers, open network sockets, or read Hermes profile credentials.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from app.model_policy import (
    BACKGROUND_EXECUTION_SUPPORTED,
    AdmissionDecision,
    DispatchResult,
    ModelPolicyError,
    ReadinessEvidence,
    admit_route,
    authorize_retry,
    categorize_failure,
    check_review_independence,
    credential_safe_summary,
    fallback_chain,
    has_qualifying_independent_pair,
    load_model_policy,
    plan_fallback_sequence,
    readiness_is_fresh,
    reconcile_synchronous_result,
    select_route,
    validate_result_provenance,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SHIPPED = REPO_ROOT / "platform" / "model-routing-policy.yaml"

NOW = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)
EPOCH = "task-epoch-1"
UNUSABLE_PROVIDERS = {
    "kimi-coding",
    "anthropic",
    "openai-codex",
    "openrouter",
    "venice",
}
READINESS_STATES = {
    "reachable",
    "unverified",
    "quota_exhausted",
    "rate_limited",
    "model_unavailable",
    "missing_auth",
    "disabled",
}
QUOTA_STATES = {"known_available", "known_exhausted", "unknown"}


def _scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise TypeError(type(value))


def _route(**overrides) -> dict:
    evidence = {
        "quota": "unknown",
        "readiness_ttl_seconds": 3600,
        "requires_reachability_probe": True,
        "readiness_state": "reachable",
    }
    if "evidence" in overrides:
        evidence = overrides.pop("evidence")
    route = {
        "provider": "example-provider",
        "model": "example-model",
        "provider_family": "example",
        "workload_classes": ["implementation"],
        "risk_tier_max": "r2",
        "data_classes": ["public", "internal"],
        "fallback_routes": [],
        "fallback_allowed": False,
        "credential_scope": "oauth-device-code",
        "evidence": evidence,
        "status": "approved",
        "tool_capabilities": [],
    }
    route.update(overrides)
    return route


def _selectable_declaration(route: dict) -> bool:
    if route.get("status") != "approved":
        return False
    evidence = route.get("evidence") or {}
    if evidence.get("quota") == "known_exhausted":
        return False
    if evidence.get("readiness_state") != "reachable":
        return False
    return True


def _pair_exists(routes: dict) -> bool:
    implementers = []
    reviewers = []
    for name, route in routes.items():
        if not _selectable_declaration(route):
            continue
        classes = set(route.get("workload_classes") or [])
        if "implementation" in classes:
            implementers.append((name, route))
        if "review" in classes:
            reviewers.append((name, route))
    for impl_name, implementer in implementers:
        for rev_name, reviewer in reviewers:
            if impl_name == rev_name:
                continue
            if implementer.get("provider_family") != reviewer.get("provider_family"):
                return True
    return False


def _emit_route(name: str, route: dict, omit: set[str]) -> list[str]:
    lines = [f"  {json.dumps(name)}:"]
    for key, value in route.items():
        if key in omit:
            continue
        if key == "evidence" and isinstance(value, dict):
            lines.append("    evidence:")
            for evidence_key, evidence_value in value.items():
                lines.append(f"      {evidence_key}: {_scalar(evidence_value)}")
            continue
        if isinstance(value, list):
            if not value:
                lines.append(f"    {key}: []")
            else:
                lines.append(f"    {key}:")
                for item in value:
                    lines.append(f"      - {_scalar(item)}")
            continue
        lines.append(f"    {key}: {_scalar(value)}")
    return lines


def write_policy(
    tmp_path: Path,
    routes: dict,
    *,
    default: str | None = None,
    omit: dict[str, set[str]] | None = None,
    pair_exists: bool | None = None,
    name: str = "policy.yaml",
) -> Path:
    omit = omit or {}
    if default is None:
        default = next(iter(routes))
    if pair_exists is None:
        pair_exists = _pair_exists(routes)
    statement = (
        "implementation acceptance requires a reviewer provider family "
        "different from the implementer family; "
        + (
            "a qualifying independent pair is declared"
            if pair_exists
            else "the current approved route set has no qualifying independent pair"
        )
    )
    lines = [
        'version: "2026-10-26.test"',
        'generated_at: "2026-10-26T00:00:00Z"',
        f"default_route: {_scalar(default)}",
        "routes:",
    ]
    for route_name, route in routes.items():
        lines.extend(_emit_route(route_name, route, omit.get(route_name, set())))
    lines.extend(
        [
            "review_independence:",
            "  profile_or_session_separation_creates_diversity: false",
            "  implementation:",
            "    reviewer_family_must_differ_from_implementer: true",
            f"    current_approved_pair_exists: {_scalar(pair_exists)}",
            f"    statement: {_scalar(statement)}",
            "",
        ]
    )
    path = tmp_path / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _evidence_for(route, **overrides) -> ReadinessEvidence:
    payload = dict(
        route_name=route.name,
        provider=route.provider,
        model=route.model,
        evidence_timestamp=NOW,
        task_epoch=EPOCH,
        reachable=True,
        failure_category=None,
    )
    payload.update(overrides)
    return ReadinessEvidence(**payload)


def _result_for(route, **overrides) -> DispatchResult:
    payload = dict(
        selected_route_name=route.name,
        provider=route.provider,
        model=route.model,
        evidence_timestamp=NOW,
        task_epoch=EPOCH,
        reachable=True,
        failure_category=None,
        side_effects_may_have_occurred=False,
        actual_provider=route.provider,
        actual_model=route.model,
        actual_route=route.name,
        partial_output=False,
    )
    payload.update(overrides)
    return DispatchResult(**payload)


def _load_shipped():
    return load_model_policy(SHIPPED)


def test_shipped_policy_loads_exactly_three_declared_routes():
    text = SHIPPED.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "unknown" in lowered
    assert "reachability" in lowered
    assert "credential" in lowered
    assert "remaining credits" in lowered or "remaining credit" in lowered

    policy = _load_shipped()
    assert set(policy.routes) == {
        "noesis_implement_primary",
        "noesis_review_primary",
        "noesis_cheap_fallback",
    }
    assert policy.default_route == "noesis_review_primary"
    assert isinstance(policy.version, str) and policy.version
    assert policy.generated_at.endswith("Z") or policy.generated_at.endswith("+00:00")
    assert policy.profile_or_session_separation_creates_diversity is False
    for route in policy.routes.values():
        assert route.provider
        assert route.model
        assert route.provider_family
        assert route.workload_classes
        assert route.risk_tier_max in {"r0", "r1", "r2", "r3"}
        assert route.data_classes
        assert isinstance(route.fallback_allowed, bool)
        assert route.fallback_routes == ()
        assert route.fallback_allowed is False
        assert route.credential_scope
        assert route.status in {"approved", "proposed", "disabled"}
        assert route.evidence.quota in QUOTA_STATES
        assert isinstance(route.evidence.readiness_ttl_seconds, int)
        assert route.evidence.readiness_ttl_seconds >= 0
        assert isinstance(route.evidence.requires_reachability_probe, bool)
        assert route.evidence.readiness_state in READINESS_STATES


def test_missing_required_field_rejected(tmp_path):
    missing_provider = write_policy(
        tmp_path,
        {"lane_a": _route()},
        omit={"lane_a": {"provider"}},
        name="missing-provider.yaml",
    )
    with pytest.raises(ModelPolicyError, match="provider"):
        load_model_policy(missing_provider)

    evidence = {
        "quota": "unknown",
        "readiness_ttl_seconds": 3600,
        "requires_reachability_probe": True,
    }
    missing_state = write_policy(
        tmp_path,
        {"lane_b": _route(evidence=evidence)},
        name="missing-readiness-state.yaml",
    )
    with pytest.raises(ModelPolicyError, match="readiness_state"):
        load_model_policy(missing_state)


def test_undefined_fallback_route_rejected(tmp_path):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(fallback_allowed=True, fallback_routes=["missing_lane"])},
    )
    with pytest.raises(ModelPolicyError, match="not defined"):
        load_model_policy(path)


def test_fallback_cycle_rejected(tmp_path):
    routes = {
        "lane_a": _route(
            fallback_allowed=True,
            fallback_routes=["lane_b"],
            provider_family="alpha",
        ),
        "lane_b": _route(
            fallback_allowed=True,
            fallback_routes=["lane_a"],
            provider_family="alpha",
        ),
    }
    path = write_policy(tmp_path, routes)
    with pytest.raises(ModelPolicyError, match="fallback cycle"):
        load_model_policy(path)


def test_fallback_disabled_with_nonempty_routes_rejected(tmp_path):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(fallback_allowed=False, fallback_routes=["lane_a"])},
    )
    with pytest.raises(ModelPolicyError, match="fallback_allowed"):
        load_model_policy(path)


def test_data_class_outside_allowed_set_rejected(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route(data_classes=["secret"])})
    with pytest.raises(ModelPolicyError, match="data class"):
        load_model_policy(path)


def test_invalid_risk_tier_rejected(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route(risk_tier_max="r9")})
    with pytest.raises(ModelPolicyError, match="risk tier"):
        load_model_policy(path)


def test_non_integer_or_negative_ttl_rejected(tmp_path):
    for label, ttl in (("float", 1.5), ("string", "3600"), ("negative", -1)):
        evidence = {
            "quota": "unknown",
            "readiness_ttl_seconds": ttl,
            "requires_reachability_probe": True,
            "readiness_state": "reachable",
        }
        path = write_policy(
            tmp_path,
            {"lane_a": _route(evidence=evidence)},
            name=f"ttl-{label}.yaml",
        )
        with pytest.raises(ModelPolicyError, match="readiness_ttl_seconds"):
            load_model_policy(path)


def test_secret_like_credential_scope_rejected(tmp_path):
    path = write_policy(
        tmp_path,
        {
            "lane_a": _route(
                credential_scope="sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"
            )
        },
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(path)


def test_unknown_workload_class_rejected(tmp_path):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(workload_classes=["not-a-workload"])},
    )
    with pytest.raises(ModelPolicyError, match="workload class"):
        load_model_policy(path)


def test_unserved_workload_class_refused():
    policy = _load_shipped()
    result = select_route(
        policy,
        "research",
        "r0",
        "public",
        {"noesis_review_primary"},
    )
    assert result.allowed is False
    assert "research" in result.reason
    assert "no route serves" in result.reason


def test_lower_risk_request_allowed_under_higher_maximum(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route(risk_tier_max="r2")})
    policy = load_model_policy(path)
    route = policy.routes["lane_a"]
    result = select_route(
        policy,
        "implementation",
        "r1",
        "internal",
        {"lane_a"},
        readiness=_evidence_for(route),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is True
    assert result.route is not None
    assert result.route.name == "lane_a"
    assert "above the requested risk tier" not in result.reason


def test_route_risk_maximum_below_request_refused(tmp_path):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(risk_tier_max="r1", workload_classes=["classification"])},
    )
    policy = load_model_policy(path)
    result = select_route(policy, "classification", "r2", "public", {"lane_a"})
    assert result.allowed is False
    assert "below the request" in result.reason


def test_disallowed_data_classification_refused(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route(data_classes=["public"])})
    policy = load_model_policy(path)
    result = select_route(policy, "implementation", "r2", "internal", {"lane_a"})
    assert result.allowed is False
    assert "data classification" in result.reason
    assert "internal" in result.reason


def test_proposed_route_refused():
    policy = _load_shipped()
    cheap = policy.routes["noesis_cheap_fallback"]
    assert cheap.status == "proposed"
    assert cheap.evidence.readiness_state == "unverified"
    assert cheap.evidence.quota == "unknown"
    result = select_route(
        policy,
        "classification",
        "r1",
        "internal_redacted",
        {"noesis_cheap_fallback"},
        readiness=_evidence_for(cheap),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is False
    assert "not approved" in result.reason
    assert "noesis_cheap_fallback" in result.reason


def test_unavailable_route_refusal_names_route(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route()})
    policy = load_model_policy(path)
    result = select_route(policy, "implementation", "r2", "internal", set())
    assert result.allowed is False
    assert "lane_a" in result.reason
    assert "available" in result.reason


def test_fallback_chain_empty_when_fallback_forbidden():
    policy = _load_shipped()
    assert fallback_chain(policy, "noesis_review_primary") == []
    assert fallback_chain(policy, "noesis_implement_primary") == []
    assert fallback_chain(policy, "noesis_cheap_fallback") == []


def test_fallback_chain_preserves_declared_order(tmp_path):
    routes = {
        "origin": _route(
            fallback_allowed=True,
            fallback_routes=["fb_b", "fb_a"],
            provider_family="alpha",
        ),
        "fb_b": _route(provider_family="alpha", workload_classes=["classification"], risk_tier_max="r1"),
        "fb_a": _route(provider_family="alpha", workload_classes=["classification"], risk_tier_max="r1"),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="origin"))
    assert fallback_chain(policy, "origin") == ["fb_b", "fb_a"]


def test_same_provider_family_review_pair_refused(tmp_path):
    routes = {
        "impl_lane": _route(
            provider="xai-oauth",
            model="grok-4.7",
            provider_family="xai",
            workload_classes=["implementation"],
        ),
        "rev_lane": _route(
            provider="xai-oauth",
            model="grok-4.7",
            provider_family="xai",
            workload_classes=["review"],
        ),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="impl_lane"))
    decision = check_review_independence(policy, "impl_lane", "rev_lane")
    assert decision.allowed is False
    assert "provider family" in decision.reason


def test_different_provider_families_record_review_roles(tmp_path):
    routes = {
        "impl_lane": _route(
            provider="minimax-oauth",
            model="MiniMax-M3",
            provider_family="minimax",
            workload_classes=["implementation"],
            status="approved",
        ),
        "rev_lane": _route(
            provider="xai-oauth",
            model="grok-4.7",
            provider_family="xai",
            workload_classes=["review", "adversarial_review"],
            status="approved",
        ),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="impl_lane"))
    decision = check_review_independence(policy, "impl_lane", "rev_lane")
    assert decision.allowed is True
    assert decision.implementer_route == "impl_lane"
    assert decision.reviewer_route == "rev_lane"
    assert decision.implementer_family == "minimax"
    assert decision.reviewer_family == "xai"


def test_unapproved_reviewer_route_refused(tmp_path):
    routes = {
        "impl_lane": _route(
            provider="minimax-oauth",
            model="MiniMax-M3",
            provider_family="minimax",
            workload_classes=["implementation"],
            status="approved",
        ),
        "rev_lane": _route(
            provider="xai-oauth",
            model="grok-4.7",
            provider_family="xai",
            workload_classes=["review"],
            status="proposed",
            evidence={
                "quota": "unknown",
                "readiness_ttl_seconds": 3600,
                "requires_reachability_probe": True,
                "readiness_state": "unverified",
            },
        ),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="impl_lane"))
    decision = check_review_independence(policy, "impl_lane", "rev_lane")
    assert decision.allowed is False
    assert "not approved" in decision.reason


def test_credential_safe_summary_has_routes_and_no_key_material():
    policy = _load_shipped()
    summary = credential_safe_summary(policy)
    text = json.dumps(summary)
    for route_name in (
        "noesis_implement_primary",
        "noesis_review_primary",
        "noesis_cheap_fallback",
    ):
        assert route_name in text
    for provider in ("minimax-oauth", "xai-oauth", "nous"):
        assert provider in text
    assert "sk-" not in text
    assert "BEGIN" not in text
    assert "known_exhausted" not in text
    assert "api_key" not in text.lower()
    evidence = summary["routes"]["noesis_review_primary"]["evidence"]
    assert evidence == {
        "readiness_ttl_seconds": 3600,
        "requires_reachability_probe": True,
    }
    assert summary["routes"]["noesis_implement_primary"]["credential_scope"] == "oauth-device-code"
    assert summary["routes"]["noesis_cheap_fallback"]["status"] == "proposed"


def test_readiness_freshness_respects_ttl():
    now = NOW
    assert readiness_is_fresh(now - timedelta(seconds=10), 3600, now) is True
    assert readiness_is_fresh(now - timedelta(seconds=3600), 3600, now) is True
    assert readiness_is_fresh(now - timedelta(seconds=3601), 3600, now) is False
    assert readiness_is_fresh(now + timedelta(seconds=5), 3600, now) is False


def test_shipped_review_independence_is_honestly_blocked():
    policy = _load_shipped()
    rule = policy.review_independence["implementation"]
    assert rule.reviewer_family_must_differ_from_implementer is True
    assert rule.current_approved_pair_exists is False
    assert "no qualifying independent pair" in rule.statement
    implementer = policy.routes["noesis_implement_primary"]
    reviewer = policy.routes["noesis_review_primary"]
    assert implementer.provider_family == "minimax"
    assert reviewer.provider_family == "xai"
    assert implementer.provider_family != reviewer.provider_family
    blocked = check_review_independence(policy, implementer.name, reviewer.name)
    assert blocked.allowed is False
    assert "not approved" in blocked.reason
    same_family = check_review_independence(policy, reviewer.name, reviewer.name)
    assert same_family.allowed is False
    assert "provider family" in same_family.reason
    assert has_qualifying_independent_pair(policy, "implementation") is False


def test_shipped_approved_routes_exclude_unusable_audit_providers(tmp_path):
    text = SHIPPED.read_text(encoding="utf-8")
    for provider in UNUSABLE_PROVIDERS:
        assert provider not in text
    policy = _load_shipped()
    approved = [route for route in policy.routes.values() if route.status == "approved"]
    assert approved
    for route in approved:
        assert route.provider not in UNUSABLE_PROVIDERS
    venice = _route(provider="venice", model="venice-model", provider_family="venice")
    loaded = load_model_policy(write_policy(tmp_path, {"venice_lane": venice}))
    assert loaded.routes["venice_lane"].provider == "venice"


def test_shipped_minimax_lane_is_disabled_and_known_exhausted():
    policy = _load_shipped()
    route = policy.routes["noesis_implement_primary"]
    assert route.provider == "minimax-oauth"
    assert route.model == "MiniMax-M3"
    assert route.provider_family == "minimax"
    assert route.workload_classes == ("implementation",)
    assert route.risk_tier_max == "r2"
    assert route.data_classes == ("public", "internal")
    assert route.fallback_routes == ()
    assert route.fallback_allowed is False
    assert route.credential_scope == "oauth-device-code"
    assert route.status == "disabled"
    assert route.evidence.quota == "known_exhausted"
    assert route.evidence.readiness_state == "quota_exhausted"
    assert route.evidence.readiness_ttl_seconds == 3600
    assert route.evidence.requires_reachability_probe is True
    result = select_route(
        policy,
        "implementation",
        "r2",
        "internal",
        {"noesis_implement_primary"},
        readiness=_evidence_for(route),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is False
    assert "noesis_implement_primary" in result.reason
    assert "disabled" in result.reason
    assert "known_exhausted" in result.reason
    admission = admit_route(policy, route, _evidence_for(route), EPOCH, NOW)
    assert isinstance(admission, AdmissionDecision)
    assert admission.allowed is False


def test_shipped_default_xai_route_is_approved_with_unknown_quota():
    policy = _load_shipped()
    assert policy.default_route == "noesis_review_primary"
    route = policy.routes["noesis_review_primary"]
    assert route.provider == "xai-oauth"
    assert route.model == "grok-4.7"
    assert route.provider_family == "xai"
    assert route.workload_classes == ("implementation", "review", "adversarial_review")
    assert route.risk_tier_max == "r2"
    assert route.data_classes == ("public", "internal")
    assert route.fallback_allowed is False
    assert route.fallback_routes == ()
    assert route.credential_scope == "oauth-device-code"
    assert route.status == "approved"
    assert route.evidence.quota == "unknown"
    assert route.evidence.readiness_state == "reachable"
    assert route.evidence.readiness_ttl_seconds == 3600
    assert route.evidence.requires_reachability_probe is True


def test_shipped_policy_has_no_provider_diverse_review_pair():
    policy = _load_shipped()
    assert has_qualifying_independent_pair(policy, "implementation") is False
    approved = [route for route in policy.routes.values() if route.status == "approved"]
    assert [route.name for route in approved] == ["noesis_review_primary"]
    assert len({route.provider_family for route in approved}) == 1


def test_xai_selectable_only_with_availability_and_fresh_same_epoch_evidence():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    evidence = _evidence_for(route)
    selected = select_route(
        policy,
        "implementation",
        "r2",
        "internal",
        {"noesis_review_primary"},
        readiness=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert selected.allowed is True
    assert selected.route is not None
    assert selected.route.name == "noesis_review_primary"
    assert selected.route.provider == "xai-oauth"
    assert selected.route.model == "grok-4.7"
    reviewed = select_route(
        policy,
        "review",
        "r2",
        "public",
        {"noesis_review_primary"},
        readiness=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert reviewed.allowed is True
    adversarial = select_route(
        policy,
        "adversarial_review",
        "r2",
        "public",
        {"noesis_review_primary"},
        readiness=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert adversarial.allowed is True
    unavailable = select_route(
        policy,
        "implementation",
        "r2",
        "internal",
        set(),
        readiness=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert unavailable.allowed is False
    assert "noesis_review_primary" in unavailable.reason


def test_missing_readiness_evidence_refuses_selection():
    policy = _load_shipped()
    result = select_route(
        policy,
        "implementation",
        "r2",
        "internal",
        {"noesis_review_primary"},
    )
    assert result.allowed is False
    assert "missing readiness evidence" in result.reason
    admission = admit_route(
        policy,
        "noesis_review_primary",
        None,
        EPOCH,
        NOW,
    )
    assert admission.allowed is False
    assert "missing readiness evidence" in admission.reason


def test_expired_readiness_evidence_refuses_admission():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    stale = _evidence_for(route, evidence_timestamp=NOW - timedelta(seconds=3601))
    assert readiness_is_fresh(stale.evidence_timestamp, route.evidence.readiness_ttl_seconds, NOW) is False
    admission = admit_route(policy, route, stale, EPOCH, NOW)
    assert admission.allowed is False
    assert "stale" in admission.reason
    selected = select_route(
        policy,
        "review",
        "r2",
        "internal",
        {"noesis_review_primary"},
        readiness=stale,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert selected.allowed is False
    assert "stale" in selected.reason


def test_wrong_task_epoch_refuses_admission():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    evidence = _evidence_for(route, task_epoch="other-epoch")
    admission = admit_route(policy, route, evidence, EPOCH, NOW)
    assert admission.allowed is False
    assert "task epoch" in admission.reason


def _failure_admission(category: str) -> AdmissionDecision:
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    evidence = _evidence_for(route, failure_category=category, reachable=False)
    return admit_route(policy, route, evidence, EPOCH, NOW)


def test_missing_auth_refuses_admission():
    admission = _failure_admission("missing_auth")
    assert admission.allowed is False
    assert "missing_auth" in admission.reason


def test_quota_exhaustion_refuses_admission():
    admission = _failure_admission("quota_exhausted")
    assert admission.allowed is False
    assert "quota_exhausted" in admission.reason
    classified = categorize_failure("quota_exhausted")
    assert classified.known is True
    assert classified.fallback_authorized is False


def test_rate_limiting_refuses_admission():
    admission = _failure_admission("rate_limited")
    assert admission.allowed is False
    assert "rate_limited" in admission.reason


def test_model_unavailable_refuses_admission():
    admission = _failure_admission("model_unavailable")
    assert admission.allowed is False
    assert "model_unavailable" in admission.reason


def test_wrong_backend_or_profile_provenance_refused():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    admission = _failure_admission("wrong_backend")
    assert admission.allowed is False
    assert "wrong_backend" in admission.reason
    mismatched = _result_for(route, actual_provider="minimax-oauth", actual_model="MiniMax-M3")
    provenance = validate_result_provenance(
        route,
        mismatched,
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert provenance.allowed is False
    assert "provider" in provenance.reason


def test_unsupported_effort_and_service_tier_refused():
    effort = _failure_admission("unsupported_effort")
    tier = _failure_admission("unsupported_tier")
    assert effort.allowed is False
    assert "unsupported_effort" in effort.reason
    assert tier.allowed is False
    assert "unsupported_tier" in tier.reason
    for category in ("unsupported_effort", "unsupported_tier"):
        classified = categorize_failure(category)
        assert classified.known is True
        assert classified.fallback_authorized is False


def test_malformed_route_evidence_rejected():
    policy = _load_shipped()
    with pytest.raises(ModelPolicyError, match="malformed"):
        ReadinessEvidence(
            route_name="",
            provider="xai-oauth",
            model="grok-4.7",
            evidence_timestamp=NOW,
            task_epoch=EPOCH,
            reachable=True,
        )
    with pytest.raises(ModelPolicyError, match="malformed"):
        ReadinessEvidence(
            route_name="noesis_review_primary",
            provider="xai-oauth",
            model="grok-4.7",
            evidence_timestamp=NOW,
            task_epoch=EPOCH,
            reachable=True,
            failure_category="not-a-real-failure",
        )
    admission = admit_route(
        policy,
        "noesis_review_primary",
        {"route_name": "noesis_review_primary"},
        EPOCH,
        NOW,
    )
    assert admission.allowed is False
    assert "malformed" in admission.reason


def _fallback_fixture(tmp_path: Path, fallback_overrides: dict | None = None, *, extra_routes: dict | None = None, chain: list[str] | None = None):
    fallback_overrides = dict(fallback_overrides or {})
    chain = chain or ["changed"]
    origin = _route(
        provider="xai-oauth",
        model="grok-4.7",
        provider_family="xai",
        workload_classes=["implementation"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        fallback_allowed=True,
        fallback_routes=chain,
        status="approved",
    )
    fallback = _route(
        provider="other-provider",
        model="other-model",
        provider_family="other",
        workload_classes=["implementation"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        fallback_allowed=False,
        fallback_routes=[],
        status="approved",
    )
    fallback.update(fallback_overrides)
    routes = {"origin": origin, "changed": fallback}
    if extra_routes:
        routes.update(extra_routes)
    policy = load_model_policy(write_policy(tmp_path, routes, default="origin"))
    evidence = {
        route.name: _evidence_for(route)
        for route in policy.routes.values()
        if route.name != "origin"
    }
    return policy, evidence


def test_fallback_data_policy_mismatch_refused(tmp_path):
    policy, evidence = _fallback_fixture(
        tmp_path,
        {"data_classes": ["public"], "tool_capabilities": ["code_modify"]},
    )
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.routes == ()
    assert "changed" not in plan.routes
    assert "data_policy_mismatch" in plan.reason


def test_fallback_tool_capability_mismatch_refused(tmp_path):
    policy, evidence = _fallback_fixture(
        tmp_path,
        {"tool_capabilities": ["read_only"], "data_classes": ["public", "internal"]},
    )
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="model_unavailable",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.routes == ()
    assert "tool_capability_mismatch" in plan.reason


def test_result_reporting_different_route_provider_or_model_rejected():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    route_mismatch = validate_result_provenance(
        route,
        _result_for(route, actual_route="noesis_implement_primary"),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    provider_mismatch = validate_result_provenance(
        route,
        _result_for(route, actual_provider="minimax-oauth"),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    model_mismatch = validate_result_provenance(
        route,
        _result_for(route, actual_model="MiniMax-M3"),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert route_mismatch.allowed is False
    assert "route" in route_mismatch.reason
    assert provider_mismatch.allowed is False
    assert "provider" in provider_mismatch.reason
    assert model_mismatch.allowed is False
    assert "model" in model_mismatch.reason
    matching = validate_result_provenance(
        route,
        _result_for(route),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert matching.allowed is True


def test_partial_output_before_failure_refuses_retry_and_fallback(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        partial_output=True,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "partial output" in plan.reason
    retry = authorize_retry(
        proposed_route="origin",
        attempt_count=1,
        partial_output=True,
        failure_category="rate_limited",
    )
    assert retry.allowed is False
    assert "partial output" in retry.reason


def test_side_effects_may_have_occurred_refuses_retry_and_fallback(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        side_effects_may_have_occurred=True,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "side effect" in plan.reason
    retry = authorize_retry(
        proposed_route="origin",
        attempt_count=1,
        side_effects_may_have_occurred=True,
        failure_category="rate_limited",
    )
    assert retry.allowed is False
    assert "side effect" in retry.reason


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("partial_output", None),
        ("partial_output", 0),
        ("partial_output", ""),
        ("partial_output", []),
        ("partial_output", {}),
        ("partial_output", False),
        ("partial_output", True),
        ("side_effects_may_have_occurred", None),
        ("side_effects_may_have_occurred", 0),
        ("side_effects_may_have_occurred", ""),
        ("side_effects_may_have_occurred", []),
        ("side_effects_may_have_occurred", {}),
        ("side_effects_may_have_occurred", False),
        ("side_effects_may_have_occurred", True),
    ],
)
def test_planner_and_retry_refuse_non_boolean_clear_flags(tmp_path, field, value):
    """The planner and the retry authorizer must match the success path.

    The success path already requires `is not False` (model_policy.py:808-813),
    so a flag that is anything other than exactly False is unsafe. The planner
    and the retry authorizer used truthiness, which admitted None, 0 and "".
    """
    policy, evidence = _fallback_fixture(tmp_path)
    expected_allowed = value is False
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        **{field: value},
    )
    retry = authorize_retry(
        proposed_route="origin",
        attempt_count=0,
        failure_category="rate_limited",
        **{field: value},
    )
    assert plan.allowed is expected_allowed
    assert retry.allowed is expected_allowed
    if expected_allowed:
        assert plan.routes == ("changed",)
    else:
        assert plan.routes == ()
        assert "partial output" in plan.reason or "side effect" in plan.reason


def test_duplicate_retry_prevented():
    first = authorize_retry(proposed_route="lane_a", attempt_count=0)
    assert first.allowed is True
    duplicate = authorize_retry(
        proposed_route="lane_a",
        attempt_count=1,
        partial_output=False,
        side_effects_may_have_occurred=False,
        failure_category="rate_limited",
    )
    assert duplicate.allowed is False
    assert "duplicate" in duplicate.reason


def test_unknown_failure_refuses_fallback(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    raw = "HTTP 429 Token Plan usage limit reached; purchase or upgrade required"
    classified = categorize_failure(raw)
    assert classified.known is False
    assert classified.fallback_authorized is False
    assert classified.category != "quota_exhausted"
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category=raw,
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "unknown failure" in plan.reason
    assert "changed" not in plan.routes


def test_fallback_plan_caps_at_three_and_ignores_undeclared(tmp_path):
    extra = {}
    for name in ("fb1", "fb2", "fb3", "fb4", "sneaky"):
        extra[name] = _route(
            provider=f"provider-{name}",
            model=f"model-{name}",
            provider_family=f"family-{name}",
            workload_classes=["implementation"],
            data_classes=["public", "internal"],
            tool_capabilities=["code_modify"],
            status="approved",
        )
    origin = _route(
        provider="xai-oauth",
        model="grok-4.7",
        provider_family="xai",
        workload_classes=["implementation"],
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        fallback_allowed=True,
        fallback_routes=["fb1", "fb2", "fb3", "fb4"],
        status="approved",
    )
    routes = {"origin": origin, **extra}
    policy = load_model_policy(write_policy(tmp_path, routes, default="origin"))
    evidence = {route.name: _evidence_for(route) for route in policy.routes.values() if route.name != "origin"}
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.allowed is True
    assert plan.routes == ("fb1", "fb2", "fb3")
    assert "fb4" not in plan.routes
    assert "sneaky" not in plan.routes


def test_synchronous_result_reconciliation_background_unsupported():
    assert BACKGROUND_EXECUTION_SUPPORTED is False
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    matched = reconcile_synchronous_result(
        route,
        _result_for(route),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
        execution_mode="synchronous",
    )
    assert matched.allowed is True
    assert matched.reconciled is True
    assert matched.background_supported is False
    assert matched.execution_mode == "synchronous"
    background = reconcile_synchronous_result(
        route,
        _result_for(route),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
        execution_mode="background",
    )
    assert background.allowed is False
    assert background.reconciled is False
    assert background.background_supported is False
    assert "unsupported" in background.reason
    assert "not activated" in background.reason
    drifted = reconcile_synchronous_result(
        route,
        _result_for(route, actual_model="other-model"),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
        execution_mode="synchronous",
    )
    assert drifted.allowed is False
    assert "model" in drifted.reason


def test_review_independence_claim_must_match_approved_set(tmp_path):
    path = write_policy(tmp_path, {"lane_a": _route()}, pair_exists=True)
    with pytest.raises(ModelPolicyError, match="qualifying"):
        load_model_policy(path)


def _evidence_body(quota: str, readiness_state: str, ttl: int = 3600) -> dict:
    return {
        "quota": quota,
        "readiness_ttl_seconds": ttl,
        "requires_reachability_probe": True,
        "readiness_state": readiness_state,
    }


def test_shipped_lower_risk_review_does_not_require_tier_inflation():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    result = select_route(
        policy,
        "review",
        "r1",
        "public",
        {"noesis_review_primary"},
        readiness=_evidence_for(route),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is True
    assert result.route is not None
    assert result.route.name == "noesis_review_primary"
    assert "above the requested risk tier" not in result.reason


def test_request_above_route_maximum_still_refused():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    result = select_route(
        policy,
        "review",
        "r3",
        "public",
        {"noesis_review_primary"},
        readiness=_evidence_for(route),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is False
    assert "below the request" in result.reason


def test_lowest_sufficient_maximum_preferred_over_default(tmp_path):
    routes = {
        "default_high": _route(risk_tier_max="r2", provider_family="xai"),
        "tight": _route(risk_tier_max="r1", provider_family="nous"),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="default_high"))
    tight = policy.routes["tight"]
    result = select_route(
        policy,
        "implementation",
        "r0",
        "internal",
        {"default_high", "tight"},
        readiness=_evidence_for(tight),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is True
    assert result.route is not None
    assert result.route.name == "tight"


def test_default_used_only_inside_lowest_sufficient_set(tmp_path):
    routes = {
        "default_lane": _route(risk_tier_max="r2", provider_family="xai"),
        "other_lane": _route(risk_tier_max="r2", provider_family="nous"),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="default_lane"))
    chosen = policy.routes["default_lane"]
    result = select_route(
        policy,
        "implementation",
        "r1",
        "internal",
        {"default_lane", "other_lane"},
        readiness=_evidence_for(chosen),
        task_epoch=EPOCH,
        now=NOW,
    )
    assert result.allowed is True
    assert result.route is not None
    assert result.route.name == "default_lane"


def test_classifier_and_implementation_only_are_not_a_review_pair(tmp_path):
    routes = {
        "classifier": _route(
            provider="nous",
            model="upstage/solar-mini4:free",
            provider_family="nous",
            workload_classes=["classification"],
            risk_tier_max="r1",
            data_classes=["public", "internal_redacted"],
            credential_scope="free-tier-anonymous",
        ),
        "impl_only": _route(
            provider="xai-oauth",
            model="grok-4.7",
            provider_family="xai",
            workload_classes=["implementation"],
        ),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="impl_only"))
    decision = check_review_independence(policy, "classifier", "impl_only")
    assert decision.allowed is False
    assert decision.implementer_route == "classifier"
    assert decision.reviewer_route == "impl_only"
    assert "implementation" in decision.reason
    assert has_qualifying_independent_pair(policy, "implementation") is False


def test_adversarial_review_alone_is_not_acceptance_review(tmp_path):
    routes = {
        "impl_lane": _route(provider_family="minimax", workload_classes=["implementation"]),
        "adv_only": _route(provider_family="xai", workload_classes=["adversarial_review"]),
    }
    false_claim = write_policy(
        tmp_path,
        routes,
        default="impl_lane",
        pair_exists=True,
        name="false-claim.yaml",
    )
    with pytest.raises(ModelPolicyError, match="qualifying"):
        load_model_policy(false_claim)
    policy = load_model_policy(
        write_policy(tmp_path, routes, default="impl_lane", pair_exists=False, name="honest.yaml")
    )
    assert has_qualifying_independent_pair(policy, "implementation") is False
    decision = check_review_independence(policy, "impl_lane", "adv_only")
    assert decision.allowed is False
    assert "review" in decision.reason


def test_unselectable_approved_implementer_cannot_be_declared_qualifying(tmp_path):
    routes = {
        "impl_exhausted": _route(
            provider_family="minimax",
            workload_classes=["implementation"],
            status="approved",
            evidence=_evidence_body("known_exhausted", "reachable"),
        ),
        "rev_lane": _route(provider_family="xai", workload_classes=["review"]),
    }
    path = write_policy(tmp_path, routes, default="rev_lane", pair_exists=True)
    with pytest.raises(ModelPolicyError):
        load_model_policy(path)


def test_qualifying_pair_calculator_rejects_unselectable_approved_implementer():
    from app.model_policy import RouteDefinition, RouteEvidence, _qualifying_pair_exists

    exhausted = RouteDefinition(
        name="impl_exhausted",
        provider="minimax-oauth",
        model="MiniMax-M3",
        provider_family="minimax",
        workload_classes=("implementation",),
        risk_tier_max="r2",
        data_classes=("public", "internal"),
        fallback_routes=(),
        fallback_allowed=False,
        credential_scope="oauth-device-code",
        evidence=RouteEvidence(
            quota="known_exhausted",
            readiness_ttl_seconds=3600,
            requires_reachability_probe=True,
            readiness_state="reachable",
        ),
        status="approved",
    )
    reviewer = RouteDefinition(
        name="rev_lane",
        provider="xai-oauth",
        model="grok-4.7",
        provider_family="xai",
        workload_classes=("review",),
        risk_tier_max="r2",
        data_classes=("public", "internal"),
        fallback_routes=(),
        fallback_allowed=False,
        credential_scope="oauth-device-code",
        evidence=RouteEvidence(
            quota="unknown",
            readiness_ttl_seconds=3600,
            requires_reachability_probe=True,
            readiness_state="reachable",
        ),
        status="approved",
    )
    assert _qualifying_pair_exists(
        {"impl_exhausted": exhausted, "rev_lane": reviewer},
        "implementation",
    ) is False


def test_disabled_exhausted_implementer_cannot_qualify(tmp_path):
    routes = {
        "impl_exhausted": _route(
            provider_family="minimax",
            workload_classes=["implementation"],
            status="disabled",
            evidence=_evidence_body("known_exhausted", "quota_exhausted"),
        ),
        "rev_lane": _route(provider_family="xai", workload_classes=["review"]),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="rev_lane", pair_exists=False))
    assert has_qualifying_independent_pair(policy, "implementation") is False
    decision = check_review_independence(policy, "impl_exhausted", "rev_lane")
    assert decision.allowed is False


def test_future_readiness_evidence_reason_is_future_not_stale():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    future = _evidence_for(route, evidence_timestamp=NOW + timedelta(seconds=1))
    admission = admit_route(policy, route, future, EPOCH, NOW)
    assert admission.allowed is False
    assert "future" in admission.reason
    assert "stale" not in admission.reason
    selected = select_route(
        policy,
        "review",
        "r2",
        "public",
        {"noesis_review_primary"},
        readiness=future,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert selected.allowed is False
    assert "future" in selected.reason
    assert "stale" not in selected.reason


def test_synchronous_success_requires_epoch_timestamp_and_selectability():
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    accepted = reconcile_synchronous_result(
        route,
        _result_for(route),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert accepted.allowed is True
    assert accepted.reconciled is True
    cross_epoch = reconcile_synchronous_result(
        route,
        _result_for(route, task_epoch="other-epoch"),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert cross_epoch.allowed is False
    assert "epoch" in cross_epoch.reason
    future = reconcile_synchronous_result(
        route,
        _result_for(route, evidence_timestamp=NOW + timedelta(days=30)),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert future.allowed is False
    assert "future" in future.reason
    assert "stale" not in future.reason
    stale = reconcile_synchronous_result(
        route,
        _result_for(route, evidence_timestamp=NOW - timedelta(days=400)),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert stale.allowed is False
    assert "stale" in stale.reason
    assert "future" not in stale.reason
    combined = reconcile_synchronous_result(
        route,
        _result_for(
            route,
            task_epoch="other-epoch",
            evidence_timestamp=NOW + timedelta(days=30),
        ),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert combined.allowed is False
    disabled = policy.routes["noesis_implement_primary"]
    disabled_success = reconcile_synchronous_result(
        disabled,
        _result_for(disabled),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert disabled_success.allowed is False
    partial = reconcile_synchronous_result(
        route,
        _result_for(route, partial_output=True),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert partial.allowed is False
    side_effects = reconcile_synchronous_result(
        route,
        _result_for(route, side_effects_may_have_occurred=True),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert side_effects.allowed is False


@pytest.mark.parametrize(
    ("status", "quota", "readiness_state"),
    [
        ("approved", "known_exhausted", "reachable"),
        ("approved", "unknown", "unverified"),
        ("approved", "known_available", "quota_exhausted"),
        ("disabled", "unknown", "reachable"),
        ("proposed", "unknown", "reachable"),
        ("disabled", "known_exhausted", "reachable"),
        ("disabled", "known_available", "quota_exhausted"),
        ("disabled", "known_available", "missing_auth"),
        ("disabled", "known_available", "disabled"),
        ("proposed", "known_available", "missing_auth"),
    ],
)
def test_contradictory_route_state_rejected(tmp_path, status, quota, readiness_state):
    path = write_policy(
        tmp_path,
        {
            "bad": _route(
                status=status,
                evidence=_evidence_body(quota, readiness_state),
            )
        },
        name=f"{status}-{quota}-{readiness_state}.yaml",
    )
    with pytest.raises(ModelPolicyError, match="inconsistent route state"):
        load_model_policy(path)


def test_consistent_non_shipped_lane_shapes_remain_loadable(tmp_path):
    routes = {
        "available": _route(evidence=_evidence_body("known_available", "reachable")),
        "disabled_exhausted": _route(
            provider_family="minimax",
            status="disabled",
            evidence=_evidence_body("known_exhausted", "quota_exhausted"),
        ),
        "proposed_unverified": _route(
            provider_family="nous",
            workload_classes=["classification"],
            risk_tier_max="r1",
            status="proposed",
            evidence=_evidence_body("unknown", "unverified", ttl=1800),
        ),
    }
    policy = load_model_policy(write_policy(tmp_path, routes, default="available"))
    assert policy.routes["available"].evidence.quota == "known_available"
    assert policy.routes["disabled_exhausted"].status == "disabled"
    assert policy.routes["proposed_unverified"].status == "proposed"


def test_token_shaped_single_segment_credential_scope_rejected(tmp_path):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(credential_scope="a1b2c3d4e5f678901234ab")},
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(path)


def test_secret_prefix_matching_category_grammar_rejected(tmp_path):
    accepted = load_model_policy(
        write_policy(
            tmp_path,
            {"lane_a": _route(credential_scope="api-key-env")},
            name="category.yaml",
        )
    )
    assert accepted.routes["lane_a"].credential_scope == "api-key-env"
    rejected = write_policy(
        tmp_path,
        {"lane_a": _route(credential_scope="sk-live")},
        name="secret-prefix.yaml",
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(rejected)


def test_fallback_duplicate_names_do_not_consume_cap(tmp_path):
    extra = {}
    for name in ("fb", "other1", "other2", "other3"):
        extra[name] = _route(
            provider=f"provider-{name}",
            model=f"model-{name}",
            provider_family=f"family-{name}",
            workload_classes=["implementation"],
            risk_tier_max="r2",
            data_classes=["public", "internal"],
            tool_capabilities=["code_modify"],
            status="approved",
        )
    origin = _route(
        provider="xai-oauth",
        model="grok-4.7",
        provider_family="xai",
        workload_classes=["implementation"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        fallback_allowed=True,
        fallback_routes=["fb", "fb", "fb", "other1", "other2", "other3"],
        status="approved",
    )
    policy = load_model_policy(write_policy(tmp_path, {"origin": origin, **extra}, default="origin"))
    evidence = {
        route.name: _evidence_for(route)
        for route in policy.routes.values()
        if route.name != "origin"
    }
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.allowed is True
    assert plan.routes == ("fb", "other1", "other2")
    assert plan.routes.count("fb") == 1
    assert "other3" not in plan.routes


def test_fallback_rejects_maximum_below_origin_when_workload_matches(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path, {"risk_tier_max": "r1"})
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "risk tier maximum" in plan.reason


def test_fallback_rejects_workload_and_risk_below_origin(tmp_path):
    policy, evidence = _fallback_fixture(
        tmp_path,
        {
            "workload_classes": ["classification"],
            "risk_tier_max": "r1",
            "data_classes": ["public", "internal"],
            "tool_capabilities": ["code_modify"],
        },
    )
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "changed" not in plan.routes


def test_fallback_does_not_plan_attempted_route(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=["changed"],
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "changed" not in plan.routes


def test_fallback_refuses_string_attempted_routes(tmp_path):
    """A bare str is a Collection[str], so it would be iterated per character.

    The character set never equals the route name, so the duplicate-retry
    exclusion would never fire and an already-attempted route could be planned
    again. The planner must refuse the invalid shape instead.
    """
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes="changed",
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "changed" not in plan.routes
    assert "attempted_routes" in plan.reason
    assert "not a string" in plan.reason


def test_fallback_rejects_candidate_below_caller_risk(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        caller_risk_tier="r3",
    )
    assert plan.allowed is False
    assert plan.routes == ()


def test_fallback_allows_candidate_covering_origin_and_caller_risk(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path, {"risk_tier_max": "r3"})
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        caller_risk_tier="r2",
    )
    assert plan.allowed is True
    assert plan.routes == ("changed",)


def test_invalid_attempt_count_refused_by_retry_and_planning(tmp_path):
    policy, evidence = _fallback_fixture(tmp_path)
    for value in (-1, False, True, 1.5, "1"):
        decision = authorize_retry(proposed_route="lane_a", attempt_count=value)
        assert decision.allowed is False
        assert "invalid" in decision.reason
        plan = plan_fallback_sequence(
            policy,
            "origin",
            failure_category="rate_limited",
            evidence_by_route=evidence,
            task_epoch=EPOCH,
            now=NOW,
            attempt_count=value,
        )
        assert plan.allowed is False
        assert plan.routes == ()
        assert "invalid" in plan.reason


def test_foreign_workload_class_cannot_authorize_classification_fallback(tmp_path):
    classy = _route(
        provider="nous",
        model="classifier",
        provider_family="nous",
        workload_classes=["classification"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        status="approved",
    )
    capable = _route(
        provider="other-provider",
        model="other-model",
        provider_family="other",
        workload_classes=["implementation"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        status="approved",
    )
    origin = _route(
        provider="xai-oauth",
        model="grok-4.7",
        provider_family="xai",
        workload_classes=["implementation"],
        risk_tier_max="r2",
        data_classes=["public", "internal"],
        tool_capabilities=["code_modify"],
        fallback_allowed=True,
        fallback_routes=["classy", "capable"],
        status="approved",
    )
    policy = load_model_policy(
        write_policy(
            tmp_path,
            {"origin": origin, "classy": classy, "capable": capable},
            default="origin",
        )
    )
    evidence = {
        name: _evidence_for(policy.routes[name]) for name in ("classy", "capable")
    }
    foreign = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        workload_class="classification",
    )
    assert foreign.allowed is False
    assert foreign.routes == ()
    assert "classy" not in foreign.routes
    assert "classification" in foreign.reason
    omitted = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert omitted.allowed is True
    assert omitted.routes == ("capable",)
    assert "classy" not in omitted.routes
    named = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        workload_class="implementation",
    )
    assert named.allowed is True
    assert named.routes == ("capable",)
    assert "classy" not in named.routes


@pytest.mark.parametrize(
    "scope",
    [
        "scope-sk-live",
        "cat-a1b2c3d4e5f678901234ab",
        "route-akiaiosfodnn7example",
        "scope-xoxb-abcd",
    ],
)
def test_secret_or_token_in_any_hyphen_segment_rejected(tmp_path, scope):
    path = write_policy(
        tmp_path,
        {"lane_a": _route(credential_scope=scope)},
        name=f"embedded-{scope}.yaml",
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(path)


@pytest.mark.parametrize(
    "scope",
    [
        "oauth-device-code",
        "api-key-env",
        "free-tier-anonymous",
        "subscription-oauth",
    ],
)
def test_valid_credential_category_labels_remain_accepted(tmp_path, scope):
    policy = load_model_policy(
        write_policy(
            tmp_path,
            {"lane_a": _route(credential_scope=scope)},
            name=f"category-{scope}.yaml",
        )
    )
    assert policy.routes["lane_a"].credential_scope == scope


@pytest.mark.parametrize(
    "scope",
    [
        "scope-sklive",
        "scope-xoxb",
        "scope-bearertoken",
        "scope-privatekey",
        "scope-sk",
    ],
)
def test_concatenated_secret_prefix_credential_scope_rejected(tmp_path, scope):
    """A secret prefix must be recognised even when its delimiter is dropped.

    The prefix detector used to require the prefix at a segment start or after
    a hyphen, so 'scope-sklive' and friends satisfied the category grammar and
    were then copied verbatim into credential_safe_summary's credential-safe
    output. The concatenated forms must be refused at load.
    """
    path = write_policy(
        tmp_path,
        {"lane_a": _route(credential_scope=scope)},
        name=f"concatenated-{scope}.yaml",
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("partial_output", None),
        ("partial_output", 0),
        ("partial_output", "false"),
        ("side_effects_may_have_occurred", None),
        ("side_effects_may_have_occurred", 0),
        ("side_effects_may_have_occurred", "false"),
    ],
)
def test_synchronous_success_rejects_non_boolean_clear_flags(field, value):
    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    decision = reconcile_synchronous_result(
        route,
        _result_for(route, **{field: value}),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert decision.allowed is False
    assert decision.reconciled is True


def test_caller_supplied_route_is_rebound_to_policy():
    """A caller RouteDefinition is not authoritative. The policy route is.

    A fabricated object shadowing a shipped name with a different provider/model,
    status='approved', or an inflated readiness TTL must be refused. A name
    absent from the policy must be refused. The genuine shipped route must
    still reconcile with fresh same-epoch evidence.
    """

    policy = _load_shipped()
    review = policy.routes["noesis_review_primary"]
    disabled = policy.routes["noesis_implement_primary"]
    fabricated = replace(
        disabled,
        provider="rogue-provider",
        model="rogue-model",
        status="approved",
        evidence=replace(review.evidence, readiness_ttl_seconds=10**9),
    )
    matching_fabrication = _result_for(fabricated)
    reconciled = reconcile_synchronous_result(
        fabricated,
        matching_fabrication,
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert reconciled.allowed is False
    assert "provider" in reconciled.reason
    provenance = validate_result_provenance(
        fabricated,
        matching_fabrication,
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert provenance.allowed is False
    assert "provider" in provenance.reason

    status_shadow = replace(disabled, status="approved", evidence=review.evidence)
    status_decision = reconcile_synchronous_result(
        status_shadow,
        _result_for(status_shadow),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert status_decision.allowed is False
    assert "status" in status_decision.reason

    inflated = replace(review, evidence=replace(review.evidence, readiness_ttl_seconds=10**9))
    stale_result = _result_for(review, evidence_timestamp=NOW - timedelta(days=400))
    stale_reconciled = reconcile_synchronous_result(
        inflated,
        stale_result,
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert stale_reconciled.allowed is False
    assert "stale" in stale_reconciled.reason
    assert "future" not in stale_reconciled.reason
    stale_provenance = validate_result_provenance(
        inflated,
        stale_result,
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert stale_provenance.allowed is False
    assert "stale" in stale_provenance.reason
    fresh_inflated = reconcile_synchronous_result(
        inflated,
        _result_for(review),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert fresh_inflated.allowed is False
    assert "readiness_ttl_seconds" in fresh_inflated.reason

    absent = replace(review, name="not-a-shipped-route")
    absent_reconciled = reconcile_synchronous_result(
        absent,
        _result_for(absent),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert absent_reconciled.allowed is False
    assert "not defined" in absent_reconciled.reason
    absent_provenance = validate_result_provenance(
        absent,
        _result_for(absent),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert absent_provenance.allowed is False
    assert "not defined" in absent_provenance.reason
    absent_name = validate_result_provenance(
        "not-a-shipped-route",
        _result_for(review),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert absent_name.allowed is False
    assert "not defined" in absent_name.reason

    genuine = reconcile_synchronous_result(
        review,
        _result_for(review),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert genuine.allowed is True
    assert genuine.reconciled is True
    genuine_provenance = validate_result_provenance(
        review,
        _result_for(review),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert genuine_provenance.allowed is True
    by_name = validate_result_provenance(
        review.name,
        _result_for(review),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert by_name.allowed is True


def test_provenance_enforces_task_epoch_and_freshness():
    """Provenance itself refuses a cross-epoch, future, or stale result.

    reconcile_synchronous_result keeps refusing those same inputs. A fresh
    same-epoch identity match is still allowed.
    """

    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    cases = (
        (_result_for(route, task_epoch="other-epoch"), "epoch", "stale"),
        (_result_for(route, evidence_timestamp=NOW + timedelta(days=30)), "future", "stale"),
        (_result_for(route, evidence_timestamp=NOW - timedelta(days=400)), "stale", "future"),
    )
    for result, needle, absent in cases:
        provenance = validate_result_provenance(
            route,
            result,
            policy,
            task_epoch=EPOCH,
            now=NOW,
        )
        assert provenance.allowed is False
        assert needle in provenance.reason
        assert absent not in provenance.reason
        decision = reconcile_synchronous_result(
            route,
            result,
            policy=policy,
            task_epoch=EPOCH,
            now=NOW,
        )
        assert decision.allowed is False
        assert needle in decision.reason
    fresh = validate_result_provenance(
        route,
        _result_for(route),
        policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert fresh.allowed is True
    accepted = reconcile_synchronous_result(
        route,
        _result_for(route),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert accepted.allowed is True
    assert accepted.reconciled is True


def test_dispatch_result_rejects_naive_evidence_timestamp():
    """A naive DispatchResult timestamp is refused at construction.

    The timezone-aware equivalent still reconciles.
    """

    policy = _load_shipped()
    route = policy.routes["noesis_review_primary"]
    with pytest.raises(ModelPolicyError, match="timezone-aware"):
        _result_for(route, evidence_timestamp=NOW.replace(tzinfo=None))
    aware = reconcile_synchronous_result(
        route,
        _result_for(route, evidence_timestamp=NOW),
        policy=policy,
        task_epoch=EPOCH,
        now=NOW,
    )
    assert aware.allowed is True
    assert aware.reconciled is True


@pytest.mark.parametrize(
    "shape",
    ["bytes", "bytearray", "memoryview", "list-of-bytes"],
)
def test_fallback_refuses_non_string_attempted_route_elements(tmp_path, shape):
    """Byte-like attempted_routes must not be planned again.

    A bytes, bytearray, or memoryview value iterates as ints, and a list of
    bytes iterates as bytes. str(item) is then not the route name, so the
    duplicate-retry exclusion would not fire. Every such shape is refused.
    """

    attempted_routes = {
        "bytes": b"changed",
        "bytearray": bytearray(b"changed"),
        "memoryview": memoryview(b"changed"),
        "list-of-bytes": [b"changed"],
    }[shape]
    policy, evidence = _fallback_fixture(tmp_path)
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=attempted_routes,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "changed" not in plan.routes
    assert "attempted_routes" in plan.reason
    assert "invalid shape" in plan.reason


def test_fallback_string_element_collections_still_exclude_or_plan(tmp_path):
    """List form still excludes by name. None still plans the route.

    Tuple, set, and generator forms of route-name strings keep that same
    exclusion. The element-type guard must not over-refuse them.
    """

    policy, evidence = _fallback_fixture(tmp_path)
    for attempted in (
        ["changed"],
        ("changed",),
        {"changed"},
        (name for name in ("changed",)),
    ):
        plan = plan_fallback_sequence(
            policy,
            "origin",
            failure_category="rate_limited",
            evidence_by_route=evidence,
            task_epoch=EPOCH,
            now=NOW,
            attempted_routes=attempted,
        )
        assert plan.allowed is False
        assert plan.routes == ()
        assert "duplicate retry" in plan.reason
    omitted = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=None,
    )
    assert omitted.allowed is True
    assert omitted.routes == ("changed",)


@pytest.mark.parametrize(
    "scope",
    [
        "risk-tier",
        "task-scope",
        "ask-approval",
        "disk-permission",
        "masked",
        "task",
        "risk",
        "mask",
        "ask",
    ],
)
def test_ordinary_category_words_are_not_secret_prefixes(tmp_path, scope):
    """A category word that merely contains 'sk' is not a secret prefix.

    The unanchored prefix alternative refused these ordinary labels. They are
    category words, and they must load.
    """

    policy = load_model_policy(
        write_policy(
            tmp_path,
            {"lane_a": _route(credential_scope=scope)},
            name=f"ordinary-{scope}.yaml",
        )
    )
    assert policy.routes["lane_a"].credential_scope == scope


@pytest.mark.parametrize(
    "scope",
    [
        "oauth-sk-live",
        "my-sklive",
        "sk-live",
        "ghp_token",
        "github_pat_abc",
        "xoxb-1234",
        "akiaiosfodnn7example",
        "bearer-token",
        "my-password-here",
        "private-key-material",
        "-----begin-rsa",
        "cat-a1b2c3d4e5f678901234ab",
    ],
)
def test_secret_prefix_forms_remain_rejected_after_anchor(tmp_path, scope):
    """Anchoring the prefix must not admit a secret-shaped scope.

    Mid-scope forms and every form the pre-repair regex refused stay refused.
    """

    path = write_policy(
        tmp_path,
        {"lane_a": _route(credential_scope=scope)},
        name=f"still-secret-{scope}.yaml",
    )
    with pytest.raises(ModelPolicyError, match="credential scope"):
        load_model_policy(path)


class _HostileRouteName(str):
    """str subclass whose str() is not the route name."""

    def __str__(self) -> str:
        return "not-the-route-name"


class _SameValueRouteName(str):
    """str subclass whose str() equals the underlying route name."""

    def __str__(self) -> str:
        return str.__str__(self)


@pytest.mark.parametrize(
    "attempted_routes",
    [
        [_HostileRouteName("changed")],
        [_SameValueRouteName("changed")],
    ],
    ids=["overridden-str-different", "overridden-str-same-value"],
)
def test_fallback_refuses_str_subclass_attempted_route_elements(tmp_path, attempted_routes):
    """A str subclass is not a plain route-name string.

    isinstance(item, str) is True for a subclass, and str(item) then calls an
    overridden __str__. When that returns a different string, the route name
    never enters the attempted set and the already-attempted route is planned
    again. An exact-type test refuses every subclass, including one whose
    __str__ returns the same value.

    The fixture must reach this guard. Origin permits fallback to the distinct
    route 'changed', and the evidence route_name matches that route. A control
    with attempted_routes=None must plan it. Otherwise an upstream exclusion
    such as malformed route evidence would mask the fail-open.
    """

    policy, evidence = _fallback_fixture(tmp_path)
    assert policy.routes["origin"].fallback_allowed is True
    assert policy.routes["origin"].fallback_routes == ("changed",)
    assert evidence["changed"].route_name == "changed"
    assert evidence["changed"].provider == policy.routes["changed"].provider
    assert evidence["changed"].model == policy.routes["changed"].model
    control = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=None,
    )
    assert control.allowed is True
    assert control.routes == ("changed",)
    item = attempted_routes[0]
    assert type(item) is not str
    assert isinstance(item, str)
    if type(item) is _SameValueRouteName:
        assert str(item) == "changed"
    else:
        assert str(item) == "not-the-route-name"
        assert str(item) != "changed"
    plan = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=attempted_routes,
    )
    assert plan.allowed is False
    assert plan.routes == ()
    assert "changed" not in plan.routes
    assert "attempted_routes" in plan.reason
    assert "invalid shape" in plan.reason
    assert "duplicate retry" not in plan.reason
    assert "malformed" not in plan.reason


def test_fallback_exact_str_elements_still_exclude_or_plan(tmp_path):
    """Plain route-name strings are still excluded by name, not by shape.

    The exact-type guard must not over-refuse a list, a generator, None, or a
    fallback to a route that has not been attempted.
    """

    policy, evidence = _fallback_fixture(tmp_path)
    assert evidence["changed"].route_name == "changed"
    generated = (name for name in ("changed",))
    assert type(generated).__name__ == "generator"
    for attempted in (
        ["changed"],
        cast(Collection[str], generated),
    ):
        plan = plan_fallback_sequence(
            policy,
            "origin",
            failure_category="rate_limited",
            evidence_by_route=evidence,
            task_epoch=EPOCH,
            now=NOW,
            attempted_routes=attempted,
        )
        assert plan.allowed is False
        assert plan.routes == ()
        assert "duplicate retry" in plan.reason
        assert "invalid shape" not in plan.reason
    omitted = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=None,
    )
    assert omitted.allowed is True
    assert omitted.routes == ("changed",)
    unattempted = plan_fallback_sequence(
        policy,
        "origin",
        failure_category="rate_limited",
        evidence_by_route=evidence,
        task_epoch=EPOCH,
        now=NOW,
        attempted_routes=["not-yet-attempted"],
    )
    assert unattempted.allowed is True
    assert unattempted.routes == ("changed",)
    assert "planned" in unattempted.reason
