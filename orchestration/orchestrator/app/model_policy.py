"""Pure loader and admission rules for the Noesis model-routing policy.

This module reads one caller-supplied YAML file and evaluates routes. It does
not call a provider, open a network connection, read the Hermes home, mutate a
profile, or activate a route. Background execution is unsupported and not
activated. Exception text is never parsed into an authorization.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app import _yaml_compat as yaml

RISK_TIERS = ("r0", "r1", "r2", "r3")
RISK_RANK = {tier: index for index, tier in enumerate(RISK_TIERS)}
DATA_CLASSES = frozenset({"public", "internal", "internal_redacted"})
WORKLOAD_CLASSES = frozenset(
    {
        "implementation",
        "review",
        "adversarial_review",
        "classification",
        "research",
        "writing",
        "agent_architecture",
    }
)
ROUTE_STATUSES = frozenset({"approved", "proposed", "disabled"})
QUOTA_STATES = frozenset({"known_available", "known_exhausted", "unknown"})
READINESS_STATES = frozenset(
    {
        "reachable",
        "unverified",
        "quota_exhausted",
        "rate_limited",
        "model_unavailable",
        "missing_auth",
        "disabled",
    }
)
FAILURE_CATEGORIES = frozenset(
    {
        "missing_auth",
        "quota_exhausted",
        "rate_limited",
        "model_unavailable",
        "wrong_backend",
        "unsupported_effort",
        "unsupported_tier",
        "malformed_route",
        "data_policy_mismatch",
        "tool_capability_mismatch",
        "partial_output",
        "route_mismatch",
    }
)
MAX_FALLBACKS = 3
_MAX_SINGLE_SEGMENT_CATEGORY_LENGTH = 12
BACKGROUND_EXECUTION_SUPPORTED = False

_TOP_LEVEL_FIELDS = frozenset(
    {"version", "generated_at", "default_route", "routes", "review_independence"}
)
_ROUTE_FIELDS = frozenset(
    {
        "provider",
        "model",
        "provider_family",
        "workload_classes",
        "risk_tier_max",
        "data_classes",
        "fallback_routes",
        "fallback_allowed",
        "credential_scope",
        "evidence",
        "status",
        "tool_capabilities",
    }
)
_REQUIRED_ROUTE_FIELDS = _ROUTE_FIELDS - {"tool_capabilities"}
_EVIDENCE_FIELDS = frozenset(
    {
        "quota",
        "readiness_ttl_seconds",
        "requires_reachability_probe",
        "readiness_state",
    }
)
_RULE_FIELDS = frozenset(
    {
        "reviewer_family_must_differ_from_implementer",
        "current_approved_pair_exists",
        "statement",
    }
)
_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_SECRET_SCOPE_RE = re.compile(
    r"(?i)(?:(?:^|-)(?:sk-|ghp_|github_pat_|xox[baprs]-|akia|bearer\b)|password|private-key|-----begin)"
)
# A secret prefix is recognised at the start of a hyphen-separated segment, or
# after a non-letter within that segment, with or without its trailing
# delimiter. Without this, a value that drops the delimiter ('scope-sklive',
# 'scope-xoxb', 'scope-bearertoken', 'scope-privatekey', 'scope-sk') satisfies
# the category grammar and would then be copied verbatim into
# credential_safe_summary's credential-safe output. The prefix is anchored so
# an ordinary word that merely contains those letters ('risk', 'task', 'mask',
# 'ask') is not treated as a secret-prefix form.
_SECRET_SCOPE_PREFIX_RE = re.compile(
    r"(?i)(?:^|[^a-z])(?:sk|ghp|githubpat|xox[baprs]|akia|bearer|password|private)"
)


class ModelPolicyError(ValueError):
    """Raised when a model policy file is malformed or missing a required field."""


@dataclass(frozen=True)
class RouteEvidence:
    """Non-secret readiness declaration stored on a route."""

    quota: str
    readiness_ttl_seconds: int
    requires_reachability_probe: bool
    readiness_state: str


@dataclass(frozen=True)
class RouteDefinition:
    """One declared route. Field names match the managed policy file."""

    name: str
    provider: str
    model: str
    provider_family: str
    workload_classes: tuple[str, ...]
    risk_tier_max: str
    data_classes: tuple[str, ...]
    fallback_routes: tuple[str, ...]
    fallback_allowed: bool
    credential_scope: str
    evidence: RouteEvidence
    status: str
    tool_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewIndependenceRule:
    """Declared independence requirement for one workload class."""

    workload_class: str
    reviewer_family_must_differ_from_implementer: bool
    current_approved_pair_exists: bool
    statement: str


@dataclass(frozen=True)
class ModelPolicy:
    """Validated model-routing policy. Loading it does not activate a route."""

    version: str
    generated_at: str
    default_route: str
    routes: Mapping[str, RouteDefinition]
    review_independence: Mapping[str, ReviewIndependenceRule]
    profile_or_session_separation_creates_diversity: bool


@dataclass(frozen=True)
class SelectionResult:
    """Policy selection outcome. allowed=True is not dispatch authority."""

    allowed: bool
    route: RouteDefinition | None
    reason: str


@dataclass(frozen=True)
class ReviewIndependenceDecision:
    """Review-pair decision with implementer and reviewer roles recorded."""

    allowed: bool
    reason: str
    implementer_route: str
    reviewer_route: str
    implementer_family: str | None = None
    reviewer_family: str | None = None


@dataclass(frozen=True)
class ReadinessEvidence:
    """Caller-supplied readiness evidence. This module does not collect it."""

    route_name: str
    provider: str
    model: str
    evidence_timestamp: datetime
    task_epoch: str
    reachable: bool
    failure_category: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.route_name, str) or not self.route_name.strip():
            raise ModelPolicyError("malformed route evidence: route_name is required")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ModelPolicyError("malformed route evidence: provider is required")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ModelPolicyError("malformed route evidence: model is required")
        if not isinstance(self.task_epoch, str) or not self.task_epoch.strip():
            raise ModelPolicyError("malformed route evidence: task_epoch is required")
        if not isinstance(self.reachable, bool):
            raise ModelPolicyError("malformed route evidence: reachable must be a boolean")
        if not isinstance(self.evidence_timestamp, datetime) or self.evidence_timestamp.tzinfo is None:
            raise ModelPolicyError(
                "malformed route evidence: evidence_timestamp must be a timezone-aware datetime"
            )
        if self.failure_category is not None and self.failure_category not in FAILURE_CATEGORIES:
            raise ModelPolicyError(
                f"malformed route evidence: unknown failure category '{self.failure_category}'"
            )


@dataclass(frozen=True)
class DispatchResult:
    """Synchronous result reported by a caller. This module does not produce one.

    evidence_timestamp must be timezone-aware. A naive timestamp is refused at
    construction so it cannot be silently read as UTC.
    """

    selected_route_name: str
    provider: str
    model: str
    evidence_timestamp: datetime
    task_epoch: str
    reachable: bool
    failure_category: str | None
    side_effects_may_have_occurred: bool
    actual_provider: str
    actual_model: str
    actual_route: str
    partial_output: bool

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_timestamp, datetime) or self.evidence_timestamp.tzinfo is None:
            raise ModelPolicyError(
                "malformed dispatch result: evidence_timestamp must be a timezone-aware datetime"
            )


@dataclass(frozen=True)
class AdmissionDecision:
    """Whether caller evidence may admit an already selected route."""

    allowed: bool
    reason: str
    route_name: str | None = None


@dataclass(frozen=True)
class ProvenanceDecision:
    """Whether a result is bound to the policy route, task epoch, and freshness bound."""

    allowed: bool
    reason: str


@dataclass(frozen=True)
class FallbackPlan:
    """Ordered declared fallback routes, capped at three. Empty means do not fall back."""

    allowed: bool
    routes: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class FailureClassification:
    """Known failures are labeled. Labeling them does not authorize fallback."""

    category: str | None
    known: bool
    fallback_authorized: bool
    reason: str


@dataclass(frozen=True)
class RetryDecision:
    """Whether another attempt is allowed. Duplicate and side-effectful retries are not."""

    allowed: bool
    reason: str


@dataclass(frozen=True)
class ReconciliationDecision:
    """Synchronous result reconciliation. Background execution is unsupported."""

    allowed: bool
    reconciled: bool
    reason: str
    execution_mode: str
    background_supported: bool = False


def load_model_policy(path: str | Path) -> ModelPolicy:
    """Read and strictly validate a model-policy YAML file."""

    policy_path = Path(path)
    try:
        text = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelPolicyError(f"unable to read model policy '{policy_path}': {exc}") from exc
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ModelPolicyError(f"invalid YAML in '{policy_path}': {exc}") from exc
    if not isinstance(loaded, dict):
        raise ModelPolicyError("policy file is not a mapping")
    _reject_unknown(loaded, _TOP_LEVEL_FIELDS, "policy")
    for field in ("version", "generated_at", "default_route", "routes", "review_independence"):
        if field not in loaded:
            raise ModelPolicyError(f"missing required field '{field}'")
    version = _non_empty_str(loaded["version"], "version")
    generated_at = _generated_at(loaded["generated_at"])
    routes = _parse_routes(loaded["routes"])
    default_route = _non_empty_str(loaded["default_route"], "default_route")
    if default_route not in routes:
        raise ModelPolicyError(f"default_route '{default_route}' is not defined")
    _reject_fallback_cycles(routes)
    rules, separation_flag = _parse_review_independence(loaded["review_independence"], routes)
    return ModelPolicy(
        version=version,
        generated_at=generated_at,
        default_route=default_route,
        routes=MappingProxyType(routes),
        review_independence=rules,
        profile_or_session_separation_creates_diversity=separation_flag,
    )


def select_route(
    policy: ModelPolicy,
    workload_class: str,
    risk_tier: str,
    data_classification: str,
    available_routes: Collection[str],
    *,
    readiness: ReadinessEvidence | None = None,
    task_epoch: str | None = None,
    now: datetime | None = None,
    required_tool_capabilities: Collection[str] | None = None,
) -> SelectionResult:
    """Select one approved route at or below its risk ceiling. Positive selection requires fresh same-epoch evidence."""

    serving = [
        route
        for route in policy.routes.values()
        if workload_class in route.workload_classes
    ]
    if not serving:
        return SelectionResult(
            False,
            None,
            f"no route serves workload class '{workload_class}'",
        )
    if risk_tier not in RISK_RANK:
        return SelectionResult(False, None, f"risk tier '{risk_tier}' is not valid")
    requested = RISK_RANK[risk_tier]
    covered = [
        route for route in serving if RISK_RANK[route.risk_tier_max] >= requested
    ]
    if not covered:
        names = ", ".join(route.name for route in serving)
        return SelectionResult(
            False,
            None,
            f"route '{names}' risk tier maximum is below the request",
        )
    data_ok = [route for route in covered if data_classification in route.data_classes]
    if not data_ok:
        return SelectionResult(
            False,
            None,
            f"data classification '{data_classification}' is not permitted",
        )
    available = {str(item) for item in available_routes}
    required_tools = frozenset(required_tool_capabilities or ())
    refusals: list[str] = []
    eligible: list[RouteDefinition] = []
    for route in data_ok:
        selectable, selectable_reason = _policy_route_selectable(route)
        if not selectable:
            refusals.append(selectable_reason)
            continue
        if required_tools and not required_tools.issubset(route.tool_capabilities):
            refusals.append(f"route '{route.name}' tool_capability_mismatch")
            continue
        if route.name not in available:
            refusals.append(f"route '{route.name}' is not in the available set")
            continue
        eligible.append(route)
    if not eligible:
        return SelectionResult(False, None, "; ".join(refusals) or "no eligible route")
    chosen = _choose(policy, eligible)
    if readiness is None or task_epoch is None or now is None:
        return SelectionResult(False, None, "missing readiness evidence")
    admission = admit_route(policy, chosen, readiness, task_epoch, now)
    if not admission.allowed:
        return SelectionResult(False, None, admission.reason)
    return SelectionResult(
        True,
        chosen,
        (
            f"selected {chosen.name} for workload class '{workload_class}' at risk tier "
            f"'{risk_tier}' with caller-supplied availability and fresh same-epoch evidence"
        ),
    )


def fallback_chain(policy: ModelPolicy, route: str | RouteDefinition) -> list[str]:
    """Return declared fallback names, or an empty list when fallback is forbidden."""

    resolved = _resolve_route(policy, route)
    if resolved is None or not resolved.fallback_allowed:
        return []
    return list(resolved.fallback_routes)


def check_review_independence(
    policy: ModelPolicy,
    implementer_route: str | RouteDefinition,
    reviewer_route: str | RouteDefinition,
) -> ReviewIndependenceDecision:
    """Refuse a pair that is not a selectable, provider-diverse implementation review."""

    implementer_name = _route_name(implementer_route)
    reviewer_name = _route_name(reviewer_route)
    implementer = policy.routes.get(implementer_name)
    reviewer = policy.routes.get(reviewer_name)
    implementer_family = None if implementer is None else implementer.provider_family
    reviewer_family = None if reviewer is None else reviewer.provider_family
    if implementer is None or reviewer is None:
        return ReviewIndependenceDecision(
            False,
            "route is not defined",
            implementer_name,
            reviewer_name,
            implementer_family,
            reviewer_family,
        )
    refusal = _implementation_acceptance_refusal(implementer, reviewer)
    if refusal is not None:
        return ReviewIndependenceDecision(
            False,
            refusal,
            implementer_name,
            reviewer_name,
            implementer_family,
            reviewer_family,
        )
    return ReviewIndependenceDecision(
        True,
        "review pair accepted; implementer and reviewer roles recorded",
        implementer_name,
        reviewer_name,
        implementer_family,
        reviewer_family,
    )


def credential_safe_summary(policy: ModelPolicy) -> dict[str, Any]:
    """Return route identity and category labels only. Evidence strings are omitted."""

    routes: dict[str, Any] = {}
    for name, route in policy.routes.items():
        routes[name] = {
            "provider": route.provider,
            "model": route.model,
            "provider_family": route.provider_family,
            "status": route.status,
            "credential_scope": route.credential_scope,
            "evidence": {
                "readiness_ttl_seconds": route.evidence.readiness_ttl_seconds,
                "requires_reachability_probe": route.evidence.requires_reachability_probe,
            },
        }
    return {
        "version": policy.version,
        "default_route": policy.default_route,
        "routes": routes,
    }


def readiness_is_fresh(evidence_timestamp: datetime | str, ttl_seconds: int, now: datetime | str) -> bool:
    """Return whether evidence is not older than its TTL. Future evidence is not fresh."""

    return _evidence_time_reason(evidence_timestamp, ttl_seconds, now) == ""


def _evidence_time_reason(
    evidence_timestamp: datetime | str,
    ttl_seconds: int,
    now: datetime | str,
) -> str:
    """Return '' when fresh, otherwise a future or stale reason."""

    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 0:
        return "readiness evidence is stale"
    timestamp = _as_utc(evidence_timestamp)
    current = _as_utc(now)
    if timestamp is None or current is None:
        return "readiness evidence is stale"
    if timestamp > current:
        return "readiness evidence timestamp is in the future"
    if (current - timestamp).total_seconds() > ttl_seconds:
        return "readiness evidence is stale"
    return ""


def has_qualifying_independent_pair(policy: ModelPolicy, workload_class: str) -> bool:
    """Return whether an approved provider-diverse implementation/review pair exists."""

    return _qualifying_pair_exists(policy.routes, workload_class)


def admit_route(
    policy: ModelPolicy,
    route: str | RouteDefinition,
    evidence: ReadinessEvidence | None,
    task_epoch: str,
    now: datetime,
) -> AdmissionDecision:
    """Admit a route only with fresh same-epoch evidence naming it exactly."""

    resolved = _resolve_route(policy, route)
    route_name = resolved.name if resolved is not None else _route_name(route)
    if resolved is None:
        return AdmissionDecision(False, f"malformed route evidence: route '{route_name}' is not defined", route_name)
    selectable, selectable_reason = _policy_route_selectable(resolved)
    if not selectable:
        return AdmissionDecision(False, selectable_reason, route_name)
    if evidence is None:
        return AdmissionDecision(False, "missing readiness evidence", route_name)
    if not isinstance(evidence, ReadinessEvidence):
        return AdmissionDecision(False, "malformed route evidence", route_name)
    if (
        evidence.route_name != resolved.name
        or evidence.provider != resolved.provider
        or evidence.model != resolved.model
    ):
        return AdmissionDecision(
            False,
            "malformed route evidence: names do not match the selected route, provider, and model",
            route_name,
        )
    if evidence.task_epoch != task_epoch:
        return AdmissionDecision(
            False,
            "readiness evidence task epoch does not match the caller task epoch",
            route_name,
        )
    time_reason = _evidence_time_reason(
        evidence.evidence_timestamp,
        resolved.evidence.readiness_ttl_seconds,
        now,
    )
    if time_reason:
        return AdmissionDecision(False, time_reason, route_name)
    if evidence.failure_category is not None:
        return AdmissionDecision(
            False,
            f"readiness evidence failure category '{evidence.failure_category}' refuses admission",
            route_name,
        )
    if evidence.reachable is not True:
        return AdmissionDecision(False, "readiness evidence is not reachable", route_name)
    return AdmissionDecision(True, f"admitted route '{resolved.name}'", route_name)


def _policy_bound_route(
    policy: ModelPolicy,
    selected_route: str | RouteDefinition,
) -> tuple[RouteDefinition | None, str]:
    """Re-bind a caller route to the policy. The policy object is authoritative.

    A name absent from the policy is refused. A caller-supplied RouteDefinition
    whose provider, model, or status disagrees with the policy route is refused.
    Readiness TTL is not compared here; freshness must use the policy TTL so an
    inflated caller TTL cannot make a stale timestamp look fresh.
    """

    if not isinstance(policy, ModelPolicy):
        return None, "malformed route: selected route is not defined"
    resolved = _resolve_route(policy, selected_route)
    if resolved is None:
        return None, f"malformed route: route '{_route_name(selected_route)}' is not defined"
    if isinstance(selected_route, RouteDefinition):
        mismatches: list[str] = []
        if selected_route.provider != resolved.provider or selected_route.model != resolved.model:
            mismatches.append("provider/model")
        if selected_route.status != resolved.status:
            mismatches.append("status")
        if mismatches:
            return None, "caller-supplied route is not the policy route: " + ", ".join(mismatches)
    return resolved, ""


def _caller_ttl_disagrees(selected_route: str | RouteDefinition, bound: RouteDefinition) -> str:
    """Refuse a caller TTL that is not the policy TTL.

    Called only after the freshness check, so a stale timestamp is refused as
    stale against the policy TTL rather than as a field mismatch.
    """

    if not isinstance(selected_route, RouteDefinition):
        return ""
    if selected_route.evidence.readiness_ttl_seconds != bound.evidence.readiness_ttl_seconds:
        return "caller-supplied route is not the policy route: readiness_ttl_seconds"
    return ""


def validate_result_provenance(
    selected_route: str | RouteDefinition,
    result: DispatchResult,
    policy: ModelPolicy,
    *,
    task_epoch: str,
    now: datetime,
) -> ProvenanceDecision:
    """Reject a result that is not bound to the policy route, task epoch, and freshness bound."""

    bound, binding_reason = _policy_bound_route(policy, selected_route)
    if bound is None:
        return ProvenanceDecision(False, binding_reason)
    mismatches: list[str] = []
    if result.actual_route != bound.name or result.selected_route_name != bound.name:
        mismatches.append("actual route")
    if result.actual_provider != bound.provider or result.provider != bound.provider:
        mismatches.append("actual provider")
    if result.actual_model != bound.model or result.model != bound.model:
        mismatches.append("actual model")
    if mismatches:
        return ProvenanceDecision(
            False,
            "result provenance mismatch: " + ", ".join(mismatches),
        )
    if not isinstance(task_epoch, str) or not task_epoch.strip() or result.task_epoch != task_epoch:
        return ProvenanceDecision(False, "result task epoch does not match the caller task epoch")
    time_reason = _evidence_time_reason(
        result.evidence_timestamp,
        bound.evidence.readiness_ttl_seconds,
        now,
    )
    if time_reason:
        return ProvenanceDecision(False, time_reason)
    ttl_reason = _caller_ttl_disagrees(selected_route, bound)
    if ttl_reason:
        return ProvenanceDecision(False, ttl_reason)
    return ProvenanceDecision(True, "result provenance matches the selected route, provider, and model")


def plan_fallback_sequence(
    policy: ModelPolicy,
    origin_route: str,
    *,
    failure_category: str | None,
    evidence_by_route: Mapping[str, ReadinessEvidence] | None = None,
    task_epoch: str,
    now: datetime,
    partial_output: bool = False,
    side_effects_may_have_occurred: bool = False,
    attempt_count: int = 0,
    caller_risk_tier: str | None = None,
    attempted_routes: Collection[str] | None = None,
    workload_class: str | None = None,
) -> FallbackPlan:
    """Plan at most three unique declared fallbacks that can cover the origin.

    A supplied workload_class must already be one of the origin route's
    workload classes. It cannot authorize a different class.
    """

    if isinstance(attempt_count, bool) or not isinstance(attempt_count, int) or attempt_count < 0:
        return FallbackPlan(False, (), "duplicate retry refused: attempt_count is invalid")
    if isinstance(attempted_routes, str):
        # A bare str is a Collection[str], so iterating it yields one character
        # per route name. The duplicate-retry exclusion would never fire and an
        # already-attempted route could be planned again. Refuse the shape.
        return FallbackPlan(
            False,
            (),
            "attempted_routes must be a collection of route names, not a string",
        )
    if attempted_routes is not None:
        # Element-type guard, at the same position as the str guard. bytes,
        # bytearray, and memoryview iterate as ints, and a list of bytes is a
        # collection of non-str elements. A str subclass passes isinstance, and
        # str(item) then invokes an overridden __str__, which may not be the
        # route name. Either way the duplicate-retry exclusion would not fire
        # and an already-attempted route could be planned again. Refuse unless
        # every element is exactly type str, so every surviving element
        # satisfies str(item) == item. Materialize once so a generator of names
        # is still excluded by name below, and so this check stays ahead of the
        # partial-output and side-effect gates.
        try:
            attempted_names = tuple(attempted_routes)
        except TypeError:
            attempted_names = None
        if attempted_names is None or not all(type(item) is str for item in attempted_names):
            return FallbackPlan(
                False,
                (),
                "attempted_routes has an invalid shape: every element must be a route-name string",
            )
        attempted_routes = attempted_names
    if partial_output is not False or failure_category == "partial_output":
        return FallbackPlan(False, (), "partial output before failure; fallback refused")
    if side_effects_may_have_occurred is not False:
        return FallbackPlan(False, (), "side effects may already have occurred; fallback refused")
    classified = categorize_failure(failure_category)
    if not classified.known:
        return FallbackPlan(False, (), "unknown failure refuses fallback")
    if caller_risk_tier is not None and caller_risk_tier not in RISK_RANK:
        return FallbackPlan(False, (), f"risk tier '{caller_risk_tier}' is not valid")
    origin = policy.routes.get(origin_route)
    if origin is None:
        return FallbackPlan(False, (), f"malformed route: origin '{origin_route}' is not defined")
    if workload_class is not None and workload_class not in WORKLOAD_CLASSES:
        return FallbackPlan(False, (), f"workload class '{workload_class}' is unknown")
    if workload_class is not None and workload_class not in origin.workload_classes:
        return FallbackPlan(
            False,
            (),
            f"workload class '{workload_class}' is not a workload of origin route '{origin.name}'",
        )
    if not origin.fallback_allowed or not origin.fallback_routes:
        return FallbackPlan(False, (), f"route '{origin.name}' does not permit fallback")
    evidence_by_route = evidence_by_route or {}
    required_workloads = (workload_class,) if workload_class else origin.workload_classes
    origin_rank = RISK_RANK[origin.risk_tier_max]
    caller_rank = None if caller_risk_tier is None else RISK_RANK[caller_risk_tier]
    attempted = {origin.name}
    if attempted_routes:
        attempted.update(str(item) for item in attempted_routes)
    planned: list[str] = []
    exclusions: list[str] = []
    seen: set[str] = set()
    for name in origin.fallback_routes:
        if len(planned) >= MAX_FALLBACKS:
            break
        if name in seen:
            exclusions.append(f"{name} excluded: duplicate fallback name")
            continue
        seen.add(name)
        if name in attempted or name not in policy.routes:
            if name == origin_route or name in attempted:
                exclusions.append(f"{name} excluded: duplicate retry")
            else:
                exclusions.append(f"{name} excluded: not defined")
            continue
        candidate = policy.routes[name]
        if not all(item in candidate.workload_classes for item in required_workloads):
            exclusions.append(f"{name} excluded: does not serve origin workload")
            continue
        candidate_rank = RISK_RANK[candidate.risk_tier_max]
        if candidate_rank < origin_rank or (caller_rank is not None and candidate_rank < caller_rank):
            exclusions.append(
                f"{name} excluded: risk tier maximum cannot cover the origin or caller risk"
            )
            continue
        if candidate.status != "approved":
            exclusions.append(f"{name} excluded: not approved")
            continue
        if frozenset(candidate.data_classes) != frozenset(origin.data_classes):
            exclusions.append(f"{name} excluded: data_policy_mismatch")
            continue
        if frozenset(candidate.tool_capabilities) != frozenset(origin.tool_capabilities):
            exclusions.append(f"{name} excluded: tool_capability_mismatch")
            continue
        evidence = evidence_by_route.get(name)
        admission = admit_route(policy, candidate, evidence, task_epoch, now)
        if not admission.allowed:
            exclusions.append(f"{name} excluded: {admission.reason}")
            continue
        planned.append(name)
    chosen = tuple(planned)
    duplicate_note = (
        f"; duplicate retry of '{origin_route}' is not included"
        if attempt_count >= 1
        else ""
    )
    if not chosen:
        reason = "; ".join(exclusions) or "no declared fallback was eligible"
        return FallbackPlan(False, (), reason + duplicate_note)
    return FallbackPlan(
        True,
        chosen,
        f"planned {len(chosen)} declared fallback route(s){duplicate_note}",
    )


def authorize_retry(
    *,
    proposed_route: str,
    attempt_count: int,
    partial_output: bool = False,
    side_effects_may_have_occurred: bool = False,
    failure_category: str | None = None,
) -> RetryDecision:
    """Refuse retry after partial output, possible side effects, or a prior attempt."""

    if isinstance(attempt_count, bool) or not isinstance(attempt_count, int) or attempt_count < 0:
        return RetryDecision(False, "duplicate retry refused: attempt_count is invalid")
    if partial_output is not False or failure_category == "partial_output":
        return RetryDecision(False, f"partial output before failure; retry of '{proposed_route}' refused")
    if side_effects_may_have_occurred is not False:
        return RetryDecision(False, f"side effects may already have occurred; retry of '{proposed_route}' refused")
    if attempt_count >= 1:
        return RetryDecision(False, f"duplicate retry of '{proposed_route}' refused")
    if failure_category is not None and not categorize_failure(failure_category).known:
        return RetryDecision(False, "unknown failure refuses fallback")
    return RetryDecision(True, "initial attempt authorized; no retry has been recorded")


def categorize_failure(category: str | None) -> FailureClassification:
    """Label a known category. Unknown strings, including exception text, refuse fallback."""

    if isinstance(category, str) and category in FAILURE_CATEGORIES:
        return FailureClassification(
            category=category,
            known=True,
            fallback_authorized=False,
            reason=f"failure '{category}' is categorized and does not authorize fallback",
        )
    return FailureClassification(
        category=None,
        known=False,
        fallback_authorized=False,
        reason="unknown failure refuses fallback",
    )


def reconcile_synchronous_result(
    selected_route: RouteDefinition,
    result: DispatchResult,
    *,
    policy: ModelPolicy,
    task_epoch: str,
    now: datetime,
    execution_mode: str = "synchronous",
) -> ReconciliationDecision:
    """Accept one synchronous success only when the policy route, epoch, time, and selectability bind."""

    if execution_mode != "synchronous":
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason="background execution is unsupported and not activated",
            execution_mode=execution_mode,
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    if not isinstance(selected_route, RouteDefinition):
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason="malformed route: selected route is not defined",
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    # Re-bind before trusting any field. A fabricated object that shadows a
    # shipped name is not authoritative for provider, model, status, or TTL.
    bound, binding_reason = _policy_bound_route(policy, selected_route)
    if bound is None:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason=binding_reason,
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    provenance = validate_result_provenance(
        selected_route,
        result,
        policy,
        task_epoch=task_epoch,
        now=now,
    )
    if not provenance.allowed:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason=provenance.reason,
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    # Own epoch check, kept even though provenance applies the same comparison.
    if not isinstance(task_epoch, str) or not task_epoch.strip() or result.task_epoch != task_epoch:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason="result task epoch does not match the caller task epoch",
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    # Own freshness check. The TTL is the policy route's, not the caller's.
    time_reason = _evidence_time_reason(
        result.evidence_timestamp,
        bound.evidence.readiness_ttl_seconds,
        now,
    )
    if time_reason:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason=time_reason,
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    selectable, selectable_reason = _policy_route_selectable(bound)
    if not selectable:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason=selectable_reason,
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    ttl_reason = _caller_ttl_disagrees(selected_route, bound)
    if ttl_reason:
        return ReconciliationDecision(
            allowed=False,
            reconciled=False,
            reason=ttl_reason,
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    if (
        result.partial_output is not False
        or result.side_effects_may_have_occurred is not False
        or result.failure_category is not None
        or result.reachable is not True
    ):
        return ReconciliationDecision(
            allowed=False,
            reconciled=True,
            reason="synchronous result reconciled as a failure and is not accepted",
            execution_mode="synchronous",
            background_supported=BACKGROUND_EXECUTION_SUPPORTED,
        )
    return ReconciliationDecision(
        allowed=True,
        reconciled=True,
        reason="synchronous result reconciled",
        execution_mode="synchronous",
        background_supported=BACKGROUND_EXECUTION_SUPPORTED,
    )


def _parse_routes(raw: Any) -> dict[str, RouteDefinition]:
    if not isinstance(raw, dict) or not raw:
        raise ModelPolicyError("missing required field 'routes'")
    names = set(raw)
    routes: dict[str, RouteDefinition] = {}
    for name, body in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ModelPolicyError("missing required field 'route name'")
        if not isinstance(body, dict):
            raise ModelPolicyError(f"route '{name}' must be a mapping")
        routes[name] = _parse_route(name, body, names)
    return routes


def _parse_route(name: str, body: Mapping[str, Any], names: set[str]) -> RouteDefinition:
    _reject_unknown(body, _ROUTE_FIELDS, f"route '{name}'")
    for field in _REQUIRED_ROUTE_FIELDS:
        if field not in body:
            raise ModelPolicyError(f"missing required field '{field}'")
    provider = _non_empty_str(body["provider"], "provider")
    model = _non_empty_str(body["model"], "model")
    provider_family = _non_empty_str(body["provider_family"], "provider_family")
    workload_classes = _string_tuple(body["workload_classes"], "workload_classes")
    if not workload_classes:
        raise ModelPolicyError(f"workload class list on route '{name}' must be non-empty")
    for workload_class in workload_classes:
        if workload_class not in WORKLOAD_CLASSES:
            raise ModelPolicyError(f"workload class '{workload_class}' is unknown")
    risk_tier_max = body["risk_tier_max"]
    if risk_tier_max not in RISK_RANK:
        raise ModelPolicyError(f"risk tier '{risk_tier_max}' is not one of {', '.join(RISK_TIERS)}")
    data_classes = _string_tuple(body["data_classes"], "data_classes")
    if not data_classes:
        raise ModelPolicyError(f"data class list on route '{name}' must be non-empty")
    for data_class in data_classes:
        if data_class not in DATA_CLASSES:
            raise ModelPolicyError(f"data class '{data_class}' is outside the allowed set")
    if not isinstance(body["fallback_allowed"], bool):
        raise ModelPolicyError(f"route '{name}' fallback_allowed must be a boolean")
    fallback_allowed = body["fallback_allowed"]
    fallback_routes = _string_tuple(body["fallback_routes"], "fallback_routes")
    if fallback_allowed is False and fallback_routes:
        raise ModelPolicyError(
            f"route '{name}' has fallback_allowed false but fallback_routes is non-empty"
        )
    for fallback_name in fallback_routes:
        if fallback_name not in names:
            raise ModelPolicyError(f"fallback route '{fallback_name}' is not defined")
    credential_scope = body["credential_scope"]
    if not _credential_scope_is_category(credential_scope):
        raise ModelPolicyError(
            f"credential scope on route '{name}' looks like a secret rather than a category"
        )
    evidence = _parse_evidence(body["evidence"], name)
    status = body["status"]
    if status not in ROUTE_STATUSES:
        raise ModelPolicyError(f"route '{name}' status '{status}' is not approved, proposed, or disabled")
    tool_capabilities = _string_tuple(body.get("tool_capabilities", []), "tool_capabilities")
    _reject_inconsistent_route_state(name, status, evidence)
    return RouteDefinition(
        name=name,
        provider=provider,
        model=model,
        provider_family=provider_family,
        workload_classes=workload_classes,
        risk_tier_max=risk_tier_max,
        data_classes=data_classes,
        fallback_routes=fallback_routes,
        fallback_allowed=fallback_allowed,
        credential_scope=credential_scope,
        evidence=evidence,
        status=status,
        tool_capabilities=tool_capabilities,
    )


def _parse_evidence(raw: Any, route_name: str) -> RouteEvidence:
    if not isinstance(raw, dict):
        raise ModelPolicyError(f"missing required field 'evidence' on route '{route_name}'")
    _reject_unknown(raw, _EVIDENCE_FIELDS, f"evidence on route '{route_name}'")
    for field in _EVIDENCE_FIELDS:
        if field not in raw:
            raise ModelPolicyError(f"missing required field '{field}'")
    quota = raw["quota"]
    if quota not in QUOTA_STATES:
        raise ModelPolicyError(
            f"route '{route_name}' quota '{quota}' must be known_available, known_exhausted, or unknown"
        )
    ttl = raw["readiness_ttl_seconds"]
    if isinstance(ttl, bool) or not isinstance(ttl, int):
        raise ModelPolicyError(
            f"readiness_ttl_seconds on route '{route_name}' must be a non-negative integer"
        )
    if ttl < 0:
        raise ModelPolicyError(
            f"readiness_ttl_seconds on route '{route_name}' must be a non-negative integer"
        )
    probe = raw["requires_reachability_probe"]
    if not isinstance(probe, bool):
        raise ModelPolicyError(
            f"route '{route_name}' requires_reachability_probe must be a boolean"
        )
    readiness_state = raw["readiness_state"]
    if readiness_state not in READINESS_STATES:
        raise ModelPolicyError(
            f"route '{route_name}' readiness_state '{readiness_state}' is not a permitted state"
        )
    return RouteEvidence(
        quota=quota,
        readiness_ttl_seconds=ttl,
        requires_reachability_probe=probe,
        readiness_state=readiness_state,
    )


def _parse_review_independence(
    raw: Any,
    routes: Mapping[str, RouteDefinition],
) -> tuple[Mapping[str, ReviewIndependenceRule], bool]:
    if not isinstance(raw, dict):
        raise ModelPolicyError("missing required field 'review_independence'")
    if "profile_or_session_separation_creates_diversity" not in raw:
        raise ModelPolicyError(
            "missing required field 'profile_or_session_separation_creates_diversity'"
        )
    separation_flag = raw["profile_or_session_separation_creates_diversity"]
    if separation_flag is not False:
        raise ModelPolicyError(
            "profile or session separation does not create provider-family diversity"
        )
    if "implementation" not in raw:
        raise ModelPolicyError("missing required field 'implementation'")
    rules: dict[str, ReviewIndependenceRule] = {}
    for key, value in raw.items():
        if key == "profile_or_session_separation_creates_diversity":
            continue
        if key not in WORKLOAD_CLASSES:
            raise ModelPolicyError(f"workload class '{key}' is unknown")
        if not isinstance(value, dict):
            raise ModelPolicyError(f"missing required field '{key}'")
        rules[key] = _parse_rule(key, value, routes)
    return MappingProxyType(rules), False


def _parse_rule(
    workload_class: str,
    raw: Mapping[str, Any],
    routes: Mapping[str, RouteDefinition],
) -> ReviewIndependenceRule:
    _reject_unknown(raw, _RULE_FIELDS, f"review independence '{workload_class}'")
    for field in _RULE_FIELDS:
        if field not in raw:
            raise ModelPolicyError(f"missing required field '{field}'")
    must_differ = raw["reviewer_family_must_differ_from_implementer"]
    if must_differ is not True:
        raise ModelPolicyError(
            "reviewer provider family must differ from the implementer family"
        )
    declared = raw["current_approved_pair_exists"]
    if not isinstance(declared, bool):
        raise ModelPolicyError("current_approved_pair_exists must be a boolean")
    actual = _qualifying_pair_exists(routes, workload_class)
    if declared != actual:
        raise ModelPolicyError(
            "declared current_approved_pair_exists does not match qualifying independent pair state"
        )
    statement = raw["statement"]
    if not isinstance(statement, str) or not statement.strip():
        raise ModelPolicyError("missing required field 'statement'")
    return ReviewIndependenceRule(
        workload_class=workload_class,
        reviewer_family_must_differ_from_implementer=True,
        current_approved_pair_exists=declared,
        statement=statement,
    )


def _qualifying_pair_exists(routes: Mapping[str, RouteDefinition], workload_class: str) -> bool:
    if workload_class != "implementation":
        return False
    for implementer in routes.values():
        for reviewer in routes.values():
            if _implementation_acceptance_refusal(implementer, reviewer) is None:
                return True
    return False


def _implementation_acceptance_refusal(
    implementer: RouteDefinition,
    reviewer: RouteDefinition,
) -> str | None:
    """Return a refusal reason, or None when the pair can accept implementation."""

    if implementer.name == reviewer.name or implementer.provider_family == reviewer.provider_family:
        return "reviewer provider family must differ from implementer provider family"
    if "implementation" not in implementer.workload_classes:
        return "implementer route must serve implementation"
    if "review" not in reviewer.workload_classes:
        return "reviewer route must serve review; adversarial_review alone is not acceptance review"
    if implementer.status != "approved" or reviewer.status != "approved":
        return (
            "route is not approved: "
            f"implementer status '{implementer.status}', reviewer status '{reviewer.status}'"
        )
    implementer_ok, implementer_reason = _policy_route_selectable(implementer)
    reviewer_ok, reviewer_reason = _policy_route_selectable(reviewer)
    if not implementer_ok or not reviewer_ok:
        details = "; ".join(reason for reason in (implementer_reason, reviewer_reason) if reason)
        return f"route is not selectable: {details}"
    return None


def _policy_route_selectable(route: RouteDefinition) -> tuple[bool, str]:
    reasons: list[str] = []
    if route.status != "approved":
        reasons.append(f"status '{route.status}' is not approved")
        if route.status == "disabled":
            reasons.append("disabled")
    if route.evidence.quota == "known_exhausted":
        reasons.append("quota known_exhausted")
    if route.evidence.readiness_state != "reachable":
        reasons.append(f"readiness_state {route.evidence.readiness_state}")
    if reasons:
        return False, f"route '{route.name}' is not selectable: " + ", ".join(reasons)
    return True, ""


def _reject_fallback_cycles(routes: Mapping[str, RouteDefinition]) -> None:
    graph = {name: route.fallback_routes for name, route in routes.items()}
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, stack: list[str]) -> str | None:
        if node in visiting:
            start = stack.index(node)
            return " -> ".join([*stack[start:], node])
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for nxt in graph.get(node, ()):
            found = walk(nxt, stack)
            if found:
                return found
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for name in graph:
        found = walk(name, [])
        if found:
            raise ModelPolicyError(f"fallback cycle: {found}")


def _reject_inconsistent_route_state(name: str, status: str, evidence: RouteEvidence) -> None:
    quota = evidence.quota
    readiness = evidence.readiness_state
    if status == "approved" and (
        readiness != "reachable" or quota not in {"unknown", "known_available"}
    ):
        raise ModelPolicyError(
            f"inconsistent route state on route '{name}': approved requires "
            "readiness_state reachable and quota unknown or known_available"
        )
    if status in {"disabled", "proposed"} and readiness == "reachable":
        raise ModelPolicyError(
            f"inconsistent route state on route '{name}': {status} must not be "
            "readiness_state reachable"
        )
    if quota == "known_exhausted" and readiness == "reachable":
        raise ModelPolicyError(
            f"inconsistent route state on route '{name}': known_exhausted must not "
            "be paired with readiness_state reachable"
        )
    if quota == "known_available" and readiness in {"quota_exhausted", "missing_auth", "disabled"}:
        raise ModelPolicyError(
            f"inconsistent route state on route '{name}': known_available must not "
            f"be paired with readiness_state {readiness}"
        )


def _credential_scope_is_category(value: Any) -> bool:
    if not isinstance(value, str) or not _CATEGORY_RE.fullmatch(value):
        return False
    if len(value) > 64 or any(len(part) > 24 for part in value.split("-")):
        return False
    parts = value.split("-")
    for part in parts:
        if len(part) > _MAX_SINGLE_SEGMENT_CATEGORY_LENGTH or any(ch.isdigit() for ch in part):
            return False
        # A secret prefix is refused when it begins the segment, or follows a
        # non-letter inside it. The delimiter may be dropped ('scope-sklive')
        # and the prefix may sit in a later segment ('oauth-sk-live',
        # 'my-sklive'). An ordinary word that merely contains those letters
        # ('risk', 'task', 'mask', 'ask') is not a secret-prefix form.
        if _SECRET_SCOPE_PREFIX_RE.search(part):
            return False
    if _SECRET_SCOPE_RE.search(value):
        return False
    return True


def _generated_at(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelPolicyError("generated_at must be an ISO-8601 UTC timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ModelPolicyError("generated_at must be an ISO-8601 UTC timestamp") from exc
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None or offset.total_seconds() != 0:
        raise ModelPolicyError("generated_at must be an ISO-8601 UTC timestamp")
    return value


def _non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelPolicyError(f"missing required field '{field}'")
    return value


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ModelPolicyError(f"missing required field '{field}'")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ModelPolicyError(f"missing required field '{field}'")
        items.append(item)
    return tuple(items)


def _reject_unknown(raw: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = set(raw) - allowed
    if unknown:
        name = sorted(unknown)[0]
        raise ModelPolicyError(f"unknown field '{name}' on {label}")


def _resolve_route(policy: ModelPolicy, route: str | RouteDefinition) -> RouteDefinition | None:
    if isinstance(route, RouteDefinition):
        return policy.routes.get(route.name, route if route.name in policy.routes else None)
    if isinstance(route, str):
        return policy.routes.get(route)
    return None


def _route_name(route: str | RouteDefinition) -> str:
    if isinstance(route, RouteDefinition):
        return route.name
    return str(route)


def _choose(policy: ModelPolicy, eligible: list[RouteDefinition]) -> RouteDefinition:
    lowest = min(RISK_RANK[route.risk_tier_max] for route in eligible)
    least = [route for route in eligible if RISK_RANK[route.risk_tier_max] == lowest]
    by_name = {route.name: route for route in least}
    if policy.default_route in by_name:
        return by_name[policy.default_route]
    return sorted(least, key=lambda route: route.name)[0]


def _as_utc(value: datetime | str) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
