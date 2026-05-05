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
from hooks.mempalace_receipt_hook import write_cancelled_record, write_job_receipt

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
        started_at=_now(),
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

    # Write palace receipt
    write_cancelled_record(
        job_id=job.job_id,
        worker=job.worker,
        correlation_id=job.correlation_id,
        requested_by=job.requested_by,
        reason=reason,
    )

    return {"job_id": str(job_id), "status": "cancelled"}


@app.post("/v1/jobs/{job_id}/complete")
async def complete_job(
    job_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Report job completion. Called by workers or the supervisor."""
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("completed", "failed", "cancelled", "timeout"):
        raise HTTPException(status_code=409, detail="Job already terminal")

    exit_code = payload.get("exit_code", 0)
    status = "completed" if exit_code == 0 else "failed"
    finished_at = _now()

    await _store.update_job(
        job_id,
        status=status,
        finished_at=finished_at,
        exit_code=exit_code,
        artifact_count=payload.get("artifact_count", job.artifact_count),
        warnings=payload.get("warnings", job.warnings),
        summary=payload.get("summary", job.summary),
        health=payload.get("health", job.health),
    )

    # Refresh job object after update
    job = await _store.get_job(job_id)

    # Write palace receipt
    receipt_path = write_job_receipt(
        job_id=job.job_id,
        worker=job.worker,
        status=job.status,
        correlation_id=job.correlation_id,
        requested_by=job.requested_by,
        started_at=job.started_at,
        finished_at=job.finished_at,
        exit_code=job.exit_code,
        artifact_count=job.artifact_count,
        warnings=job.warnings,
        summary=job.summary,
        traceparent=job.traceparent,
        mode=job.mode,
    )

    return {
        "job_id": str(job_id),
        "status": status,
        "receipt_path": str(receipt_path),
    }


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
