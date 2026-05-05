# DreamScheduler MCP Tool Specification

**Status:** Draft  
**Priority:** P0  
**Target:** Hermes → OpenClaw dream governance  
**Depends on:** Broker control plane (Phase 1), Hermes supervisor (Phase 2)

---

## Overview

Expose the DreamEngine scheduler as an MCP tool suite registered with Hermes. This makes dream lifecycle control a first-class Hermes capability rather than a peer service with flat priorities.

---

## Tool Registry

### `dream_scheduler.trigger_micro_dream`

Trigger an immediate micro-dream (consolidation cycle) on a specific OpenClaw worker or worker pool.

**Input Schema:**
```json
{
  "worker_id": "string | 'pool:<pool_name>'",
  "priority": "critical | high | normal | low",
  "context": {
    "trigger_reason": "string",
    "goal_id": "string | null",
    "max_gpu_seconds": "number | null",
    "max_cost_usd": "number | null"
  },
  "interrupt_token": "string | null"
}
```

**Output Schema:**
```json
{
  "dream_id": "uuid",
  "status": "queued | running | rejected",
  "reason": "string | null",
  "estimated_completion": "ISO-8601 | null"
}
```

**Behavior:**
- If a dream is already running on the target worker and the new request has higher `priority`, the running dream is checkpointed and yielded (see `pause_dream`).
- If priority is equal or lower, the request is queued.
- `interrupt_token` is an opaque handle that Hermes can later use to suspend this specific dream.

---

### `dream_scheduler.pause_dream`

Gracefully checkpoint and suspend an active dream.

**Input Schema:**
```json
{
  "dream_id": "uuid",
  "checkpoint": "boolean = true",
  "resume_token_ttl_seconds": "number = 3600"
}
```

**Output Schema:**
```json
{
  "dream_id": "uuid",
  "status": "paused | completed | not_found",
  "checkpoint_path": "string | null",
  "resume_token": "string | null"
}
```

**Behavior:**
- If `checkpoint: true`, the world model latent state and policy replay buffer are serialized to `checkpoint_path`.
- A `resume_token` is returned that can be passed to `trigger_micro_dream` to resume from checkpoint.
- If the dream has already completed, status is `completed` and no token is issued.

---

### `dream_scheduler.get_dream_status`

Poll status of a specific dream or list active dreams on a worker.

**Input Schema:**
```json
{
  "dream_id": "uuid | null",
  "worker_id": "string | null",
  "pool_name": "string | null"
}
```

**Output Schema:**
```json
{
  "dreams": [
    {
      "dream_id": "uuid",
      "worker_id": "string",
      "status": "queued | running | paused | completed | failed",
      "priority": "critical | high | normal | low",
      "progress_percent": "number | null",
      "started_at": "ISO-8601 | null",
      "estimated_completion": "ISO-8601 | null"
    }
  ]
}
```

**Behavior:**
- At least one of `dream_id`, `worker_id`, or `pool_name` must be provided.
- Returns up to 50 most recent dreams if filtered by worker/pool.

---

### `dream_scheduler.set_dream_budget`

Set per-worker or per-pool resource budgets for dream execution.

**Input Schema:**
```json
{
  "target": {
    "worker_id": "string | null",
    "pool_name": "string | null",
    "global": "boolean = false"
  },
  "budget": {
    "max_gpu_seconds_per_hour": "number | null",
    "max_cost_usd_per_day": "number | null",
    "max_concurrent_dreams": "number | null",
    "dream_ratio_cap": "number | null"
  }
}
```

**Output Schema:**
```json
{
  "applied": "boolean",
  "previous_budget": "object | null",
  "effective_at": "ISO-8601"
}
```

**Behavior:**
- `global: true` applies to all workers unless overridden by a worker-specific budget.
- Budget changes take effect immediately for queued dreams; running dreams are not interrupted unless the new budget would be exceeded.
- `dream_ratio_cap` clamps the DreamEngine's dream-to-real ratio (e.g., 1024:1 max).

---

## HermesInterruptToken Mechanism

Every dream pipeline run must accept an `interrupt_token` injected by the broker before execution. The token is a lightweight JSON object:

```json
{
  "token_id": "uuid",
  "issued_by": "hermes",
  "issued_at": "ISO-8601",
  "action": "none | pause | abort",
  "action_set_at": "ISO-8601 | null",
  "checkpoint_on_pause": "boolean = true"
}
```

**Polling contract:**
- The Prefect `dream_pipeline` must poll the broker's token endpoint every 30 seconds.
- If `action` transitions to `pause`, the pipeline enters checkpoint-and-yield within 60 seconds.
- If `action` is `abort`, the pipeline terminates without checkpoint (emergency stop).
- Hermes sets `action` via the broker's job control API, which forwards to the worker's local interrupt file (e.g., `/tmp/dream_interrupt_<token_id>.json`).

---

## Error Codes

| Code | Meaning | Retryable |
|---|---|---|
| `DREAM_WORKER_OFFLINE` | Target worker is not heartbeating | Yes (exponential backoff) |
| `DREAM_ALREADY_RUNNING` | Worker is busy and new priority ≤ current | Yes (queue) |
| `DREAM_CHECKPOINT_FAILED` | Latent state serialization failed | No — requires operator review |
| `DREAM_BUDGET_EXCEEDED` | Budget would be exceeded by this request | No — adjust budget or wait |
| `DREAM_INVALID_TOKEN` | Resume or interrupt token not found | No |

---

## Integration with Broker

The broker exposes these tools to Hermes via its native MCP server. Under the hood:

1. Hermes calls `dream_scheduler.*` → broker MCP server.
2. Broker validates the call against the worker's registered capabilities.
3. Broker translates to OpenClaw worker gRPC/HTTP API.
4. Worker executes and streams status back to broker.
5. Broker caches last-known status for `get_dream_status` polling.

**Authorization:** Hermes must present its ANS identity attestation on every call. The broker rejects unsigned scheduler commands.

---

## Open Questions

- Should `trigger_micro_dream` support bulk targeting (e.g., all workers in a facility)?
- What is the SLA for checkpoint-and-yield on a worker under full GPU load?
- Should budget enforcement be soft (warn + log) or hard (reject + kill)?
