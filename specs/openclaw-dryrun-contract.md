# OpenClaw Dry-Run Execution Contract

**Status:** Draft  
**Priority:** P0  
**Target:** OpenClaw worker action validation before live effect  
**Depends on:** Broker control plane (Phase 1), Hermes supervisor (Phase 2)

---

## Overview

Replace the DreamEngine's "Canary" stage (1–10% real traffic) with a **dry-run execution** mode for infrastructure-acting agents. OpenClaw generates the full action plan, logs it to an append-only audit store, and Hermes reviews it before any live effect is applied.

This is a safety-critical contract: it prevents partial or unsafe ASIC overclocking, cooling setpoint changes, and treasury swap triggers from reaching production without explicit supervisor approval.

---

## Execution Stages (Revised)

| Stage | DreamEngine Name | OpenClaw Name | Live Effect? | Hermes Approval? | Purpose |
|---|---|---|---|---|---|
| 1 | Shadow | Shadow | No | No | Run in pure simulation against world model |
| 2 | Canary | **Dry-Run** | No | No | Generate full action plan, write to audit log, diff against last approved plan |
| 3 | Gradual | **Threshold-Gradual** | Yes, per-action | Per-action | Each action individually approved until anomaly silence period met |
| 4 | Full | Full | Yes | Post-hoc review only | Automatic execution, batched review |

---

## Dry-Run Mode Specification

### Trigger Conditions

Dry-run is **mandatory** when **any** of the following are true:

- Action target is classified as `infra-hardware` (miners, PSUs, cooling loops).
- Action target is classified as `treasury` (swap triggers, hedge adjustments).
- Action's estimated blast radius (§ Blast Radius Calculation) exceeds the worker's configured threshold.
- Worker has not yet completed its anomaly silence period (§ Threshold-Gradual exit criteria).

Dry-run is **optional but recommended** for:

- `infra-software` actions (firmware flashes, config pushes) on first deployment.
- Cross-facility coordinated actions.

### Action Plan Schema

During dry-run, the worker produces a structured action plan:

```json
{
  "plan_id": "uuid",
  "worker_id": "string",
  "worker_ans_identity": "string",
  "generated_at": "ISO-8601",
  "dry_run": true,
  "trigger_context": {
    "dream_id": "uuid | null",
    "goal_id": "string",
    "observed_state_hash": "string"
  },
  "actions": [
    {
      "action_id": "uuid",
      "sequence": 1,
      "target": {
        "resource_type": "asic | cooling | treasury | network | software",
        "resource_id": "string",
        "facility": "string"
      },
      "operation": {
        "type": "set_clock | set_voltage | set_fan | swap | hedge | reboot | flash",
        "parameters": { "...": "..." }
      },
      "estimated_impact": {
        "hashrate_delta_ths": "number | null",
        "power_delta_kw": "number | null",
        "thermal_delta_c": "number | null",
        "financial_exposure_usd": "number | null"
      },
      "rollback_procedure": {
        "automatic": "boolean",
        "steps": ["string"]
      },
      "blast_radius_score": "number (0.0–1.0)"
    }
  ],
  "plan_summary": {
    "total_actions": 1,
    "max_blast_radius_score": 0.85,
    "aggregate_financial_exposure_usd": 0,
    "estimated_execution_time_seconds": 120
  },
  "diff_against_last_approved": {
    "last_approved_plan_id": "uuid | null",
    "actions_added": 1,
    "actions_removed": 0,
    "actions_modified": 0,
    "parameter_drift": { "...": "..." }
  }
}
```

### Audit Store Contract

Every dry-run plan is appended to an **immutable, sequenced audit log**:

- **Backend:** Append-only stream (Kafka topic or Redpanda stream `openclaw.dryrun.audit`).
- **Retention:** 7 years for treasury actions, 2 years for hardware actions.
- **Integrity:** Each entry is signed by the worker's ANS identity key. Broker verifies signature before appending.
- **Indexing:** Queryable by `plan_id`, `worker_id`, `resource_id`, `generated_at` range.

