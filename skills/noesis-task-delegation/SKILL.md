---
name: noesis-task-delegation
description: "Plan and delegate tasks to Noesis specialist profiles."
version: 0.4.2
author: Elvis Nuno (enuno), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [noesis, delegation, planning, control-plane, specialist-routing, task-ledger]
    related_skills: [noesis-control-plane-dev, subagent-driven-development, test-driven-development, systematic-debugging]
---

# Noesis Task Delegation

Use the noesis-agent-stack's control plane to plan a user request, classify it
into bounded tasks, match each task to a Noesis specialist profile, dispatch
it through the durable task ledger, supervise the lifecycle, and integrate the
reviewed result back. This skill is the **operator-facing procedure**;
`noesis-control-plane-dev` is the developer-side skill for changing the
routing code itself.

## When to Use

- A non-trivial user request arrives that touches more than one domain
  (architecture + implementation + research + ops, or any mixed combination).
- The active profile is `noesis-orchestrator` (or an upstream of it) and
  the request should be split into specialist-owned subtasks.
- The operator wants a bounded plan-first delegation through the canonical
  capability index, not ad-hoc routing.
- The result must be auditable: persisted task ledger, profile identity
  attestation, ordered reviews, explicit orchestrator acceptance.

Don't use for:

- Trivial one-line asks (just answer them).
- Pure read-only research that does not need a plan or task ledger may use an eligible specialist, but still dispatch through the verified canonical route when the user requires Noesis control-plane execution. Do not substitute a direct `hermes -p <profile> chat` invocation from the supervisor.
- Changing the control plane itself (use `noesis-control-plane-dev`).
- A single coding change should still be assigned to the eligible Hermes engineering profile through the authoritative task lifecycle; never replace that route with a non-Hermes harness or a direct supervisor-launched profile session.

## Prerequisites

