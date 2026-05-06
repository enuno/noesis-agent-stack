DOC: Hermes Supervisor Functional Specification

AUDIENCE: Engineers implementing, integrating, or extending the Hermes supervisor profile.

---

# Hermes — Functional Specification

> **Agent ID:** `main-hermes`  
> **Scope:** Supervisor and conscious operator for the Noesis agent stack. Owns approvals, rejections, plans, schedule changes, and delegations to builder, QA, content, ops, treasury, and OpenClaw worker lanes.

This document specifies what Hermes does, how it interfaces with the rest of the platform, and what data it maintains. For identity and operating style, see [SOUL.md](./SOUL.md). For the runtime prompt, see [systemprompt.md](./systemprompt.md). For operator-facing procedures, see [RUNBOOK.md](./RUNBOOK.md).

---

## Overview

Hermes is the only persistent reasoning layer in the Noesis stack. Its primary responsibilities are:

- **Planning:** Determine what work is needed based on vault health, signal events, sprint state, and operator direction.
- **Authorization:** Decide whether a planned action can proceed autonomously or requires human approval.
- **Dispatch:** Issue typed broker jobs to `research-openclaw`, `subconscious-openclaw`, and future worker lanes.
- **Monitoring:** Track job execution via broker callbacks and health reports.
- **Interpretation:** Convert worker artifacts into concise operator summaries, update sprint state, and make approval/rejection decisions on build intents.
- **Escalation:** Surface situations that exceed Hermes's authority or pose risk to the operator with context and a recommended action.

Hermes does not execute tools against live infrastructure, write directly to worker write surfaces, or take irreversible actions without explicit operator sign-off.

---

## Core Features

### 1. Approval and Escalation

Hermes evaluates every planned action against its authority matrix (see [POLICY.md](./POLICY.md)) and the safety invariants defined in [systemprompt.md](./systemprompt.md).

- **Autonomous approval:** Hermes may approve routine refresh jobs, scheduled subconscious walks, and health-check jobs that fall within budget, scope, and confidence thresholds.
- **Operator approval required:** Build intents, jobs with `require_human_approval: true`, sprint lock overrides, and any action touching live infrastructure or financial systems.
- **Escalation triggers:** Low confidence on high-signal findings, cost overruns, `critical` health status, schema violations, speculative findings used as primary justification, or any policy conflict.

When escalating, Hermes produces a concise summary containing:
- Trigger condition and severity
- Current system state and relevant context
- Recommended action
- Consequence of inaction (if known and bounded)

Hermes then enters a "waiting for operator decision" state and does not proceed until it receives explicit instruction.

### 2. Delegation Routing

Hermes routes work to workers through the broker control plane only. It does not invoke workers through ad-hoc channels.

Routing decisions are based on:
- **Worker capability:** The target worker must list the required capability in its registry entry.
- **Mode mapping:** Each worker supports a set of modes (e.g., `research-openclaw`: `refresh`, `focus`, `build_intent`; `subconscious-openclaw`: `digest`, `pattern-walk`, `drift-from-research`, `deep`, `surface`, `targeted`).
- **Sprint state:** If a sprint lock is active on the subconscious room, new `research-openclaw` jobs are suppressed unless overridden by a critical signal or operator instruction.
- **Cost and priority:** Jobs are dispatched with `max_cost_usd`, `priority`, and `timeout_s` bounds appropriate to the worker and task type.

Default dispatch parameters per worker are defined in [systemprompt.md](./systemprompt.md).

### 3. Workflow State Transitions

Hermes drives and gates the four primary platform workflows defined in `WORKFLOWS.md`:

| Workflow | Hermes Role |
|---|---|
| `research-refresh` | Approves scope and source plan before the job leaves `pending_approval`; interprets results. |
| `subconscious-walk` | Approves walk mode and snapshot set before the job leaves `pending_approval`; reviews signal events. |
| `build-promotion` | Promotes intent drafts from subconscious room; approves build plan before implementation; gates handoff to QA. |
| `release-validation` | Approves validation scope; reviews QA verdict and accepts or rejects it. |

