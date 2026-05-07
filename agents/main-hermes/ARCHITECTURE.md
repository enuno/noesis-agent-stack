# main-hermes Supervisor Runtime Architecture

## Overview

The main-hermes supervisor is a reasoning layer that reads signals, evaluates authority, resolves routes, applies approval gates, dispatches jobs to the broker, and monitors outcomes. It does **not** execute tools on live infrastructure or write to worker surfaces.

## Design Principles

1. **Supervisor Isolation** — Hermes holds context and coordinates; workers execute.
2. **Broker as Sole Control Plane** — All worker dispatch goes through the broker REST API.
3. **Atomic State** — All writes are atomic (temp file → fsync → rename).
4. **Append-Only Ledgers** — Decision logs, cost ledgers, and signal inboxes are JSONL.
5. **Stdlib Only** — No third-party dependencies in the supervisor runtime.

## Module Map

| Module | Purpose |
|---|---|
| `scripts/lib/schemas.py` | Lightweight JSON schema validation (stdlib only). |
| `scripts/lib/routing.py` | Parse `platform/routing.yaml`, resolve routes via override → default → fallback chain. |
| `scripts/lib/approval.py` | Authority matrix (autonomous / escalate / forbidden) and cumulative cost tracking. |
| `scripts/lib/state.py` | Atomic sprint state, decision log, cost ledger, signal inbox. |
| `scripts/lib/workflows.py` | Load workflow YAMLs, validate transitions, lookup approval gates. |
| `scripts/lib/broker_client.py` | Typed `urllib`-based broker REST client with retry. |
| `scripts/init_state.py` | CLI to initialize `workspace/hermes/` state files. |
| `scripts/hermes_cycle.py` | Main planning/dispatch loop. |

## Data Flow

```
Signal Inbox (JSONL)
    |
    v
hermes_cycle.py
    |
    +-- routing.resolve(objective, payload) --> RouteRule
    |
    +-- approval.evaluate(action, payload, cost) --> (level, reason)
    |       FORBIDDEN  -> log, block
    |       ESCALATE   -> log, emit escalation event
    |       AUTONOMOUS -> continue
    |
    +-- broker_client.submit_job(BrokerJob) --> BrokerResponse
    |
    +-- state.log_decision(record)
    +-- state.save_sprint(sprint)
```

## Routing Resolution

Priority chain (hard-coded in `RoutingTable.resolve`):

1. **override_rules** — exact or regex match on `objective`
2. **default_rules** — exact or regex match
3. **fallback** — catch-all rule

The routing YAML parser is line-based and handles the tabular structure used in `platform/routing.yaml` without requiring a full YAML parser.

## Authority Matrix

Encoded in `ApprovalEngine._default_matrix()`:

| Pattern | Level |
|---|---|
| `research.*` | AUTONOMOUS |
| `read.*` | AUTONOMOUS |
| `tool.local.*` | AUTONOMOUS |
| `build.*` | ESCALATE |
| `qa.*` | ESCALATE |
| `deploy.*` | ESCALATE |
| `override.*` | ESCALATE |
| `cancel.*` | ESCALATE |
| `admin.*` | FORBIDDEN |

Additional hard-coded forbidden checks:
- Any action containing `vault.write`, `vault.delete`, `financial.transfer`, `capability.escalate`, `secret.expose`
- Any payload path containing `vault` combined with write/delete actions

Cost controls:
- Default sprint limit: $50 USD / 500k tokens
- Escalation trigger at 80% of either limit
- All costs logged to `cost_ledger.jsonl`

## Workflow Bindings

`WorkflowBinding` wraps a loaded `WorkflowDef` and tracks current state + history.

Key operations:
- `allowed_transitions(from_state)` — list valid transitions
- `can_transition(to_state)` — check if a transition is valid
- `transition(to_state)` — apply transition, update history

Workflow YAMLs are parsed with a line-based parser that extracts states, transitions, approval gates, timeouts, and retry policies.

## Broker Client

`BrokerClient` uses `urllib.request` with:
- Configurable timeout (default 30s)
- Exponential backoff retry (default 3 retries, 2s base)
- Automatic retry on 5xx and 429
- Typed `BrokerJob` dataclass matching `broker-job.schema.json`

Endpoints implemented:
- `GET /health`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs?status={status}`
- `POST /v1/jobs/{job_id}/cancel`

## State Management

`StateManager` owns the `workspace/hermes/` directory:

| File | Format | Purpose |
|---|---|---|
| `sprint_state.json` | JSON | Active/completed/failed job lists, timestamps. |
| `decision_log.jsonl` | JSONL | Every authority evaluation result. |
| `cost_ledger.jsonl` | JSONL | Every cost event (USD, tokens, job_id). |
| `signal_inbox.jsonl` | JSONL | Incoming signal events with processed flag. |

All writes are atomic via `tempfile.mkstemp` + `os.replace`.

## Main Loop (`hermes_cycle.py`)

```
1. Read unprocessed signals from inbox.
2. For each signal:
   a. Resolve route.
   b. Evaluate authority.
   c. If FORBIDDEN -> log, skip.
   d. If ESCALATE -> log, skip (await operator).
   e. If AUTONOMOUS -> build BrokerJob, submit to broker.
   f. Mark signal processed.
3. Monitor active jobs via broker GET.
4. Update sprint state.
```

Run modes:
- `--once` — single cycle, then exit.
- Continuous — sleep 30s between cycles (configurable via `--interval`).

## Safety Invariants

1. No direct vault writes — broker-only, via typed jobs.
2. No autonomous irreversible actions — all builds/QA/deploys escalate.
3. No capability escalation — forbidden pattern blocks.
4. Speculative findings not actionable — research outputs require validation workflow.
5. Sprint lock is a hard gate — 80% cost threshold triggers escalation.
6. Approval bypass is logged — every evaluation writes to decision log.
7. Broker is sole worker control plane — no out-of-band worker access.

## Future Work

- Integrate with actual broker API once orchestration layer is live.
- Add async signal ingestion from filesystem watchers or webhooks.
- Implement operator escalation UI (human-in-the-loop approval).
- Add metrics export (prometheus-style) for cost and queue depth.
