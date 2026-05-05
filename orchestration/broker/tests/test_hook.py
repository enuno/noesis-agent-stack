import json
from pathlib import Path
from uuid import UUID

import pytest

from hooks.mempalace_receipt_hook import (
    write_cancelled_record,
    write_event_snapshot,
    write_job_receipt,
)

PALACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "mempalace" / "broker"


class TestWriteJobReceipt:
    def test_writes_receipt_file(self):
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        path = write_job_receipt(
            job_id=job_id,
            worker="research-openclaw",
            status="completed",
            correlation_id=UUID("a7e8c9d0-1111-2222-3333-444455556666"),
            requested_by="main-hermes",
            exit_code=0,
            artifact_count=2,
            summary={"findings": 5},
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["job_id"] == str(job_id)
        assert data["worker"] == "research-openclaw"
        assert data["status"] == "completed"
        assert data["receipt_version"] == "1.0"
        assert data["artifact_count"] == 2
        assert data["summary"]["findings"] == 5
        assert "emitted_at" in data
        # Clean up
        path.unlink()

    def test_omits_none_fields(self):
        job_id = UUID("12345678-1234-5678-1234-567812345679")
        path = write_job_receipt(
            job_id=job_id,
            worker="coder",
            status="failed",
            correlation_id=UUID("a7e8c9d0-1111-2222-3333-444455556666"),
            requested_by="main-hermes",
        )
        data = json.loads(path.read_text())
        assert "started_at" not in data
        assert "finished_at" not in data
        assert "exit_code" not in data
        path.unlink()


class TestWriteEventSnapshot:
    def test_writes_event_snapshot(self):
        job_id = UUID("12345678-1234-5678-1234-56781234567a")
        events = [
            {"severity": "info", "message": "started"},
            {"severity": "error", "message": "something broke"},
        ]
        path = write_event_snapshot(job_id, events)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["job_id"] == str(job_id)
        assert data["event_count"] == 2
        assert len(data["events"]) == 2
        path.unlink()


class TestWriteCancelledRecord:
    def test_writes_cancelled_record(self):
        job_id = UUID("12345678-1234-5678-1234-56781234567b")
        path = write_cancelled_record(
            job_id=job_id,
            worker="qa",
            correlation_id=UUID("a7e8c9d0-1111-2222-3333-444455556666"),
            requested_by="main-hermes",
            reason="operator override",
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["status"] == "cancelled"
        assert data["reason"] == "operator override"
        assert data["cancelled_at"]
        path.unlink()