- The noesis-agent-stack repo is at `~/projects/noesis-agent-stack/` (or
  the operator's chosen path); the v3 prototype install is in place at
  `~/.hermes/hermes-agent/` with the 6 REPLACE + 6 ADD overlay applied
  (see `workspace/a6-v3-prototype-install/`).
- The control plane module is importable:
  `cd ~/projects/noesis-agent-stack && .venv/bin/python -c "import app.control_plane, app.specialist_routing"`.
- The capability index is reproducible from the registry:
  `CapabilityIndex.from_repo(adapter=HermesCliAdapter())`.
- The TaskStore is the authoritative ledger; never edit `tasks.jsonl`
  by hand. The control plane records every transition.

## How to Run

Invoke through the canonical Python entrypoint:

```python
from app.control_plane import Orchestrator
from app.launcher import HermesCliAdapter
from app.models import Verification

orch = Orchestrator(
    ledger_path,
    runtime_adapter=HermesCliAdapter(),
    inference_enforcer=InferenceEnforcer(...),  # or None for offline
)
result = orch.route_and_launch(
    title="...",
    intent="...",
    acceptance_criteria=["..."],
    verification=Verification(method="automated_test"),
    idempotency_key="...",
    required_capability="...",
    dry_run=False,
    approved_provider="...",
    approved_model="...",
    workspace="...",
    timeout_s=60,
)
```

For multi-task plans, run the orchestrator's planner
(`Orchestrator.plan(intent, ...)`) first; the planner returns a
`SpecialistGraph` whose nodes become individual `route_and_launch` calls.

## Quick Reference

| What | Where |
|---|---|
| Capability index | `app/specialist_routing.py::CapabilityIndex.from_repo` |
| Task classifier | `app/specialist_routing.py::TaskClassifier` |
| Profile launch + identity attestation | `app/launcher.py::HermesCliAdapter` |
| Task ledger | `app/store.py::TaskStore` (sqlite, JSONL) |
| Task contract schema | `contracts/orchestration/task-contract.schema.json` |
| Review gate | `app/control_plane.py::_assert_review_evidence` |
| Quarantine gate (F-1) | `app/control_plane.py::_assert_spawn_gates` |
| Inference lane | `app/inference_enforcer.py::InferenceEnforcer` |
| Plugin install | `scripts/install-noesis-specialist-router.sh` |
| Live test (offline) | `.venv/bin/python -m pytest orchestration/orchestrator/tests -q` |

## Procedure

**Pre-flight: honor exact prerequisite gates before any broader discovery.**
When the operator supplies an exact file or directory path and says absence is
a stop condition, test only that literal path first, using the narrowest
read/existence operation available. If it is absent or unreadable, return only
the requested blocker and stop: do not widen the search, load ancillary
workflows, update artifacts, diagnose downstream systems, or dispatch work.
This preserves the operator's bounded evidence scope and avoids turning a
single prerequisite check into an unauthorized discovery run.

**Pre-flight: resolve the workspace before authoring anything.** When a
task names a project directory but does not impose an exact-path stop gate,
check every plausible spelling of the path (e.g. `~/project/X` vs
`~/projects/X`) before creating anything. If an established repository already
exists at one candidate, that is the workspace: lead with
`Resolved workspace: <absolute path>` (especially when the supplied hint used
a singular/plural spelling that differs), rather than saying the hinted
spelling is absent in a way that sounds like the repository itself is missing.
Treat its in-flight uncommitted work as out-of-scope (never overwrite or fold
it into the task), and never silently substitute a fresh directory. Read the
repo's AGENTS.md/README conventions first and reuse its existing roles and
inventories before writing new ones.

0. **Verify the real dispatch route before promising or launching work.** Inspect the current eligible roster, capability policy, TaskContract entrypoint, and available dispatch tool for this session. A profile name in the roster, a working `hermes -p` command, or a generic Hermes subagent is not proof that the canonical route is available. Persist and launch through the existing Noesis control plane, preserving its task ID, idempotency key, approvals, identity attestation, leases, and review chain. If no canonical dispatch tool or existing task ID is available, do not guess a host, fabricate a task ID, or invoke the profile directly from the supervisor; report the precise missing route and stop dispatch-dependent work. A provider/model change requested by the operator is an invocation-scoped routing amendment only when the canonical dispatcher supports it; do not edit global/profile configuration or bypass task admission to make the route work.

   **Treat dry-run as persisted preflight, not disposable probing.** Run one dry-run before a consequential launch to inspect `task_class`, selected profile, route, and attestation, but immediately reconcile the ledger afterward: the router may append `task_proposed` and `preflight_proposed` and allocate a real task ID even though no worker starts. A green dry-run proves selection only. It does not prove launch authorization; a real call can still return `observe_mode_not_authorizing`. On that result, record `dispatch_not_delivered`, do not wait for a nonexistent process, do not try alternate providers, and request the minimum supported mode/authorization change. Resume or terminalize the persisted proposal through the implemented lifecycle before creating a successor.

   **Preflight: confirm the chosen profile is not blocked in runtime reconciliation.** Before `propose`, look up the candidate profile in `platform/runtime-reconciliation.yaml`. Do not accept that file's single `repo_declared` field as the whole repository truth: compare the model/provider in `agents/<profile>/agent.yaml`, `profiles/noesis-roster.yaml`, `profiles/live/<profile>/config.yaml`, current `~/.hermes/profiles/<profile>/config.yaml`, and the reconciliation row's observed-runtime evidence and timestamp. If those layers disagree, report each layer separately and require an explicit source-precedence decision before proposing a materialization change; current installed bytes establish what is materialized, not what policy should become. Inspect profile configs with bounded line ranges or metadata-key searches only—broad config reads can disclose unrelated inline credentials into tool logs.

   If `resolution.state` is `blocked` (typical cause: a committed live config declares a disabled lane like `OPENROUTER_FALLBACK` while the installed config uses another route), the dispatch will be refused at the spawn gate with `inference_denied → reconciliation_blocked` *regardless* of how correct the contract shape is. Halt before proposing; this is a policy-state gate, not a contract fix. Present the operator with the exact multi-layer drift, evidence freshness, gate message, and two or three legitimate moves (define declaration precedence and reconcile repository sources; authorize a one-shot override; or skip the dedicated slice and consolidate into a lane-permitted specialist). Do not edit route declarations, materialized profiles, or the freeze to make dispatch work—the orchestrator is not a privileged executor, and policy boundaries are operator-owned.

1. **Classify the request.** Read the user's intent. Decide whether the
   request is atomic (one specialist, fast path) or multi-domain (a
   bounded plan). If multi-domain, decompose into a `SpecialistGraph` via
   `Orchestrator.plan(intent, ...)`. Each node carries a
   `Classification(task_class, required_capability, reviewer_required)`.
   Inspect the dry-run `task_class` before launch; `required_capability`
   does not override keyword classification. For a planning task, keep the
   title, intent, and criteria centered on decomposition, dependencies,
   ownership, gates, and recovery. Incidental words such as “review,”
   “audit,” or “verify” can classify the whole task as reviewer-only and
   reject the intended planner as `not_independent_reviewer`. Express later
   assurance work as ordered quality gates, and set `reviewer_profile` only
   when the current task actually requires a reviewer. If classification is
   wrong, stop before launch, reconcile any persisted dry-run proposal, and
   submit the corrected contract under a fresh idempotency key.
   Before dispatch, canonicalize repeated or conflicting authority text into
   one constraint set. A direct correction controls over copied older wording;
   for spend, request count, timeout, egress, and rollout scope, retain the
   stricter bound unless the operator explicitly says they are widening that
   exact bound. Record the canonical value in the contract and reject later
   packet boilerplate that would silently widen it.
   **Completion criterion:** every requirement from the user maps to a
   graph node, or an explicit plan-level constraint (e.g. "no
   installation, evidence only"). No requirement is silently dropped, and
   every resolved conflict names the controlling instruction. A primary route
   plus fallback providers is provider resilience, not a parallel-worker plan;
   model parallel work only when the contract names distinct work products,
   dependencies, worker identities, budgets, workspaces, and an integration
   gate.

2. **Match to the best eligible specialist.** For each node, call
   `CapabilityIndex.from_repo(adapter=HermesCliAdapter())` and
   `select(intent=node.intent, required_capability=node.classification.required_capability,
   risk_tier="r0", allow_generic_fallback=False)`. The selection returns
   a `SelectionDecision` with the chosen `SpecialistRecord` and the
   ranked candidates. **Completion criterion:** the selection reason is
   recorded; the `policy_self_exclusion` rule rejects `noesis-orchestrator`
   and `default`/`coder` as workers unless explicitly allowed; the
   selected profile is in the `policy_eligible` set, not just `defined`.
   Verify the profile's role constraints before making it an assignee: a
   reviewer-only profile remains ineligible to execute even a read-only audit.
   Assign the audit to an eligible architecture or analysis specialist and bind
   the reviewer-only profile through `reviewer_profile` and the ordered review
   transition instead. **Never weaken reviewer-only admission policy just to
   make a planning graph executable.**

3. **Apply the spawn-gate policy checks** (in `_assert_spawn_gates`):
   - Quarantine gate: a quarantined task must never spawn.
   - Stale-epoch gate: the caller's `expected_epoch` must match the
     persisted `assignment_epoch`; otherwise reject.
   - Lease-expired gate: refused.
   - Approval gate: refused if the task requires approval and no
     manifest is recorded.
   - Inference gate: `InferenceEnforcer.check(provider, model)` must pass.
   **Completion criterion:** every gate's pass/fail is recorded in the
   task ledger as a `*_gate_passed` or `*_gate_failed` event with the
   reason.

4. **Persist the assignment and budget.** Before any launch, the
   `TaskStore.persist_assignment` writes the task, the `assignment_epoch`,
   the lease, the workspace ownership, and the budget reservation. The
   idempotency key is set to `f"<user>:<scope>:<short-hash>"` so a
   re-attempt with the same key is rejected by the optimistic-concurrency
   check. For bounded parallel work, give every child a distinct task ID,
   attempt/epoch, lease, reservation, workspace, preflight receipt, invocation
   state, and artifact set. Reserve the aggregate envelope for all mandatory
   children plus integration, verification, and review before launching any
   child; unknown usage stays unknown and blocks a falsely precise remaining
   budget. When fanning out to native subagent children, give each child a
   disjoint file-ownership set named in its contract, run independent
   tracks in parallel, and serialize any track whose inputs include
   another track's discovered facts (e.g. a chart's actual values keys)
   — dispatch it only after the upstream track's artifacts are verified.
   **Completion criterion:** the ledger has the `task_proposed`
   event; the next event is `assignment_recorded` with the epoch; no
   external action precedes the persistence.

5. **Launch through the explicit runtime target.** Use the profile-aware
   runtime adapter to launch the selected specialist, and bind attestation to
   the exact environment that will execute the child. Record the requested
   profile, spawned PID/session, child `HERMES_HOME`, resolved profile path,
   and a manifest digest over the identity-bearing profile files. Attest that
   same child profile directory immediately before spawn; an installed-profile
   `hermes profile show` result is not valid when the launch subsequently
   switches to a different isolated home. If fallback denial requires an
   isolated profile, materialize the specialist identity there from an explicit
   allowlist and verify its manifest equals the approved launch identity—never
   substitute a minimal name-only `SOUL.md`. **Completion criterion:** the
   durable event binds requested profile, loaded profile, child profile path,
   child manifest digest, and spawn environment; any identifier or manifest
   mismatch blocks before inference and records `dispatch_not_delivered`.

   **Verify credential reachability in the exact spawn home before consuming an inference attempt.** An installed profile may have a `.env`, `auth.json`, or configured secret sources while an isolated fallback-denial home contains only its generated route config plus identity files. Inspect the launcher implementation to determine whether it hydrates the target profile's secret scope or merely copies the parent's environment. Treat `No usable credentials` before a model turn as `credential_unavailable_to_child`, not provider rejection; validity, quota, and funding remain unknown until a separately authorized live request. The parent session's own working provider is **not** evidence of child reachability: when the parent hermes process resolved secrets at its own startup (Bitwarden SM project, keyring), spawned launcher children start cold even while the supervisor's own inference works — run a trivial one-shot `hermes -p <profile> chat` probe from the exact launch environment as the cheapest pre-flight check, and when a launch is refused, read the child's captured error text from the process log for the mechanism instead of inferring it from routing-event flags (`model_driven_canary`, `verification_pending` are static fields, not live provider state — see `noesis-delegation-monitoring`). Never copy the whole `.env` or secret-source output into the isolated home. A repair must resolve into a private mapping, inject only the approved provider's documented credential variable names into the child environment, redact stdout/stderr, and test unrelated-secret exclusion, wrong-profile isolation, missing-source failure, and fallback denial.

   **Qualify the route, not merely the profile name.** Before every launch, record separate evidence for profile-local authentication, launcher-selected lane/provider/model, isolated-child credential reachability, provider acceptance, model entitlement, quota/rate/account capacity, and approved monetary budget. Label each fact `verified`, `currently_callable`, `unknown`, or `blocked`, with observation time and expiry. A local auth row, model listing, dry-run, or tiny accepted request cannot prove full-task capacity. Select for price only among routes that already pass policy, privacy, workload-quality, execution-boundary, and reviewer-independence gates. Decompose canary limits into deadline, runtime budget, turns, provider requests, input/output tokens, USD admission, and provider/account caps; never treat one as another. If any required hard bound is unsupported, hold launch and present one revised approval envelope. Use `references/credential-diagnostics.md` for the readiness matrix, source-convergence gate, probe sequence, and control checklist.

   **When the canonical route is broken, separate diagnostic authorization from executor authority.** First establish whether an independently authorized, non-supervisor executor already exists; do not retry the same route, create a worker, substitute a provider, or let the orchestrator inherit terminal authority. If none exists, consume the authorization by preparing an exact operator-run probe derived from the installed resolver and launcher source—do not ask for the same generic authorization again. Inspect every configured helper before including it, exclude helpers that cannot supply the target credential names, start from an allowlisted environment, disable installs and persistent caches, suppress helper stdout/stderr, and emit only approved presence/provenance fields. A source error means presence is unknown, not absent; a locally present credential still proves nothing about provider acceptance, quota, or funds. Keep an independent checksum or other non-secret read-only step runnable when secret resolution must stop. Mark the diagnostic `not run` until the operator returns its redacted receipt. See `references/credential-diagnostics.md` for the decision table and receipt rules.

   **Bootstrap implementation and review only when the operator explicitly authorizes that degraded path.** If canonical implementers and reviewers are both unavailable, do not pretend intended Noesis ownership creates delivery. Prepare two separate operator-launchable contracts: one write-capable development executor in isolated worktrees and one independent read-only reviewer bound to the frozen candidate digest. Each contract records the actual harness, version, model/provider when surfaced, resumable session/thread id, base revisions, limits, prohibited actions, and receipts. Prefer distinct harness/provider ecosystems for independence. Label the result `bootstrap`, never canonical Forge/Sentinel/Skeptic work; a bootstrap PASS leaves mandatory canonical qualification outstanding. If the supervisor cannot launch the harness, stop at complete contracts and mark execution `not started` rather than borrowing terminal authority. When closing a task checklist, treat contract-file writes as proof of specification only: executor-path readiness requires an observed binary/auth/session check; if the supervisor cannot run it, attach a concise blocked reason instead of marking that readiness item verified. See `references/noncanonical-bootstrap.md` for the contract and status recipe.

   **Hard-list the in-scope files in the implementation contract.** A
   worktree-scoped bounded implementer can edit any tracked file it
   encounters, not just the ones the contract happens to mention. Name
   the in-scope file list as a closed set in the implementation
   contract. The closed set also forbids `role:` and `include_role`
   targets outside that set: an untracked sibling role can make
   `--syntax-check` pass on this checkout and still be absent from a
   clean commit of only the owned paths. After the implementer session returns
   `not_self_approved: true`, run `git status -s` and
   `git diff --stat HEAD` in the worktree; if any path appears that
   is not in the in-scope list, the implementer has polluted the
   candidate — `git checkout HEAD -- <file>` each out-of-scope
   change BEFORE the reviewer session starts, re-compute the diff
   SHA-256, and re-anchor the reviewer contract. The B2 worktree
   saw this exact failure mode: a bounded implementer rewrote the
   unrelated `IMPLEMENTATION_PLAN.md` (a 225-line F1–F5 plan) into
   a 69-line B2 plan. If the reviewer had launched against the
   polluted diff, the verdict would have been against a different
   candidate than the contract named. The in-fleet review skill
   bakes a `implementation_plan_md_clean` boolean (or equivalent
   per-file boolean) into the Sentinel contract so the reviewer
   auto-blocks when the worktree has drifted.

6. **Collect the candidate and verify it.** When the child process
   exits, the adapter records the candidate revision, the changed paths,
   the verification command output, and the residual risks. The
   orchestrator runs the verifier: `Verification(method=...)` resolves
   to a real command (e.g. `pytest tests/ -q`) and the exit status is
   captured. A passing verifier is **necessary but not sufficient** for
   completion.

   Reconcile the final summary against tool-level mutation results before
   trusting its file count. If a child reports completion but the runtime says a
   write failed, confirm the intended path is absent, inspect whether a valid
   alternative implements the same requirement, trace every include/reference
   to that alternative, and exercise the real parser or renderer. Do not call
   the whole candidate failed merely because an abandoned filename failed, and
   do not call it complete merely because the summary omitted the failure.

   Parse an implementer receipt's changed-file list only from its explicitly
   delimited changed-files section. Never treat every backticked bullet as a
   path: pin strings, image references, and dependency constraints often use the
   same Markdown shape and will corrupt file-existence checks and candidate
   digests.

   **Completion criterion:** the candidate digest is recorded in the ledger as
   a `result_submitted` event with the verifier exit status; a
   `verifier_failed` event is recorded if the exit is non-zero, and every
   declared candidate path exists or has an explicitly verified replacement.

7. **Run ordered reviews** (spec → quality → integration). Spec
   review must `PASS` for the current candidate revision before quality
   review can start. Quality review must `APPROVED` for the current
   candidate revision. For multi-task plans, a separate integration
   review runs after all task-level gates pass. The reviews are bound to
   the candidate digest; any candidate change after a review invalidates
   the prior verdict. **Completion criterion:** the ledger shows
   `spec_review_passed → quality_review_approved` for the current
   candidate digest; for multi-task plans, `integration_review_passed`
   follows; any open `critical` or `important` finding blocks
   `completed`.

   **Default: run reviewers in-fleet, not via operator hand-carry —
   except for formal qualification rounds, which are operator-mediated
   by standing policy.**
   Spec and quality reviewers are themselves Noesis profiles
   (`noesis-sentinel` for spec, `noesis-skeptic` for adversarial quality).
   Dispatch each as a bounded child task through the same canonical
   `Orchestrator.propose → approve → claim → start` lifecycle the
   implementer used, with three non-negotiables:

   1. **Exact-candidate binding.** The review contract names the
      `baseline_commit`, the `tracked_diff_sha256` (computed from
      `git diff HEAD | shasum -a 256` over the candidate worktree), the
      list of in-scope files, and the focused-test count the reviewer
      must reproduce. The contract ships as a file the reviewer reads;
      the reviewer writes its verdict to a NEW file at a documented path
      with a strict YAML-like schema. If the candidate moves between
      propose and verdict, dispatch is invalid and the review must
      `BLOCKED`.
   2. **Capability-routed proposal.** Look up the reviewer's declared
      capability from its installed profile or the canonical roster
      (`noesis-sentinel` declares `code_review`; `noesis-skeptic`
      declares `adversarial_review`). Do not guess. The proposal's
      `required_capability` must match the declared string or admission
      is rejected with `capability_mismatch`.
   3. **Cross-reviewer assignment.** `reviewer_profile` must be a
      reviewer-only profile; the orchestrator profile and other
      non-reviewer profiles are not valid as `reviewer_profile`
      (`reviewer_must_be_reviewer_only`). Use the *other* reviewer as
      the `reviewer_profile` on each review task (Sentinel reviews
      Skeptic's task, Skeptic reviews Sentinel's task) so the review
      chain stays independent even when only two reviewer profiles
      exist.

   **Dependency-gate only the second reviewer.** Give Sentinel
   `parent_task_id=implementer_task_id` for lineage but no dependency on the
   implementation task: the implementation is normally `awaiting_review`, so
   making Sentinel depend on its success creates a circular gate. Spec must
   return `verdict: PASS` before quality review may claim; declare
   `depends_on=[sentinel_task_id]` on the Skeptic proposal and only call
   `o.claim`/`o.start` on the Skeptic task after reading the Sentinel verdict
   file and confirming `verdict: PASS` literally.

   **Reviewer process shape.** Launch each reviewer as a one-shot
   `hermes -p <reviewer> chat --query-file <contract.md> --oneshot
   --provider <authorized-lane> -m <authorized-model> -t file,terminal
   --ignore-user-config --in <worktree> --max-turns
   300 --format stream-json --reasoning high` as a tracked background
   process with PID/session-id recorded in the task. (Do not add
   `--run-budget` — the installed gateway CLI rejects the flag; wall
   clock is bounded only by `--max-turns` plus external supervision,
   which the route amendment must disclose.) The explicit pair
   selects the primary lane, but neither it nor `--ignore-user-config`
   proves fallback suppression. Inspect startup output and the session
   record: any `Model fallback:` to an unapproved provider/model makes
   the review `dispatch_not_delivered`, even if the process exits zero or
   emits prose. Reviewer runs are *not* exempt from the no-fallback rule.

   **Completion criterion:** the orchestrator only transitions the
   implementer task to `completed` after both verdict files exist at
   their declared paths, both schemas validate, both verdicts match the
   allowed enum, and the candidate digest recorded in each verdict
   file is byte-equal to the digest the contract named.

8. **Accept explicitly and close.** The orchestrator's
   `accept(task_id, operator="noesis-orchestrator")` — the method is
   `accept` on `Orchestrator`, not `accept_result` — writes a
   `task_accepted` event with the orchestrator's identity, the
   accepted candidate digest, and the accepted review chain. The task
   transitions to `completed`. A `cancel` or `block` path uses
   `cancel(task_id, reason=...)` or `block(task_id, reason=...)` with
   the typed reason; both persist the cause. **Completion criterion:** the
   ledger has the `task_accepted` event; the task is in `completed`
   state; the orchestrator returns the final
   `evidence-based execution report` containing the contract reference,
   the request/resolved/launcher-confirmed profiles, the chronological
   state trace, the verification outcomes, the review records, the
   resource usage, and the termination/cleanup/restoration evidence.

9. **When a review returns REQUEST_CHANGES, run the bounded remediation
   cycle instead of accepting or hand-revising the failed candidate.**
   The implementer does not self-correct from a reviewer verdict; the
   failed candidate stays durably `failed` in the ledger and is
   never accepted. Recovery is a fresh implementer task in the same
   worktree, then a fresh review pair against a new candidate digest:
   1. Close the review task durably: `o.record_review(...)` with the
      cross-reviewer profile and Skeptic's findings, then
      `o.fail(review_task_id, reason='REQUEST_CHANGES — see
      <SKEPTIC-VERDICT-...>.md')`.
   2. Close the implementer task durably: `o.fail(implementer_task_id,
      reason='skeptic_request_changes: <one-line summary> — see
      <verdict file>.md')`. The `reason` is the durable event payload;
      a future operator recovering from the ledger will see what
      blocked acceptance.
   3. Propose a fresh bounded task:
      `o.propose(title='<name> remediation <letter>: <fix scope>',
      intent='Fix <each important finding> in the same worktree.
      Strict TDD: failing test first. No edits outside the in-scope
      files. not_self_approved: true.',
      assignee_profile=<same implementer profile>,
      required_capability=..., verification=...,
      idempotency_key='<user>:<name>-remediation-<letter>:<date>',
      risk_tier='r1', timeout_s=5400, max_attempts=1,
      reviewer_profile=<the other reviewer>,
      parent_task_id=<implementer_task_id>,
      labels=['control_plane','remediation','offline_only',
      '<name>_remediation'])`. Before approval, verify that the active
      hash-bound authorization expressly covers this additional attempt,
      its route/model, duration, fallback policy, writable paths, and any
      review rounds. Reuse that manifest only within its explicit remaining
      budget; otherwise stop and obtain a new operator authorization and
      manifest. The new task is a sibling in the ledger, not a modification
      of the original.
   4. The bounded implementer produces a new result file
      `IMPLEMENTER-RESULT-<letter>.md` with a fresh
      `tracked_diff_sha256`. Re-anchor review contracts to that new
      candidate identity only when the active authorization expressly
      includes those reviews. Otherwise stop after implementation and ask
      for exact-candidate Sentinel authorization; Skeptic remains gated on
      a fresh Sentinel PASS and its applicable authorization.
   5. Continue another repair/review iteration only if an unspent,
      explicit retry-and-review budget in the current manifest covers it.
      Stop when the named attempt, route, time, cost, or review budget is
      exhausted; preserve the rejected candidate and ledger history, then
      request a new scoped authorization. Prior approval of one attempt or
      one candidate does not transfer to a new implementation attempt or a
      changed candidate digest.

## Native-delegation governed pilot (Path B — official Hermes backend)

Use when the operator authorizes a bounded pilot of native `delegate_task`
with the `advanced-delegation` plugin's `profile_routes` backend instead of
the canonical control-plane launcher. The canonical launcher and its gates
remain the qualified authority; a native pilot is evidence-gathering, not a
replacement dispatch system.

1. **Reconcile the installed state with bounded fields only:** core
   version/revision and install-tree cleanliness, plugin version, the
   enabled delegation backend, and conflicting active sessions/delegations
   (process list + the native `async_delegations` store). Never upgrade,
   reinstall, or enable anything to make a route work.
2. **Verify the restriction surface before promising any child shape**
   (see `references/native-delegation-enforcement.md`): a delegate child's
   toolsets derive from the parent's *in-memory* toolset, and the per-task
   toolset-narrowing parameter is not necessarily exposed on the current
   session's `delegate_task` surface. If it is not, the only native route
   to a minimal child is a FRESH parent session launched with
   `-t/--toolsets`.
3. **Prefer a zero-tool child.** Launch the fresh parent with
   `-t delegation`: the parent holds exactly `delegate_task`; the leaf-role
   strip removes `delegation` from the inherited child toolsets, leaving
   the child with zero tools. Supply the complete sanitized brief inline in
   the task goal/context; the child's final message returns through the
   inline synchronous join (oneshot stateless channel). The restriction is
   schema-level — the tools never enter the child's function schema — not a
   prompt instruction.
4. **Bind the pilot in a durable brief:** pilot id, exact named profile,
   task and permitted inputs, the actual selected provider/model per
   profile, effective tools, limits, expected result, stop conditions. Do
   not fabricate `expected_epoch`/approved-pair enforcement the native
   backend does not supply; record route checks as procedural observations.
5. **Config hygiene, pilot-scoped only:** `delegation.backend:
   profile_routes` with an allowlist of exactly the named profile and a
   `default:` route; `delegation.max_iterations` as the child cap (it is
   config-authoritative); `inherit_mcp_toolsets: false`; a child-profile
   route/fallback amendment only when the configured route is
   unauthenticated, preserving the exact old settings for restoration. 0600
   backups; record a non-secret diff.
6. **Operator-executed launch; the supervisor stands down.** Prepare the
   exact command (`hermes -p <profile> chat --query-file <q> --oneshot -t
   delegation --format stream-json ...` — no `--ignore-user-config` when
   the pilot needs the delegation config, no `--yolo`) and a compact
   handoff. Never mutate the running supervisor's tool surface and assume
   it took effect, and never leave two supervisors dispatching the same
   pilot.
7. **Validate provenance:** parent session id and profile manifest pin;
   `delegate_task` result JSON with requested == loaded profile and child
   session id; child init model/provider and absence of fallback events;
   zero tool-call events in the child transcript; child exit_reason within
   the iteration cap; usage evidence. Correlate the native SQLite
   delegation id with the pilot id — it is the single execution-state
   authority. Never hand-append invented lifecycle events to
   `tasks.jsonl`; use a distinctly labeled pilot evidence artifact.
8. **Independent review before any expansion.** An eligible reviewer
   inspects brief + config diff + session log + result. If none is
   available, report execution verification separately and keep reviewed
   adoption pending; do not expand the allowlist automatically.
9. **Rollback:** restore configs from backup and stop/reconcile pilot work
   through supported mechanisms. Rollback does not erase durable sessions,
   SQLite records, logs, or artifacts — and does not claim to.

### Operator-executed launch packets (the packet + companion + drill pattern)

When the operator authorizes a pilot but reserves execution ("the operator
will execute the exact packet"), deliver three artifacts, then stand down:

1. **Launch packet (Markdown), revisioned by filename.** Each correction
   produces a NEW file (`...-pilot-003.md`), never an in-place rewrite; the
   superseded revision is preserved byte-identical and its reported hashes
   stay valid. The packet states design facts, exact operator commands, the
   authorized config delta, scope guard, and honest limitations.
2. **Companion script (stdlib-only Python or sh).** Implements bounded
   non-secret identity extraction, guarded apply, and verifiable restore:
   - Precondition mismatch or refused check = exit 2 with ZERO writes; never
     weaken a precondition to make apply pass.
   - Refuse symlinks and non-regular files at every boundary (live config,
     preimage, script copy, attempt dir).
   - Refuse-if-exists on the attempt directory; create it 0700 with umask
     077; noclobber for every evidence file; never `>`-truncate prior logs.
   - Two individually-atomic replacements are NOT one transaction: validate
     everything first, preflight writability beside each target, then write
     with a progress marker between the two replaces; a crash mid-apply
     leaves marker-tracked partial state that `restore` completes.
   - Record ORIGINAL config modes separately from backup-file modes
     (backups are 0600 regardless of source); restore re-applies the
     recorded original mode and verifies bytes AND mode programmatically.
   - Whole-config hashes never reach the terminal or public receipts — only
     a 0600 private-integrity ledger; terminal output is MATCH/MISMATCH
     tokens and sanitized status. Preimages may contain secrets.
   - Restore refuses on any live-vs-post-apply hash mismatch (concurrent
     modification); investigate, never bypass.
3. **Operator runbook (single executable script).** One command runs the
   whole flow; per-phase exit codes are recorded to files; a launch failure
   cannot skip cleanup (no `set -e` on the cleanup path, explicit RC capture);
   parent termination is verified before restore; NO automatic retry of any
   failed phase; a manual recovery command is documented for SIGKILL/
   terminal loss (shell traps cannot cover those).

**Drill the procedure on synthetic fixtures before handing over.** Build
fixture profile dirs with the exact preimage shapes plus a canary-secret line
outside every affected window; stub the CLI binary (PATH-prepended shim that
answers `--help` and exits nonzero at launch); run the full runbook via the
script's env-override hooks. Verify: fresh setup, refuse-if-exists,
precondition refusal with zero writes (check the live file CONTENT, don't
assume), simulated partial apply completed by restore, nonzero launch outcome
still restores, concurrent-modification refusal then success after untamper,
original-mode restoration, and zero canary leakage into any emitted artifact
(preimages excepted). In the drill, every REFUSED message is evidence: read
its actual text before attributing it to a guard — most anomalies in a drill
pass are harness errors (wrong fixture shape, stale fixture state), and the
script's correct refusal is not a script defect. Reset fixtures to pristine
between drills. Never claim the live procedure passed from compilation or
identity-only dry runs.

**Run an independent review round on the exact delivered files before asking
for operator approval.** Dispatch a separate reviewer context (fresh subagent,
no shared transcript) that: verifies the sha256 of every hash-identified
artifact first; reads the actual delivered files rather than the packet's
claims; spot-checks the drill evidence by re-running drills in its own scratch
dir; marks each claim PASS/FAIL/UNVERIFIED with file:line evidence; and hunts
for fail-open paths, races, and output leaks the preparer missed. Reviewers
find defects — expect at least a second revision. On any finding: produce a
successor artifact with a NEW hash (never patch a hash-identified file), keep
the superseded one byte-identical, document the findings and fixes in the new
revision, and re-drill the changed paths. After fixes, run a second-round
delta review (diff old vs new to confirm only intended changes; trace for
regressions such as renamed-file inconsistencies across copy targets,
refuse-lists, receipts, and recovery commands). See
`references/operator-packet-review.md` for the approval-manifest structure and
the review-round procedure.

## Pitfalls

- **Place every precondition check before the first mutation, and gate the
  launch on apply success.** A check that runs after apply (e.g. a YOLO-mode
  or credential precondition inside the launch branch) fails with the
  configuration already modified: the runner exits "refused" while both
  profiles are live-mutated, with no restore and no pointer to recovery —
  the same masking class the packet was written to prevent. Any check that
  can fail after mutation must instead route through restore, never through
  a bare `fail`. Equally: never launch when apply did not exit exactly 0 —
  launching against unapplied or partially applied configuration is an
  ungoverned dispatch. Both rules are enforced in runner design by a
  pre-mutation phase (flags, YOLO, directory refusal) and a launch branch
  conditional on `APPLY_RC -eq 0`.

- **Cleanup success must not mask failure: the final exit code reports the
  worst outcome.** A runner that restores configuration and then exits 0
  after a failed launch (or failed restore) produces a success-shaped result
  that automation and operators read as PASS. Exit non-zero on launch failure
  (after clean restore), on restore failure, and on apply-not-complete; give
  apply-not-complete-with-nothing-applied its own honest wording ("nothing
  was applied; restore not applicable; verify-if-uncertain") instead of
  "RESTORE FAILED". Every phase still records its own exit file so receipts
  carry the full picture.

- **A parsed CLI flag is not a honored flag — verify against dispatch code.**
  `hermes --usage-file` is parsed at top level but absent from the chat
  subcommand's passthrough table, so on `chat --oneshot` it is silently
  ignored. Capture the target subcommand's `--help` before any mutation and
  require every launch flag to appear; for any flag whose effect matters,
  confirm in the installed source that the subcommand's dispatch actually
  passes it through. Remove unhonored flags from the command line by design
  decision recorded in the packet — never leave an instruction that tells
  the operator to delete a flag and relaunch ad hoc.

- **The byte-identical restore postcondition covers every target, including
  ones apply never touched.** When apply is partial (first file replaced,
  second interrupted), restore of the applied file can succeed while a second
  profile drifted externally; exiting 0 there prints "RESTORE OK" over a
  silent MISMATCH. Restore must clear success on any live-vs-preimage drift
  for a not-applied profile (exit non-zero, MISMATCH prominent, file left
  untouched) — fail-safe direction preserved, honesty restored.

- **Keep capability claims honest across native and custom paths.** Native
  child-command approval (deny-by-default) is not a Noesis pre-spawn
  contract gate; toolset restriction is not an OS boundary (a process still
  reaches what its OS identity can reach); procedural approval, route, and
  reviewer boundaries remain procedural, and past successful reviews do not
  establish bypass resistance; rollback restores configuration but does not
  erase durable sessions, SQLite records, logs, or artifacts; and an
  offline-qualified custom backend HAS code enforcement even when it is
  not installed — never word a record so these distinctions disappear.

- **No native hard wall-clock cap exists for delegate sessions.**
  `--max-turns` bounds the parent CLI only; a child's iteration cap is the
  config-authoritative `delegation.max_iterations`. State supervision
  honestly — never represent it as a hard timeout or promise unattended
  cancellation.

- **`delegation.max_iterations` is config-authoritative.** `delegate_task`
  explicitly ignores a caller-supplied max_iterations; set the cap in the
  active profile's config and verify the child's recorded `exit_reason`.

- **`inherit_mcp_toolsets` defaults true.** A narrowed delegate child
  re-gains the parent's MCP toolsets unless `delegation.inherit_mcp_toolsets:
  false` is set — network/MCP access is not removed by narrowing alone.

- **Profile-config toolset keys do not narrow a delegate child.** The child
  receives explicit parent-derived constructor arguments that override the
  child profile's own `enabled_toolsets`; only a fresh parent's `-t`
  restriction or an actually-exposed per-task toolset parameter narrows the
  child. Verify exposure in the installed source before relying on it, and
  stop before dispatch if the required restriction cannot be established
  through the real path.

- **One specialist's provider is not another's.** Check the named
  profile's own provider/model and its presence in the authenticated pool
  (presence only — never read values); do not assume a route that worked
  for one profile is ready for another, and do not retry a historically
  exhausted route without new readiness evidence.

- **Do not bypass the planner.** Calling `route_and_launch` directly
  with a multi-domain intent produces a single best-fit specialist and
  silently drops the other requirements. Always call
  `Orchestrator.plan(intent, ...)` for mixed-domain asks.

- **Route by the artifact, not the product name.** A request to package
  or deploy an application's Helm chart or Ansible role is
  implementation or operations work. Do not select a messaging or
  gateway skill because the product name matches. Those skills own
  client setup, media, and relay diagnosis, not cluster install
  automation.

- **Run reviewers in the fleet by default; never silently replace a mandatory reviewer.** Spec and quality reviewers are Noesis profiles dispatched through the same `Orchestrator.propose → approve → claim → start` lifecycle as the implementer. If that route is unavailable, return the precise blocker. Use an operator-launched external reviewer only when the operator explicitly authorizes a bootstrap path; bind it to the exact frozen candidate, label it bootstrap review, and keep mandatory Sentinel/Skeptic qualification outstanding. External bootstrap review is degraded evidence, not canonical reviewer delivery. The one standing exception to in-fleet dispatch is a **formal qualification round** (frozen-candidate Sentinel/Skeptic receipt chain): there the operator-mediated launch is the authorized path and the orchestrator never launches reviewer inference — see `noesis-in-fleet-review` → `references/formal-qualification-rounds.md`.

- **The `reviewer_profile` field is reviewer-only and is not the
  orchestrator.** Policy rejects a non-reviewer `reviewer_profile`
  with `reviewer_must_be_reviewer_only`; the orchestrator profile
  itself is rejected. The cross-reviewer pattern is the default:
  Sentinel's review task has `reviewer_profile=noesis-skeptic`,
  Skeptic's has `reviewer_profile=noesis-sentinel`, so the review
  chain stays independent even when only two reviewer profiles
  exist. When you have more than two reviewers, still never name the
  implementer as `reviewer_profile`.

- **`assignee_profile` cannot be `noesis-orchestrator` (or any
  supervisor profile).** The policy rejects a supervisor
  `assignee_profile` with `supervisor_cannot_execute: '<profile>'
  is a supervisor profile and must delegate, not execute`. Even
  when the supervisor is the natural "owner" of the task (for
  example, recording an external verdict into a review-task's
  ledger state), the assignee must be an executable specialist
  profile. The orchestrator drives the work, but its role is
  *supervisor* — the assignee on the task must be a profile that
  actually carries out the work. Apply the same identity gate to an
  operator-launched harness handoff: before running Git/worktree commands or
  editing code, verify that the new session's active runtime/profile is a
  development executor and not the supervisor that authored the handoff. A
  prompt saying "act as the executor" does not reclassify an already-running
  supervisor session; stop before mutation and give the exact contract path to
  a genuinely separate coding-harness session. For meta-auditing of reviewer
  work, the cleanest assignment is the cross-reviewer profile
  (Sentinel's review-task assignee is Sentinel, but the
  meta-reviewer `reviewer_profile` is Skeptic; that is the
  pattern that survives the policy gates).

- **Look up the reviewer's declared capability from the roster
  before proposing.** A wrong capability string is a hard
  `capability_mismatch` at admission. Common pairs:
  `noesis-sentinel` → `code_review` (NOT `review_spec`,
  `block_merge`, or any made-up token);
  `noesis-skeptic` → `adversarial_review` (NOT `code_review`).
  Read the actual profile's declared capability set rather than
  guessing from the profile name; profiles can declare multiple
  capabilities and the wrong one will be silently accepted if it
  happens to be in the set.

- **Convert `UUID` fields to `str` before formatting into ledger
  output.** `print('task_id=' + task.task_id)` raises
  `TypeError: can only concatenate str (not "UUID") to str`.
  Always coerce: `print('task_id=' + str(task.task_id))` or use an
  f-string. The ledger survives, the diagnostic output does not —
  the right-hand side breaks first.

- **Do not treat a backend `success` as task completion.** A green
  verifier plus a green `hermes -p <profile>` exit is necessary, not
  sufficient. The orchestrator's explicit `accept` is what transitions
  to `completed`; without it, the task remains in
  `verifying` or `awaiting_acceptance` even if the child has exited 0.

- **Do not allow generic fallback for the default profile or
  `coder` by default.** `allow_generic_fallback=True` requires an
  explicit policy allowance recorded in the task's contract. The
  default is `False`; the prototype scope permits this only when
  every other specialist was rejected and the operator's
  fallback policy is recorded.

- **Do not select `noesis-orchestrator` as a worker for non-orchestration
  tasks.** The `policy_self_exclusion` table rejects
  `noesis-orchestrator` and `main-hermes` as worker targets. If the
  routing returns them as candidates, the selection is wrong; rebuild
  the capability index or fix the task's `required_capability`.

- **Agency profiles are advisory-only in the control plane.** Agency
  profiles appear in the capability index through the advisory registry
  adapter (tier `advisory`, source `agency-curation`), but their declared
  capability set is the converter's generic advisory set — never a domain
  capability string. Policy refuses any r2/r3 or irreversible assignment
  to them with `advisory_cannot_execute_consequential`. Route agency
  profiles to r0 advisory input only; never make one the executing
  assignee of consequential work, and never name one as `reviewer_profile`
  (they are not reviewer-only). Use them as optional advisory evidence
  feeding a Noesis specialist's node, not as a substitute for one.

- **Do not edit the TaskStore by hand.** Every transition goes through
  the control plane. A hand edit is undetectable by the controller
  and breaks the optimistic-concurrency contract. If a task is stuck
  in an unexpected state, use `Orchestrator.cancel(task_id,
  reason="manual_unlock")` or `Orchestrator.block(task_id, reason=...)`
  from a fresh controller, never a `sed`/`awk` on `tasks.jsonl`. Read the
  appended event back before claiming the transition succeeded.

- **Do not collapse working-tree change, local commit, publication,
  installation, and activation into one status.** Verify each boundary
  separately: changed bytes, local commit identity, remote branch/PR, merged
  source, installed bytes, enabled runtime, and live identity proof. Permission
  to create a local conventional commit does not authorize push, PR creation,
  merge, installation, or activation. A green worker exit is only a self-report;
  read the result artifact and verify the exact boundary it claims. The
  orchestrator never fills missing implementation or commit work itself—route a
  bounded successor task to an eligible executor.

- **Do not re-attempt with the same idempotency key after a crash.**
  A crash during spawn records a `quarantine` event with reason
  `handle_uncertain` (F-1 fail-closed). A subsequent `route_and_launch`
  with the same `idempotency_key` is rejected by the quarantine gate
  with `RoutingBlocked("quarantined")`. Use a new key (e.g.
  `<user>:<scope>:<hash>:attempt2`) for a fresh attempt after manual
  review of the partial work.

- **Describe provider use literally.** A direct Forge/Sentinel/Skeptic child
  session is an inference/provider call even when it is only development or
  review. Distinguish it from a provider-readiness probe, live production worker,
  installation, or activation; never summarize an inference-backed workflow as
  “no provider call.”

- **Policy lane names are not Hermes provider ids.** The spawn gate
  compares `approved_provider` to the policy lane name, while `hermes
  --provider` requires a provider id from `PROVIDER_REGISTRY`. Before
  declaring that boundary broken, read `hermes_provider_for_lane` and
  the launcher call site. If the mapping is present, pass the lane name
  to the gate and the mapped provider id to Hermes. If the mapping is
  absent, stop and report that missing map. Do not cite a stale
  "no mapping exists" note as a current blocker, and do not skip
  reconciliation gates because the map exists.

- **Operator-authorized ledger-recorded direct launch (degraded route when
  canonical spawn is broken).** With explicit operator approval only: (1)
  propose + approve the task in the canonical ledger with a `degraded_dispatch`
  label and the route deviation recorded in the intent; (2) launch directly as
  a tracked background process `hermes -p <profile> chat --provider <hermes-
  provider-id> -m <model> -q "$(cat <contract.md>)"` on the freeze-permitted
  observed lane; (3) inspect the session output for any `Model fallback` to an
  unapproved lane — that is `dispatch_not_delivered` even on exit 0; (4) parse
  the final stream result and verify artifacts yourself before closeout; (5)
  walk the state machine `enqueue → claim(claimed_by=assignee) → start →
  submit_handoff → submit_candidate → accept`, then prove durability with a
  fresh ledger replay. Keep the contract Rich-safe (no raw square/angle
  brackets outside code fences) or the CLI crashes before the model runs.

- **Treat an aborted turn with zero worker tool calls as
  `dispatch_not_delivered`, not as implementer failure, failed audit, or reviewer
  verdict.** Initialization banners — including a `system.init` record naming
  the requested model — prove only CLI initialization, not which backend handled
  the generation. Inspect the final structured result, token counts, provider
  error text, assistant tool-call count, authorized write scope, and required
  result artifacts. An unsupported-model, quota, timeout, or billing rejection
  with zero tokens remains non-delivery even when Hermes created a resumable
  session or displayed the requested model name. Preserve the process log and
  resumable session identity, block the unsatisfied task through
  `Orchestrator.block(task_id, reason=...)`, and read back the `task_blocked`
  event. Create a successor with a new idempotency key only after the operator
  authorizes an available route or a pre-authorized retry budget applies. Never
  mark the missing assignee artifact complete or spend another provider turn
  merely to repair the record.

- **Do not bypass a refused guard to make a drill or apply pass.** When a
  companion script or drill refuses, the refusal IS the evidence: read the
  actual message, fix the fixture or the precondition, and re-run. Most
  "failures" in a fixture drill turn out to be harness errors (fixture
  shaped unlike the real preimage, fixture left in a mutated state by a
  prior drill) — resetting to pristine and re-running is the repair, not
  editing the guard.

- **Never infer worker success from a shell pipeline exit code.** Commands such
  as `hermes ... | tee log` and `... | tail` normally return the final filter's
  status, so the shell can report zero while Hermes' structured result carries
  `exit_code: 1` or `exit_code: 130`. Enable `set -o pipefail` when the shell
  status is part of evidence, and in all cases parse the final stream-JSON
  `result` record; classify delivery from that record plus tool calls and
  artifacts, not from the wrapper process status.

- **Do not equate profile-name attestation with loaded specialist identity.**
  `requested_profile_id == loaded_profile_id` is necessary but insufficient:
  compare the manifest digest and profile path under the exact child
  `HERMES_HOME` used at spawn. Attesting the installed profile and then
  launching from a different isolated home can silently replace specialist
  instructions, tools, skills, and memory configuration while preserving the
  same profile name. Refuse before inference when the spawn environment cannot
  prove the approved identity-bearing bytes, and test both installed/isolated
  mismatch and a minimal name-only profile as negative cases.

- **Do not stage `git add -A` in a noesis-orchestrator session.** A
  mixed-domain task that includes implementation produces a coding
  subagent; the coding subagent stages its own files. The orchestrator
  should not touch the working tree of any other agent.

- **Record the live closeout through the state-machine API, not store
  edits.** After the child exits: `submit_handoff(task_id, handoff={...})`
  → `submit_candidate(task_id, candidate_revision=..., candidate_digest=...)`
  (moves to `awaiting_review` when a reviewer is set) →
  `record_review(task_id, stage="spec", verdict="PASS", reviewer=...,
  candidate_revision=..., findings=[...])` → quality `APPROVED` →
  `accept(task_id, operator="noesis-orchestrator")`. The class is
  `Orchestrator` in `app/control_plane.py`. Restart-equivalent recovery is
  free: constructing a fresh `Orchestrator(ledger_path=...)` replays the
  JSONL ledger and reconstructs state — prove it after any closeout.

- **Size the lease for the whole cycle, not just execution.** The claim
  lease starts at dispatch; reviews and acceptance happen after the child
  exits but before `accept`, and `accept` refuses an expired lease by
  design with no re-claim path from `awaiting_review`. A timeout that
  covers only the specialist run will strand a fully reviewed candidate.
  When a lease does expire mid-review, close honestly (ledger left at
  `awaiting_review` with full chronology, operator decides between
  designed-halt closure and a separately authorized re-attempt) — never
  force the state or hand-edit the claim.

- **Build reviewer packets as files with artifacts inlined
  programmatically.** `write_file` writes content literally — a
  `$(cat file)` placeholder embedded in written content is NOT expanded
  and ships as broken prompt text; inline diffs via a python/shell
  `replace()` step instead. Invoke reviewers detached and tracked from
  the outset (`HERMES_FALLBACK_HOME=<isolated> nohup hermes -p <profile>
  --provider <lane> -m <model> -z "$(cat packet.txt)"` as a background
  process with notify) — foreground timeouts kill reviewers mid-verdict.
  A working-tree candidate's identity is `git diff > candidate.diff` +
  `sha256sum candidate.diff`, recorded as the candidate digest.

- **Report real dispatch identities and limits, never "dispatched,
  awaiting next turn."** A dispatch claim is only real once the tool
  result gives you a process identity (PID or session id) and a
  deadline; cite both. If no identity came back, the dispatch did not
  start — say so instead of implying it is running. Conversely, verify
  with `pgrep`/`ps` before claiming any dispatch has finished, and if
  a blocked workstream has an independent authorized alternative,
  continue that alternative rather than stalling the whole loop.

- **Respect one-shot terminal execution guards.** If a one-shot Hermes
  session blocks a multi-line heredoc before execution, record it as a
  blocked tool call—not as a test result—and do not loosen global approval
  settings or repeat the same command. Use file tools for reads and rewrite
  required diagnostics as quoted `python3 -c` or simple shell commands; keep
  the same authorized session, scope, and retry budget, and preserve the
  refusal in the execution chronology.

- **Treat a dispatch that crashes inside the Hermes CLI as a no-op,
  not a failed implementer.** A prompt that contains literal
  `[...]` argv samples, angle-bracket placeholder lists, or any
  other Rich-markup-shaped token will be parsed by the CLI's Rich
  console (`cli_single_query.py::_run_single_query_mode`) and crash
  with `rich.errors.MarkupError` before the model is invoked. The
  process exits non-zero, no specialist runs, no source is touched,
  and no result file is written — so a non-zero shell exit alone is
  not evidence the implementer failed. **Sanitize every contract
  prompt before `hermes -p <profile> chat -q <contract>`**:
  rephrase bracket-list examples in prose ("a five-element argv
  containing the interpreter, the probe path, the uid, the gid, and
  the target"), or escape the whole prompt (`hermes chat -q "$(cat
  contract.txt | sed ...)"`), and after any non-zero dispatch
  `grep -nE "MarkupError|Traceback" <dispatch.log>` before treating
  the implementer as the failing component. The first signal of this
  class of failure is the absence of any `not_self_approved: true`
  receipt at the documented path.

- **Use a per-prompt Rich-markup audit when contracts grow long or
  contain code samples.** Before dispatching any contract > ~1 KiB,
  run a one-liner that lists every `[/...]` and `<...>` token in
  the file: `python3 -c "import sys;t=open(sys.argv[1]).read();
  print('brackets=',t.count('['),'closing=',t.count(']'),'lt=',
  t.count('<'),'gt=',t.count('>'))" <contract>`. Any non-zero count
  in a contract that does not deliberately demonstrate markup
  parsing is a latent dispatch crash; rephrase before launching.
  This is cheap and has caught a Rich-crashing contract that would
  otherwise have wasted a 35-minute implementer lease.
- **The raw count is necessary but not sufficient — run a fence-aware
  per-line audit before dispatch.** A `count('[')` only flags markup
  candidates anywhere in the file, including tokens that are safe
  inside ` ``` ` code fences and inside backticked command samples.
  Rich parses the prompt text surrounding fences, not fences
  themselves, but it DOES parse inline-backtick spans — so a
  `<tmp>/perm-0700` inside `` `/usr/bin/python3 … <tmp>/perm-0700/target` ``
  will crash the CLI even though it is "inside a backtick." The
  fence-aware audit walks the file and prints every `[`, `]`, `<`, `>`
  that appears outside any ` ``` ` line, with line number and 30 chars
  of context: `python3 -c "p=open('contract.md').read();in_code=False;
  flag=[]
  for i,ch in enumerate(p):
    if i+3<=len(p) and p[i:i+3]=='\`\`\`': in_code=not in_code; continue
    if in_code: continue
    if ch in '[]<>': flag.append((p[:i].count(chr(10))+1, ch, p[max(0,i-30):i+30].replace(chr(10),' ')))
  [print(f) for f in flag]; print('count=',len(flag))"`. The dispatch
  is safe only when the printed count is zero; a non-zero count
  inside non-code regions means rephrase before launch. The same
  rule applies to angle-bracket comparison operators in code
  examples (e.g. `len(argv) < 4`) when they sit in an inline backtick.

- **Plugin tool refuses `no_configured_ledger` in a desktop session:
  use the CLI mirror with explicit env, scoped to the invocation.**
  Hermes plugin tool hosts do not inherit profile `.env` bindings in
  desktop sessions (the gateway hot-reloads dotenv per turn; the desktop
  app does not), so the refusal can appear even when the profile `.env`
  correctly sets `NOESIS_TASK_LEDGER`. Verify the binding exists in the
  profile `.env`, then run the same handler through the CLI mirror.
  The CLI mirror must be invoked from the package directory with
  `PYTHONPATH=.` so the `app` module resolves — running from the repo
  root with no `PYTHONPATH` fails with `ModuleNotFoundError: No module
  named 'app'`. The working invocation is:

  ```bash
  cd ~/projects/noesis-agent-stack/orchestration/orchestrator && \
    NOESIS_AGENT_STACK_ROOT=~/projects/noesis-agent-stack \
    NOESIS_TASK_LEDGER=../../workspace/orchestrator/tasks.jsonl \
    NOESIS_TASK_EVENTS=../../workspace/orchestrator/routing-events.jsonl \
    INFERENCE_ROUTING_MODE=enforce \
    PYTHONPATH=. \
    python -m app.specialist_dispatch_cli \
      --input <payload.json> \
      --ledger <abs-or-rel-path-from-cwd> \
      --events <abs-or-rel-path-from-cwd>
  ```

  Use the project's own Python (`.venv/bin/python` is one option; the
  Hermes-installed 3.14 venv works if the project's deps are in
  `sys.path`); the `INFERENCE_ROUTING_MODE` must be scoped to the
  invocation, not exported globally. The contract JSON keys are exactly
  those accepted by `_make_orchestrator` in
  `app/specialist_dispatch_cli.py` — `title, intent,
  acceptance_criteria, verification, idempotency_key,
  required_capability, risk_tier, timeout_s, max_attempts,
  reviewer_profile, approval_required, parent_task_id, max_depth,
  allow_generic_fallback, dry_run, inference_routing_context,
  approved_provider, approved_model, workspace, expected_epoch` — a
  missing or extra key surfaces as a `TypeError` in `_make_orchestrator`
  *before* the policy gate runs, so a `success: false, code:
  type_error_payload` from the CLI is a contract shape problem, not a
  policy-state problem. Do not claim or assume a desktop restart fixes
  the binding, and do not introduce persistent environment or routing
  changes as part of the workaround.

- **`inference_denied → reconciliation_blocked` is a policy state, not
  a contract shape problem.** When the CLI mirror returns
  `{"success": false, "code": "inference_denied", "reason":
  "reconciliation_blocked: profile '<X>' is blocked in runtime
  reconciliation"}`, the contract is fine; the policy is refusing. The
  block lives in `platform/runtime-reconciliation.yaml` and is set when
  the profile's `repo_declared` config disagrees with the observed
  runtime config in a way the global catalog treats as drift (for
  example, the committed config declares `OPENROUTER_FALLBACK` while
  the catalog keeps OpenRouter `status: disabled`). Do not re-shape the
  contract (changing `approved_provider`/`approved_model`, removing
  `required_capability`, etc.) — the gate fires before any of those
  fields are read. The recipe is: (a) cite the exact `resolution.state:
  blocked` row and its `required_gates`; (b) name the drift (the
  committed `profiles/live/<profile>/config.yaml` line vs the installed
  `~/.hermes/profiles/<profile>/config.yaml` line); (c) offer the
  operator the two or three legitimate moves (reconcile the repo
  config to the observed runtime and amend the registry; authorize a
  one-shot override; or skip the dedicated slice and consolidate into
  a lane-permitted specialist); (d) wait. The orchestrator is not a
  privileged executor and must not edit profile configs, amend the
  freeze, or pick a non-eligible profile to force the dispatch through.

- **A timed-out or expired approval prompt is neither approval nor
  refusal.** When the operator does not answer an r2/r3 approval question
  within its window, proceed only with the scope that needs no approval
  (controller-local artifacts, read-only inspection, offline validation),
  keep every remote write and irreversible action held at the gate, log
  the posture decision in the nervous event stream, and end the turn
  with the exact prerequisites the operator must supply. Never widen
  scope because the operator was slow, and never treat silence as a
  yes: a gate that times out is closed until explicitly opened.

- **Native `delegate_task` children are a ledger-external route with
  self-reporting workers.** They are acceptable for controller-local,
  reversible artifact work while the canonical ledger route is
  spawn-blocked, or when the operator explicitly authorizes a degraded
  dispatch; they write no task ledger entry and their final summaries
  are unverified claims. The orchestrator must bind each child's
  identity and artifact paths in its own records, verify the artifacts
  itself before accepting anything, and name the route deviation in the
  final report. For code work, cross-check the child's reported
  changed-paths against `git status -s` and `git diff --stat HEAD` in
  the worktree — git is the authoritative changed set, and a self-report
  can omit a path that did change; the omission is either a reporting
  gap or evidence of an edit the report does not account for, and both
  must be resolved before the result is frozen or accepted. Never route r2/r3 remote mutations (SSH writes,
  installs, exposure changes, spending) through them without an explicit
  operator approval manifest.

- **Keep `delegate_task` `output_schema` flat, or omit it.** Deeply
  nested JSON Schema compositions (multi-level `properties` +
  `required` + `type`) fail the tool's schema validation and burn
  dispatch attempts one at a time; a one- or two-level schema — or none
  at all — passes, and the parent can hold the child to its reported
  artifact list by verifying files directly instead.

## Verification

Prove the skill worked with these checks (all read-only):

```bash
# 1. Specialist-routing fixtures pass through the real entrypoint
cd ~/projects/noesis-agent-stack
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_specialist_routing.py -q
# expected: 24 passed (13 representative tasks + 11 invariants)

# 2. Bootstrap launcher controls (crash, dry-run, quarantine) pass
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_bootstrap_launcher_controls.py -q
# expected: 23 passed

# 3. Quarantine gate is fail-closed (F-1)
.venv/bin/python -m pytest orchestration/orchestrator/tests/test_bootstrap_launcher_controls.py::test_crash_before_and_after_spawn_is_uncertain_and_does_not_relaunch -v
# expected: 1 passed; second route_and_launch raises RoutingBlocked("quarantined")

# 4. Full Noesis test suite is green
.venv/bin/python -m pytest orchestration/orchestrator/tests/ -q
# expected: 255 passed, 0 failed

# 5. The installed Hermes still carries the v3 prototype
cd ~/.hermes/hermes-agent
git status --porcelain | wc -l
# expected: 12 (6 REPLACE + 6 ADD; v3 prototype intact)
```

## Routing matrix (canonical 12-specialist + reviewer fixtures)

| Intent keyword(s) | Task class | Required capability | Selected specialist | Reviewer |
|---|---|---|---|---|
| mcp, hermes, agent, profile, prompt, routing | agent_architecture | profile_spec | noesis-architect | none |
| review, qa, security, audit, verify, validation | review | code_review | noesis-sentinel | none |
| implement, patch, code, test, python | implementation | code_modify | noesis-forge | noesis-sentinel |
| docker, k8s, observability, incident | operations | observability | noesis-substrate | noesis-sentinel |
| osint, timeline, provenance, public-source | osint | timeline_construct | noesis-tracer | noesis-skeptic |
| wallet, on-chain, crypto, protocol | crypto | protocol_research | noesis-ledger | noesis-skeptic |
| legal, advocacy, filing, administrative | advocacy | legal_research_support | noesis-advocate | noesis-skeptic |
| research, sources, cited, market, brief, evidence | research | cited_brief | noesis-signal | noesis-skeptic |
| csv, spreadsheet, chart, analyze data | data | structured_analysis | noesis-grid | noesis-skeptic |
| write, runbook, docs, documentation, changelog | writing | technical_writing | noesis-quill | none |
| comms, customer, external, message, announce | comms | comms_draft | noesis-herald | noesis-skeptic |
| plan, dependency, decompose, roadmap, phase | planning | plan_artifact | noesis-cartographer | noesis-skeptic |
| triage, priorities, status, deadline | chief_of_staff | triage | noesis-steward | none |
| archive, provenance, changelog, snapshot | documentation | archive | noesis-scribe | none |

Plus four invariant tests prove the negative space:

- `test_architecture_does_not_fall_back_to_default_or_coder` — no silent
  generic fallback.
- `test_every_policy_eligible_specialist_has_a_routing_fixture` — full
  roster coverage.
- `test_self_delegation_and_cycles_are_blocked` — orchestrator is not a
  worker target; cycles raise `RoutingBlocked`.
- `test_loaded_profile_mismatch_is_blocked` — identity attestation is
  the binding; an LLM saying "I am X" is not proof.

## References

- `references/credential-diagnostics.md` — exact-child credential reachability,
  route-readiness taxonomy, source convergence, workload/cost selection, and
  bounded provider-probe controls.
- `references/frozen-candidate-deployment.md` — two-stage
  install/port/rollout workflow for a frozen qualified candidate:
  read-only proposal artifacts, operator final-approval gate, phased
  execution (staging → source apply → validation) with rollback,
  cross-lineage port gating, and interruption recovery.
- `references/noncanonical-bootstrap.md` — explicitly authorized external
  development/review bootstrap when canonical implementers and reviewers are
  unavailable, including provenance, digest binding, and status separation.
- `references/native-delegation-enforcement.md` — verified mechanics of
  native `delegate_task` and the `advanced-delegation` `profile_routes`
  backend: child toolset derivation, leaf-role blocks, config-authoritative
  iteration caps, MCP inheritance, the restricted-parent zero-tool-child
  recipe, and the profile_routes configuration shape.
- `references/operator-packet-review.md` — approval-manifest structure
  (the twelve sections), the independent review-round procedure, the
  finding-to-revision discipline, and the reviewer fixture recipe for
  operator-executed launch packets.
