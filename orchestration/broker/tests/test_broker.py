import pytest
from fastapi.testclient import TestClient


class TestSubmitJob:
    def test_submit_job_success(self, client: TestClient, sample_job):
        response = client.post("/v1/jobs", json=sample_job)
        assert response.status_code == 202
        data = response.json()
        assert data["worker"] == sample_job["worker"]
        assert data["status"] == "pending"
        assert "job_id" in data

    def test_submit_job_validation_failure(self, client: TestClient):
        payload = {"worker": "research-openclaw"}  # missing required fields
        response = client.post("/v1/jobs", json=payload)
        assert response.status_code == 400

    def test_submit_job_unknown_worker(self, client: TestClient, sample_job):
        sample_job["worker"] = "unknown-worker"
        response = client.post("/v1/jobs", json=sample_job)
        # Schema enum catches unknown worker before registry check
        assert response.status_code == 400

    def test_submit_job_scope_violation(self, client: TestClient, sample_job):
        sample_job["write_scope"] = ["workspace/coder-jobs"]
        sample_job["read_scope"] = ["workspace/research-vault"]
        response = client.post("/v1/jobs", json=sample_job)
        assert response.status_code == 422

    def test_submit_job_idempotency_conflict(self, client: TestClient, sample_job):
        sample_job["idempotency_key"] = "unique-key-123"
        response = client.post("/v1/jobs", json=sample_job)
        assert response.status_code == 202
        # second submission with same key
        response2 = client.post("/v1/jobs", json=sample_job)
        assert response2.status_code == 409


class TestGetJob:
    def test_get_job_success(self, client: TestClient, sample_job):
        created = client.post("/v1/jobs", json=sample_job).json()
        job_id = created["job_id"]
        response = client.get(f"/v1/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["job_id"] == job_id

    def test_get_job_not_found(self, client: TestClient):
        response = client.get("/v1/jobs/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 404


class TestCancelJob:
    def test_cancel_job_success(self, client: TestClient, sample_job):
        created = client.post("/v1/jobs", json=sample_job).json()
        job_id = created["job_id"]
        response = client.post(f"/v1/jobs/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_job_not_found(self, client: TestClient):
        response = client.post("/v1/jobs/11111111-1111-1111-1111-111111111111/cancel")
        assert response.status_code == 404

    def test_cancel_job_terminal_conflict(self, client: TestClient, sample_job):
        created = client.post("/v1/jobs", json=sample_job).json()
        job_id = created["job_id"]
        client.post(f"/v1/jobs/{job_id}/cancel")
        response = client.post(f"/v1/jobs/{job_id}/cancel")
        assert response.status_code == 409


class TestJobEvents:
    def test_get_job_events(self, client: TestClient, sample_job):
        created = client.post("/v1/jobs", json=sample_job).json()
        job_id = created["job_id"]
        response = client.get(f"/v1/jobs/{job_id}/events")
        assert response.status_code == 200
        assert response.json()["events"] == []


class TestJobArtifacts:
    def test_get_job_artifacts(self, client: TestClient, sample_job):
        created = client.post("/v1/jobs", json=sample_job).json()
        job_id = created["job_id"]
        response = client.get(f"/v1/jobs/{job_id}/artifacts")
        assert response.status_code == 200
        assert response.json()["artifacts"] == []


class TestListWorkers:
    def test_list_workers(self, client: TestClient):
        response = client.get("/v1/workers")
        assert response.status_code == 200
        data = response.json()
        assert len(data["workers"]) == 4
        names = {w["name"] for w in data["workers"]}
        assert names == {"research-openclaw", "subconscious-openclaw", "coder", "qa"}


class TestHealth:
    def test_health_endpoint(self, client: TestClient):
        response = client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "uptime_s" in data
        assert "queued_jobs" in data
        assert "active_jobs" in data
        assert "workers_healthy" in data
        assert "workers_total" in data
