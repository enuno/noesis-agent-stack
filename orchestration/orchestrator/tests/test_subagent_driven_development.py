"""Subagent-driven development workflow regressions.

Exercises the real workflow entrypoint: approved plan ingestion -> fresh
implementation session -> ordered spec/quality reviews -> remediation -> final
integration review. Adapters are mocked so no external Claude Code/Codex process
or production state is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.subagent_development import (
    Finding,
    MockCodingSessionAdapter,
    ReviewVerdict,
    SDDWorkflow,
    WorkflowBlocked,
)


APPROVED_PLAN = """
Plan: specialist routing demo
Approval: approval-demo-001

Task T1: Add a routing helper.
Acceptance:
- helper returns selected specialist
- tests cover missing profiles
Files: orchestration/orchestrator/app/specialist_routing.py
Verify: uv run pytest orchestration/orchestrator/tests/test_specialist_routing.py -q
"""


def test_complete_trace_with_remediation_and_ordered_reviews(tmp_path: Path) -> None:
    adapter = MockCodingSessionAdapter()
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=adapter)
    run = workflow.ingest_approved_plan(
        plan_text=APPROVED_PLAN,
        approval_ref="approval-demo-001",
        baseline_revision="base-sha",
    )

    task = run.tasks[0]
    workflow.mark_ready(run.plan_id, task.task_id)
    impl1 = workflow.dispatch_implementation(run.plan_id, task.task_id, backend="codex")
    assert impl1.owner_profile == "noesis-forge"
    assert impl1.context_id.startswith("fresh-")

    workflow.complete_implementation(
        run.plan_id,
        task.task_id,
        candidate_revision="rev-1",
        changed_paths=["orchestration/orchestrator/app/specialist_routing.py"],
        artifacts={"pytest": "failed before remediation"},
    )

    workflow.record_spec_review(
        run.plan_id,
        task.task_id,
        verdict=ReviewVerdict.REQUEST_CHANGES,
        reviewer_profile="noesis-sentinel",
        candidate_revision="rev-1",
        findings=[Finding("important", "helper", "missing missing-profile case", "add coverage")],
    )
    assert workflow.task(run.plan_id, task.task_id).state == "remediation"

    impl2 = workflow.dispatch_remediation(run.plan_id, task.task_id, backend="codex")
    assert impl2.context_id != impl1.context_id
    workflow.complete_implementation(
        run.plan_id,
        task.task_id,
        candidate_revision="rev-2",
        changed_paths=["orchestration/orchestrator/app/specialist_routing.py"],
        artifacts={"pytest": "22 passed"},
    )
    workflow.record_spec_review(
        run.plan_id,
        task.task_id,
        verdict=ReviewVerdict.PASS,
        reviewer_profile="noesis-sentinel",
        candidate_revision="rev-2",
        findings=[],
    )
    workflow.record_quality_review(
        run.plan_id,
        task.task_id,
        verdict=ReviewVerdict.APPROVED,
        reviewer_profile="noesis-sentinel",
        candidate_revision="rev-2",
        findings=[],
    )

    assert workflow.task(run.plan_id, task.task_id).state == "completed"
    integration = workflow.record_integration_review(
        run.plan_id,
        verdict=ReviewVerdict.APPROVED,
        reviewer_profile="noesis-skeptic",
        candidate_revision="rev-2",
        verification={"full_suite": "126 passed"},
        findings=[],
    )
    assert integration.verified is True
    assert workflow.synthesize(run.plan_id)["status"] == "verified"


def test_quality_review_cannot_precede_spec_pass(tmp_path: Path) -> None:
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=MockCodingSessionAdapter())
    run = workflow.ingest_approved_plan(APPROVED_PLAN, approval_ref="approval-demo-001", baseline_revision="base")
    task = run.tasks[0]
    workflow.mark_ready(run.plan_id, task.task_id)
    workflow.dispatch_implementation(run.plan_id, task.task_id, backend="codex")
    workflow.complete_implementation(run.plan_id, task.task_id, candidate_revision="rev-1", changed_paths=[], artifacts={})

    with pytest.raises(WorkflowBlocked, match="spec_review_required"):
        workflow.record_quality_review(
            run.plan_id,
            task.task_id,
            verdict=ReviewVerdict.APPROVED,
            reviewer_profile="noesis-sentinel",
            candidate_revision="rev-1",
            findings=[],
        )


def test_review_approval_invalidated_by_candidate_change(tmp_path: Path) -> None:
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=MockCodingSessionAdapter())
    run = workflow.ingest_approved_plan(APPROVED_PLAN, approval_ref="approval-demo-001", baseline_revision="base")
    task = run.tasks[0]
    workflow.mark_ready(run.plan_id, task.task_id)
    workflow.dispatch_implementation(run.plan_id, task.task_id, backend="codex")
    workflow.complete_implementation(run.plan_id, task.task_id, candidate_revision="rev-1", changed_paths=[], artifacts={})
    workflow.record_spec_review(run.plan_id, task.task_id, verdict=ReviewVerdict.PASS, reviewer_profile="noesis-sentinel", candidate_revision="rev-1", findings=[])

    workflow.complete_implementation(run.plan_id, task.task_id, candidate_revision="rev-2", changed_paths=[], artifacts={})
    with pytest.raises(WorkflowBlocked, match="spec_review_required"):
        workflow.record_quality_review(run.plan_id, task.task_id, verdict=ReviewVerdict.APPROVED, reviewer_profile="noesis-sentinel", candidate_revision="rev-2", findings=[])


def test_missing_backend_blocks_without_launch(tmp_path: Path) -> None:
    adapter = MockCodingSessionAdapter(available_backends={"codex": False})
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=adapter)
    run = workflow.ingest_approved_plan(APPROVED_PLAN, approval_ref="approval-demo-001", baseline_revision="base")
    task = run.tasks[0]
    workflow.mark_ready(run.plan_id, task.task_id)

    with pytest.raises(WorkflowBlocked, match="backend_unavailable"):
        workflow.dispatch_implementation(run.plan_id, task.task_id, backend="codex")
    assert adapter.launches == []


def test_shared_file_conflicts_prevent_simultaneous_writers(tmp_path: Path) -> None:
    plan = APPROVED_PLAN + """
