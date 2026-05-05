# WORKFLOWS — State Transition Definitions

> Typed workflow definitions for the noesis-agent-stack platform. Each workflow specifies its trigger, states, transitions, and approval gates so that Hermes Main can route, broker can execute, and QA can validate against a single source of truth.

## Workflow summary

| Workflow | Purpose | Primary actors |
|---|---|---|
| `research-refresh` | Collect, score, and preserve evidence in the research vault | Hermes Main, broker, Research (OpenClaw) |
| `subconscious-walk` | Traverse room memory, emit signals, and update the signal board | Hermes Main, broker, Subconscious (OpenClaw) |
| `build-promotion` | Advance an approved intent through plan, code, and artifact handoff | Hermes Main, broker, Coder, MemPalace |
| `release-validation` | Verify build artifacts against evidence, schema, and policy before release | Hermes Main, broker, QA, MemPalace |

---

## 1. research-refresh

### Purpose
Run a bounded evidence collection cycle, normalize findings, and write durable artifacts to the research vault.

### Trigger
- **Scheduled**: Cron or interval defined in `platform/schedules/research.yaml`
- **Manual**: Hermes Main submits a typed refresh job via broker API
- **Event-driven**: Subconscious signal board requests updated research snapshot for a topic

### States

```
[ idle ]
  |
  | trigger: schedule / manual / event
  v
[ pending_approval ]
  |
  | Hermes Main approves scope and source plan
  v
[ queued ]
  |
  | broker assigns worker and enforces scopes
  v
[ collecting ]
  |
  | worker executes bounded source plan
  v
[ normalizing ]
  |
  | findings scored, claims promoted, sources linked
  v
[ writing_vault ]
  |
  | artifacts persisted to workspace/research-vault/
  v
[ checkpoint ]
  |
  | HEARTBEAT checkpoint save every 15 exchanges
  v
[ validating ]
  |
  | structural validation against schemas
  v
[ completed ]
  |
  | EOS save, handoff eligibility determined
  v
[ archived ]
```

### Transitions

| From | To | Condition | Auto or Gate |
|---|---|---|---|
| `idle` | `pending_approval` | Trigger received | Auto |
| `pending_approval` | `queued` | Hermes Main approves scope and source plan | Approval gate: Hermes Main |
| `pending_approval` | `rejected` | Scope too broad, source plan missing, or policy conflict | Approval gate: Hermes Main |
| `queued` | `collecting` | Worker assigned and healthy | Auto |
| `queued` | `failed` | Worker unavailable after timeout | Auto |
| `collecting` | `normalizing` | Source plan complete or bounded limit reached | Auto |
| `collecting` | `checkpoint` | 15 exchanges reached | Auto (HEARTBEAT) |
| `checkpoint` | `collecting` | Checkpoint saved successfully | Auto |
| `normalizing` | `writing_vault` | Normalization pass complete | Auto |
| `writing_vault` | `validating` | All artifacts written | Auto |
| `validating` | `completed` | Schema and integrity checks pass | Auto |
| `validating` | `failed` | Schema mismatch or integrity failure | Auto |
| `completed` | `archived` | EOS save complete and retention policy applied | Auto |
| any | `cancelled` | Hermes Main or operator issues cancel | Approval gate: Hermes Main or operator override |

### Approval gates

1. **Scope approval**: Hermes Main must approve the source plan and read/write scopes before the job leaves `pending_approval`.
2. **Claim promotion**: No finding may be promoted to a claim without passing the threshold defined in `agents/research-openclaw/config/thresholds.yaml`.
3. **Vault write approval**: Research worker cannot write outside `workspace/research-vault/`. Broker enforces this at the runtime level.

---

## 2. subconscious-walk

### Purpose
Consume research snapshots and room memory, perform a bounded reflective walk, and emit signal events or intent drafts without executing them.

