"""FastAPI broker control plane."""

import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app import registry, scopes, schemas
from app.models import Approval, Artifact, Event, HealthResponse, JobCreate, JobResponse
from app.store import JobStore

app = FastAPI(title="Hermes-OpenClaw Broker", version="1.0.0")
_store = JobStore()
_start_time = time.time()


def _now() -> datetime:
    return datetime.utcnow()


@app.post("/v1/jobs", status_code=202)
async def submit_job(payload: dict[str, Any]) -> JobResponse:
    # Schema validation
    try:
        schemas.validate_job_request(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {exc}")

    # Idempotency
    idempotency_key = payload.get("idempotency_key")
    if idempotency_key and _store.check_idempotency(idempotency_key):
        raise HTTPException(status_code=409, detail="Idempotency key conflict")

    # Scope and worker enforcement
    scopes.enforce_worker_known(payload["worker"])
    scopes.enforce_write_in_read(payload.get("write_scope", []), payload.get("read_scope", []))
    scopes.enforce_correlation_id(payload.get("correlation_id"))

    job = JobResponse(
        job_id=uuid4(),
        worker=payload["worker"],
        mode=payload.get("mode"),
        requested_by=payload["requested_by"],
        correlation_id=UUID(payload["correlation_id"]),
        traceparent=payload.get("traceparent"),
        priority=payload.get("priority", "normal"),
        timeout_s=payload["timeout_s"],
        write_scope=payload.get("write_scope", []),
        read_scope=payload.get("read_scope", []),
        input_artifacts=payload.get("input_artifacts"),
        approval=Approval(**payload["approval"]) if payload.get("approval") else None,
        parameters=payload.get("parameters"),
        idempotency_key=idempotency_key,
        status="pending",
    )

    await _store.create_job(job)
    return job


@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: UUID) -> JobResponse:
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: UUID, reason: str | None = None) -> dict[str, Any]:
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("completed", "failed", "cancelled", "timeout"):
        raise HTTPException(status_code=409, detail="Job already terminal")

    await _store.update_job(job_id, status="cancelling")
    # Simulate immediate cancellation for skeleton
    await _store.update_job(job_id, status="cancelled", finished_at=_now())
    return {"job_id": str(job_id), "status": "cancelled"}


@app.get("/v1/jobs/{job_id}/events")
async def get_job_events(
    job_id: UUID,
    after: str | None = Query(None, description="ISO-8601 timestamp"),
    severity: str | None = Query(None, regex=r"^(debug|info|warning|error|critical)$"),
) -> dict[str, Any]:
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    after_dt = datetime.fromisoformat(after.replace("Z", "+00:00")) if after else None
    events = await _store.list_events_for_job(job_id, after=after_dt, severity=severity)
    return {"job_id": str(job_id), "events": [e.model_dump(mode="json") for e in events]}


@app.get("/v1/jobs/{job_id}/artifacts")
async def get_job_artifacts(job_id: UUID) -> dict[str, Any]:
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    artifacts = await _store.list_artifacts_for_job(job_id)
    return {"job_id": str(job_id), "artifacts": [a.model_dump(mode="json") for a in artifacts]}


@app.get("/v1/workers")
async def list_workers() -> dict[str, Any]:
    workers = registry.list_workers()
    return {"workers": [w.model_dump(mode="json") for w in workers]}


@app.get("/v1/health")
async def health() -> HealthResponse:
    jobs = await _store.list_jobs()
    queued = sum(1 for j in jobs if j.status == "pending")
    active = sum(1 for j in jobs if j.status in ("queued", "running"))
    workers = registry.list_workers()
    healthy_workers = sum(1 for w in workers if w.healthy)
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime_s=int(time.time() - _start_time),
        queued_jobs=queued,
        active_jobs=active,
        workers_healthy=healthy_workers,
        workers_total=len(workers),
    )
