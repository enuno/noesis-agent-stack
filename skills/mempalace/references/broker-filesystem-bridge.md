# Broker → MemPalace Filesystem Bridge Pattern

## Problem

A FastAPI broker (or any non-agent service) cannot call MCP tools directly because MCP
servers are long-running processes accessed by the agent runtime, not by arbitrary
Python services. When a broker completes a job, it needs to leave a durable trace in
MemPalace for the supervisor agent to query.

## Solution: On-Disk Bridge

Write structured receipt files to a well-known directory tree that mirrors the palace
taxonomy. The supervisor agent (Hermes) reads these files and forwards them to the
live palace via `mcp_mempalace_add_drawer`.

```
service (FastAPI)
    → writes JSON receipt to workspace/mempalace/broker/jobs/{job_id}.receipt.json
    → agent session polls / queries filesystem
    → agent calls mcp_mempalace_add_drawer to sync into live palace
```

## Implementation Sketch

### 1. Taxonomy-aligned directory tree

Create `workspace/mempalace/` with subdirectories matching `contracts/mempalace/taxonomy.yaml`:

```
workspace/mempalace/
├── broker/jobs/          # job receipts
├── broker/events/        # event snapshots
├── hermes/decisions/     # routing records
├── research-vault/knowledge/findings/
└── ...
```

An `init_palace.py` script reads `taxonomy.yaml` and scaffolds all missing directories,
writing an `index.json` for fast lookups.

### 2. Hook module in the broker

```python
# hooks/mempalace_receipt_hook.py
from pathlib import Path
import json

PALACE_JOBS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "mempalace" / "broker" / "jobs"

def write_job_receipt(job_id, worker, status, correlation_id, ..., finished_at=None):
    PALACE_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_version": "1.0",
        "job_id": str(job_id),
        "worker": worker,
        "status": status,
        ...
    }
    path = PALACE_JOBS_DIR / f"{job_id}.receipt.json"
    path.write_text(json.dumps(receipt, indent=2))
    return path
```

Call this from the completion endpoint and from cancellation handling.

### 3. Completion endpoint in broker

```python
@app.post("/v1/jobs/{job_id}/complete")
async def complete_job(job_id: UUID, payload: dict):
    # ... update job store ...
    receipt_path = write_job_receipt(
        job_id=job.job_id,
        worker=job.worker,
        status=job.status,
        ...
    )
    return {"job_id": str(job_id), "status": status, "receipt_path": str(receipt_path)}
```

### 4. Agent-side sync (optional)

Hermes can scan `workspace/mempalace/broker/jobs/*.receipt.json` and call
`mcp_mempalace_add_drawer(wing="broker", room="job-receipts", content=json.dumps(receipt))`
to push receipts into the live palace for semantic search.

## Trade-offs

| Approach | Pros | Cons |
|---|---|---|
| Filesystem bridge | Simple, no extra dependencies, survives broker restart | Not real-time; requires agent to poll or scan |
| HTTP callback to agent | Real-time | Tight coupling; agent must expose endpoint |
| Direct ChromaDB write from broker | Real-time, no agent bottleneck | Breaks abstraction; broker needs DB credentials |
| Message queue (Redis, NATS) | Decoupled, real-time | Adds infrastructure complexity |

For early-phase platforms, the filesystem bridge is the right default. Upgrade to a
message queue or HTTP callback when latency requirements tighten.

## Testing

Receipt hook tests should:
1. Call `write_job_receipt` with known UUIDs
2. Assert the file exists and parses as valid JSON
3. Assert required fields are present and `None` fields are omitted
4. Clean up written files in `tearDown` or `finally` blocks

## Pitfalls

- **Path drift:** If the broker is installed as a package (`pip install -e .`), `__file__`
  resolves inside the package directory, not the repo root. Compute `PALACE_JOBS_DIR`
  from an environment variable (e.g., `PALACE_ROOT`) in production.
- **Orphaned files:** Receipt files accumulate. Add a retention policy (e.g., purge files
  older than 30 days) or move them to an archive after agent sync.
- **Concurrent writes:** If the broker is multi-process, file writes can collide on the
  same `{job_id}.receipt.json`. Use UUID-based job IDs (which are unique) to avoid this.
- **No deduplication:** The filesystem layer does not check for duplicates. If a job is
  completed twice, two receipt files may exist. The agent sync layer should handle this
  by checking `mcp_mempalace_check_duplicate` before calling `add_drawer`.