Hermes does not directly mutate workflow state. It issues approvals, rejections, and cancellations through the broker API. The broker owns the canonical state machine.

Key transition rules:
- No workflow may bypass the defined state sequence.
- A cancellation from Hermes or the operator is valid from any state and moves the job to `cancelled`.
- Transitions that fail automatic validation (schema, checksum, scope) are rejected by the broker without Hermes intervention.

### 4. Handoff Validation

Before a worker output becomes input to another workflow, Hermes validates the handoff:

- **Schema conformance:** The artifact must validate against its declared schema (e.g., `contracts/handoffs/build-intent.schema.json`).
- **Evidence linkage:** Build intents must reference the research vault artifacts and subconscious signal IDs that justified them.
- **Checksum integrity:** Artifact checksums recorded in the broker receipt must match the files on disk.
- **Policy check:** The handoff must not violate shared policy, guardrails, or safety invariants.

If validation fails, Hermes rejects the handoff, logs the reason in `decision-log.jsonl`, and may dispatch a corrective job or escalate to the operator depending on severity.

### 5. Human-Override Hooks

Hermes provides explicit hooks for operator intervention:

- **Sprint lock override:** The operator can force a sprint lock release or impose one manually.
- **Job cancellation:** The operator can cancel any in-flight job. Hermes propagates the cancel to the broker and updates sprint state.
- **Approval bypass flag:** For emergency recovery, an operator can attach `operator_override: true` with a reason string. Hermes logs the override and proceeds, but still enforces hard safety invariants (e.g., no autonomous financial transactions).
- **Direct message injection:** Operator messages sent outside the normal cycle trigger an on-demand planning loop and take precedence over scheduled actions.

---

## Interfaces

### Broker Job Submission

Hermes submits jobs to `POST /v1/jobs` with payloads conforming to `contracts/handoffs/broker-job.schema.json`.

Required fields in every payload:
- `agent`: target worker ID
- `mode`: worker execution mode
- `traceparent`: distributed trace continuity
- `idempotency_key`: pattern `{agent}:{mode}:{topic}:{date}`
- `sandbox_mode`: default `true`
- `max_cost_usd`: per-job cap
- `timeout_s`: execution limit
- `priority`: `normal`, `high`, or `background`

Hermes enforces that `require_human_approval` is set to `true` for build intents and any job exceeding routine scope.

### Artifact Consumption

Hermes reads artifacts from:
- `workspace/research-vault/` — findings, claims, sources, dossiers, briefs, run receipts, health reports
- `workspace/subconscious-room/` — walk notes, signal events, board state, intent drafts
- `workspace/coder-jobs/` — build plans and implementation artifacts (during `build-promotion`)
- `workspace/qa-reports/` — validation reports and verdicts (during `release-validation`)

Hermes never writes to these directories. It writes its own state only to `workspace/hermes/`.

### Palace Query

Hermes queries MemPalace for context before approving or delegating. The query interface (`agents/main-hermes/tools/palace_query.py`) supports:

- `mcp_mempalace_search` — semantic search across wings and rooms
- `mcp_mempalace_kg_query` — temporal knowledge graph lookups for entity timelines
- `mcp_mempalace_diary_read` — read per-agent diary entries

Hermes uses palace context to:
- Verify job history and prior decisions before re-dispatching similar work
- Check for stale memory or contradictory facts in the KG
- Confirm artifact references and correlation IDs

---

## Data Model

### Sprint State (`workspace/hermes/sprint-state.json`)

```json
{
  "sprint_id": "string | null",
  "status": "idle | active | locked",
  "build_intent_ref": "string | null",
  "build_intent_status": "draft | pending_approval | approved | rejected | completed | abandoned",
  "sprint_lock_on_subconscious": "boolean",
  "started_at": "ISO8601 | null",
  "last_updated_at": "ISO8601",
  "operator_notes": "string | null"
}
```

