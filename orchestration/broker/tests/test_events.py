"""Regression tests for broker event-stream evidence.

Defect (deployment-verification-2026-10-06): accepted lifecycle transitions
emitted no events, so GET /v1/jobs/{id}/events returned an empty array after
submit and cancel. These tests exercise the real HTTP interface.

Durability note (pinned here so tests never imply more than is implemented):
event streams are in-memory and per-process. The durable record for a job is
its palace receipt plus supervisor ledgers.
"""

import pytest
from fastapi.testclient import TestClient


class TestLifecycleEvents:
    def test_submit_emits_submitted_event(self, client: TestClient, sample_job):
        job = client.post("/v1/jobs", json=sample_job).json()
        events = client.get(f"/v1/jobs/{job['job_id']}/events").json()["events"]
        assert [e["type"] for e in events] == ["broker.job.submitted"]
        e = events[0]
        assert e["job_id"] == job["job_id"]
        assert e["correlation_id"] == job["correlation_id"]
        assert e["severity"] == "info"
        assert e["source"] == "broker"
        assert e["payload"]["worker"] == sample_job["worker"]

    def test_cancel_emits_ordered_cancelling_cancelled(self, client: TestClient, sample_job):
        job = client.post("/v1/jobs", json=sample_job).json()
        response = client.post(f"/v1/jobs/{job['job_id']}/cancel", params={"reason": "operator halt"})
        assert response.status_code == 200
        events = client.get(f"/v1/jobs/{job['job_id']}/events").json()["events"]
        types = [e["type"] for e in events]
        assert types == ["broker.job.submitted", "broker.job.cancelling", "broker.job.cancelled"]
        # Ordered by time.
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)

    def test_complete_emits_terminal_event(self, client: TestClient, sample_job):
        job = client.post("/v1/jobs", json=sample_job).json()
        response = client.post(
            f"/v1/jobs/{job['job_id']}/complete", json={"exit_code": 0, "artifact_count": 2}
        )
        assert response.status_code == 200
        events = client.get(f"/v1/jobs/{job['job_id']}/events").json()["events"]
        assert events[-1]["type"] == "broker.job.completed"

    def test_failed_completion_emits_error_event(self, client: TestClient, sample_job):
        job = client.post("/v1/jobs", json=sample_job).json()
        client.post(f"/v1/jobs/{job['job_id']}/complete", json={"exit_code": 1})
        events = client.get(f"/v1/jobs/{job['job_id']}/events").json()["events"]
        assert events[-1]["type"] == "broker.job.failed"
        assert events[-1]["severity"] == "error"

    def test_events_conform_to_contract(self, client: TestClient, sample_job):
        import json
        import jsonschema
        from pathlib import Path

        job = client.post("/v1/jobs", json=sample_job).json()
        client.post(f"/v1/jobs/{job['job_id']}/cancel")
        schema = json.loads(
            (Path(__file__).resolve().parents[3] / "contracts" / "broker-api" / "events.schema.json").read_text()
        )
        events = client.get(f"/v1/jobs/{job['job_id']}/events").json()["events"]
        assert events, "expected events to validate"
        for e in events:
            jsonschema.Draft202012Validator(schema).validate(e)


class TestRejectionAudit:
    def test_rejections_recorded_and_sanitized(self, client: TestClient, sample_job):
        # schema-invalid
        client.post("/v1/jobs", json={"worker": "research-openclaw"})
        # duplicate idempotency
        dup = dict(sample_job, idempotency_key="audit-dup-001")
        client.post("/v1/jobs", json=dup)
        client.post("/v1/jobs", json=dup)
        # scope violation
        bad_scope = dict(sample_job, read_scope=["workspace/research-vault"],
                         write_scope=["workspace/subconscious-room"])
        client.post("/v1/jobs", json=bad_scope)

        rejections = client.get("/v1/audit/rejections").json()["rejections"]
        codes = [r["code"] for r in rejections]
        assert "schema_validation_failed" in codes
        assert "idempotency_key_conflict" in codes
        assert "policy_rejected" in codes
        for r in rejections:
            # Structured, sanitized: no schema dumps, no stack traces.
            assert set(r.keys()) == {"timestamp", "code", "message", "correlation_id"}
            assert "Traceback" not in r["message"]
            assert "properties" not in r["message"]

    def test_structured_error_response(self, client: TestClient, sample_job):
        response = client.post("/v1/jobs", json={"worker": "x"})
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "schema_validation_failed"
        assert "correlation_id" in detail
        # No raw schema dump in the response.
        assert "enum" not in str(detail)
