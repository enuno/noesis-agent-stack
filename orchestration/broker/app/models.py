"""Pydantic models aligned with contracts/broker-api/job.schema.json."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Approval(BaseModel):
    required: bool
    approved_by: str | None = None
    approved_at: datetime | None = None


class JobCreate(BaseModel):
    worker: str
    mode: str | None = None
    requested_by: str
    correlation_id: UUID
    traceparent: str | None = Field(
        None, pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"
    )
    priority: str = "normal"
    timeout_s: int = Field(..., ge=60, le=7200)
    write_scope: list[str]
    read_scope: list[str]
    input_artifacts: list[str] | None = None
    approval: Approval | None = None
    parameters: dict[str, Any] | None = None
    idempotency_key: str | None = None


class JobResponse(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    worker: str
    mode: str | None = None
    requested_by: str
    correlation_id: UUID
    traceparent: str | None = None
    priority: str = "normal"
    timeout_s: int
    write_scope: list[str]
    read_scope: list[str]
    input_artifacts: list[str] | None = None
    approval: Approval | None = None
    parameters: dict[str, Any] | None = None
    idempotency_key: str | None = None
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    health: str | None = None
    artifact_count: int = 0
    warnings: list[str] | None = None
    summary: dict[str, Any] | None = None


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = Field(..., pattern=r"^(debug|info|warning|error|critical)$")
    message: str
    source: str | None = None
    metadata: dict[str, Any] | None = None


class Artifact(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    path: str
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkerProfile(BaseModel):
    name: str
    runtime: str
    modes: list[str]
    read_scopes: list[str]
    write_scopes: list[str]
    emits: list[str]
    approval_required_for: list[str]
    healthy: bool = True


class HealthResponse(BaseModel):
    status: str = Field(..., pattern=r"^(ok|degraded|down)$")
    version: str
    uptime_s: int
    queued_jobs: int
    active_jobs: int
    workers_healthy: int
    workers_total: int