### Trigger
- **Scheduled**: Cron or interval defined in `platform/schedules/subconscious.yaml`
- **Manual**: Hermes Main submits a walk job via broker API
- **Event-driven**: Research vault update produces a new snapshot flagged for subconscious inbox

### States

```
[ idle ]
  |
  | trigger: schedule / manual / event
  v
[ pending_approval ]
  |
  | Hermes Main approves walk mode and snapshot set
  v
[ queued ]
  |
  | broker assigns worker and enforces scopes
  v
[ reading_inbox ]
  |
  | worker loads research snapshots and prior room state
  v
[ walking ]
  |
  | worker traverses room, notes patterns, scores fascinations
  v
[ checkpoint ]
  |
  | HEARTBEAT checkpoint save every 15 exchanges
  v
[ filtering ]
  |
  | signals scored against thresholds; weak signals dropped
  v
[ updating_board ]
  |
  | signal board state updated; intent drafts written
  v
[ drafting_intent ]
  |
  | build intents composed for signals that exceed threshold
  v
[ completed ]
  |
  | EOS save; intents remain drafts awaiting Hermes review
  v
[ archived ]
```

### Transitions

| From | To | Condition | Auto or Gate |
|---|---|---|---|
| `idle` | `pending_approval` | Trigger received | Auto |
| `pending_approval` | `queued` | Hermes Main approves walk mode and snapshot set | Approval gate: Hermes Main |
| `pending_approval` | `rejected` | Snapshot set unavailable or policy conflict | Approval gate: Hermes Main |
| `queued` | `reading_inbox` | Worker assigned and healthy | Auto |
| `queued` | `failed` | Worker unavailable after timeout | Auto |
| `reading_inbox` | `walking` | Inbox loaded successfully | Auto |
| `walking` | `checkpoint` | 15 exchanges reached | Auto (HEARTBEAT) |
| `checkpoint` | `walking` | Checkpoint saved successfully | Auto |
| `walking` | `filtering` | Walk bounded limit reached or room fully traversed | Auto |
| `filtering` | `updating_board` | Filter pass complete | Auto |
| `updating_board` | `drafting_intent` | Board state persisted | Auto |
| `drafting_intent` | `completed` | Intent drafts written to room | Auto |
| `completed` | `archived` | EOS save complete | Auto |
| any | `cancelled` | Hermes Main or operator issues cancel | Approval gate: Hermes Main or operator override |

### Approval gates

1. **Walk mode approval**: Hermes Main must approve the walk mode (`deep`, `surface`, `targeted`) and the snapshot set before the job leaves `pending_approval`.
2. **Signal threshold**: Subconscious may not alter its own thresholds to force promotion. Thresholds are read from `agents/subconscious-openclaw/config/thresholds.yaml` and enforced by broker read scopes.
3. **Intent draft gate**: Intent drafts are NOT approved tasks. They MUST remain in `workspace/subconscious-room/intents/` and MUST NOT trigger builds until Hermes Main promotes them through the `build-promotion` workflow.

---

## 3. build-promotion

### Purpose
Advance an approved build intent through planning, implementation, and artifact production. This is the only workflow that produces production code.

### Trigger
- **Manual**: Hermes Main promotes an intent draft from the subconscious room after review
- **Event-driven**: Approved plan from a previous build cycle requires next-phase execution (e.g., merge, deploy, doc update)
- **Scheduled**: Recurring maintenance or dependency update job approved in prior session

### States

```
[ idle ]
  |
  | trigger: Hermes promotion / event / schedule
  v
[ pending_approval ]
  |
  | Hermes Main approves plan and assigns Coder scope
  v
[ plan_drafting ]
  |
  | Coder or Hermes composes typed build plan from handoff
  v
[ plan_review ]
  |
  | Hermes Main reviews plan against evidence and policy
  v
[ queued ]
  |
  | broker assigns Coder worker and enforces write scopes
  v
[ implementing ]
  |
  | Coder executes build plan, writes artifacts to coder-jobs/
  v
[ checkpoint ]
  |
  | HEARTBEAT checkpoint save every 15 exchanges
  v
[ self_verifying ]
  |
  | Coder runs unit tests, lint, type-check per plan
  v
[ handoff_prep ]
  |
  | artifacts packaged, checksums computed, schema validated
  v
[ awaiting_qa ]
  |
  | handoff queued for release-validation workflow
  v
[ completed ]
  |
  | EOS save; artifacts await QA gate
  v
[ archived ]
```

