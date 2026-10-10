"""Task contract model and the orchestrator state machine.

States (exactly the supervised lifecycle):

    proposed -> approved -> queued -> claimed -> running
             -> awaiting_review | blocked | failed | succeeded | cancelled

Transitions are validated here and nowhere else. Assignees report outcomes;
they never write a state directly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

SCHEMA_VERSION = "1.0"

TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"approved", "cancelled", "blocked"}),
    "approved": frozenset({"queued", "cancelled", "blocked"}),
    "queued": frozenset({"claimed", "blocked", "cancelled", "failed"}),
    "claimed": frozenset({"running", "blocked", "cancelled", "failed"}),
    "running": frozenset(
        {"awaiting_review", "succeeded", "failed", "blocked", "cancelled"}
    ),
    "awaiting_review": frozenset({"succeeded", "failed", "blocked", "cancelled"}),
    "blocked": frozenset({"queued", "cancelled", "failed"}),
    "failed": frozenset({"queued", "cancelled"}),  # retry re-queues
    "succeeded": frozenset(),
    "cancelled": frozenset(),
}

RISK_TIERS = ("r0", "r1", "r2", "r3")

IRREVERSIBLE_OPERATIONS = frozenset(
    {
        "production_mutation",
        "financial_operation",
        "wallet_signing",
        "credential_rotation",
        "dns_or_firewall_change",
        "destructive_data_operation",
        "external_publication",
    }
)


class TransitionError(RuntimeError):
    """Raised when a state transition is not permitted."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


@dataclass
class Verification:
    method: str
    evidence_required: bool = True
    command: str | None = None


@dataclass
class Retry:
    max_attempts: int = 1
    attempts: int = 0
    backoff_s: int = 30

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.max_attempts


@dataclass
class Approval:
    required: bool
    state: str = "not_required"
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_manifest_id: str | None = None


# Review stages in the authoritative lifecycle. Spec compliance must pass for a
# candidate before quality review may begin; integration is plan/root-level.
REVIEW_STAGES = frozenset({"spec", "quality", "integration"})
SPEC_VERDICTS = frozenset({"PASS", "REQUEST_CHANGES", "BLOCKED"})
QUALITY_VERDICTS = frozenset({"APPROVED", "REQUEST_CHANGES", "BLOCKED"})
# Positive success only. Failure verdicts are never mapped toward PASS/APPROVED.
_POSITIVE_REVIEW_VERDICT = {
    "spec": "PASS",
    "quality": "APPROVED",
}


@dataclass
class ReviewRecord:
    """A review verdict bound to one candidate revision (never a stale diff)."""

    stage: str
    verdict: str
    reviewer: str
    candidate_revision: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    at: datetime = field(default_factory=utcnow)


@dataclass
class Delegation:
    """Authoritative delegation/assignment record lived on the task contract.

    This is the extension of the TaskStore contract with delegation behavior;
    a task that has been explicitly assigned to a specialist carries this. It
    records assignment epoch (monotonic fencing), active attempt, resolved
    runtime profile, the current candidate revision/digest, revision-bound
    reviews, and the explicit orchestrator acceptance. Budget accounting is
    minimal and honest: unknown token usage is tracked as ``None``, never as 0.
    """

    assignment_epoch: int = 0
    attempt: int = 0
    runtime_profile: str | None = None
    candidate_revision: str | None = None
    candidate_digest: str | None = None
    contract_revision: str | None = None
    baseline: str | None = None
    reviews: list[ReviewRecord] = field(default_factory=list)
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    request_limit: int | None = None
    requests_used: int = 0
    budget_tokens: int | None = None
    tokens_used: int | None = None  # None = unknown, tracked explicitly, never 0
    approved_provider: str | None = None
    approved_model: str | None = None
    launch_reservation: dict[str, Any] | None = None

    def current_reviews(self, stage: str) -> list[ReviewRecord]:
        rev = self.candidate_revision
        return [r for r in self.reviews if r.stage == stage and r.candidate_revision == rev]

    def current_verdicts(self) -> dict[str, str]:
        """Best current candidate's verdicts keyed by stage (later review wins)."""
        out: dict[str, str] = {}
        rev = self.candidate_revision
        if not rev:
            return out
        for r in self.reviews:
            if r.candidate_revision == rev:
                out[r.stage] = r.verdict
        return out

    def required_review_satisfied(self, stage: str) -> bool:
        """Satisfied only by the explicit positive verdict for that stage.

        Spec requires PASS. Quality requires APPROVED. Missing, unknown,
        malformed, wrong-stage, BLOCKED, REQUEST_CHANGES, and unsupported
        stages fail closed. A failure verdict is never coerced into success.
        """
        expected = _POSITIVE_REVIEW_VERDICT.get(stage)
        if expected is None:
            return False
        verdict = self.current_verdicts().get(stage)
        if not isinstance(verdict, str) or not verdict.strip():
            return False
        return verdict == expected

    def budget_exceeded(self) -> bool:
        if self.request_limit is not None and self.requests_used > self.request_limit:
            return True
        return False



