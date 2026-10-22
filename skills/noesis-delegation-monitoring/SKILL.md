---
name: noesis-delegation-monitoring
description: "Route and monitor delegated work in the Noesis stack."
version: 0.1.0
author: Elvis Nuno (enuno), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [noesis, monitoring, lifecycle, leases, heartbeats, escalation, restart-recovery, cancellation]
    related_skills: [noesis-task-delegation, noesis-control-plane-dev, subagent-driven-development, test-driven-development, systematic-debugging]
---

# Noesis Delegation Routing and Monitoring

Monitor work that has been delegated through the noesis control plane
(`noesis-task-delegation`): supervise the lifecycle after launch, detect
self-clone / cycle / fallback attempts, reconcile partial work, handle
cancellation, recover from controller restart, and escalate blocks. This
skill covers the **runtime side** of delegation. The plan-and-dispatch side
lives in `noesis-task-delegation`; the developer-side for changing the
routing code lives in `noesis-control-plane-dev`.

## When to Use

- A task has been dispatched through `Orchestrator.route_and_launch` (or
  through a Claude Code/Codex session launched by `noesis-forge`) and
  is now in the `running` or `verifying` state.
- The orchestrator needs to supervise the lifecycle, collect the
  candidate revision, run ordered reviews, and accept the result.
- A failure was reported (crash, lease expiry, quarantine, profile
  mismatch, verifier non-zero exit) and a bounded recovery or escalation
  decision is required.
- The controller restarted and the in-flight task ledger needs to be
  reconciled without duplicate launch.

Don't use for:

- Contracts that have never produced a durable task or preflight event (use
  `noesis-task-delegation`). A dry-run that already wrote `task_proposed` or
  `preflight_proposed` is durable state and must be reconciled here even when
  no worker was dispatched.
- A new feature or bugfix that needs planning (use `omh-plan` first,
  then `noesis-task-delegation` for the dispatch).
- A change to the control plane itself (use `noesis-control-plane-dev`).
- A live production incident response where the operator is the
  decision-maker (use the operator-facing incident response workflow;
  this skill is for the routine case where the operator has already
  authorized the work).

## Prerequisites

