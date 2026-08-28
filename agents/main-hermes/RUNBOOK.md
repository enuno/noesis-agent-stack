DOC: Hermes Operator Runbook

AUDIENCE: Human operators running the Noesis agent stack. Assumes familiarity with the platform layout and basic broker operations.

---

# Hermes — Runbook

> **Agent ID:** `main-hermes`  
> **Purpose:** Step-by-step procedures for common operator actions and incident response.

Before using this runbook, confirm that:
- The broker control plane is running (`orchestration/broker/`).
- MemPalace is initialized and queryable.
- `workspace/hermes/` exists and is writable.
- You have read access to `agents/main-hermes/POLICY.md` and `agents/main-hermes/SPEC.md`.

---

## Starting a Sprint

A sprint begins when Hermes promotes a build intent from the subconscious room and the operator approves it.

1. **Review the build intent.**
   - Hermes will present a concise summary: objective, rationale, acceptance criteria, estimated cost, and risks.
   - The intent document is located at `workspace/research-vault/build-intents/<intent_id>.json`.
   - Validate it against `contracts/handoffs/build-intent.schema.json` if you want to inspect it directly.

2. **Approve or reject.**
   - If rejecting: reply with a reason. Hermes writes the rejection to `workspace/hermes/build-intent-log.jsonl` and notifies research context for the next run.
   - If approving: reply with explicit approval. Hermes will declare a sprint lock.

3. **Confirm sprint lock.**
   - Check `workspace/hermes/sprint-state.json`. Expected state:
     ```json
     {
       "status": "active",
       "sprint_lock_on_subconscious": true,
       "build_intent_status": "approved"
     }
     ```
   - The lock suppresses non-critical `research-openclaw` jobs and sets `subconscious-openclaw` to `drift-from-research` mode.

4. **Monitor progress.**
   - Hermes surfaces sprint progress in every planning cycle summary.
   - Review `workspace/hermes/decision-log.jsonl` for dispatch and interpretation events.
   - Review `workspace/hermes/cost-ledger.jsonl` to track burn against the daily cap.

---

## Approving a Build Intent

Build intents are produced by `research-openclaw` and drafted by `subconscious-openclaw`. Hermes cannot self-approve them.

1. **Wait for Hermes summary.**
   - Hermes reads the intent from `workspace/research-vault/build-intents/` or `workspace/subconscious-room/intents/`.
   - It validates schema conformance, evidence linkage, and policy compliance.
   - It presents: objective, rationale, acceptance criteria, estimated cost, risks, and a recommendation.

2. **Evaluate the evidence.**
   - Check that referenced research vault artifacts exist and are fresh.
   - Check that signal IDs (if any) are acknowledged in `workspace/hermes/signal-inbox/`.
   - Confirm estimated cost is within the daily cap and per-job limits.

3. **Make a decision.**
   - **Approve:** Reply with explicit approval. Hermes updates `sprint-state.json` and may dispatch a `subconscious-openclaw` drift job.
   - **Reject:** Reply with a reason. Hermes logs the rejection and notifies research context.
   - **Request changes:** Reply with specific modifications. Hermes holds the intent in `pending_approval` until you re-review.

4. **Log verification.**
   - Confirm an entry appears in `workspace/hermes/decision-log.jsonl` with `category: approval` or `category: rejection`.

---

## Cancelling a Job

You may cancel any in-flight job. Hermes propagates the cancel to the broker.

1. **Identify the job.**
   - Job ID is provided in Hermes status summaries or in the broker API (`GET /v1/jobs`).
   - Confirm the job is not in a terminal state (`completed`, `failed`, `archived`).

2. **Send cancel instruction.**
   - Message Hermes with the job ID and the word `cancel` or `stop`.
   - Include a reason if the cancellation is non-routine (e.g., "source plan too broad", "budget redirect").