### Transitions

| From | To | Condition | Auto or Gate |
|---|---|---|---|
| `idle` | `pending_approval` | Trigger received | Auto |
| `pending_approval` | `plan_drafting` | Hermes Main approves intent and assigns Coder | Approval gate: Hermes Main |
| `pending_approval` | `rejected` | Intent lacks evidence, plan violates policy, or scope unsafe | Approval gate: Hermes Main |
| `plan_drafting` | `plan_review` | Build plan written to `workspace/coder-jobs/<job_id>/plan/` | Auto |
| `plan_review` | `queued` | Hermes Main approves plan | Approval gate: Hermes Main |
| `plan_review` | `plan_drafting` | Plan rejected with revision notes | Approval gate: Hermes Main |
| `queued` | `implementing` | Coder assigned and healthy | Auto |
| `queued` | `failed` | Coder unavailable after timeout | Auto |
| `implementing` | `checkpoint` | 15 exchanges reached | Auto (HEARTBEAT) |
| `checkpoint` | `implementing` | Checkpoint saved successfully | Auto |
| `implementing` | `self_verifying` | Code complete per plan | Auto |
| `self_verifying` | `handoff_prep` | Self-verify passes (tests, lint, type-check) | Auto |
| `self_verifying` | `failed` | Self-verify fails and retry limit reached | Auto |
| `handoff_prep` | `awaiting_qa` | Handoff schema validates, checksums recorded | Auto |
| `awaiting_qa` | `completed` | Release-validation workflow accepts handoff | Approval gate: QA via release-validation |
| `awaiting_qa` | `failed` | Release-validation workflow rejects handoff | Approval gate: QA via release-validation |
| `completed` | `archived` | EOS save complete and QA gate passed | Auto |
| any | `cancelled` | Hermes Main or operator issues cancel | Approval gate: Hermes Main or operator override |

### Approval gates

1. **Intent promotion**: Hermes Main must explicitly promote an intent draft from `subconscious-room/` into a build job. Subconscious signals cannot directly enter `build-promotion`.
2. **Plan approval**: Hermes Main must approve the typed build plan before implementation begins. Coder may not self-approve its own plan.
3. **Handoff eligibility**: The handoff schema (`contracts/handoffs/build-plan.schema.json`) must validate, and all artifacts must have matching checksums, before the job may enter `awaiting_qa`.
4. **QA gate**: `release-validation` workflow must accept the handoff before the build is considered complete. Coder cannot skip QA.

---

## 4. release-validation

### Purpose
Audit build artifacts against evidence, schema, policy, and operational readiness before release or merge.

### Trigger
- **Event-driven**: `build-promotion` workflow enters `awaiting_qa` state
- **Manual**: Hermes Main or operator submits artifacts for ad-hoc validation
- **Scheduled**: Recurring validation sweep of pending or recently completed builds

### States

