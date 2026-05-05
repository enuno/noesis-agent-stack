"""In-memory job store with async locking."""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from app.models import Artifact, Event, JobResponse


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[UUID, JobResponse] = {}
        self._events: dict[UUID, list[Event]] = {}
        self._artifacts: dict[UUID, list[Artifact]] = {}
        self._idempotency: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, job: JobResponse) -> JobResponse:
        async with self._lock:
            self._jobs[job.job_id] = job
            self._events[job.job_id] = []
            self._artifacts[job.job_id] = []
            return job

    async def get_job(self, job_id: UUID) -> JobResponse | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job(self, job_id: UUID, **fields) -> JobResponse | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in fields.items():
                setattr(job, key, value)
            return job

    async def list_jobs(self) -> list[JobResponse]:
        async with self._lock:
            return list(self._jobs.values())

    async def cancel_job(self, job_id: UUID) -> JobResponse | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in ("completed", "failed", "cancelled", "timeout"):
                return job
            job.status = "cancelled"
            job.finished_at = datetime.utcnow()
            return job

    async def list_events_for_job(
        self,
        job_id: UUID,
        after: datetime | None = None,
        severity: str | None = None,
    ) -> list[Event]:
        async with self._lock:
            events = self._events.get(job_id, [])
            if after:
                events = [e for e in events if e.timestamp > after]
            if severity:
                sev_order = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
                min_level = sev_order.get(severity, 0)
                events = [e for e in events if sev_order.get(e.severity, 0) >= min_level]
            return events

    async def list_artifacts_for_job(self, job_id: UUID) -> list[Artifact]:
        async with self._lock:
            return list(self._artifacts.get(job_id, []))

    async def append_event(self, job_id: UUID, event: Event) -> Event:
        async with self._lock:
            if job_id not in self._events:
                self._events[job_id] = []
            self._events[job_id].append(event)
            return event

    async def append_artifact(self, job_id: UUID, artifact: Artifact) -> Artifact:
        async with self._lock:
            if job_id not in self._artifacts:
                self._artifacts[job_id] = []
            self._artifacts[job_id].append(artifact)
            job = self._jobs.get(job_id)
            if job:
                job.artifact_count = len(self._artifacts[job_id])
            return artifact

    def check_idempotency(self, key: str) -> bool:
        """Return True if key is already known and within the window."""
        now = datetime.utcnow()
        window = timedelta(seconds=3600)
        if key in self._idempotency:
            if now - self._idempotency[key] < window:
                return True
        self._idempotency[key] = now
        # Prune old entries
        cutoff = now - window
        self._idempotency = {
            k: v for k, v in self._idempotency.items() if v > cutoff
        }
        return False
