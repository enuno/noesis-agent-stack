"""Durable credential-attempt fencing on the existing TaskStore.

No provider process is started. Stores are disposable files.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Barrier, Thread
from uuid import UUID

import pytest

from app.store import (
    ATTEMPT_FENCE_EVENT,
    SCHEMA_FENCE_EVENT,
    AttemptFenceError,
    TaskStore,
    validate_credential_attempt_identity,
)

PARENT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"


def _attempt(task_id: str = PARENT, seat_id: str = "forge", round_n: int = 1) -> str:
    return f"{task_id}|{seat_id}|round-{round_n}|attempt-1"


def _fence(store: TaskStore, **over):
    kwargs = dict(
        task_id=PARENT,
        seat_id="forge",
        round_n=1,
        attempt_id=_attempt(),
        assignment_epoch=0,
    )
    kwargs.update(over)
    return store.fence_credential_attempt(**kwargs)


def test_restart_after_fence_and_before_settle_is_not_unused(tmp_path: Path):
    path = tmp_path / "tasks.jsonl"
    first = TaskStore(path)
    _fence(first)
    rebuilt = TaskStore(path)
    assert rebuilt.credential_attempts[_attempt()] == "fenced"
    with pytest.raises(AttemptFenceError) as raised:
        _fence(rebuilt)
    assert raised.value.code == "attempt_already_fenced"


def test_uncertain_replay_is_not_reusable(tmp_path: Path):
    path = tmp_path / "tasks.jsonl"
    store = TaskStore(path)
    _fence(store)
    store.settle_credential_attempt(_attempt(), "uncertain")
    rebuilt = TaskStore(path)
    assert rebuilt.credential_attempts[_attempt()] == "uncertain"
    with pytest.raises(AttemptFenceError):
        _fence(rebuilt)


def test_distinct_seats_and_rounds_do_not_collapse(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    _fence(store, seat_id="forge", attempt_id=_attempt(seat_id="forge"))
    _fence(store, seat_id="skeptic", round_n=2, attempt_id=_attempt(seat_id="skeptic", round_n=2))
    assert set(store.credential_attempts) == {
        _attempt(seat_id="forge"),
        _attempt(seat_id="skeptic", round_n=2),
    }


def test_duplicate_fence_cannot_both_pass(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    barrier = Barrier(2)
    results: list[str] = []

    def once() -> None:
        local = TaskStore(store.ledger_path)
        barrier.wait()
        try:
            _fence(local)
            results.append("fenced")
        except AttemptFenceError as exc:
            results.append(exc.code)

    threads = [Thread(target=once), Thread(target=once)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["attempt_already_fenced", "fenced"]


def test_malformed_attempt_record_fails_closed(tmp_path: Path):
    path = tmp_path / "tasks.jsonl"
    path.write_text(
        json.dumps(
            {
                "event": SCHEMA_FENCE_EVENT,
                "schema_version": "1.1",
                "task": {"schema_fence": True},
            }
        )
        + "\n"
        + json.dumps(
            {
                "event": ATTEMPT_FENCE_EVENT,
                "schema_version": "1.1",
                "task_id": PARENT,
                "seat_id": "forge",
                "round": True,
                "attempt_id": _attempt(),
                "outcome": "fenced",
                "assignment_epoch": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    store = TaskStore(path)
    assert store.replay_error
    with pytest.raises(AttemptFenceError) as raised:
        _fence(store, task_id=OTHER, seat_id="quill", round_n=1, attempt_id=_attempt(OTHER, "quill"))
    assert raised.value.code == "replay_error"


def test_closed_to_fenced_is_rejected_on_replay(tmp_path: Path):
    path = tmp_path / "tasks.jsonl"
    store = TaskStore(path)
    _fence(store)
    store.settle_credential_attempt(_attempt(), "closed")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event": ATTEMPT_FENCE_EVENT,
                    "schema_version": "1.1",
                    "task_id": PARENT,
                    "seat_id": "forge",
                    "round": 1,
                    "attempt_id": _attempt(),
                    "outcome": "fenced",
                    "assignment_epoch": 0,
                }
            )
            + "\n"
        )
    rebuilt = TaskStore(path)
    assert rebuilt.replay_error
    assert "invalid attempt transition" in rebuilt.replay_error


def test_storage_failure_does_not_record_a_fence(tmp_path: Path, monkeypatch):
    store = TaskStore(tmp_path / "tasks.jsonl")

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(store, "append_control_event", boom)
    with pytest.raises(OSError):
        _fence(store)
    assert store.credential_attempts == {}
    text = store.ledger_path.read_text(encoding="utf-8") if store.ledger_path.exists() else ""
    assert ATTEMPT_FENCE_EVENT not in text


def test_old_reader_fence_is_not_silent_compatibility(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    _fence(store)
    text = store.ledger_path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    fence = next(record for record in records if record["event"] == SCHEMA_FENCE_EVENT)
    assert "task" in fence
    with pytest.raises(KeyError):
        TaskStore._rehydrate(fence["task"])


def test_identity_rejects_ambiguous_encodings():
    with pytest.raises(ValueError):
        validate_credential_attempt_identity(
            task_id="not-a-uuid",
            seat_id="forge",
            round_n=1,
            attempt_id="not-a-uuid|forge|round-1|attempt-1",
            assignment_epoch=0,
        )
    with pytest.raises(ValueError):
        validate_credential_attempt_identity(
            task_id=PARENT,
            seat_id="forge",
            round_n=True,
            attempt_id=_attempt(),
            assignment_epoch=0,
        )
    with pytest.raises(ValueError):
        validate_credential_attempt_identity(
            task_id=PARENT,
            seat_id="for|ge",
            round_n=1,
            attempt_id=f"{PARENT}|for|ge|round-1|attempt-1",
            assignment_epoch=0,
        )
    with pytest.raises(ValueError):
        validate_credential_attempt_identity(
            task_id=PARENT,
            seat_id="forge",
            round_n=1,
            attempt_id=_attempt(),
            assignment_epoch=True,
        )
    with pytest.raises(ValueError):
        validate_credential_attempt_identity(
            task_id=PARENT,
            seat_id="forge",
            round_n=1,
            attempt_id=_attempt(round_n=2),
            assignment_epoch=0,
        )