@dataclass
class TaskContract:
    """Durable unit of supervised cross-profile work."""

    title: str
    intent: str
    assignee_profile: str
    required_capability: str
    risk_tier: str
    idempotency_key: str
    acceptance_criteria: list[str]
    verification: Verification
    timeout_s: int
    correlation_id: UUID
    retry: Retry = field(default_factory=Retry)
    approval: Approval | None = None
    reviewer_profile: str | None = None
    depends_on: list[UUID] = field(default_factory=list)
    irreversible_operations: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    parent_task_id: UUID | None = None
    traceparent: str | None = None

    task_id: UUID = field(default_factory=uuid4)
    state: str = "proposed"
    handoff: dict[str, Any] | None = None
    claim: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=utcnow)
    created_by: str = "noesis-orchestrator"
    updated_at: datetime | None = None
    terminal_reason: str | None = None
    delegation: Delegation = field(default_factory=Delegation)

    def __post_init__(self) -> None:
        if self.risk_tier not in RISK_TIERS:
            raise ValueError(f"Unknown risk tier: {self.risk_tier}")
        unknown = set(self.irreversible_operations) - IRREVERSIBLE_OPERATIONS
        if unknown:
            raise ValueError(f"Unknown irreversible operations: {sorted(unknown)}")
        if not self.acceptance_criteria:
            raise ValueError("acceptance_criteria must not be empty")
        if self.approval is None:
            self.approval = Approval(required=False, state="not_required")

    # ---------------------------------------------------------------- state --

    def can_transition_to(self, new_state: str) -> bool:
        return new_state in ALLOWED_TRANSITIONS.get(self.state, frozenset())

    def transition_to(self, new_state: str, *, reason: str | None = None) -> None:
        if new_state == self.state:
            raise TransitionError(f"Task is already in state '{new_state}'")
        if not self.can_transition_to(new_state):
            raise TransitionError(
                f"Illegal transition {self.state} -> {new_state} "
                f"(allowed: {sorted(ALLOWED_TRANSITIONS.get(self.state, []))})"
            )
        self.state = new_state
        self.updated_at = utcnow()
        if new_state in TERMINAL_STATES or new_state == "blocked":
            self.terminal_reason = reason
        # A re-queued task releases its lease so a fresh claim is required.
        if new_state == "queued":
            self.claim = None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    # ---------------------------------------------------------------- lease --

    def apply_claim(self, claimed_by: str) -> None:
        now = utcnow()
        self.claim = {
            "claimed_by": claimed_by,
            "claimed_at": now,
            "lease_expires_at": now + timedelta(seconds=self.timeout_s),
        }

    def lease_expired(self, *, now: datetime | None = None) -> bool:
        """True when a claimed/running task has outlived its timeout lease."""
        if not self.claim:
            return False
        now = now or utcnow()
        return now > self.claim["lease_expires_at"]

    # ------------------------------------------------------------ serialize --

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        data["task_id"] = str(self.task_id)
        data["correlation_id"] = str(self.correlation_id)
        data["parent_task_id"] = str(self.parent_task_id) if self.parent_task_id else None
        data["depends_on"] = [str(d) for d in self.depends_on]
        data["created_at"] = _iso(self.created_at)
        data["updated_at"] = _iso(self.updated_at)
        approval = data["approval"] or {}
        if approval:
            approval["approved_at"] = _iso(self.approval.approved_at if self.approval else None)
        if self.claim:
            data["claim"] = {
                "claimed_by": self.claim["claimed_by"],
                "claimed_at": _iso(self.claim["claimed_at"]),
                "lease_expires_at": _iso(self.claim["lease_expires_at"]),
            }
        data["delegation"] = {
            "assignment_epoch": self.delegation.assignment_epoch,
            "attempt": self.delegation.attempt,
            "runtime_profile": self.delegation.runtime_profile,
            "candidate_revision": self.delegation.candidate_revision,
            "candidate_digest": self.delegation.candidate_digest,
            "contract_revision": self.delegation.contract_revision,
            "baseline": self.delegation.baseline,
            "accepted_by": self.delegation.accepted_by,
            "accepted_at": _iso(self.delegation.accepted_at),
            "request_limit": self.delegation.request_limit,
            "requests_used": self.delegation.requests_used,
            "budget_tokens": self.delegation.budget_tokens,
            "tokens_used": self.delegation.tokens_used,
            "approved_provider": self.delegation.approved_provider,
            "approved_model": self.delegation.approved_model,
            "launch_reservation": self.delegation.launch_reservation,
            "reviews": [
                {
                    "stage": r.stage,
                    "verdict": r.verdict,
                    "reviewer": r.reviewer,
                    "candidate_revision": r.candidate_revision,
                    "findings": list(r.findings),
                    "at": _iso(r.at),
                }
                for r in self.delegation.reviews
            ],
        }
        return data