- The noesis-agent-stack repo is at `~/projects/noesis-agent-stack/` (or
  the operator's chosen path); the v3 prototype install is in place.
- The TaskStore ledger is at the path recorded in the task's
  `ledger_path` field; the orchestrator instance owns the JSONL append.
- The Hermes CLI binary is on PATH: `hermes --version` resolves.
- The `hermes` profile directory exists at
  `~/.hermes/profiles/<profile_id>/` for every specialist that may run.
- A capable reviewer profile is available
  (`noesis-sentinel` for spec/security, `noesis-skeptic` for quality).

## How to Run

The orchestrator instance that dispatched the task is the only writer
to the task's ledger. A separate monitoring run opens a fresh
controller and reconciles the ledger without re-launching.

```python
from app.control_plane import Orchestrator
from app.launcher import HermesCliAdapter

# Same Orchestrator class as the dispatching run; the ledger path is
# the only required input. The control plane replays the JSONL and
# surfaces pending tasks; it does not start new launches unless
# route_and_launch is called explicitly.
orch = Orchestrator(
    ledger_path,
    runtime_adapter=HermesCliAdapter(),
    inference_enforcer=None,  # monitoring does not need to re-check policy
)

# Inspect the in-flight state (read-only)
state = orch.reconcile()  # returns ReconciledState (no side effects)

# Accept a result once reviews pass
orch.accept(task_id, operator="noesis-orchestrator")

# Cancel a task
orch.cancel(task_id, reason="lease_expired")

# Block a task
orch.block(task_id, reason="missing_runtime")
```

For long-running work, the orchestrator's monitoring heartbeat is run
from a separate process or a sidecar; the lease deadline and the
verifier exit are the binding signals, not the heartbeat itself.

## Quick Reference

| What | Where |
|---|---|
| Reconciliation entry | `Orchestrator.reconcile()` |
| Lease expiry check | `task.lease_expired()` |
| Quarantine gate (F-1) | `_assert_spawn_gates` |
| Stale-epoch gate | `_assert_spawn_gates` |
| Reviewer binding check | `_assert_review_evidence` |
| Identity attestation | `HermesCliAdapter.assert_attestation` |
| Process liveness | `psutil.pid_exists(pid)` or `os.kill(pid, 0)` |
| Sandbox lifecycle in tests | `tests/test_bootstrap_launcher_controls.py` |
| Failure-injection tests | `tests/test_delegation_failure_injection.py` |
| Quarantine writer path | `app/control_plane.py::_record_quarantine` |
| Reviewer disposition (PASS/APPROVED/REQUEST_CHANGES) | `ReviewVerdict` enum |
| Task state machine | `app/models.py::TaskState` |

## Verifying a CLI-dispatched completion (no control plane)

When a specialist was dispatched as a background `hermes -p <profile> -m
<model> --provider <lane> chat -q <contract-file>` process, the completion
notification is a claim, not evidence. Run this checklist before
dispatching any next stage.

Before launching a reviewer, freeze the complete review packet: candidate and
tree identity, all mandatory discrepancies, evidence limitations, prohibited
actions, output path, and verdict vocabulary. Hash the packet in durable
storage. A reviewer receives the prompt snapshot taken at process start; a
supplement written afterward does not amend that run. Reject a verdict that
omits a required disposition instead of retroactively treating the supplement
as reviewed.

1. **Recompute the result-file hash yourself:** `shasum -a 256
   <result-path>` must match the value the child reported. A child's
   self-reported SHA-256 is a self-report; the receipt binds only after
   your recomputation matches.
2. **Verify candidate identity in its own worktree:** `git rev-parse
   HEAD HEAD^` equals the claimed candidate and parent; `git status
   --porcelain` shows no unexpected tracked modifications; the log
   subjects match the freeze packet.
3. **Verify each protected tree with a per-repo scoped command**
   (`git -C <abs-path> rev-parse HEAD`) or a separate terminal call.
   A terminal call's workdir applies to the whole compound command —
   folded multi-repo checks silently report one tree's identity for
   every repo, so a "protected tree unchanged" claim made that way is
   worthless.
4. **Read the verdict from the reviewer's receipt file** (grep
   `Primary verdict`), never from the child's stdout summary, which can
   truncate or paraphrase. Record the receipt path and its SHA-256.
5. **Gate the next stage on the receipt verdict.** Sentinel
   `PASS` / `PASS-WITH-COMMENTS` unblocks the Skeptic; `REQUEST_CHANGES`
   opens a bounded remediation attempt with an explicit attempt counter
   and fresh idempotency key in the new contract (two same-root-cause
   repairs, then a changed-approach proposal to the operator — see
   Procedure step 10); `INSUFFICIENT_EVIDENCE` re-dispatches the same
   review with the missing evidence named.
6. **Check liveness before reporting completion.** When the operator
   asks for a final report, run `ps`/`pgrep` on the dispatched PIDs and
   inspect the artifact directory first. If any dispatch is still
   running, report the verified state and what remains — never
   summarize running work as results. Interpret process state explicitly:
   `Z` is a defunct zombie, not evidence of continued execution; reconcile
   its parent and durable outputs rather than calling it active.
7. **For deployment-automation candidates, verify the real execution path.**
   Static YAML assertions do not prove Ansible behavior. Run the supported
   invocation against the actual bounded target, capture the integer exit and
   observed facts, and bind each discovered value to the later policy gate.
   In `--check`, remember that `command` tasks are skipped unless explicitly
   allowed; add `check_mode: false` only to commands proven read-only, preserve
   `changed_when: false`, and test missing/malformed/failed discovery as
   fail-closed. Prove no writes with independent before/after snapshots or
   hashes of destination paths, service state, identities, and rollback
   material—neither `changed=0` nor a successful recap is no-mutation proof.

## Procedure

1. **Reconcile every durable preflight and in-flight task on controller restart.** Open a fresh
   `Orchestrator(ledger_path, ...)`; the constructor replays the JSONL
   into the in-memory state. First inventory tasks that have only
   `task_proposed`/`preflight_proposed` events: dry-run can create these without
   a process. If the launch response is `observe_mode_not_authorizing`, classify
   it as `dispatch_not_delivered`, record the exact enablement action, and never
   poll or wait because no runtime identity exists. Resume or close that proposal
   through supported lifecycle behavior before issuing a new key. For each task
   in `assigned` or `running`,
   reconcile the actual runtime state: read the recorded PID, check
   `psutil.pid_exists(pid)`, and update the task's
   `last_observed_runtime_state`. A recorded PID that no longer exists
   transitions the task to `verify_uncertain` (NOT `verifying`); the
   result is the explicit "uncertain, do not assume completed" state.
   **Completion criterion:** every in-flight task has a fresh
   `last_observed_runtime_state` recorded; no transition to `completed`
   is made without a verified verifier exit + a recorded
   `task_accepted`.

