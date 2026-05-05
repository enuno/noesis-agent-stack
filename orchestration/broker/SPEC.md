# Broker Specification

## Design goals

1. **Schema validation** — Every inbound job is validated against `job.schema.json` before acceptance.
2. **Scope enforcement** — Workers cannot write outside their declared write scopes, and write scopes must be subsets of read scopes.
3. **Idempotency** — Duplicate `idempotency_key` values within a 1-hour window are rejected with HTTP 409.
4. **Observability** — Every job state change, event, and artifact is queryable through the API.

## Job lifecycle

```
  +---------+    submit     +--------+    start     +--------+
  | pending | -----------> | queued | ---------> | running|
  +---------+              +--------+            +--------+
                                |                     |
                                | cancel              | complete
                                v                     v
                          +-----------+          +----------+
                          |cancelled  |          |completed |
                          +-----------+          +----------+
                                |
                                | fail / timeout
                                v
                          +----------+
                          | failed   |
                          | timeout  |
                          +----------+
```

## Data models

See `app/models.py` for Pydantic definitions. Key fields:

- `job_id` (UUID) — broker-assigned on submission
- `worker` (string) — target worker profile; must exist in registry
- `mode` (string) — execution mode passed to worker
- `requested_by` (string) — submitting agent
- `correlation_id` (UUID) — tracing ID across the request chain
- `priority` (enum) — critical, high, normal, low, background
- `timeout_s` (integer) — 60–7200 seconds
- `write_scope` (string[]) — must be subset of `read_scope`
- `read_scope` (string[]) — paths the worker may read
- `status` (enum) — pending, queued, running, completed, failed, cancelled, timeout

## Scope enforcement rules

1. `write_scope ⊆ read_scope` — HTTP 422 if violated.
2. `worker ∈ registry` — HTTP 422 if unknown.
3. `correlation_id` is required — HTTP 422 if missing.

## Error codes

| Code | Meaning |
|---|---|
| 400 | Schema validation failure |
| 404 | Job not found |
| 409 | Idempotency key conflict or job already terminal |
| 422 | Worker unknown, scope violation, or missing correlation ID |

## Future work

- Persistent store (SQLite/PostgreSQL) instead of in-memory dict
- Authentication and authorization middleware
- Streaming SSE endpoint for real-time job events
- Worker heartbeat and auto-deregistration
- Queue back-pressure and priority scheduling
