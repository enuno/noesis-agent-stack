# Phase 2 Gap Report: main-hermes Supervisor

## Status
All Python modules pass `py_compile`. Workspace initializes.
However, the implementation diverges from SPEC.md and POLICY.md in several areas.

## Critical Gaps

### 1. Sprint State Schema Mismatch
**SPEC requires:**
- `status`: idle | active | locked
- `build_intent_ref`, `build_intent_status`
- `sprint_lock_on_subconscious: boolean`
- `started_at`, `last_updated_at`, `operator_notes`

**Current:** `SprintState` has `active_jobs`, `completed_jobs`, `failed_jobs` but lacks build-intent fields and sprint-lock flag.
**Impact:** Cannot enforce sprint-lock safety invariant (POLICY §5).

### 2. Decision Log Schema Mismatch
**SPEC requires:** `decision_id`, `decision`, `rationale`, `category`, `outcome_ref`, `operator_involved`
**Current:** Simple dict with `timestamp` injected; no structured schema.
**Impact:** Decisions are not queryable by category or linked to outcomes.

### 3. Cost Ledger Schema Mismatch + Wrong Cap
**SPEC requires:** `agent`, `mode`, `cost_usd`, `cumulative_daily_usd`, `cumulative_monthly_usd`, `budget_status`
**POLICY requires:** Daily cap $10.00 USD, warning at 80% ($8.00)
**Current:** Only `job_id`, `usd`, `tokens`, `note`. Cap is hard-coded $50.00.
**Impact:** Cost overrun detection is non-compliant.

### 4. Signal Inbox Format Mismatch
**SPEC requires:** Directory `signal_inbox/` with JSON files containing `severity`, `topic`, `summary`, `confidence`, `acknowledged_at`, `action_taken`
**Current:** Single JSONL file `signal_inbox.jsonl` with `source`, `event_type`, `payload`, `processed` boolean.
**Impact:** Inbox structure does not match signal-event.schema.json contract.

### 5. BrokerJob Dataclass Missing Fields
**Schema requires:** `schema_version`, `issued_at`, `issued_by`, `context`, `denied_capabilities`, `priority`, `idempotency_key`
**Current:** Missing all of the above. `hermes_cycle.py` builds incomplete jobs.
**Impact:** Broker will reject payloads or they will fail schema validation.

### 6. Routing Does Not Parse routing.yaml Structure
**Current:** Resolves by `objective` string against hard-coded/regex rules.
**Required:** Should match `signal_type` against `trigger_conditions` from `platform/routing.yaml` override_rules / default_rules / fallback chain.
**Impact:** Router is decoupled from the authoritative routing table.

### 7. Approval Engine Missing Policy Features
- No `operator_override` handling (POLICY §6)
- No `category` tagging on decisions
- No escalation record structure
- No capability registry validation (POLICY §3: cannot escalate capabilities)
- No speculative-finding blocker (POLICY §4)

### 8. Missing Palace Query Tool
**SPEC requires:** `agents/main-hermes/tools/palace_query.py` for semantic search, KG lookup, diary read before significant decisions.
**Current:** Does not exist.

### 9. Workflow Bindings Not Integrated into Cycle
**Current:** `hermes_cycle.py` loads workflows but never consults them during dispatch.
**Required:** Should check `approval_required` from routing rule and enforce workflow state transitions via broker.

## Recommended Fix Priority
1. Fix cost cap ($10) and cost ledger schema
2. Align SprintState with SPEC
3. Add missing BrokerJob fields
4. Enhance approval engine with operator_override and categories
5. Create palace_query.py skeleton
6. Align signal inbox format (or update SPEC to match JSONL — needs decision)
7. Wire routing.yaml parser into routing.py
8. Integrate workflow gates into hermes_cycle.py
