"""The noesis-orchestrator control plane.

This module is the only component permitted to mutate task state. It plans
(create), dispatches (claim), supervises (sweep, retry, break), and synthesizes
(synthesize) — it never performs the assigned work itself and holds no
execution toolset.

Emergency stop: `engage_circuit_breaker()` halts all dispatch immediately;
already-running work is left to its lease and swept normally.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app import policy
from app.models import Approval, Retry, TaskContract, TransitionError, Verification, utcnow
from app.policy import DispatchDecision, PolicyViolation
from app.store import DEFAULT_LEDGER, TaskStore

# Consecutive failures within one correlation graph before dispatch is halted.
DEFAULT_FAILURE_THRESHOLD = 3


@dataclass
class CircuitBreaker:
    """Halts dispatch after repeated failures, or on operator command."""

    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    consecutive_failures: int = 0
    manually_tripped: bool = False
    reason: str | None = None

    @property
    def is_open(self) -> bool:
        """Open means: no further dispatch."""
        return self.manually_tripped or self.consecutive_failures >= self.failure_threshold

    def record_failure(self, reason: str) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.reason = f"failure threshold reached: {reason}"

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if not self.manually_tripped:
            self.reason = None

    def trip(self, reason: str) -> None:
        self.manually_tripped = True
        self.reason = reason

    def reset(self, *, operator: str) -> None:
        self.manually_tripped = False
        self.consecutive_failures = 0
        self.reason = f"reset by {operator}"


class Orchestrator:
    """Least-privilege planner / dispatcher / supervisor / synthesizer."""

    profile_name = "noesis-orchestrator"

    def __init__(
        self,
        ledger_path: Path | str = DEFAULT_LEDGER,
        *,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
    ) -> None:
        self.store = TaskStore(ledger_path)
        self.breaker = CircuitBreaker(failure_threshold=failure_threshold)

    # ------------------------------------------------------------------ plan --

    def propose(
        self,
        *,
        title: str,
        intent: str,
        assignee_profile: str,
        required_capability: str,
        acceptance_criteria: list[str],
        verification: Verification,
        idempotency_key: str,
        correlation_id: UUID | None = None,
        risk_tier: str = "r0",
        timeout_s: int = 900,
        max_attempts: int = 1,
        depends_on: list[UUID] | None = None,
        irreversible_operations: list[str] | None = None,
        reviewer_profile: str | None = None,
        approval_required: bool | None = None,
        labels: list[str] | None = None,
        parent_task_id: UUID | None = None,
    ) -> TaskContract:
        """Create a durable task contract, or return the existing one.

        Idempotent: re-delivery of a known idempotency_key never duplicates work.
        """
        existing = self.store.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        irreversible = irreversible_operations or []
        if approval_required is None:
            approval_required = bool(irreversible) or risk_tier in policy.APPROVAL_REQUIRED_TIERS

        task = TaskContract(
            title=title,
            intent=intent,
            assignee_profile=assignee_profile,
            required_capability=required_capability,
            risk_tier=risk_tier,
            idempotency_key=idempotency_key,
            acceptance_criteria=list(acceptance_criteria),
            verification=verification,
            timeout_s=timeout_s,
            correlation_id=correlation_id or uuid4(),
            retry=Retry(max_attempts=max_attempts),
            approval=Approval(
                required=approval_required,
                state="pending" if approval_required else "not_required",
            ),
            reviewer_profile=reviewer_profile,
            depends_on=list(depends_on or []),
            irreversible_operations=irreversible,
            labels=list(labels or []),
            parent_task_id=parent_task_id,
        )

        # Admission policy runs before anything is persisted.
        policy.validate_admission(task)
        return self.store.put(task, event="task_proposed")

    # -------------------------------------------------------------- approval --

    def approve(
        self,
        task_id: str | UUID,
        *,
        operator: str,
        approval_manifest_id: str | None = None,
    ) -> TaskContract:
        """Record a human approval. Agents may never call this on their own behalf."""
        task = self._require(task_id)
        if task.approval and task.approval.required:
            task.approval.state = "granted"
            task.approval.approved_by = operator
            task.approval.approved_at = utcnow()
            task.approval.approval_manifest_id = approval_manifest_id
        decision = policy.check_approval(task)
        if not decision.allowed:
            raise PolicyViolation("approval_invalid", decision.reason)
        task.transition_to("approved")
        return self.store.put(task, event="task_approved")

    def deny(self, task_id: str | UUID, *, operator: str, reason: str) -> TaskContract:
        task = self._require(task_id)
        if task.approval:
            task.approval.state = "denied"
            task.approval.approved_by = operator
            task.approval.approved_at = utcnow()
        task.transition_to("cancelled", reason=f"approval denied by {operator}: {reason}")
        return self.store.put(task, event="task_denied")

    def enqueue(self, task_id: str | UUID) -> TaskContract:
        """Move an approved (or approval-exempt) task into the dispatch queue."""
        task = self._require(task_id)
        if task.state == "proposed":
            decision = policy.check_approval(task)
            if not decision.allowed:
                raise PolicyViolation("approval_gate_required", decision.reason)
            task.transition_to("approved")
        task.transition_to("queued")
        return self.store.put(task, event="task_queued")

    # ------------------------------------------------------------- dispatch --

    def dispatchable(self, task_id: str | UUID) -> DispatchDecision:
        task = self._require(task_id)
        if self.breaker.is_open:
            return DispatchDecision(False, f"circuit breaker open: {self.breaker.reason}")
        if task.state != "queued":
            return DispatchDecision(False, f"task is '{task.state}', not 'queued'")
        return policy.check_dispatchable(task, self.store.all_tasks())

    def check_gate_blocked(self, task_id: str | UUID) -> bool:
        """True when a task is held by an unsatisfied human approval gate.

        Inspection helper for operators and dashboards; performs no mutation.
        """
        task = self._require(task_id)
        return not policy.check_approval(task).allowed

    def claim(self, task_id: str | UUID, *, claimed_by: str) -> TaskContract:
        """Hand the task to its assignee. Rejects any claim by a different profile."""
        task = self._require(task_id)
        decision = self.dispatchable(task_id)
        if not decision.allowed:
            raise PolicyViolation("dispatch_blocked", decision.reason)
        if claimed_by != task.assignee_profile:
            raise PolicyViolation(
                "claim_by_wrong_profile",
                f"task is assigned to '{task.assignee_profile}', not '{claimed_by}'",
            )
        task.transition_to("claimed")
        task.apply_claim(claimed_by)
        return self.store.put(task, event="task_claimed")

    def start(self, task_id: str | UUID) -> TaskContract:
        task = self._require(task_id)
        task.transition_to("running")
        task.retry.attempts += 1
        return self.store.put(task, event="task_started")

    # ------------------------------------------------------------- outcomes --

    def submit_handoff(self, task_id: str | UUID, handoff: dict[str, Any]) -> TaskContract:
        """Assignee reports structured evidence. This does not itself succeed the task."""
        task = self._require(task_id)
        task.handoff = handoff
        next_state = "awaiting_review" if task.reviewer_profile else "running"
        if task.state != next_state:
            task.transition_to(next_state)
        return self.store.put(task, event="task_handoff_submitted")

    def succeed(self, task_id: str | UUID, *, now: datetime | None = None) -> TaskContract:
        """Complete a task only when evidence, review, and lease all hold."""
        task = self._require(task_id)
        policy.validate_handoff(task, now=now)
        task.transition_to("succeeded")
        self.breaker.record_success()
        return self.store.put(task, event="task_succeeded")

    def fail(self, task_id: str | UUID, *, reason: str) -> TaskContract:
        task = self._require(task_id)
        task.transition_to("failed", reason=reason)
        self.breaker.record_failure(reason)
        return self.store.put(task, event="task_failed")

    def block(self, task_id: str | UUID, *, reason: str) -> TaskContract:
        task = self._require(task_id)
        task.transition_to("blocked", reason=reason)
        return self.store.put(task, event="task_blocked")

    def cancel(self, task_id: str | UUID, *, reason: str) -> TaskContract:
        task = self._require(task_id)
        task.transition_to("cancelled", reason=reason)
        return self.store.put(task, event="task_cancelled")

    def retry(self, task_id: str | UUID) -> TaskContract:
        """Re-queue a failed task when its bounded retry budget allows."""
        task = self._require(task_id)
        if task.retry.exhausted:
            raise PolicyViolation(
                "retry_budget_exhausted",
                f"task exhausted {task.retry.max_attempts} attempt(s)",
            )
        task.transition_to("queued")
        return self.store.put(task, event="task_requeued")

    # ------------------------------------------------------------ supervise --

    def sweep_timeouts(self, *, now: datetime | None = None) -> list[TaskContract]:
        """Fail or re-queue every task that outlived its lease. Stale work never succeeds."""
        now = now or utcnow()
        swept: list[TaskContract] = []
        for task in list(self.store.all_tasks().values()):
            if task.state not in ("claimed", "running"):
                continue
            if not task.lease_expired(now=now):
                continue
            self.fail(task.task_id, reason=f"timeout after {task.timeout_s}s")
            if not task.retry.exhausted and not self.breaker.is_open:
                self.retry(task.task_id)
            swept.append(task)
        return swept

    def escalate(self, task_id: str | UUID, *, reason: str) -> dict[str, Any]:
        """Produce an operator-facing escalation record. Never auto-resolves."""
        task = self._require(task_id)
        return {
            "escalation_for": str(task.task_id),
            "title": task.title,
            "assignee_profile": task.assignee_profile,
            "state": task.state,
            "risk_tier": task.risk_tier,
            "attempts": task.retry.attempts,
            "max_attempts": task.retry.max_attempts,
            "terminal_reason": task.terminal_reason,
            "reason": reason,
            "circuit_breaker_open": self.breaker.is_open,
            "requires_human": True,
        }

    def emergency_stop(self, *, operator: str, reason: str) -> CircuitBreaker:
        self.breaker.trip(f"{reason} (by {operator})")
        return self.breaker

    def resume(self, *, operator: str) -> CircuitBreaker:
        self.breaker.reset(operator=operator)
        return self.breaker

    # ------------------------------------------------------------ synthesize --

    def synthesize(self, correlation_id: str | UUID) -> dict[str, Any]:
        """Fold a task graph into one operator-facing result. Read-only."""
        tasks = self.store.list_by_correlation(correlation_id)
        by_state: dict[str, list[str]] = {}
        for task in tasks:
            by_state.setdefault(task.state, []).append(task.title)
        succeeded = [t for t in tasks if t.state == "succeeded"]
        return {
            "correlation_id": str(correlation_id),
            "task_count": len(tasks),
            "by_state": by_state,
            "complete": bool(tasks) and all(t.state == "succeeded" for t in tasks),
            "blocked": [t.title for t in tasks if t.state == "blocked"],
            "failed": [t.title for t in tasks if t.state == "failed"],
            "awaiting_approval": [
                t.title
                for t in tasks
                if t.approval and t.approval.required and t.approval.state == "pending"
            ],
            "evidence": [
                {
                    "task": t.title,
                    "assignee": t.assignee_profile,
                    "summary": (t.handoff or {}).get("summary"),
                }
                for t in succeeded
            ],
            "circuit_breaker_open": self.breaker.is_open,
        }

    # ---------------------------------------------------------------- helper --

    def _require(self, task_id: str | UUID) -> TaskContract:
        task = self.store.get(task_id)
        if task is None:
            raise PolicyViolation("unknown_task", f"no task contract with id {task_id}")
        return task


__all__ = [
    "CircuitBreaker",
    "Orchestrator",
    "PolicyViolation",
    "TransitionError",
    "Verification",
]