**Log entry format:**
```json
{
  "sequence_number": 18446744073709551615,
  "plan_id": "uuid",
  "worker_ans_identity": "string",
  "plan_hash_sha256": "string",
  "signature": "string",
  "appended_at": "ISO-8601",
  "broker_id": "string"
}
```

---

## Threshold-Gradual Stage

### Entry Criteria

A worker transitions from Dry-Run to Threshold-Gradual when:

1. At least **10 dry-run plans** have been generated for the same `goal_id`.
2. The **last 10 plans** have a diff similarity ≥ 95% against the first dry-run plan (stability check).
3. No dry-run plan in the last 10 has exceeded the `max_blast_radius_score` threshold.
4. Hermes has explicitly approved the transition via `broker.approve_worker_stage(worker_id, 'threshold_gradual')`.

### Per-Action Approval

In Threshold-Gradual, each action is held in a **pending queue**:

- Action is submitted to the broker with `approval_status: pending`.
- Hermes has `approval_timeout_seconds` (default: 300) to review.
- If Hermes approves, the action executes and the result is logged.
- If Hermes rejects, the action is dropped and the worker receives a `REJECTED` signal.
- If timeout expires, the action is **rejected by default** (fail-closed).

### Exit Criteria to Full

A worker transitions to Full when:

1. At least **50 actions** have been approved and executed in Threshold-Gradual.
2. Zero rejections in the last 25 actions.
3. Zero anomaly alerts (from reality drift detection) in the last 48 hours.
4. Anomaly silence period of 24 hours has elapsed since the last rejection or anomaly.
5. Hermes explicit approval.

---

## Blast Radius Calculation

Each action carries a `blast_radius_score` computed by the worker before dry-run output:

```python
def compute_blast_radius(action) -> float:
    score = 0.0
    if action.target.resource_type == "asic":
        score += 0.3 * normalize(action.operation.parameters.get("clock_delta_mhz", 0), max=500)
        score += 0.3 * normalize(action.operation.parameters.get("voltage_delta_mv", 0), max=100)
    if action.target.resource_type == "cooling":
        score += 0.2 * normalize(action.operation.parameters.get("setpoint_delta_c", 0), max=10)
    if action.target.resource_type == "treasury":
        score += 0.4 * normalize(action.estimated_impact.financial_exposure_usd, max=1_000_000)
    if not action.rollback_procedure.automatic:
        score += 0.2
    return min(score, 1.0)
```

**Thresholds:**
- `score < 0.3`: Low — may skip dry-run if worker is already in Full stage.
- `0.3 ≤ score < 0.7`: Medium — always dry-run.
- `score ≥ 0.7`: High — dry-run + Hermes mandatory review even in Full stage.

---

## Hermes Review Interface

Hermes reviews dry-run plans via the broker's MCP tool:

### `openclaw.review_dryrun_plan`

**Input:**
```json
{
  "plan_id": "uuid",
  "decision": "approve | reject | modify",
  "modifications": [
    {
      "action_id": "uuid",
      "override_parameters": { "...": "..." },
      "skip": false
    }
  ] | null,
  "review_comment": "string | null"
}
```

**Behavior:**
- `approve`: plan transitions to executable; actions are released to the worker queue.
- `reject`: plan is discarded; worker receives `REJECTED` and must regenerate.
- `modify`: Hermes edits parameters inline; modified plan is re-signed by broker and appended to audit log as a new entry.

---

## Failure Modes

| Scenario | Response |
|---|---|
| Worker generates dry-run plan but audit store is unreachable | Halt execution; worker enters `DEGRADED` state; alert Hermes |
| Hermes review times out | Fail-closed: reject plan |
| Worker ANS signature invalid | Broker drops plan; worker banned until re-authenticated |
| Blast radius calculation overflows or NaN | Treat as `score = 1.0` (high) and force dry-run |
| Action executed without matching approved plan | Emergency halt of worker; forensic audit triggered |

---

## Open Questions

- Should dry-run plans include estimated P&L for treasury actions?
- How do we handle rollback when an action is partially applied (e.g., 2 of 5 ASICs reclocked before thermal trip)?
- Should the audit store be replicated across facilities for disaster recovery?