3. **Hermes actions.**
   - Issues `POST /v1/jobs/{job_id}/cancel` to the broker.
   - Updates `decision-log.jsonl` with `category: dispatch` and the cancellation reason.
   - If the job was part of an active sprint, Hermes assesses whether the sprint can continue or should be marked `locked` pending your decision.

4. **Verify termination.**
   - Poll broker `GET /v1/jobs/{job_id}` until status is `cancelled`.
   - Check that no new dependent jobs were dispatched after the cancel.

---

## Handling a Critical Health Alert

A `critical` health status means halt new job dispatch immediately.

1. **Acknowledge the alert.**
   - Hermes will notify you immediately with: worker ID, health status, last successful run timestamp, and any failure signatures.
   - Reply to confirm receipt so Hermes knows you are engaged.

2. **Assess scope.**
   - Read the latest health report in `workspace/research-vault/health/` or `workspace/subconscious-room/health/`.
   - Check broker events (`GET /v1/jobs/{job_id}/events`) for the failing job.
   - Check `workspace/hermes/cost-ledger.jsonl` to see if the failure coincided with a cost spike.

3. **Decide on action.**
   | Scenario | Operator Action |
   |---|---|
   | Worker crashed after a single job | Hermes retries once automatically. If it fails again, ask Hermes to issue a targeted health-check job. |
   | Persistent `critical` status across multiple jobs | Instruct Hermes to halt all dispatch to that worker. Inspect worker logs and broker runtime. |
   | Data corruption or schema violation | Instruct Hermes to quarantine recent artifacts. Do not approve new jobs until root cause is found. |
   | Cost overrun caused by runaway job | See "Cost Overrun Response" below. |

4. **Resume or stand down.**
   - If the issue is resolved: instruct Hermes to resume normal cycle.
   - If the issue is systemic: keep dispatch halted. Hermes will continue assessing health but will not issue new jobs until you explicitly approve.

---

## Cost Overrun Response

Cost overruns are handled at two levels: per-job limit breach and daily cap breach.

### Per-Job Limit Breach

1. **Broker should auto-kill** the job if runtime cost enforcement is enabled.
2. **Hermes logs** the breach in `decision-log.jsonl`.
3. **Operator inspects:**
   - Was the scope larger than estimated?
   - Was the worker model profile more expensive than planned?
   - Is there a loop or runaway API call in the worker output?
4. **Operator decides:**
   - Adjust future per-job limits in the broker job payload.
   - Re-dispatch with a tighter scope and lower cap.
   - Escalate to engineering if the breach indicates a platform bug.

### Daily Cap Breach

1. **Hermes pauses dispatch** of all non-essential jobs.
2. **Hermes notifies you** with current daily spend and which jobs contributed.
3. **Operator options:**
   - **Wait until next UTC day** for the cap to reset.
   - **Authorize specific jobs** one-by-one with `operator_override: true` and a reason. Hermes will still require explicit per-job approval.
   - **Raise the daily cap** by modifying the platform configuration and restarting the planning cycle. Document the change in `workspace/hermes/operator-notes/`.
4. **Verify ledger:** Check `workspace/hermes/cost-ledger.jsonl` for accuracy against broker receipts.

---

## Manual Override Procedures

Use overrides only when normal policy gates would block necessary recovery or urgent action.

### Sprint Lock Override

1. **Request override.** Message Hermes: `override sprint lock: <reason>`.
2. **Hermes confirms:** It will repeat the reason back and ask for final confirmation.
3. **Confirm.** Reply `confirm`.
4. **Hermes actions:**
   - Sets `sprint_lock_on_subconscious: false` in `sprint-state.json`.
   - Logs the override in `decision-log.jsonl` with `category: override`.
   - May now dispatch `research-openclaw` jobs during an active sprint.

### Approval Bypass for Emergency Recovery

