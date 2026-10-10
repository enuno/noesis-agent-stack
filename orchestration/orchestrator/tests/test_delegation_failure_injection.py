"""Failure-injection and integrity tests for the durable delegation store.

These exercise the real DelegationStore and transition logic (no mocks for the
store), injecting duplicate, stale, out-of-order, and unauthorized events to
prove the acceptance criteria: required transitions cannot be bypassed,
duplicate/stale events cannot corrupt authoritative state, reviews bind to the
current candidate, completion requires explicit orchestrator acceptance, and
recovery does not blindly relaunch uncertain execution.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.delegation import (
    ActivationError,
    DelegationStore,
    HandoffEnvelope,
    MessageType,
    TaskState,
)


def _store(tmp_path: Path) -> DelegationStore:
    return DelegationStore(tmp_path / "delegated-tasks.jsonl")


def _task_id() -> str:
    return str(uuid4())


def _assign(*, task_id: str, sender: str = "noesis-orchestrator", epoch: int = 1,
            idem: str | None = None, protocol: str = "noesis.delegated-task/v1") -> HandoffEnvelope:
    return HandoffEnvelope(
        protocol_version=protocol,
        message_id=str(uuid4()),
        message_type=MessageType.ASSIGN,
        sender_id=sender,
        recipient_id="noesis-forge",
        root_task_id=task_id,
        task_id=task_id,
        attempt_id=f"{task_id}/a1",
        contract_revision="c-rev-1",
        assignment_epoch=epoch,
        correlation_id=task_id,
        idempotency_key=idem or f"idem-{task_id}",
        expected_task_version=0,
        payload={
            "intent": "implement the patch",
            "acceptance_criteria": ["tests pass"],
            "required_capability": "implement",
        },
    )


def _to_verifying(store: DelegationStore, task_id: str, *, rev: str = "rev-1") -> None:
    store.mark_ready(task_id, by="noesis-orchestrator")
    store.start_running(task_id, by="noesis-forge")
    store.submit_verifying(task_id, by="noesis-forge", candidate_revision=rev)


def _to_quality(store: DelegationStore, task_id: str, *, rev: str = "rev-1") -> None:
    _to_verifying(store, task_id, rev=rev)
    store.record_review(task_id, stage="spec", verdict="PASS", reviewer="noesis-sentinel",
                        candidate_revision=rev, findings=[])


# ------------------------------------------------------- duplicate events --
def test_duplicate_accept_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    _to_quality(store, task_id)
    store.record_review(task_id, stage="quality", verdict="APPROVED", reviewer="noesis-sentinel",
                        candidate_revision="rev-1", findings=[])
    first = store.accept(task_id, by="noesis-orchestrator")
    second = store.accept(task_id, by="noesis-orchestrator")

    assert first.state is TaskState.completed
    assert second.state is TaskState.completed
    assert second.accepted is True
    # No version corruption from the duplicate.
    assert second.version == first.version


def test_duplicate_result_same_revision_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    store.mark_ready(task_id, by="noesis-orchestrator")
    store.start_running(task_id, by="noesis-forge")
    first = store.submit_verifying(task_id, by="noesis-forge", candidate_revision="rev-1")
    second = store.submit_verifying(task_id, by="noesis-forge", candidate_revision="rev-1")

    assert second.state is TaskState.verifying
    assert second.candidate_revision == "rev-1"
    assert second.version == first.version


# ------------------------------------------------- candidate-change binding --
def test_candidate_change_invalidates_prior_reviews(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    _to_quality(store, task_id, rev="rev-1")
    store.record_review(task_id, stage="quality", verdict="APPROVED", reviewer="noesis-sentinel",
                        candidate_revision="rev-1", findings=[])

    # A new candidate revision is submitted after reviews -> old reviews must be
    # invalidated so quality on rev-2 cannot reuse the rev-1 spec PASS.
    store.submit_verifying(task_id, by="noesis-forge", candidate_revision="rev-2")
    task = store.get(task_id)
    assert all(r.candidate_revision == "rev-2" for r in task.reviews)
    assert task.reviews == []

    # Quality on rev-2 must be refused until a fresh spec PASS on rev-2.
    with pytest.raises(ActivationError):
        store.record_review(task_id, stage="quality", verdict="APPROVED", reviewer="noesis-sentinel",
                            candidate_revision="rev-2", findings=[])


# ------------------------------------------------------- version conflicts --
def test_stale_expected_version_rejects_accept(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    _to_quality(store, task_id)
    store.record_review(task_id, stage="quality", verdict="APPROVED", reviewer="noesis-sentinel",
                        candidate_revision="rev-1", findings=[])
    current = store.get(task_id)

    with pytest.raises(ActivationError):
        store.accept(task_id, by="noesis-orchestrator", expected_task_version=current.version - 1)


def test_stale_expected_version_rejects_start(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    store.mark_ready(task_id, by="noesis-orchestrator")
    current = store.get(task_id)

    with pytest.raises(ActivationError):
        store.start_running(task_id, by="noesis-forge", expected_task_version=current.version - 1)


# ------------------------------------------------------------- cancellation --
def test_cancel_prevents_new_work(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    store.mark_ready(task_id, by="noesis-orchestrator")
    store.cancel(task_id, by="noesis-orchestrator", reason="superseded")

    assert store.get(task_id).state is TaskState.cancelled
    with pytest.raises(ActivationError):
        store.start_running(task_id, by="noesis-forge")
    with pytest.raises(ActivationError):
        store.accept(task_id, by="noesis-orchestrator")


def test_cancel_requires_orchestrator(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    with pytest.raises(ActivationError):
        store.cancel(task_id, by="noesis-forge", reason="rogue")


# ------------------------------------------------------- protocol / auth -----
def test_unsupported_protocol_version_fails_explicitly(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ActivationError):
        store.process(_assign(task_id=_task_id(), protocol="noesis.delegated-task/v0"))


def test_assignee_cannot_accept_own_result(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task_id = _task_id()
    store.process(_assign(task_id=task_id))
    _to_quality(store, task_id)
    store.record_review(task_id, stage="quality", verdict="APPROVED", reviewer="noesis-sentinel",
                        candidate_revision="rev-1", findings=[])
    with pytest.raises(ActivationError):
        store.accept(task_id, by="noesis-forge")


# ------------------------------------------------------- recovery / restart --
def test_restart_preserves_cancelled_state(tmp_path: Path) -> None:
    ledger = tmp_path / "delegated-tasks.jsonl"
    task_id = _task_id()
    first = DelegationStore(ledger)
    first.process(_assign(task_id=task_id))
    first.mark_ready(task_id, by="noesis-orchestrator")
    first.cancel(task_id, by="noesis-orchestrator", reason="superseded")

    second = DelegationStore(ledger)
    assert second.get(task_id).state is TaskState.cancelled
    # Replaying the same ASSIGN must not relaunch a cancelled task.
    assert second.process(_assign(task_id=task_id)) is not None
    assert second.get(task_id).state is TaskState.cancelled