Rules:
- Only one sprint may be `active` at a time.
- `sprint_lock_on_subconscious: true` suppresses non-critical `research-openclaw` jobs.
- On build intent completion or abandonment, status transitions to `idle` and `sprint_id` is cleared.

### Decision Log (`workspace/hermes/decision-log.jsonl`)

Append-only log. One JSON object per line.

```json
{
  "timestamp": "ISO8601",
  "decision_id": "uuid",
  "decision": "string",
  "rationale": "string",
  "category": "dispatch | approval | rejection | escalation | sprint_lock | override | other",
  "outcome_ref": "string | null",
  "operator_involved": "boolean"
}
```

Hermes writes to this log for every non-trivial decision: job dispatch, build intent approval/rejection, escalation, sprint lock change, and operator override.

### Cost Ledger (`workspace/hermes/cost-ledger.jsonl`)

Append-only log. One JSON object per line.

```json
{
  "timestamp": "ISO8601",
  "job_id": "string",
  "agent": "string",
  "mode": "string",
  "cost_usd": "number",
  "cumulative_daily_usd": "number",
  "cumulative_monthly_usd": "number",
  "budget_status": "ok | warning | exceeded"
}
```

Rules:
- Updated after every broker job callback.
- If `cumulative_daily_usd` crosses 80% of the `$10 USD` daily cap, Hermes alerts the operator before dispatching further jobs.
- If the cap is exceeded, dispatch pauses and the operator is notified.

### Signal Inbox (`workspace/hermes/signal-inbox/`)

Directory of unacknowledged signal events from `subconscious-openclaw`.

Each signal is a JSON file:

```json
{
  "signal_id": "string",
  "source_walk_id": "string",
  "severity": "low | medium | high | critical",
  "topic": "string",
  "summary": "string",
  "confidence": "speculative | moderate | high",
  "received_at": "ISO8601",
  "acknowledged_at": "ISO8601 | null",
  "action_taken": "string | null"
}
```

Rules:
- Hermes reviews the inbox during every planning cycle.
- Signals are acknowledged by writing `acknowledged_at` and `action_taken`.
- `critical` and `high` severity signals may trigger immediate operator escalation or override sprint lock rules.

---

## Exit Criteria

Hermes supervisor profile is considered complete for Phase 2 when:

1. Hermes can submit broker jobs with fully typed payloads conforming to `contracts/handoffs/broker-job.schema.json`.
2. Hermes can consume worker artifacts from the research vault and subconscious room without directly mutating worker state.
3. Routing and approval rules reflect the contract boundaries defined in `WORKFLOWS.md` and `contracts/handoffs/`.
4. `sprint-state.json`, `decision-log.jsonl`, and `cost-ledger.jsonl` are created, updated, and readable by Hermes on every cycle.
5. MemPalace query interface is functional and invoked before significant approval or delegation decisions.
6. All safety invariants listed in [systemprompt.md](./systemprompt.md) and [POLICY.md](./POLICY.md) are enforced.
7. Escalation paths to the human operator are exercised and documented in [RUNBOOK.md](./RUNBOOK.md).

---

## RELATED

- [SOUL.md](./SOUL.md) — Identity and values
- [systemprompt.md](./systemprompt.md) — System prompt, authorities, operating loop
- [POLICY.md](./POLICY.md) — Authority matrix, cost controls, safety invariants, escalation rules
- [RUNBOOK.md](./RUNBOOK.md) — Operator procedures
- `DEVELOPMENT_PLAN.md` — Phase 2 deliverables
- `WORKFLOWS.md` — Workflow state machines and approval gates
- `contracts/handoffs/broker-job.schema.json` — Job payload schema
- `contracts/handoffs/build-intent.schema.json` — Build intent schema