2. **Detect the F-1 quarantine.** When a launch raises an exception
   after `persist_assignment` but before `record_result`, the
   control plane records a `quarantine` event with reason
   `handle_uncertain` and adds the task to the persistent quarantine
   set. A subsequent `route_and_launch` with the same
   `idempotency_key` is rejected by the quarantine gate. **Completion
   criterion:** a follow-up `route_and_launch(same_idempotency_key)`
   raises `RoutingBlocked("quarantined")`; the ledger has the
   `quarantine` event with reason matching the failure mode.

3. **Detect self-clone and cycle attempts.** The
   `policy_self_exclusion` table rejects `noesis-orchestrator` and
   `main-hermes` as worker targets. If a child process is observed
   spawning another `hermes -p noesis-orchestrator` instance, the
   orchestrator records a `cycle_detected` event and the parent task
   transitions to `blocked` with reason `self_clone_attempt`. The
   `_assert_spawn_gates` block in the **child's** launch also catches
   this at the gate level; a child that selects
   `noesis-orchestrator` for its own task gets `RoutingBlocked`.
   **Completion criterion:** the cycle detection has been exercised
   in a regression test (`test_self_delegation_and_cycles_are_blocked`
   in `test_specialist_routing.py`); any live cycle event lands in
   the ledger as `cycle_detected`.

4. **Detect generic-fallback attempts.** A launch that is forced
   through `default` or `coder` without an explicit
   `allow_generic_fallback=True` recorded in the task contract is
   rejected by the capability index's selection. The
   `InferenceEnforcer.check(provider, model)` step also refuses any
   provider/model pair that is not in the approved lane. A
   `fallback_attempt` event is recorded with the
   requested-vs-resolved provider. **Completion criterion:** no
   `fallback_attempt` event in the ledger; every
   `task_accepted` event has a `provider` field that matches the
   requested provider verbatim.

5. **Handle lease expiry during execution.** Each task has a lease
   issued at `persist_assignment` time. The orchestrator's
   `monitor_loop` (or the sidecar's heartbeat loop) calls
   `task.lease_expired()` for each in-flight task. A task whose lease
   has expired is marked `lease_expired`; the recorded PID is
   signaled (SIGTERM, then SIGKILL after a grace period); the task
   transitions to `cancelling` and then `cancelled` once termination
   is confirmed. **Completion criterion:** every expired-lease task
   has a `termination_signal_sent` event with the signal and the
   timestamp; the PID is no longer present at
   `last_observed_runtime_state`.

6. **Heartbeat loss does NOT prove process termination.** A
   `heartbeat_lost` event is a state, not a verdict. The
   `last_observed_runtime_state` is "heartbeat_lost"; the actual
   termination is confirmed by `psutil.pid_exists(pid) == False` or
   by the child process group's exit (via the `start_new_session=True`
   spawn option). Until termination is confirmed, the task remains
   in `verify_uncertain`. **Completion criterion:** every
   `heartbeat_lost` event is followed by either a `terminated`
   event (confirmed) or another `heartbeat_lost` event with a
   later timestamp (still uncertain).

7. **Reconcile partial work before retry.** A retry after a
   crash, lease expiry, or sandbox failure is **not** a clean slate.
   The orchestrator's `reconcile_partial_work(task_id)` returns the
   list of changed paths, the partial artifacts, and the consumed
   budget. The next attempt is a new `attempt_id`; the prior
   attempt's lease is revoked; the new attempt's
   `predecessor_attempt_id` references the prior. **Completion
   criterion:** the new attempt's `predecessor_attempt_id` is
   recorded; the prior attempt's `attempt_status` is `failed` or
   `cancelled`; the new attempt's budget reservation is
   `parent_budget - consumed`.