1. **Request bypass.** Message Hermes with the job or action, plus `operator_override: true` and a mandatory reason string.
2. **Hermes validates:** The requested action must not violate hard safety invariants (e.g., no autonomous financial transactions, no direct vault writes).
3. **Hermes logs:** The override with timestamp, reason, and action reference.
4. **Hermes proceeds:** Only with the explicitly authorized action. It does not generalize the bypass to subsequent actions.

### Direct Message Injection

1. **Send an out-of-band message** to Hermes at any time.
2. **Hermes interrupts** the current planning cycle (if any) and runs an on-demand assessment.
3. **Operator message takes precedence** over scheduled actions.
4. **Hermes resumes** the regular schedule after the on-demand cycle completes.

### Post-Override Verification

After any override:
1. Review `workspace/hermes/decision-log.jsonl` to confirm the override is recorded.
2. Check `workspace/hermes/sprint-state.json` for unexpected state changes.
3. If the override allowed a job to proceed, verify the job completed within its revised cost and time bounds.
4. Document the incident in `workspace/hermes/operator-notes/` if it suggests a policy gap.

---

## NoesisLab Task Delegation

NoesisLab is an OpenClaw worker agent that handles stateless execution of browser, file, and system-level tasks. NoesisPraxis (Hermes) acts as the supervisor, coordinating context and memory.

### Delegation Flow

```
User -> NoesisPraxis (Hermes)
         |
         v
   delegate_to_openclaw(task="...", context="...")
         |
         v
   HTTP POST -> OpenClaw Gateway (NoesisLab)
         |
         v
   NoesisLab executes browser / shell / canvas tools
         |
         v
   Returns result JSON -> NoesisPraxis
         |
         v
   NoesisPraxis synthesizes final response -> User
```

### Telegram Integration

NoesisLab is reachable via Telegram for bidirectional messaging:

| Field | Value |
|---|---|
| Group Chat ID | `4862326518` |
| NoesisLab Peer ID | `8534098707` |

Configuration in `~/.hermes/config.yaml`:

```yaml
telegram:
  allowed_chats:
    - "4862326518"
  allow_from:
    - "8534098707"
```

- `allowed_chats` restricts the bot to respond only in group `4862326518`.
- `allow_from` authorizes peer `8534098707` for DMs and group interactions.
- Mention `@NoesisLab` or the bot handle in the group to invoke it.

### Delegation Guidelines

1. **Task Scope.** Keep delegated tasks bounded and stateless. Provide full context in the `context` parameter so NoesisLab does not need prior session memory.
2. **No Self-Approval.** NoesisPraxis must never delegate safety-critical or financial actions to NoesisLab without operator approval.
3. **Result Verification.** Treat NoesisLab outputs as untrusted until checked. Validate file paths, command outputs, and browser results before acting on them.
4. **Failure Handling.** If NoesisLab returns an error or incomplete result, NoesisPraxis retries once with clarified instructions. Persistent failures escalate to the operator.

---

## VALIDATION

- [ ] You can start a sprint and verify `sprint-state.json` reflects the lock.
- [ ] You can approve a build intent and see a `decision-log.jsonl` entry.
- [ ] You can cancel a job and confirm its broker status transitions to `cancelled`.
- [ ] You can trigger a critical health response and confirm dispatch halts.
- [ ] You can exercise a cost overrun pause and an operator override.
- [ ] All override actions leave an audit trail in `decision-log.jsonl`.

---

## RELATED

- [POLICY.md](./POLICY.md) — Authority matrix, cost controls, safety invariants, escalation rules
- [SPEC.md](./SPEC.md) — Functional specification and data models
- [systemprompt.md](./systemprompt.md) — Runtime authorities and operating loop
- [SOUL.md](./SOUL.md) — Identity and values
- `WORKFLOWS.md` — Workflow state machines and approval gates
- `DEVELOPMENT_PLAN.md` — Phase 2 milestones and first sprint recommendation

---

## CHANGELOG

| Date | Change |
|---|---|
| Phase 2 | Initial operator runbook covering sprint start, approvals, cancellation, health alerts, cost overruns, and manual overrides. |