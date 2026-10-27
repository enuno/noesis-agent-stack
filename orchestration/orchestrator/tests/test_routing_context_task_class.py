"""Regression coverage for the ``task_class`` precedence guard (F4).

``Orchestrator._routing_context_for_task`` resolves the routing task class
from three sources, in this order:

1. an explicit ``task_class`` override recorded in the inference routing
   context for the task,
2. otherwise the first label on the task contract,
3. otherwise the literal ``"general"``.

The unguarded expression

    overrides.get("task_class") or task.labels[0] if task.labels else "general"

parses as ``(overrides.get("task_class") or task.labels[0]) if task.labels else
"general"`` — the conditional applies to the whole expression, not only to the
label lookup. When the task carries no labels the entire expression collapses
to ``"general"`` and an explicit override is silently discarded.

These tests pin all three branches of the intended semantics.
"""

from __future__ import annotations

from pathlib import Path

from app.control_plane import Orchestrator
from app.models import Verification


def _orchestrator(tmp_path: Path) -> Orchestrator:
    return Orchestrator(tmp_path / "tasks.jsonl")


def _task(orch: Orchestrator, *, idempotency_key: str, labels: list[str]):
    return orch.propose(
        title="task_class precedence probe",
        intent="Probe the task_class precedence in the routing context",
        assignee_profile="noesis-signal",
        required_capability="deep_research",
        acceptance_criteria=["probe complete"],
        verification=Verification(method="probe"),
        idempotency_key=idempotency_key,
        labels=labels,
    )


def test_explicit_override_wins_when_task_has_no_labels(tmp_path: Path) -> None:
    """An explicit override must win even when the task carries no labels.

    Against the unguarded expression this yields ``"general"`` instead of
    the override, because the conditional swallows the whole expression
    when ``task.labels`` is empty.
    """
    orch = _orchestrator(tmp_path)
    task = _task(orch, idempotency_key="f4:override-without-labels", labels=[])
    assert task.labels == []
    orch._inference_routing_context[str(task.task_id)] = {"task_class": "research"}

    context = orch._routing_context_for_task(task)

    assert context.task_class == "research"


def test_first_label_is_used_when_no_override_is_present(tmp_path: Path) -> None:
    """Without an override, the first label is the task class."""
    orch = _orchestrator(tmp_path)
    task = _task(
        orch,
        idempotency_key="f4:first-label-fallback",
        labels=["research", "urgent"],
    )
    assert task.labels == ["research", "urgent"]
    assert str(task.task_id) not in orch._inference_routing_context

    context = orch._routing_context_for_task(task)

    assert context.task_class == "research"


def test_general_is_used_when_no_override_and_no_labels(tmp_path: Path) -> None:
    """With neither an override nor labels, the task class is ``general``."""
    orch = _orchestrator(tmp_path)
    task = _task(orch, idempotency_key="f4:general-fallback", labels=[])
    assert task.labels == []
    assert str(task.task_id) not in orch._inference_routing_context

    context = orch._routing_context_for_task(task)

    assert context.task_class == "general"


def test_override_wins_over_labels_when_both_are_present(tmp_path: Path) -> None:
    """An explicit override takes precedence over the first label."""
    orch = _orchestrator(tmp_path)
    task = _task(
        orch,
        idempotency_key="f4:override-over-label",
        labels=["research", "urgent"],
    )
    orch._inference_routing_context[str(task.task_id)] = {"task_class": "implementation"}

    context = orch._routing_context_for_task(task)

    assert context.task_class == "implementation"
