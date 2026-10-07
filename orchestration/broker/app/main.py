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


# --------------------------------------------------------------------- events
# Event streams are per-process, in-memory, and ordered by (timestamp, append
# order). They are NOT restart-durable: the durable records for a job are its
# palace receipt and the supervisor's ledgers. Retention: life of the process.
# Emitters validate every event against contracts/broker-api/events.schema.json
# before appending, so the stream is contract-conformant by construction.

async def _emit(
    job: JobResponse,
    event_type: str,
    *,
    severity: str = "info",
    payload: dict[str, Any] | None = None,
    source: str = "broker",
) -> Event:
    event = Event(
        job_id=job.job_id,
        correlation_id=job.correlation_id,
        type=event_type,
        source=source,
        payload=payload or {},
        severity=severity,
        traceparent=job.traceparent,
    )
    # Contract conformance guard; raises (fail closed) if the model drifts.
    # exclude_none: the contract rejects explicit nulls (additionalProperties: false
    # plus string-typed optional fields).
    dumped = event.model_dump(mode="json", exclude_none=True)
    schemas.validate_event_payload(dumped)
    return await _store.append_event(job.job_id, event)


async def _reject(code: str, message: str, *, status_code: int, correlation_id: Any = None) -> None:
    """Record sanitized audit evidence for a rejected request (bounded)."""
    await _store.append_rejection(
        {
            "timestamp": _now().isoformat(),
            "code": code,
            "message": message,
            "correlation_id": str(correlation_id) if correlation_id else None,
        }
    )


@app.post("/v1/jobs", status_code=202)
async def submit_job(payload: dict[str, Any]) -> JobResponse:
    # Schema validation
    try:
        schemas.validate_job_request(payload)
    except Exception as exc:
        code = "schema_validation_failed"
        message = f"job payload failed schema validation: {type(exc).__name__}"
        await _reject(code, message, status_code=400, correlation_id=payload.get("correlation_id"))
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": message, "correlation_id": payload.get("correlation_id")},
        )

    # Idempotency
    idempotency_key = payload.get("idempotency_key")
    if idempotency_key and _store.check_idempotency(idempotency_key):
        code = "idempotency_key_conflict"
        await _reject(code, "duplicate submission within dedup window", status_code=409,
                correlation_id=payload.get("correlation_id"))
        raise HTTPException(
            status_code=409,
            detail={"code": code, "message": "duplicate submission within dedup window",
                    "correlation_id": payload.get("correlation_id")},
        )

    # Scope and worker enforcement
    try:
        scopes.enforce_worker_known(payload["worker"])
        scopes.enforce_write_in_read(payload.get("write_scope", []), payload.get("read_scope", []))
        scopes.enforce_correlation_id(payload.get("correlation_id"))
    except HTTPException as exc:
        code = "policy_rejected"
        await _reject(code, str(exc.detail), status_code=422,
                      correlation_id=payload.get("correlation_id"))
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": str(exc.detail),
                    "correlation_id": payload.get("correlation_id")},
        )

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
    await _emit(
        job,
        "broker.job.submitted",
        payload={
            "worker": job.worker,
            "mode": job.mode,
            "requested_by": job.requested_by,
            "priority": job.priority,
        },
    )
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
    await _emit(job, "broker.job.cancelling", payload={"reason": reason})
    # Simulate immediate cancellation for skeleton
    await _store.update_job(job_id, status="cancelled", finished_at=_now())
    await _emit(job, "broker.job.cancelled", payload={"reason": reason})

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

    # Refresh job object after update (store mutates in place)
    await _emit(
        job,
        "broker.job.completed" if status == "completed" else "broker.job.failed",
        severity="info" if status == "completed" else "error",
        payload={"exit_code": exit_code, "artifact_count": job.artifact_count},
    )
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
    severity: str | None = Query(None, pattern=r"^(debug|info|warning|error|critical)$"),
) -> dict[str, Any]:
    job = await _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    after_dt = datetime.fromisoformat(after.replace("Z", "+00:00")) if after else None
    events = await _store.list_events_for_job(job_id, after=after_dt, severity=severity)
    # exclude_none: the contract rejects explicit nulls on optional fields.
    return {"job_id": str(job_id), "events": [e.model_dump(mode="json", exclude_none=True) for e in events]}


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


@app.get("/v1/audit/rejections")
async def list_rejections() -> dict[str, Any]:
    """Sanitized audit trail of rejected submissions (in-memory, per-process).

    Durability guarantee: same as the event stream — process lifetime only.
    """
    return {"rejections": await _store.list_rejections()}


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