Task T2: Update the same routing helper docs.
Acceptance:
- docs updated
Files: orchestration/orchestrator/app/specialist_routing.py
Verify: uv run pytest orchestration/orchestrator/tests/test_specialist_routing.py -q
"""
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=MockCodingSessionAdapter())
    run = workflow.ingest_approved_plan(plan, approval_ref="approval-demo-001", baseline_revision="base")
    workflow.mark_ready(run.plan_id, "T1")
    workflow.mark_ready(run.plan_id, "T2")
    workflow.dispatch_implementation(run.plan_id, "T1", backend="codex")

    with pytest.raises(WorkflowBlocked, match="workspace_conflict"):
        workflow.dispatch_implementation(run.plan_id, "T2", backend="codex")


def test_restart_recovers_without_duplicate_dispatch(tmp_path: Path) -> None:
    ledger = tmp_path / "sdd-ledger.jsonl"
    workflow = SDDWorkflow(ledger, session_adapter=MockCodingSessionAdapter())
    run = workflow.ingest_approved_plan(APPROVED_PLAN, approval_ref="approval-demo-001", baseline_revision="base")
    workflow.mark_ready(run.plan_id, "T1")
    first = workflow.dispatch_implementation(run.plan_id, "T1", backend="codex")

    restarted = SDDWorkflow(ledger, session_adapter=MockCodingSessionAdapter())
    with pytest.raises(WorkflowBlocked, match="already_implementing"):
        restarted.dispatch_implementation(run.plan_id, "T1", backend="codex")
    assert restarted.task(run.plan_id, "T1").attempts[-1].session_id == first.session_id


def test_final_integration_failure_reopens_affected_work(tmp_path: Path) -> None:
    workflow = SDDWorkflow(tmp_path / "sdd-ledger.jsonl", session_adapter=MockCodingSessionAdapter())
    run = workflow.ingest_approved_plan(APPROVED_PLAN, approval_ref="approval-demo-001", baseline_revision="base")
    task = run.tasks[0]
    workflow.mark_ready(run.plan_id, task.task_id)
    workflow.dispatch_implementation(run.plan_id, task.task_id, backend="codex")
    workflow.complete_implementation(run.plan_id, task.task_id, candidate_revision="rev-1", changed_paths=[], artifacts={})
    workflow.record_spec_review(run.plan_id, task.task_id, verdict=ReviewVerdict.PASS, reviewer_profile="noesis-sentinel", candidate_revision="rev-1", findings=[])
    workflow.record_quality_review(run.plan_id, task.task_id, verdict=ReviewVerdict.APPROVED, reviewer_profile="noesis-sentinel", candidate_revision="rev-1", findings=[])

    workflow.record_integration_review(
        run.plan_id,
        verdict=ReviewVerdict.REQUEST_CHANGES,
        reviewer_profile="noesis-skeptic",
        candidate_revision="rev-1",
        verification={"full_suite": "integration failure"},
        findings=[Finding("critical", "integration", "combined behavior regressed", "remediate T1")],
        affected_task_ids=["T1"],
    )
    assert workflow.task(run.plan_id, "T1").state == "remediation"
