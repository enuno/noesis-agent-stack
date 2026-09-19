"""Durable append-only task store.

Persistence is an append-only JSONL event log (the repository's established
ledger convention, cf. contracts/ledgers/*.schema.json), not chat or in-memory
state. Current task state is a left fold over the log, so the control plane
survives process restarts and every transition remains auditable.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.models import (
    Approval,
    Retry,
    TaskContract,
    Verification,
    utcnow,
)

DEFAULT_LEDGER = Path("workspace/orchestrator/tasks.jsonl")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_dt(value: str | None) -> datetime:
    parsed = _parse_dt(value)
    if parsed is None:
        raise ValueError("expected a timestamp in the task ledger, found none")
    return parsed


class TaskStore:
    """Append-only JSONL task ledger with a replayed in-process index."""

    def __init__(self, ledger_path: Path | str = DEFAULT_LEDGER) -> None:
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, TaskContract] = {}
        self._by_idempotency: dict[str, str] = {}
        if self.ledger_path.exists():
            self.replay()

    # ------------------------------------------------------------ persistence

    def _append(self, event: str, task: TaskContract) -> None:
        record = {"event": event, "recorded_at": utcnow().isoformat(), "task": task.to_dict()}
        line = json.dumps(record, sort_keys=True, default=str)
        # Append durably: write then fsync so a crash cannot lose an accepted
        # transition that the caller has already been told about.
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def replay(self) -> None:
        """Rebuild current state by folding the append-only log."""
        self._tasks.clear()
        self._by_idempotency.clear()
        with self.ledger_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                task = self._rehydrate(record["task"])
                self._tasks[str(task.task_id)] = task
                self._by_idempotency[task.idempotency_key] = str(task.task_id)

    @staticmethod
    def _rehydrate(data: dict[str, Any]) -> TaskContract:
        approval_raw = data.get("approval") or {}
        claim_raw = data.get("claim")
        task = TaskContract(
            title=data["title"],
            intent=data["intent"],
            assignee_profile=data["assignee_profile"],
            required_capability=data["required_capability"],
            risk_tier=data["risk_tier"],
            idempotency_key=data["idempotency_key"],
            acceptance_criteria=list(data["acceptance_criteria"]),
            verification=Verification(**data["verification"]),
            timeout_s=data["timeout_s"],
            correlation_id=UUID(data["correlation_id"]),
            retry=Retry(**data["retry"]),
            approval=Approval(
                required=approval_raw.get("required", False),
                state=approval_raw.get("state", "not_required"),
                approved_by=approval_raw.get("approved_by"),
                approved_at=_parse_dt(approval_raw.get("approved_at")),
                approval_manifest_id=approval_raw.get("approval_manifest_id"),
            ),
            reviewer_profile=data.get("reviewer_profile"),
            depends_on=[UUID(d) for d in data.get("depends_on", [])],
            irreversible_operations=list(data.get("irreversible_operations", [])),
            labels=list(data.get("labels", [])),
            parent_task_id=UUID(data["parent_task_id"]) if data.get("parent_task_id") else None,
            traceparent=data.get("traceparent"),
            task_id=UUID(data["task_id"]),
        )
        task.state = data["state"]
        task.handoff = data.get("handoff")
        task.created_at = _require_dt(data["created_at"])
        task.created_by = data["created_by"]
        task.updated_at = _parse_dt(data.get("updated_at"))
        task.terminal_reason = data.get("terminal_reason")
        if claim_raw:
            task.claim = {
                "claimed_by": claim_raw["claimed_by"],
                "claimed_at": _parse_dt(claim_raw["claimed_at"]),
                "lease_expires_at": _parse_dt(claim_raw["lease_expires_at"]),
            }
        return task

    # ----------------------------------------------------------------- access

    def put(self, task: TaskContract, event: str = "task_updated") -> TaskContract:
        self._tasks[str(task.task_id)] = task
        self._by_idempotency[task.idempotency_key] = str(task.task_id)
        self._append(event, task)
        return task

    def get(self, task_id: str | UUID) -> TaskContract | None:
        return self._tasks.get(str(task_id))

    def find_by_idempotency_key(self, key: str) -> TaskContract | None:
        task_id = self._by_idempotency.get(key)
        return self._tasks.get(task_id) if task_id else None

    def all_tasks(self) -> dict[str, TaskContract]:
        return dict(self._tasks)

    def list_by_state(self, state: str) -> list[TaskContract]:
        return [t for t in self._tasks.values() if t.state == state]

    def list_by_correlation(self, correlation_id: str | UUID) -> list[TaskContract]:
        return [
            t for t in self._tasks.values() if str(t.correlation_id) == str(correlation_id)
        ]
