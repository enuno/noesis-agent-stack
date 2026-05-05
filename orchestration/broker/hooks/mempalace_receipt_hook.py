"""Broker hook that writes job receipts to the on-disk MemPalace bridge.

In production this would forward to the live MemPalace via MCP or HTTP.
For Phase 1.5 it writes JSON receipt files to workspace/mempalace/broker/jobs/
so that Hermes can sync them into the palace proper.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

RECEIPT_VERSION = "1.0"
PALACE_JOBS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "mempalace" / "broker" / "jobs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_job_receipt(
    job_id: UUID,
    worker: str,
    status: str,
    correlation_id: UUID,
    requested_by: str,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    exit_code: int | None = None,
    artifact_count: int = 0,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
    traceparent: str | None = None,
    mode: str | None = None,
) -> Path:
    """Serialize a job receipt and write it to the palace bridge.

    Returns the path to the written receipt file.
    """
    PALACE_JOBS_DIR.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "receipt_version": RECEIPT_VERSION,
        "job_id": str(job_id),
        "worker": worker,
        "mode": mode,
        "status": status,
        "correlation_id": str(correlation_id),
        "requested_by": requested_by,
        "traceparent": traceparent,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "exit_code": exit_code,
        "artifact_count": artifact_count,
        "warnings": warnings or [],
        "summary": summary or {},
        "emitted_at": _now_iso(),
    }

    # Filter out None values for a cleaner payload
    receipt = {k: v for k, v in receipt.items() if v is not None}

    receipt_path = PALACE_JOBS_DIR / f"{job_id}.receipt.json"
    with open(receipt_path, "w") as fh:
        json.dump(receipt, fh, indent=2)

    return receipt_path


def write_event_snapshot(
    job_id: UUID,
    events: list[dict[str, Any]],
) -> Path:
    """Write an event snapshot for a job to the palace bridge."""
    events_dir = PALACE_JOBS_DIR.parent / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "snapshot_version": "1.0",
        "job_id": str(job_id),
        "event_count": len(events),
        "events": events,
        "emitted_at": _now_iso(),
    }

    path = events_dir / f"{job_id}.events.json"
    with open(path, "w") as fh:
        json.dump(snapshot, fh, indent=2)

    return path


def write_cancelled_record(
    job_id: UUID,
    worker: str,
    correlation_id: UUID,
    requested_by: str,
    reason: str | None = None,
) -> Path:
    """Write a cancellation record to the palace bridge."""
    cancelled_dir = PALACE_JOBS_DIR.parent / "cancelled-jobs"
    cancelled_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "receipt_version": RECEIPT_VERSION,
        "job_id": str(job_id),
        "worker": worker,
        "status": "cancelled",
        "correlation_id": str(correlation_id),
        "requested_by": requested_by,
        "reason": reason,
        "cancelled_at": _now_iso(),
    }

    path = cancelled_dir / f"{job_id}.cancelled.json"
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)

    return path