8. **Bind reviews to the current candidate revision.** A spec
   review or quality review that targets a candidate digest not
   equal to the most recent `result_submitted` digest is invalid.
   The `_assert_review_evidence` check enforces this. A
   reviewer's `verdict` must be one of `PASS | REQUEST_CHANGES |
   BLOCKED` (spec) or `APPROVED | REQUEST_CHANGES | BLOCKED`
   (quality); anything else is rejected as malformed. **Completion
   criterion:** the ledger's most recent `result_submitted.digest`
   matches the `review_record.candidate_digest` for every
   `spec_review_passed` and `quality_review_approved` event; an
   attempt to record a verdict for a stale digest raises
   `StaleReviewError`.

9. **Review authority transitions adversarially, not just by suite count.** For lease, acceptance, retry, or optimistic-concurrency changes, require probes across restart/replay, two controller instances, and—when the ledger is shared across processes—two processes. Exercise stale deep copies and live mutable objects: a version field is not a concurrency boundary if a loser mutates shared in-memory state before compare-and-swap, or if `put` compares only an instance-local cache while holding a file lock. Require worker actions to present current persisted attempt authority, keep execution release one-way, and create a fresh attempt only through an explicit authority-owned transition. Treat absent legacy fields as absence, never permission to invent a first epoch. See `references/authority-transition-review.md` for the reusable review matrix. **Completion criterion:** the losing writer leaves both persisted and in-memory authority unchanged; replay selects the same winner; no review or candidate from an older attempt survives.

10. **Escalate blocks explicitly.** When a task cannot proceed —
   missing capability, missing runtime, exhausted budget, repeated
   failure, or a reviewer prompt that was never delivered — the orchestrator
   records a `block` event with a typed reason and a `next_required_action`
   field. Distinguish `dispatch_not_delivered` from a reviewer-produced
   `BLOCKED` verdict so the chronology does not invent a review. The control
   plane does NOT auto-retry unless the active task contract pre-authorizes a
   bounded remediation or route-attempt budget. With that authorization, record the reviewer verdict and predecessor attempt, dispatch the next bounded attempt without asking again, and preserve every failed/intermediate verification run. After two repairs for the same root cause without materially new evidence, stop with one changed-approach proposal rather than a third variation. **Completion criterion:** every
   blocked task has a `block` event with `next_required_action`
   populated; every automatic remediation cites its pre-authorization and predecessor; the operator-facing report names the block reason
   and the smallest decision needed.

11. **Cancellation is explicit and verifiable.** A `cancel`
    call records a `cancel_requested` event, sends SIGTERM to the
    recorded PID (and SIGKILL after a grace period), waits for
    termination, then records `cancel_confirmed`. The
    `cleanup_status` is `confirmed` only after `psutil.pid_exists`
    is `False`. An uncertain cleanup is recorded as
    `cleanup_uncertain` and the workspace is marked
    `workspace_reusable=False` until the operator clears the flag.
    **Completion criterion:** every `cancel_confirmed` event has
    a recorded termination signal + a `last_observed_runtime_state
    == "not_present"` snapshot; a `cleanup_uncertain` event is
    visible in the report and the operator is asked to verify.

12. **Do not silently repair or relaunch.** A reviewer disposition
    `REQUEST_CHANGES` or `BLOCKED` does not auto-trigger a new
    attempt. The orchestrator's `process_review_verdict(verdict,
    findings)` records the verdict and returns a `NextAction`
    enum: `REMEDIATE`, `ACCEPT`, `CANCEL`, or `ESCALATE`. A
    `REQUEST_CHANGES` maps to `REMEDIATE` only if the operator
    pre-authorized a bounded remediation budget; otherwise it
    maps to `ESCALATE`. **Completion criterion:** every
    `REQUEST_CHANGES` or `BLOCKED` verdict has a corresponding
    `next_action` event with the typed action and the operator
    pre-authorization recorded; no silent retry.

13. **Restart recovery without duplicate launch.** The
    `Orchestrator.reconcile()` is the only safe entrypoint after
    a restart. It does not call `route_and_launch`; it only
    replays the JSONL into memory and records the
    `reconcile_completed` event with the in-flight task
    inventory. Any explicit `route_and_launch` after a restart
    is a NEW task with a new `idempotency_key`; the prior
    `idempotency_key` is rejected by the optimistic-concurrency
    check. **Completion criterion:** a `reconcile_completed` event
    is recorded with the in-flight task count; no new
    `persist_assignment` precedes the `reconcile_completed`
    event.

## Pitfalls

- **Do not store qualification receipts or review contracts only under profile `cache/scratch`.** The profile scratch cache prunes idle entries after 24 hours, which can erase dispatch logs, reviewer receipts, contract supplements, and acknowledgments before reconciliation. Put authoritative contracts, receipts, verdicts, and evidence manifests in the task's durable artifact directory or ledger before dispatch; scratch may hold disposable logs only. After completion, preserve required log evidence durably and record its SHA-256 before advancing a gate. If artifacts were pruned, mark the review incomplete and require a fresh review rather than reconstructing a verdict from chat history.

- **Do not call `route_and_launch` on a reloaded Orchestrator
  without inspecting the in-flight task set first.** A duplicate
  launch with the same `idempotency_key` is rejected by the
  optimistic-concurrency check, but a NEW key on a partially
  completed task produces two parallel attempts. Always call
  `Orchestrator.reconcile()` first and read the
  `in_flight_task_ids` before any `route_and_launch`.

- **Do not trust a backend's `success` flag.** A green
  `hermes -p <profile> chat` exit is necessary, not sufficient.
  The verifier exit, the candidate digest, and the review chain
  are the binding signals. Treat any "the child said success"
  as `verify_pending` until the verifier exit and the
  identity attestation both pass.

- **Do not relaunch a quarantined task with the same
  `idempotency_key`.** The F-1 gate is fail-closed: a crash
  during spawn records a `quarantine` event and the same
  key is rejected on the second attempt. Use a new key
  (`<user>:<scope>:<hash>:attempt2`) and a new `attempt_id`,
  and ensure `predecessor_attempt_id` is recorded.

- **Do not treat a `heartbeat_lost` event as `terminated`.**
  Heartbeat loss is a state, not a verdict. The actual
  termination is confirmed by `psutil.pid_exists(pid) == False`
  or by the child process group's exit. Until confirmed, the
  task remains in `verify_uncertain`; auto-completing a
  `verify_uncertain` task is a fail-open and breaks the
  `test_heartbeat_loss_does_not_imply_termination` invariant.

- **Do not record a `verdict` for a stale candidate digest.**
  A reviewer's verdict is bound to the candidate digest they
  inspected. A new `result_submitted` event invalidates all
  prior verdicts. The orchestrator's
  `process_review_verdict(verdict, findings, candidate_digest)`
  raises `StaleReviewError` if the digest is not the most
  recent; a try/except that catches it and records anyway
  is a fail-open and breaks the
  `test_review_invalidated_by_candidate_change` invariant.

- **Do not promote a `REJECTED` reviewer verdict to
  `REQUEST_CHANGES` or vice versa.** A `REJECTED` verdict
  (where the reviewer's tool returned malformed JSON) is
  recorded as `verdict_malformed` and triggers an
  `ESCALATE` next-action, not a `REMEDIATE`. The verdict
  enum is closed.

- **Do not edit `tasks.jsonl` by hand.** Every transition
  goes through the control plane. A hand edit is undetectable
  by the controller and breaks the optimistic-concurrency
  contract. Use `Orchestrator.cancel(task_id, reason=...)`
  or `Orchestrator.block(task_id, reason=...)` for manual
  intervention, then read back the appended event before reporting success.

- **Do not let `cleanup_uncertain` silently resolve.** A
  workspace whose cleanup is uncertain must be marked
  `workspace_reusable=False` and the operator must verify
  before any new attempt touches the same workspace path.

- **Do not retry a failed verifier on a new attempt_id
  without first recording the failure.** The control plane
  preserves the prior `attempt_status` and the consumed
  budget; a new attempt_id inherits a reduced budget but
  also references the prior failure as
  `predecessor_attempt_id`. A retry that does not record
  the failure is a budget-accounting defect.

- **Do not treat another specialist's in-flight worktree as candidate
  evidence.** Concurrent dispatches on disjoint worktrees are allowed
  even on the same profile (one owner per writable worktree); the
  worktree a still-running specialist owns may be dirty when a
  different dispatch completes. Note it and move on — never hash its
  files or cite its porcelain in an unrelated candidate's receipt.

- **Do not dispatch the dependent reviewer from the implementer's
  summary.** The review contract must cite the prior receipt's path
  plus your recomputed SHA-256, the frozen candidate identity, and a
  per-finding closure map — assembled from the receipt file, not from
  the completion-notification text.

- **Do not manufacture a missing assignee artifact to satisfy a gate.** If an
  implementer or reviewer omits a required acknowledgment or receipt, an
  orchestrator-authored pointer may preserve context only when it is labeled
  as supplemental, authored after completion, and explicitly not fulfilling
  the assignee requirement. Keep the gate incomplete until the required
  evidence exists or the operator changes the contract.

- **Classify a pre-delivery Hermes failure separately from a reviewer verdict.**
  If the CLI reports that the message was not sent or no model turn/session was
  created, record `dispatch_not_delivered`, preserve stdout, stderr, timestamps,
  exact profile/provider/model, and produce no synthetic verdict. A provider
  lane attempt still consumes any invocation budget named by the contract even
  when no reviewer ran; after the authorized primary and backup are exhausted,
  block and request a new route decision rather than silently trying a third
  provider. Do not describe this as reviewer failure or qualification evidence.

- **Require identity pins to fail closed against an adversarial matrix,
  not just the happy path.** A candidate-integrity pin that accepts a
  wrong candidate id, a path subset, a reordered path list, duplicates,
  case/unicode variants, empty manifests, or extra keys is fail-open,
  and a reviewer will find it. The closure pattern is exact
  candidate-id equality plus ordered-tuple path equality, proven by a
  matrix (typically 15-20 malformed variants) where every variant is
  rejected with a non-zero exit. A pin verified only against its own
  valid manifest proves nothing about its rejection behavior — do not
  close a pin finding without the matrix.

- **Verify protected-state invariance before re-dispatching an
  interrupted executor.** A watchdog-aborted or stalled child (e.g.
  exit 130 after a provider-side API timeout) may or may not have
  applied its writes. Before any retry: check the repos' HEADs and
  cleanliness, re-hash every not-yet-applied preimage, and inspect
  service load states. Record the interruption as its own ledger
  event carrying that verification evidence, then re-dispatch fresh
  with discovered live state folded into the prompt ("service not
  loaded — quiesce will report No such process; record and
  continue"). Assume zero writes only after the hashes prove it,
  never because the process died early.

- **A repeated "Duplicate tool output" response masks the real error.**
  When an identical tool call (e.g. a monitoring `process_manage`
  poll) is re-issued with empty or unserialized arguments, the runtime
  may deduplicate it and return "Duplicate tool output — same content
  as a more recent call" without executing — hiding the underlying
  invocation failure. Re-issue ONCE with explicit minimal valid
  arguments (e.g. `action=list`) to surface the true schema error;
  never loop the empty call.

- **Do not import reconstructed Hermes runner entrypoints during a read-only
  review without checking early-recovery behavior first.** Importing
  `run_agent`, `agent.legacy_cli`, or initialization paths can execute Hermes
  source-update recovery tails and write reconstructed bytes into the installed
  checkout, even when the intended review is read-only. Inspect pending update
  markers and `_early_recovery` import behavior, use a supported isolated home
  outside protected roots, and prefer subprocess/static probes that avoid
  runner imports. If an accidental write occurs, preserve the complete side
  effect chronology, restore only the exact affected installed paths to their
  verified prior identity, and verify both candidate and installed worktrees
  before continuing.

- **Reject a playbook include that points outside the closed write set.**
  `--syntax-check` passes when an untracked sibling role already exists
  on this checkout, so the play looks valid while a clean commit of only
  the owned paths is not. Replace that include with an in-role assert
  that the required binary is already on the execution host. See
  `references/offline-ansible-helm-validation.md`.

- **Recompute a candidate tree hash only after the last write returns.**
  A hash started in the same turn as a patch can omit that write and
  still look stable. Freeze the digest, then dispatch the reviewer.
  A hash computed in parallel with the edit is not a pin.

- **Do not treat a matching chart version string as the published artifact.**
  A vendored default-branch SHA, a chart-release commit, and an OCI tag
  are three identities. Record which one the role installs. Do not claim
  byte-identity with a registry layer that was not unpacked and hashed.

- **A child can pass all of its own validation while silently violating
  the spec constraint it found most inconvenient.** The child authors
  both the artifact and the checks, so the checks inherit the deviation
  (example class: a target-side execution requirement replaced by the
  easier controller-side path, then validated against the wrong
  inventory so the mismatch never surfaces). Identify the riskiest
  constraint before dispatch — execution model, credential handling,
  exposure surface, and release ownership. A default-false live-check
  flag is fail-open when the install task still calls Helm: force the
  check in play `vars:` and refuse Helm unless a same-run ownership
  fact was set. After completion read the artifact itself:
  playbook top matter, `hosts:` lines, connection mode, kubeconfig and
  secret references, plus a grep for the forbidden patterns named in
  the contract. Rerun at least one validation command under the
  correct inventory; an anomaly like a single-host target validating
  as `localhost` is a deviation signal, not a passing check. See
  `references/offline-ansible-helm-validation.md` for the offline
  validation recipe.

## Verification

Prove the skill worked with these checks (all read-only):

```bash
# 1. Bootstrap launcher controls (crash, dry-run, quarantine, lease)
cd ~/projects/noesis-agent-stack
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_bootstrap_launcher_controls.py -q
# expected: 23 passed