```
[ idle ]
  |
  | trigger: build event / manual / schedule
  v
[ pending_approval ]
  |
  | Hermes Main or operator approves validation scope
  v
[ queued ]
  |
  | broker assigns QA worker and enforces read scopes
  v
[ ingesting ]
  |
  | QA loads build artifacts, plan, evidence trail, and policy
  v
[ schema_check ]
  |
  | artifact schemas, handoff schemas, and checksums verified
  v
[ contradiction_check ]
  |
  | evidence trail checked for contradictions, stale claims, broken links
  v
[ policy_check ]
  |
  | build checked against shared policy, guardrails, and safety model
  v
[ checkpoint ]
  |
  | HEARTBEAT checkpoint save every 15 exchanges
  v
[ test_execution ]
  |
  | integration tests, replay tests, and failure injection if applicable
  v
[ verdict_drafting ]
  |
  | QA composes validation report with verdict and blocking issues
  v
[ verdict_review ]
  |
  | Hermes Main reviews QA verdict
  v
[ accepted ]
  |
  | build approved for release/merge
  v
[ rejected ]
  |
  | build blocked; issues logged; return to Coder or close
  v
[ archived ]
```

### Transitions

| From | To | Condition | Auto or Gate |
|---|---|---|---|
| `idle` | `pending_approval` | Trigger received | Auto |
| `pending_approval` | `queued` | Hermes Main or operator approves validation scope | Approval gate: Hermes Main or operator |
| `pending_approval` | `rejected` | Validation scope undefined or policy prohibits | Approval gate: Hermes Main |
| `queued` | `ingesting` | QA assigned and healthy | Auto |
| `queued` | `failed` | QA worker unavailable after timeout | Auto |
| `ingesting` | `schema_check` | Artifacts and evidence loaded | Auto |
| `schema_check` | `contradiction_check` | All schemas validate, checksums match | Auto |
| `schema_check` | `rejected` | Schema mismatch or checksum failure | Auto |
| `contradiction_check` | `policy_check` | No contradictions detected, or contradictions documented and waived | Auto |
| `contradiction_check` | `rejected` | Unresolvable contradiction in evidence trail | Auto |
| `policy_check` | `test_execution` | Policy checks pass | Auto |
| `policy_check` | `rejected` | Policy violation (safety, scope, secret exposure) | Auto |
| `test_execution` | `checkpoint` | 15 exchanges reached | Auto (HEARTBEAT) |
| `checkpoint` | `test_execution` | Checkpoint saved successfully | Auto |
| `test_execution` | `verdict_drafting` | Tests complete | Auto |
| `test_execution` | `rejected` | Test failure and retry limit reached | Auto |
| `verdict_drafting` | `verdict_review` | Report written to `workspace/qa-reports/<job_id>/` | Auto |
| `verdict_review` | `accepted` | Hermes Main accepts QA verdict | Approval gate: Hermes Main |
| `verdict_review` | `rejected` | Hermes Main rejects or requests re-validation | Approval gate: Hermes Main |
| `accepted` | `archived` | EOS save complete; build cleared for release | Auto |
| `rejected` | `archived` | EOS save complete; issues preserved for retry or audit | Auto |
| any | `cancelled` | Hermes Main or operator issues cancel | Approval gate: Hermes Main or operator override |

### Approval gates

1. **Scope approval**: Hermes Main or an authorized operator must approve what is being validated and against which policy version.
2. **Schema gate**: All artifacts must conform to their declared schemas and checksums must match. This is automatic but blocking.
3. **Contradiction gate**: QA must flag stale claims, broken source links, or evidence that contradicts the build justification. Unresolved contradictions block acceptance.
4. **Policy gate**: Safety model violations (e.g., secret exposure, unauthorized external call, scope creep) result in automatic rejection.
5. **Verdict gate**: Hermes Main must explicitly accept or reject the QA verdict. QA cannot self-release.

---

## Cross-workflow integrity rules

1. **No bypass**: A build intent MUST pass through `build-promotion` and `release-validation` before any production merge or deploy. There is no fast path.
2. **Evidence linkage**: Every `build-promotion` handoff MUST reference the research vault artifacts and subconscious signal IDs that justified it. QA validates this linkage.
3. **State isolation**: Workflow state transitions are owned by the broker. Agents report outcomes; they do not directly mutate workflow state.
4. **Replayability**: Every transition MUST leave a receipt in the broker event log and a corresponding drawer in MemPalace.