# 2. Failure injection (duplicate launch, stale epoch, malformed message, etc.)
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_delegation_failure_injection.py -q
# expected: 10 passed

# 3. Reviewer-gate fail-closed (revision binding, invalidation, missing evidence)
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_review_gate_fail_closed.py -q
# expected: 13 passed

# 4. Authoritative ledger integration (restart recovery, optimistic concurrency)
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_authoritative_ledger_integration.py -q
# expected: 14 passed

# 5. Quarantine gate is fail-closed (F-1)
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_bootstrap_launcher_controls.py::test_crash_before_and_after_spawn_is_uncertain_and_does_not_relaunch -v
# expected: 1 passed; second route_and_launch raises RoutingBlocked("quarantined")

# 6. Full Noesis test suite is green
.venv/bin/python -m pytest orchestration/orchestrator/tests/ -q
# expected: 255 passed, 0 failed
```

## References

- `references/authority-transition-review.md` — adversarial review
  matrix for authority transitions (leases, acceptance, retries,
  optimistic concurrency).
- `references/offline-ansible-helm-validation.md` — controller-only
  validation recipe for delegated Ansible/Helm artifacts: syntax checks
  per inventory, vault-password harness, template rendering, helm
  lint/template review, out-of-scope role includes, chart-pin versus
  published distribution, and fail-open live checks.

## Lifecycle state reference (for monitoring)

```
pending
  └─> ready             (dependencies satisfied, preflight passed)
       └─> assigned     (assignment_epoch recorded, lease issued)
            └─> running  (subprocess spawned, PID recorded, attestation passed)
                 ├─> verifying        (verifier exit 0, candidate digest recorded)
                 │    └─> spec_review
                 │         └─> quality_review
                 │              └─> completed
                 ├─> verify_uncertain  (verifier exit non-zero OR PID lost)
                 │    └─> cancelled | cleanup_uncertain | remediated
                 ├─> verify_failed     (identity attestation mismatch)
                 │    └─> cancelled | remediated
                 └─> cancelled        (operator-initiated or lease expired)
```

Supporting states: `awaiting_clarification`, `awaiting_approval`,
`remediation`, `blocked`, `failed`, `cancelling`, `cleanup_uncertain`.

Required gates (a task can leave a state only if every required gate
has the matching `*_gate_passed` event in the ledger):

- `assigned`: `quarantine_gate_passed`, `epoch_gate_passed`,
  `lease_gate_passed`, `approval_gate_passed`,
  `inference_gate_passed`.
- `running`: `attestation_gate_passed`
  (`loaded_profile_id == requested_profile_id`).
- `verifying`: `verifier_exit_zero` (or the verifier's specific
  acceptance signal).
- `quality_review`: `spec_review_passed` for the current
  `candidate_digest`.
- `completed`: `quality_review_approved` for the current
  `candidate_digest`, no open `critical` or `important` finding,
  and an explicit `task_accepted` event.
