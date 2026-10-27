---
name: noesis-control-plane-dev
version: 1.4.0
author: noesis-orchestrator
license: Proprietary
description: "Use when changing Noesis routing or task lifecycle."
metadata:
  hermes:
    tags: [orchestration, task-ledger, delegation, control-plane, noesis]
    related_skills: [subagent-driven-development, test-driven-development]
---

# Noesis control-plane development and rollout

## When to Use

Use for specialist routing, TaskStore/delegation integration, planning, review
and acceptance gates, plugin exposure, and staged activation in
`~/projects/noesis-agent-stack`. These are verification requirements, not a
claim that the current implementation satisfies them.

## Procedure

1. **Re-establish authority and evidence.** Read repository instructions, the
   actual request-to-launch and result-to-acceptance paths, schemas, tests, and
   applicable inference/reconciliation policy. Treat prior pass counts and
   readiness reports as historical. Before dispatching repair from a contested
   candidate, verify both Git-object membership and worktree hashes: run
   `git rev-parse HEAD`, `git status --short`, `git show HEAD:<path>` for each
   claimed manifest path, and hash both the HEAD object and working-tree file.
   A candidate digest can be a working-tree/review snapshot rather than a HEAD
   object; preserve contradictory older claims but correct the gate ledger with
   file-by-file evidence. Identify the authorized implementation owner and
   independent reviewer before dispatch; do not substitute an inherited
   supervisor context for a named executor. For integration plans, inventory
   each candidate's verified branch/SHA, implemented entrypoints, persistence,
   scheduler behavior, external costs, and deployment ownership before assigning
   architecture; see `references/integration-planning.md` for the evidence table
   and budget-gated adapter pattern. For a read-only custom-versus-native
   release-path choice (smallest verified scope, competing-systems guard,
   preserve the nonselected backend as a frozen asset), see
   `references/release-path-decision.md`. For protocol-adaptable delegation
   amendments, follow `references/protocol-adapter-planning.md`: separate
   architecture intent, repository behavior, installed capability, and verified
   deployment; preserve Noesis authority above native/ACP/A2A transports; and
   amend the existing standing goal rather than creating a competing plan.
   For operator-authorized bounded adaptations to a prior candidate (v2 → v3, a new candidate with
   a small operator-named set of behavior-preserving edits), see
   `references/bounded-adaptation-flow.md` for the manifest-versioning
   discipline, the new-identity rule, and the fresh-review requirement.
   When the operator directs consultation of an internal wiki or knowledge base,
   orient from that wiki's `AGENTS.md`/resolver/index, search for the exact topic,
   and read the smallest relevant page cluster before implementation dispatch.
   Distill source-backed principles into concrete contract invariants (for
   example deterministic pre-action verification, durable external state,
   explicit ownership, observable refusal reasons, collision avoidance, and
   bounded stop controls), and cite the source paths in the handoff. Treat wiki
   guidance as advisory design input rather than execution authority; do not
   edit, ingest, log, commit, or push the wiki merely because it was consulted.
2. **Carry forward scoped decisions.** Record what the user already approved,
   its exact targets, prerequisites, and remaining gates. Continue authorized
   feasible work without offering the same choices again. A human provider
   correction is not independent security review. Resolve policy state names,
   enforcement mode, gate requirements, and decision authority from their
   actual consumers rather than labels alone. Do not equate fallback-only
   documentation with permission when the effective lane is disabled.
   Track executor readiness, reconciliation, implementation defects, and provider
   availability as separate blockers. Reconcile amendments by task id,
 idempotency key, candidate identity, and artifact identity before dispatch:
   attach a clarification to the existing task/review state instead of creating
 another attempt or review cycle. When approval grants exactly one additional
 provider/model turn in an existing live session, deliver one self-contained
 prompt through that session's already-approved route; do not launch a duplicate
 worker, change provider settings, or spend another turn to repair/report the
 result. Make the prompt fully self-contained against context compaction: it
 must carry the approval manifest path and its SHA-256, the sole writable target
 path, the exact corrections as a numbered list, the explicit stop condition,
 and the expected unchanged candidate digest — so a later session can deliver it
 verbatim without reconstructing any prior context. After the turn becomes idle,
 verify its persisted tool-call record and
 return only the operator-requested artifacts before stopping. Bound only what
 the authorization actually says: if the approval forbids dependency preparation,
 require the worker to keep the declared test command inside an existing, verified
 environment and report an environment blocker instead of invoking a setup
 wrapper; if a shared setup script cannot honor that, the bounded prompt must say
 so explicitly rather than relying on the script's defaults. Treat a setup
 wrapper's implicit preparation — such as a `pm sync` that exits `already in
 sync` with empty steps — as a preparation boundary violation when the approval
 forbade dependency preparation; the absence of downloaded components does not
 erase the boundary breach. Treat an interrupted-session record as proof
   that an attempt existed, not that its process is live; likewise, a handoff
   copied into a worker workspace is durable delivery, not worker acknowledgment.
   Record these states separately and do not label the task actively running
   without process/session evidence. Ask for quota confirmation only when it
   enables the next actionable gate; it does not resolve the others. When one
   approval contains contradictory numeric limits (cost, requests, turns,
   duration, or concurrency), hold only the operation that depends on that
   number and continue already-authorized offline work. Do not select the more
   permissive value or silently infer the lower one. Require an explicit
   correction, then persist a scoped amendment naming the authoritative value,
   what it supersedes, and when it expires; every later packet and enforcement
   check must use the corrected value and must not repeat the superseded one.
   If dispatch itself needs repair, prepare a manually initiated bootstrap for
   an independently authorized coding context rather than recursively using the
   broken launcher or inheriting the supervisor identity. Before launch, compare
   the implementation authorization with its held operations: an approval that
   authorizes source implementation while still prohibiting every provider/model
   request, worker launch, and supervisor execution has authorized preparation,
   not an executable coding route. Continue the safe preparation immediately
   (isolated worktree, frozen baseline, manifest, durable proposed/approved task),
   then ask one decision that names the exact bootstrap profile, provider/model,
   duration, fallback rule, child-session rule, and credential boundary. Do not
   infer that route from “go ahead.” When the operator amends a hash-bound
   manifest, block the old approved task as superseded and create a successor
   whose approval binds the new digest; never rewrite the old approval pointer
   in place or launch against stale authorized bytes.

   For a separately authorized direct Hermes bootstrap, use `--query-file` for
   the complete handoff (it preserves arbitrary prompt text without Rich/shell
   parsing), pass the exact `--provider` and `-m` pair, and prevent inherited
   fallback configuration. When the runtime has no dedicated no-fallback flag,
   `--ignore-user-config` with explicit provider/model and an explicit minimal
   toolset is the safe session-scoped shape: it preserves the selected profile's
   identity/rules while dropping its configured fallback chain. Record this as
   a bootstrap exception, not proof that canonical routing works. Start the
   process as a tracked background job with session/PID and wall-clock budget;
   only then mark it running. Do not require this bootstrap to prove normal
   routing; return ordinary execution to the repaired authoritative lifecycle
   afterward. If no execution context is verified, deliver a complete copy/paste
   repair prompt, not merely a request for an executor. See
   `references/bootstrap-handoffs.md` for the package checklist.

   Preserve provider and model identifiers literally from the operator's
   authorization; do not autocorrect a near-match. If the provider rejects an
   unsupported model before inference, preserve that dispatch result, make no
   code/task-state claims from it, and ask for the exact supported identifier
   rather than guessing. When the operator corrects the route while a successor
   is already active, treat the message as steering: do not interrupt a working
   process or launch a duplicate. A fallback is usable only when the operator
   explicitly authorizes it; keep it within the original total time/request
   budget, disable inherited automatic fallback, and start at most the named
   fallback after the primary attempt has definitively failed.
3. **Reproduce the defect before changing code.** Use the project's configured
   test environment: `uv run pytest orchestration/orchestrator/tests -q` or a
   targeted file. When dependency installation is prohibited, use
   `uv run --no-sync pytest ...` with the existing environment. A fresh git
   worktree has no `.venv` — invoke the main checkout's interpreter directly
   from the worktree's `orchestration/orchestrator` cwd
   (`PYTHONPATH= <main-checkout>/.venv/bin/python -m pytest tests/ -q`):
   clearing PYTHONPATH matters because a global PYTHONPATH pointing at a
   Hermes runtime venv shadows the project venv's dependencies (ruamel).
   Preserve the test process exit status; do not pipe it through a successful tail command.
   A verification-tool rejection means tests did not run, not tests failed or
   passed. Write failing behavioral tests before the smallest repair.
4. **Keep one authoritative lifecycle.** TaskStore/tasks.jsonl owns state.
   Trace every writer and reader before declaring another file a projection.
   An exporter alone does not disable an independently mutable legacy store.
   Derive projections from committed state; do not require non-atomic dual
   writes. Back up ledgers before migration, detect uncertain active work,
   retain identity/artifacts/audit history, and make migration restart-safe.
5. **Persist admission before execution.** Apply planning, approval, inference,
   dependency, budget, and workspace gates before invoking the launcher.
   Separate specialist selection from execution-configuration selection: first
   choose a role-eligible profile, then build a non-executing proposal for the
   exact provider/model, tools, skills, plugins, MCP servers, data destinations,
   and aggregate limits. Compare alternatives through a cached, versioned
   capability snapshot rather than probing the fleet on every dispatch. The
   proposal must resolve to one typed result: keep, task-scoped override,
   alternate specialist, approval required, or precise block. Treat configured,
   installed, effective-process, and observed-runtime state as separate facts;
   authentication is not quota, missing quota evidence is `UNKNOWN`, and an
   aggregator does not count as an independent backup until its upstream failure
   domain is known. Freeze the approved configuration to the admitted attempt;
   route changes after admission require an audited transition or new attempt,
   never an opaque runtime fallback. See
   `references/adaptive-configuration-readiness.md` for the full preflight,
   readiness, failover, and report-only audit design.
   Persist assignment/attempt and launch intent first. Reserve budget before
   paid inference or external execution where supported; dashboards may display
   budget state, but dispatch/adapters must enforce it while the dashboard is
   offline. Record verified runtime identity afterward; do not retrofit a
   running assignment after the process has already finished. Replays of
 uncertain launch intent must block or reconcile, never blindly relaunch.
 Count physical transport or adapter invocations—not merely reservations—in
 duplicate-dispatch tests: admission idempotency can return the same admission
 twice while still allowing two physical requests. Test duplicate admission
 delivery before one request separately from a genuinely new transport attempt,
 and prove reuse of an admission identity cannot exceed the physical-attempt
 allowance. If the published interface cannot represent that distinction,
 stop with an interface-change proposal instead of silently redefining it.
6. **Audit every completion entrypoint.** Require explicit supervisor
   acceptance of valid evidence and current-revision reviews. Inspect legacy
   `succeed`, direct store writes, and alternate handlers as well as `accept`.
   Match positive verdicts explicitly: spec requires PASS, quality requires
   APPROVED. Test BLOCKED, REQUEST_CHANGES, missing, and unknown values as
   failures; a lookup returning the supplied verdict is not a safe predicate.
   Verify actor/session authority, candidate digest binding, invalidation,
   unresolved findings, and termination evidence. A caller-supplied name is
   not authenticated authority; different names alone do not prove independent
   review contexts.
7. **Update persistence and schema together.** Extend dataclass serialization,
   published JSON schema, and TaskStore rehydration in the same change. Test
   round trips and old records; absent evidence remains unknown, never an
   invented approval. Preserve one source of truth for shared reservations.
   Unknown usage must remain unknown even when another attempt reports usage;
   post-hoc counters are not pre-launch spending enforcement.
8. **Verify at the correct boundary.** Mock the process-spawn boundary for
   hazardous crash tests, not the controller/store. Exercise the real plugin
   handler and dispatch entrypoint. For offline tool exposure, assemble the
   final model-facing schemas through the CLI loading path in an isolated
   home: registry membership alone is insufficient. Validate schema, exact
   multiplicity, disabled/invalid registration, and profile isolation. Do not
   call a post-discovery membership check a warning reproduction or a live
   canary. See `references/verification-boundaries.md` for the evidence matrix; see
 `references/bootstrap-handoffs.md` for the handoff checklist; see
 `references/repair-mechanism-inspection.md` for the per-finding mechanism
 inspection table and BLOCKER format.
9. **Run and report actual verification.** Compile edited modules with
   `uv run python -m py_compile <edited .py files>`, then targeted regressions
   and the full suite. Inspect the scoped diff, including whitespace, using
   permitted editing tools for corrections. Report commands, exit statuses,
   counts, untested boundaries, and artifact paths. Never promote a green
   suite to proof of requirements it does not assert. For cross-repository test
   fixtures, pass reconstruction roots through explicit, narrowly named
   environment variables and assert module origins; do not accept a green run
   produced by path-constructor or `sys.path` redirection. See
   `references/clean-reconstruction.md` for the fixture-repair pattern.
   For the decision layer offline evaluation pattern (SHADOW runner, FakeReplayProvider
   reuse, event log, freeze manifest with per-file SHA-256), see
   `references/decision-layer-evaluation.md`. For installation/port proposals
   invalidated by a destination-HEAD drift between inspection and execution, see `references/drift-port-proposal.md` for the halt-on-drift pattern, the re-bind cycle, and the source-of-truth discipline for overlay bytes. For the operator-authorized bounded offline compatibility check against the installed baseline (the verification step that follows the drift-authorized re-emit), see `references/bounded-compat-check.md` for the three-layer staging model, the per-hunk annotation heuristic, and the finding-classification discipline.
10. **Roll out through distinct gates.** Separate working-tree implementation,
    local commit, publication, offline complete, policy eligible, live verified,
    deployed, observation complete, and fully accepted. An authorization for a
    local conventional commit does not authorize push, PR creation, merge,
    installation, activation, or live execution; report each boundary by its
    verified evidence rather than collapsing them into “done.”
    Verify provider recovery and limits under the user's probe constraints;
    do not silently use the parent session's provider. Before calling a router
    live, reconcile four independent surfaces: repository plugin bytes, installed
    plugin bytes, plugin enabled state, and profile toolset exposure. A green
    direct CLI dispatch proves the control-plane/launcher path, not that the
    model can see the plugin tool. Use the authorized model-driven dry-run, then
    reviewed execution, then persistent activation. For a temporary plugin
    canary, follow `references/specialist-plugin-canary.md`: snapshot exact
    bytes and state, classify pre-delivery failures separately, and restore by
    content rather than trusting command success.
    Resolve the affected process and supported reload mechanism first. Preserve
    prior configuration and ledger-compatible rollback. Keep unverified coding
 backends disabled; specialist-native success does not verify them. Report
 an incomplete observation window honestly. If a gate blocks live work,
   finish feasible offline work and request only the precise remaining action.
   For the prodqual loopback target's authorized apply, use
   `references/prodqual-apply-runbook.md` — the approval-time extra-var
   binding, the Ansible config selection that avoids the repo-root vault
   reference, the live destination preflight checklist, and the same-UID
   prototype-label halt that must be resolved by the operator before any
   re-attempt. After clean reconstruction and every required independent review passes, request the exact installation/port proposal for that pinned identity; do not treat qualification as installation authority. If dependency discovery exposes a code defect, authorize or request only the bounded repair, then reconstruct and re-review the changed identity. If an environment prerequisite is missing, request the specific environment setup rather than permission to alter the candidate. Do not loop through unchanged status reports, rerun already-current tests/status checks, or poll for absent results while awaiting an external executor or decision; repeated restatement of the standing goal is not a new authorization. Present the unresolved material choice once through `clarify` with the recommended option first, then stop until the operator answers rather than producing another prose blocker digest.

## New Noesis profile registration discipline

Creating `~/.hermes/profiles/<name>` is installation, not complete stack
registration. For every new native profile, update the canonical roster entry,
`agents/<name>/SOUL.md`, `agents/<name>/agent.yaml`, sanitized
`profiles/live/<name>/` snapshot, runtime-reconciliation record, fleet counts,
and the orchestrator's delegation/discovery metadata in one isolated branch.
Run the repository's inference-routing validator first: a new roster identity
without reconciliation must fail as missing rather than being waved through.
Then parse every changed YAML file, run the targeted registry-admission tests,
run `git diff --check`, scan the staged artifacts for literal secrets, and
commit only the narrow profile delta. Keep the operator's dirty checkout
untouched by using a separate worktree, and verify both worktrees at the end.

For the installed profile, clone only as a bootstrap: replace the source
identity, remove inherited MCPs/plugins/toolsets that the role does not need,
run `hermes -p <name> config check`, verify profile-local Honcho isolation, and
complete an exact provider/model canary. A successful `profile create` banner
is not proof that cloned Honcho identity, workspace, provider route, or tool
exposure is correct. Repository snapshots must contain settings and secret
references only; if an existing "sanitized" snapshot contains literal
credentials, report it as a separate security finding and never copy those
bytes into the new profile.

## Filling the ledger for out-of-band-executed work

When an executor reported evidence by writing artifacts directly (never called
`submit_candidate`, lease lapsed during the review), do not write terminal state
out-of-band either — drive the repair through the state machine (`block → enqueue →
claim → start → submit_candidate → record_review → accept`) so the acceptance gate
and review provenance stay authoritative. See
`references/out-of-band-task-closeout.md` for the exact sequence, the
`app`-package import root, and the required verdict tokens.

## Test construction details

- For citation/source-reference outputs (receipts, planner decisions, audit records), assert the CITED CONTENT — the referenced records, keys, and values — not only the top-level verdict/disposition. A coercion can preserve the disposition while silently dropping or mangling the evidence (e.g. `value = d.get(k) is True` erases the raw value before it is cited); printing the full payload in a demonstration/demo run is how such gaps surface, so run one demonstration that dumps every field a consumer reads.
- Read capability declarations and fixture definitions before constructing
  contracts; do not guess capability strings or fixture names. Know the
  admission mechanism: `policy.validate_assignment` only enforces capability
  when `profile.capabilities` is non-empty, so a registry adapter that
  registers a profile with an empty capability set silently bypasses
  capability admission — adapters must fail closed (raise) when their source
  declares no capabilities. When the fleet's converter emits one generic
  capability set for a whole profile family, bind tasks only to those declared
  strings and carry the domain distinction in intent and labels; never invent
  per-domain capability strings to make a workflow fit.
- Keep forced lease-expiry values as datetimes, because runtime comparisons
  expect datetimes rather than ISO strings.
- Never write a secret-shaped literal into any source under
  `orchestration/orchestrator/` — `test_schema_conformance` scans every `*.py`
  and `*.md` there for secret patterns, so a negative test for secret
  detection trips the repo-wide scan itself. Construct the token dynamically
  at test runtime (string concatenation across literals defeats the static
  regex while still exercising the detector).
- Before treating a full-suite failure inside a fresh worktree as a
  regression, check whether the failing test reads a fixture under `workspace/`:
  `git ls-files <path>` empty means the fixture is an untracked local artifact
  that no checkout contains. Copy it from the operator's main checkout to run
  the suite, and report it as an environmental defect — do not edit the test
  to tolerate the missing file.
- **A non-strict `xfail` marker on an already-repaired defect reports XPASS
  forever.** The gate-defect regression file marks known defects
  `xfail(strict=False)`; when the underlying production fix lands, the test
  starts passing but pytest reports XPASS — outside the passed count and
  still labelled "known broken". A suite whose baseline includes XPASS is
  misreporting a fixed defect as open, and any count assertion written
  against it drifts. Investigate every XPASS against the production code
  before trusting the baseline: confirm the repair is present, then remove
  ONLY that stale marker so the test counts as a real pass, and keep the
  markers for defects that are still open. Removing a marker for a still-open
  defect is manufacturing green — verify by running the affected tests in an
  isolated copy first: the de-markered test must pass, and the still-open
  defects must keep failing.
- **Build the CI environment before writing the CI workflow.** A suite that
  depends on the developer's installed package, an ambient `PYTHONPATH`, a
  real `HOME`, or a local fixture will fail the first time a runner sees it.
  Reconstruct the environment hermetically (own interpreter, pinned
  dependencies, isolated `HOME`, fixtures materialized from tracked
  repository content, tooling first on `PATH`) and run the suite there
  BEFORE authoring the workflow. Run the identical command on the base tree
  in a detached worktree to separate pre-existing environment coupling from
  candidate regressions, and record both numbers. See
  `candidate-ci-coverage` for the full recipe and the skip/xfail/xpass
  baseline accounting.
- Pair source-level findings with behavioral regressions. Label a finding
  source-confirmed until the regression actually runs.
- **Probe authorization semantics at the final spawn boundary, not just at the
  policy helper.** For bounded non-dry-run launch, add behavioral regressions
  proving that missing enforcer initialization, observe/shadow decisions, a
  policy-resolved provider/model mismatch, omitted or stale assignment epoch,
  and candidate/policy snapshot drift all reject before spawn. Read the actual
  routing-decision dataclass before binding fields — checking guessed attributes
  with `getattr(..., None)` can turn a real mismatch into `None == no check` and
  silently authorize the launch. An optional freshness argument is not a gate
  when the normal CLI/plugin caller can omit it; require and test it through the
  real caller surface. Direct `_assert_spawn_gates` tests are useful reproductions
  but do not replace CLI/plugin regressions.
- For SQLite-backed governed accounting, inspect the actual connection isolation
  level, context-manager behavior, SQL statements, and commit points before
  describing transaction semantics; absence of explicit `BEGIN`/`COMMIT` does
  not make an autocommitted statement transactionless. Test explicit provisioning
  separately from ordinary reopen, and test main-database deletion separately
  from WAL-only and SHM-only deletion because those failures are not equivalent.
  Promise observability outside unavailable primary storage, not an impossible
  durable marker within it. State the trusted-owner boundary explicitly: WAL
  locking and ordinary permissions do not defeat a malicious same-authority
  writer.
  - Audit historical acceptance after discovering a fail-open gate. Compare the
  verdicts valid for the candidate at acceptance, not an earlier failed review
  that was superseded by remediation. Report exact audited paths and gaps;
  absence at the default ledger path does not exclude caller-supplied ledgers.
  Preserve history and request the exact corrective event if safe append-only
  invalidation or downstream dependency handling is not established.
  - Direct lifecycle-helper tests supplement, but do not replace, tests through
  the normal router/plugin request and result paths. Treat an import or re-export
  of a lifecycle helper as wiring evidence only: trace every production
  transition call site, persistence writer, replay fold, and acceptance gate,
  then drive each invariant through those real paths. Otherwise a helper can be
  locally correct while production keeps enforcing the old lifecycle.

- **Lease semantics for lifecycle/planner changes**: a lease gates execution, not review. Once a candidate is submitted (`verifying`), the execution attempt is over — an active-attempt check that treats a live lease in `verifying` as 'still executing' starves review proposals; the correct test is `state == running AND lease active`. `expire_lease` on a running task must move it to `blocked` (suspect), never silently succeed. Also note the store drops reviews bound to a superseded candidate on candidate change, so scope-mismatch references can only arise from externally ingested rows — tests must inject those rows deliberately rather than expecting store transitions to produce them.

- **Lease-lifecycle changes (execution vs review/acceptance authority)**: before recommending any lease/timeout change, enumerate every call site that consults the lease (`grep -n "lease_expired\\|lease.is_active\\|lease is not None" app/`) and classify what each gate protects. A single `timeout_s` spanning claim→dispatch→running→review→accept conflates execution freshness with review/acceptance authority: review is external and unbounded, so a valid, fully-reviewed candidate can outlive the lease through no fault of the worker, and acceptance is then refused by design. Do not fix this by raising the timeout (hides latency variance, keeps the wrong invariant) or by adding renewal (extends execution authority during review). The correct shape: execution lease released one-way at candidate submission (epoch-stamped), stale worker reports rejected by attempt epoch rather than wall-clock, and acceptance gated on current-candidate reviews + current epoch + orchestrator identity — never on lease liveness. A designed halt here (acceptance refused on expired lease with green reviews) is the safety property working; preserve it as evidence — do not retroactively accept, renew the lease, or rewrite timestamps to make the run appear end-to-end successful, and record timeout-sizing as a design finding instead.

- **Event/result model fields are capability-index defaults, not the launched pair**: the dispatch result and routing event carry `model_provider`/`model_id` from the capability-index selection, while the actual launch command uses the approved per-task pair. Cite `launch_command` + launcher attestation as execution evidence; never cite the default fields.

- **Reviewer lane-switch discipline**: when a reviewer invocation on one provider lane yields no verdict twice (foreground timeout kill; detached run exiting 130 with banner-only output), switch lanes rather than retrying the same one — reviewer identity is the profile, the model lane is a provider choice. Preserve each failed attempt's output file as evidence, and extract the verdict by grepping the `VERDICT:` token, because output files begin with secret-manager banners and tailing the end can miss a verdict printed early.

- **Handoff-packet snapshot identity (revision refs are not content identities)**: an abbreviated commit range like `abc1234+def5678` is a revision reference, never a sufficient standalone identity for an operator-mediated review packet. Before freezing any packet, compute: (a) full 40-char revisions for every commit in scope; (b) per-file sha256 of each reviewed file at the tip via `git cat-file blob <tip>:<path> | sha256sum`; (c) a combined snapshot digest over the name-prefixed concatenation of the reviewed files PLUS their frozen code dependencies (e.g. the module the reviewed code imports); (d) a later-change inspection `git log <tip>..HEAD --name-only` proving no later commit touches the reviewed code or its dependencies; (e) `git status --porcelain` for the reviewed paths. Verify the snapshot digest BEFORE the review starts and after it returns. See `references/review-handoff-identity.md` for the exact command recipe.
- **Dirty-worktree candidate manifests must separate identity from evidence metadata**: create a pure `candidate-files.sha256` containing only final `hash  path` rows and verify it with `shasum -a 256 -c`; keep baseline, test chronology, unavailable-linter notes, and scope declarations in a separate evidence manifest. Build the review patch from tracked AND new candidate files — ordinary `git diff` omits untracked files, so append a `git diff --no-index --binary /dev/null <new-file>` fragment for every new file. Reverify the pure manifest after the last documentation edit; any byte change creates a new candidate identity and invalidates pending verdicts. Follow `references/protocol-adapter-planning.md` for the bounded offline adapter-contract slice and review-freeze sequence.
- **Per-file content hash: use `git show` or `git cat-file blob`, never `git ls-tree ^{tree}`**: the `git ls-tree <commit>^{tree} -- <path>` form returns the SHA of the **tree entry blob** that points at the file, not the file's actual content. That blob SHA is computed from the file's mode + path + content and is normally identical to the content SHA, but a small change in tree construction (e.g. a different mode bit, a directory rearrangement) can produce a different blob SHA for the same content. The two safe forms for per-file content sha256 are `git show <tip>:<path> | shasum -a 256` and `git cat-file blob <tip>:<path> | sha256sum`. Use one of those. The wrong form silently breaks recipe reproduction — every per-file hash matches the documented table, the combined digest does not, and the discrepancy is in the tree-entry encoding, not content drift. Same recipe applies to any combined-digest verification (planner, A6 v3, lease-lifecycle, etc.).

- **Combined-digest recipe: never let `sort` over raw `sha256sum` output stand in for the documented sort over `path:hash` lines**: a one-liner that pipes raw `sha256sum` output through `sort` and then rewrites each line as `path:hash` is sorting the raw bytes (by hash), not the canonical `path:hash` lines (by path). The combined digest will diverge from a recipe that was documented over sorted `path:hash` lines even when every per-file hash matches the table. The discrepancy is in the recipe encoding, not content drift. Build the canonical recipe text exactly as documented — for the planner-digest style: `printf 'path:hash\n...'` in alphabetical path order, then `sha256sum` over the joined bytes. If a recipe file shows a one-shot shell snippet that sorts raw output, treat it as a doc bug in the example, not a contradiction of the canonical recipe text. Validate the recipe before declaring a digest mismatch to be a real drift.

- **Never `bool()`-coerce authoritative booleans at replay**: `bool("false")` is `True`, `bool("yes")` is `True`, `bool(0)` is `False`, `bool(None)` is `False`. Wrapping `data.get(key, False)` in `bool(...)` silently turns present-non-bool values into authoritative facts: a lease recorded as `"revoked": "false"` replays as revoked, a task recorded as `"accepted": "yes"` replays as accepted and the planner reports `completed_within_scope`. The fail-closed shape is the pattern already in `TaskStore._optional_execution_revoked`: present and `isinstance(value, bool)` → use it; present and not bool → raise `ValueError`; absent → documented default. Apply the same shape to every authoritative boolean parsed from a durable record (`accepted`, `revoked`, `quarantined`, `approved`, `blocked`). When the contract permits "absent → default," do not coerce the absent branch through `bool(default)` either; pass the default through the same type check or use an explicit `if "key" not in raw: return default` so the default never silently swallows a present-malformed value. Silent rewriting of historical records at replay is a fail-open defect; provenance for diagnostics is preserved by carrying the raw value into the replay error, not by coercing it.

- **Advisory adapters must be authority-isolated, not just data-minimal**: any read-only retrieval/ranking/copilot layer (Jev, embedding recall, a council scorer, an LLM summarizer) integrated with noesis imports only the read-only projection (`GraphProjection` / `GraphQuery`); it never imports `TaskStore`, `DelegationStore`, or any module that can mutate authoritative state. The shipped payload to the external backend is fingerprints only — entity_id, type, evidence_state, scope — never raw record bodies, lease timestamps, approval manifest IDs, or finding descriptions. Withhold **identities of access-filtered records too**, not just their contents: report only the count to the external backend, never individual entity_ids, so the backend cannot derive what it was filtered from. Mandatory exact-identity evidence is returned to the caller before the adapter is consulted and cannot be demoted, excluded, or reranked by any probabilistic signal — if the adapter's stop reason is "enough" while a mandatory record is missing, that is a false-sufficiency defect. The adapter is never a mandatory dependency for noesis operation; on timeout, malformed output, outage, or budget exhaustion it falls back to a deterministic baseline that does not touch the external backend. Confidence returned by the external backend is a model signal, not proof of correctness or permission.

- Quarantine writer-to-gate wiring discipline: when implementing or reviewing quarantine behavior, trace the full path from every production failure handler to the canonical quarantine writer to the replay handler to the admission/dispatch gates. A common defect pattern is: (1) production path emits a different event type than replay folds; (2) append_control_event updates the JSONL but not the in-memory gate set; (3) tests inject the event directly rather than driving the production handler; (4) malformed records are ignored rather than failing closed; (5) duck-typed gate methods silently skip when absent. Each of these is a separate fail-open. Verify all five are closed before claiming quarantine is effective.

- Bounded integration opening-plan discipline: when the operator authorizes bounded development integration (not just repair), produce a code-grounded opening plan BEFORE any implementation dispatch. The plan must identify: exact repository revisions and workspace locations; actual registered implementation/reviewer profiles; supported dispatch and execution routes; authority ownership and filesystem/process boundaries; proposed files and interfaces; tests, numeric process limits, and wall-clock limits; recovery and stop conditions. State explicitly which integration invariants map to which enforcement mechanisms. If the plan requires broader permissions or an interface-contract change, stop the affected branch and request exact approval — do not proceed silently. The plan file is an audit artifact: record its SHA-256 in the ledger. When the operator requests a pre-implementation clarification pass, append it as a separate appendix to the SAME plan file (do not fork the plan); recompute and record the new plan SHA-256 after each append.

- Additive interface-change discipline: when an operator authorizes an additive field on a versioned interface (e.g. `fresh_execution: bool` on `AdmissionResult`), record BEFORE editing: (a) schema/version treatment — the interface version stays unchanged only if the change is purely additive with no semantic break; (b) the exact compatibility rule — what existing integrations receive for the new field and what they must NOT silently interpret it as; (c) fail-closed validation — e.g. `__post_init__` raising when `admitted=True` and the field is `None`, so a missing value can never authorize execution; (d) the authorization scope — prototype-only, no other semantics altered. Resolve sketch-level contradictions (e.g. a `bool = False` default combined with an `is None` check is a dead validation) by re-reading both stated requirements and choosing the reading that satisfies ALL of them (e.g. `Optional[bool] = None` with explicit-on-admit and denial-normalization-to-False); record the resolution as a deviation, not silently.

- **Defect-in-existing-code vs defect-in-proposed-design**: when receipt verification surfaces a replay/persistence defect, determine whether the defect is ALREADY LIVE in shipped code or would be INTRODUCED by the new design. Read the actual replay/fold code path and the actual existing writer (e.g. an existing task-mutation writer may be replayed correctly while a proposed `append_control_event` writer would be ignored). State which one carries the defect; do not blanket-label the whole area defective. If the existing path is correct and only the proposed path is defective, the correction belongs in the design, not the shipped code.

- **Bounded-adaptation vs drift re-emit (manifest versioning)**: when the operator selects "Request a bounded adaptation candidate" after reviewing a prior proposal, the result is a NEW candidate (new manifest version, e.g. `a6-port-approval/v3`, new qualified successor digest, new operator approval required). It is NOT a re-emission bound to a new HEAD (that is `references/drift-port-proposal.md`). The drift case reuses the prior proposal's overlay bytes and only rebinds the destination HEAD; the bounded-adaptation case modifies overlay bytes (typically a small, operator-named set of behavior-preserving edits) and recomputes the integrated digest. The two flows have different signatures: drift re-emit preserves the digest, bounded adaptation CHANGES the digest. The new manifest must (a) preserve the parent digest as `parent_qualified_successor_digest` for audit, (b) carry forward unchanged non-green scopes verbatim, (c) require fresh Sentinel and Skeptic reviews of the new identity (the prior reviews do not transfer), and (d) include focused regression tests that exercise only the adapted files, not the full prior battery (which may have prior-irrelevant results). Issue a new manifest version rather than silently editing the prior version. The new manifest file lives at a separate path (e.g. `a6-port-approval-v{N}-manifest.md`) and the proposal directory is named separately (e.g. `a6-adaptation-port-proposal/`), with the operator's installed checkout and any prior proposal directories preserved unchanged.

- **Worktree-path interception by `tests/home_io_guard`**: a hermes test module named `tests/home_io_guard.py` intercepts `os.stat` (and other file I/O) calls and refuses any that touch a path the guard classifies as "real hermes home." When a check, an isolated import probe, or a pytest collection triggers a transitive import (e.g. `run_agent.py` → `hermes_bootstrap.py` → `_settle_interrupted_update` → `Path.is_file()`), the guard may classify the staging directory of the bounded check (`/Users/elvis/.hermes/profiles/<profile>/cache/scratch/.../staging/noesis-overlay/...`) as a real hermes home because it sits inside the operator's profile path. The test then fails with `TEST BUG: file I/O against the REAL hermes home: <path>`. Workarounds, in order of preference: (1) source-level checks that read files directly without importing them (e.g. `Path(worktree).read_text()`); (2) tests that import only modules that do not trigger `hermes_bootstrap` (e.g. `agent.runtime_enforcement` is safe; `run_agent` is not); (3) when the failure is in the operator's own v2 battery (e.g. `test_rebuild_with_matching_governed_context_succeeds`), classify it as an environmental defect and report it; do not edit `home_io_guard.py` to whitelist the staging path unless the operator explicitly widens the source-edit scope. Always re-verify the operator's installed checkout (`git rev-parse HEAD`, `git status --porcelain`) at the end of the bounded check — the staging worktree is registered in the operator's git worktree list and any code that mutates the operator's repo can break that assumption.

- Bounded scope-choice discipline: when the operator presents a scope choice (e.g. A: trusted-worker prototype vs B: enforced authority boundary), the orchestrator must (1) recommend one option with rationale; (2) if A is selected, label the unsatisfied strong isolation claim EXPLICITLY UNSATISFIED in the plan and in every downstream artifact; (3) state that no production/adversarial multi-agent security acceptance is implied; (4) proceed only after the operator confirms the scope choice. Do not let a same-UID trust limitation be silently accepted — it must be a labeled, operator-accepted caveat.

- Receipt-verification lead-finding discipline: a receipt verification pass may discover REAL code defects that are outside its authorization to fix. Lead the verification report with the finding; classify it as UNRESOLVED; identify the exact file/line; distinguish existing-code from proposed-design defects; and propose the smallest bounded correction (affected files, tests, scope) WITHOUT implementing it. The report must not describe the candidate as contract-complete while the finding is open. Return the correction proposal for operator decision (authorize fix / defer with known limitation / halt).

- Integration prototype scope discipline: when the operator selects a bounded trusted-worker prototype scope over an enforced authority boundary, label strong worker-write isolation as EXPLICITLY UNSATISFIED and state that no production or adversarial multi-agent security acceptance is implied. Accept the same-UID trust limitation for the prototype only. Do not claim workers are technically prevented from modifying authority state — not passing ledger paths is data minimization, not access control. If an enforced boundary is required, stop and request a separately approved scope with exact process identity, permissions, service interface, and host changes.

- **Governed parallel execution discipline**: build parallelism inside the existing
  TaskStore/Orchestrator lifecycle—never add a second scheduler, approval ledger,
  task store, or supervisor. A provider primary plus backups is resilience, not
  worker parallelism. Distinct workers require distinct task IDs, attempt
  IDs/epochs, leases, reservations, workspaces, preflight evidence, invocation
  state, and artifacts; each child must cross the normal `route_with_preflight`
  boundary independently.

  Atomically admit the whole required envelope before launch: every mandatory
  child plus integration, verification, and review capacity. Do not reserve an
  integration task later with a zero budget, and never convert missing usage or
  cost to zero. Bind reservations to the validated task, route, budget, and
  contract revision so restart/replay cannot re-admit stale authority.

  Parent cancellation is an authority transition, not a status label. Persist
  child revocation, request termination, and distinguish confirmed stop,
  requested-but-unconfirmed stop, late completion after revocation, and
  workspace-safe versus workspace-unsafe reuse. While termination or usage is
  uncertain, parent completion and workspace reuse fail closed. Rehydrate these
  states on restart and prove replay cannot relaunch children or integration.

  Test through the production swarm/dispatch entrypoint with barriers and fake
  transports: race two admissions against the real aggregate budget; execute the
  actual concurrent integration path; cancel while children are active; inject
  unknown usage and late completion; restart from the ledger; and count physical
  transport calls. Direct policy-helper tests with fabricated “one already
  running” state are supplemental only.

- **Same-agent concurrency and replay-vs-execution discipline**: a
  per-(task_id, admitted_attempt_id) duplicate limit does NOT protect concurrent
  distinct attempt IDs sharing one AIAgent. Select an explicit mechanism—serialize
  admission → transport → settlement per agent instance, or maintain
  concurrency-safe per-attempt boundary state—and use it consistently in code
  and tests. A threading lock alone proves neither rejection nor a total count of
  one; test two distinct concurrent attempts against the same agent with fake
  transport counting. For replay versus execution, an existing reservation
  returned as admitted is NOT sufficient to permit transport: define fresh
  execution authorization versus duplicate delivery (for example, a
  `fresh_execution` field that must be true before transport). For
  crash/redelivery, retain consumed allowance and deny automatic re-execution of
  an ambiguous attempt unless a separately accounted new attempt is authorized.
  Do not claim exact-once remote execution after ambiguous crashes.

- Store consistency and authorization linearization discipline: do not describe BEGIN IMMEDIATE alone as making external TaskStore validation atomic with SQLite reservation. Bind the validated task/route/budget revision to the reservation explicitly (e.g. contract_revision and baseline columns in the reservation record). Specify the ordering or serialization mechanism for authority updates and admission: an already authorized attempt may complete under its bound revision according to the documented cancellation policy, but this is distinct from validating stale state before an unrelated SQLite lock. For durable reconciliation of TaskStore-first/SQLite-second failure, persist quarantine state in the TaskStore JSONL with requires_manual_reconciliation: true, and specify recovery behavior: restart opens (never creates) the SQLite ledger, replays the TaskStore, and preserves quarantine state.

- Review-verdict recording discipline (audit updates): a new review event gets a NEW separate receipt file; never edit the prior reviewer receipt, completion packet, diff, manifest, or logs — prior artifacts stay byte-identical. The receipt binds to the FULL candidate identity (baseline commit, content digest, diff sha256, manifest sha256); abbreviated digest prefixes are display-only, never the recorded identity. Never cite any hash, commit id, or artifact path from memory in a receipt or supplement — recompute every cited value from source after the artifact's final edit and patch in the real values; when a receipt must reference itself, record its own hash in the ledger rather than inside the file. Record exactly the verdict and scope delivered (verdict, static-vs-reproduced, binding scope); do not reconstruct finding text that was not delivered, and set `verification_reproduced` accurately (a static review is false even when the verdict is PASS). Never let a receipt imply endorsement of unreviewed corrections: a follow-up handoff's "Required invariants" is a PROPOSED corrected remediation contract — state explicitly that the reviewer has not reviewed or endorsed it (e.g. `reviewer_endorsement_of_corrections: false`) until a reviewer approves that successor snapshot. Ledger status updates are in-place transitions (e.g. NOT_REVIEWED → REQUEST_CHANGES) that preserve the prior row text as history; set the next decision explicitly (operator authorization of the bounded follow-up, not another review dispatch). Idempotency: if an instruction to record a verdict matches already-recorded state (same reviewer, verdict, candidate digest), do NOT rewrite the receipt — a new write changes its hash and fabricates a second record; verify the receipt fields, ledger lines, and preserved artifact hashes, then report confirmation. No audit-record write authorizes code changes, tests, provider calls, reviewer relaunch, adapter/runtime work, installation, activation, commit, push, merge, or deployment — say so. When the operator supplies a review verdict that was produced outside the orchestrator's observed session, mark provenance as operator-supplied in the receipt and do not claim the orchestrator observed or can attest the review session itself. When recording a second reviewer's verdict, first verify the first reviewer's receipt is preserved byte-identical by checking its SHA-256; report both receipt hashes in the ledger line.

- Finding-provenance correction discipline (audit clarifications): when the operator directs a correction to finding attribution or numbering without authorizing a new review or candidate change, write a SEPARATE audit-clarification file (e.g. `track-b-aN-finding-provenance-clarification.md`) rather than editing the original review receipt. Preserve the original receipt byte-identical; the clarification file carries the corrected mapping (e.g. restored original N1–N6 numbering, verbatim finding statements) and explicitly states it does not supersede the original receipt. Update the ledger to reference the clarification path and SHA-256 while preserving the original receipt hash. Record any separately-categorized items (e.g. network-denial, profile-isolation, historical-verdict notes) as qualification caveats distinct from the reviewer's findings, not as substituted findings. State explicitly that the audit correction authorizes documentation updates only — no implementation, tests, provider calls, integration, installation, activation, commit, push, merge, or deployment.

- **Operator-mediated external review**: when the operator freezes a review packet and directs external manual review, do not launch reviewer inference from installed Hermes; the operator hand-carries the packet and candidate identity to fresh reviewer contexts and returns the verdict text. Record it in a new receipt verbatim with accurate `verification_reproduced` and provenance marked operator-supplied, then reconcile the ledger to an explicit per-reviewer state (e.g. SENTINEL_SPEC_PASS / SKEPTIC_PENDING). Never carry a historical candidate's verdict forward as a verdict on the current candidate — historical findings (e.g. Skeptic REQUEST_CHANGES on a prior digest) are review inputs only. Preserve the complete test chronology including failed or environmental-defect runs; never describe a split-run verification as entirely successful. Reference an existing review receipt by path and SHA-256 instead of duplicating or overwriting it; fill in the receipt hash by recomputing after the ledger line is written, not from memory. Record any separately supplied reviewer attestations the operator returns (e.g. independent candidate-identity recomputation) as claims in the receipt with provenance, not as orchestrator-verified facts. When both reviewers return verdicts, update the ledger to the explicit combined state (e.g. SENTINEL_SPEC_PASS / SKEPTIC_QUALITY_APPROVED) and restate the scope suitability in one sentence; keep the held-work list unchanged until the operator issues a separate acceptance event. Write a separate receipt per reviewer — never edit the prior reviewer's receipt to add a second verdict. When recording a second reviewer's verdict, verify the first reviewer's receipt is preserved byte-identical by checking its SHA-256 before writing the new receipt. Record any separately supplied reviewer attestations the operator returns (e.g. independent candidate-identity recomputation) as claims in the receipt with provenance, not as orchestrator-verified facts. When both reviewers return verdicts, update the ledger to the explicit combined state (e.g. SENTINEL_SPEC_PASS / SKEPTIC_QUALITY_APPROVED) and restate the scope suitability in one sentence; keep the held-work list unchanged until the operator issues a separate acceptance event.

  **In-fleet review is the default; operator hand-carry is the degraded fallback.** When a Noesis implementation candidate returns `not_self_approved: true`, the orchestrator should dispatch Sentinel and Skeptic as bounded child sessions through the same `Orchestrator.propose → approve → claim → start` lifecycle the implementer used, not freeze a packet and ask the operator to carry it. The reviewer contract is a file (`--query-file`), the proposal is capability-routed (`noesis-sentinel` → `code_review`; `noesis-skeptic` → `adversarial_review`), the `reviewer_profile` is the *other* reviewer (Sentinel reviews Skeptic's task, Skeptic reviews Sentinel's task) so the chain stays independent, the candidate is bound to a tracked diff SHA-256 the reviewer must reproduce, and Skeptic's proposal declares `depends_on=[<sentinel_task_id>]` so it only claims after the spec verdict is `PASS`. The operator hand-carry flow above is reserved for when the in-fleet route is genuinely unavailable (reviewer profile not installed, no authorized provider/model lane, or the launcher itself is the thing under review). See `noesis-in-fleet-review` for the exact procedure.

  **`reviewer_profile` is reviewer-only and is not the orchestrator.** Policy rejects a non-reviewer `reviewer_profile` with `reviewer_must_be_reviewer_only`; the orchestrator profile itself is rejected. The cross-reviewer pattern (Sentinel reviews Skeptic's task, Skeptic reviews Sentinel's task) is the default for Noesis, where only two reviewer profiles are installed. With three or more reviewers, still never name the implementer or the orchestrator as `reviewer_profile`. A made-up `required_capability` is rejected with `capability_mismatch`; a wrong string that happens to also be in the reviewer's declared set is silently accepted, so look up the declared capability from the installed profile or the canonical roster (e.g. `noesis-sentinel` declares `code_review`; `noesis-skeptic` declares `adversarial_review`).

- Memory-vs-recorded-verdict discipline: when session memory at start describes a reviewer verdict (PASS / BLOCKED / INSUFFICIENT_EVIDENCE) that does not match the recorded review artifact, report BOTH: the recorded verdict verbatim from the artifact (read the receipt file with `read_file` or `skill_view`, never recall from memory), and the memory claim as a "preserved provenance note, not an independent reviewer verdict." Do not reinterpret a recorded BLOCKED as PASS, and do not reinterpret a recorded PASS as BLOCKED, on the basis of memory. The recorded artifact is authoritative for the verdict; memory may be stale across compaction or session boundaries. This applies any time a recorded reviewer verdict is consumed, not only during a drift-port cycle.

- Candidate-freeze and review-verification discipline: use the candidate's documented digest recipe exactly; never universalize one recipe across packages. Some candidates hash the UTF-8 bytes of newline-joined per-file digests, while others hash the raw-byte concatenation of files in manifest order. Recompute every per-file hash first, validate the ordered path set, then reproduce the declared recipe byte-for-byte before acting. When every per-file hash matches the recipe's table but the combined digest does not reproduce, the discrepancy is in the recipe encoding, not content drift: rebuild the recipe text exactly as documented (e.g. printf the sorted `path:hash` lines) before declaring drift or a doc bug. In particular, `sort` applied to raw `sha256sum` output orders lines by hash, so a one-liner that sorts before rewriting to `path:hash` lines yields a different combined digest than a recipe documented over sorted `path:hash` lines — sort the rewritten lines, not the raw output. Validate diff integrity from the packet's own tree state: a scoped diff may legitimately reverse-apply against a dirty working tree while failing forward `git apply --check` there; forward-apply it against a clean clone checked out at the verified baseline before declaring an apply failure. The worktree can diverge from a frozen candidate while HEAD is unchanged (an external executor's uncommitted edits) — recompute hashes, never trust HEAD alone. Before classifying a signal (a warning line, a fallback banner, an environment identity) as a successor-only defect, grep the frozen prior-candidate evidence for the same signal; when it appears in both candidates' logs, record it as a shared caveat applying to both, not a new violation introduced by the successor. HEAD can also lack files present in a reviewed working-tree snapshot; verify `git show HEAD:<path>` for each manifest path before saying a candidate is "in HEAD" or "merged." Do not infer "not begun" from the absence of a completion JSON, and do not infer "complete" from a narrative report; a report claiming PASS while admitting failing regressions or producer-compatibility breaks is VERIFICATION_INCOMPLETE, not completion. Verify any external claim (e.g. "merged to main") against checkout truth (git log/HEAD) and per-path object membership, not just the branch tip. HEAD can also ADVANCE externally during supervision (an executor or another context commits to the main checkout mid-window, contradicting a "no commit" freeze invariant) — re-check `git rev-parse HEAD` and `git log` at the END of supervision, not just the start, and flag any new commit rather than silently accepting it. A relayed summary figure (e.g. "240 passed, 4 failed") may not match the actual packet — record the packet's real exit status and counts, not the relayed summary. When reconciling a review finding, determine whether the cited code was the reviewed revision or added afterward: a spot-check against newer post-remediation code does not refute a finding that was correct against the reviewed revision. A reviewer context that implemented a slice is not independent of that slice — it should stop at independence (BLOCKED_AT_INDEPENDENCE, a suitability stop, not a candidate rejection) rather than issue a verdict; record distinct review events (suitability stop vs candidate-shaping verdict) without conflating them. Before qualification, prove that the declared candidate is reconstructable from its recorded baseline in a clean copy: inventory every dirty imported/transitive dependency, ensure each required changed byte is either frozen in the manifest and reconstructing patch or demonstrably unnecessary, then run the qualifying tests in that clean reconstruction and rehash afterward. Tests in a dirty worktree prove that worktree, not the declared subset. A reviewer PASS limited to named files does not cure an incomplete integrated manifest; the orchestrator must remain BLOCKED rather than silently folding unfrozen dependencies into the candidate. Follow `references/clean-reconstruction.md` for dependency classification, clean extraction, module-origin checks, identity construction, and review handoff. A conditional reviewer verdict remains unresolved until its stated conditions are evidenced and that reviewer issues the required final disposition; never translate CONDITIONAL into approval during synthesis.
 Do not treat a clean final run as proof that an earlier failed attempt in the same bounded turn was harmless: if the attempt log preserves a failed first run, the packet must disclose it as a flake/failure-to-retry and the receipt must evaluate it, not compress the result to the final green exit. An execution turn that violates the authorized environment boundary cannot be retroactively cleaned by its own completion packet; record the violation as a blocker and require a new authorization for any corrective or reporting turn.
  When a remediation completion packet is reported, do not wait for a new
  dispatch or loop on "blocked awaiting external initiation": if the operator
  states the work is already complete, treat the handoff as historical and go
  ingest the existing packet. Run a bounded, read-only receipt verification
  (no implementation, no tests, no provider sessions, no state change):
  (1) inventory the reported artifacts and confirm each exists; (2) read the
  completion JSON and its manifests; (3) recompute every per-file sha256 against
  the live working tree and the candidate content digest (sha256 of the
  sorted-by-path concatenation of the changed files); (4) verify the baseline
  commit object exists and HEAD is unchanged; (5) verify the untracked runtimes
  (installed Hermes, main checkout) are untouched; (6) reconcile each handoff
  item against the packet, flagging reasoned deviations (e.g. a load-induced
  failure classified from preserved logs rather than re-enacted) as justified
  caveats, not defects; (7) report the verified candidate identity and the
  proposed frozen review scope. A packet that is `not_self_approved` and
  `not_reviewed` is an implementation+evidence package only — it authorizes
  independent review, never installation or integration. Separate receipt integrity from acceptance: if a requested clarification supplement is absent or uses the wrong finding namespace, issue one exact documentation-only request and hold reviewer dispatch rather than synthesizing the implementer's missing claims. A passing-log summary does not prove the subprocess exit status; recover the real status from the preserved tool/session result or classify it unknown. Distinguish provider-backed authoring from test-subprocess network behavior: live model calls in the worker session invalidate an unqualified `no_live_provider_calls` claim, while mock-oriented test names alone do not prove the tests made no network requests. Verify the packet's literal claims against the preserved artifacts; a statement that dependency/provider state was unchanged must be checked against setup banners, environment inheritance, and wrapper behavior, not merely copied forward. See `references/evidence-receipt.md` for the bounded successor-package receipt procedure and the post-receipt reconciliation/impact-audit procedure.
  When test evidence is delivered, read the saved logs themselves, not only the
  completion narrative: a retried suite can pass on the final attempt while the log
  still records a first-attempt failure, and the packet must carry that flake
  forward as evidence instead of compressing it to a green summary. Treat any
  dependency/tool-install banner inside a test log as an execution-boundary
  violation when the approval forbade dependency preparation, even if the tests
  later exited 0. A wrapper that spawned test children without an explicit
  Hermes profile can also leak into the default profile; record the wrong-profile
  fallback as a blocker unless the exact cache mutation is proven absent. Do not
  accept a PASS narrative that admits
  failing regressions, and do not classify a failure as "unrelated flake" without
  proof: an isolated replay that REPRODUCES the failure means it is real, not load
  flakiness, and regression-vs-preexisting stays open until the failing test is
  run against the clean baseline without the change. Supervise external test runs
  to termination within the authorized budget (a test's per-file `--file-timeout`
  is not an overall process-tree deadline); on expiry cancel managed processes,
  verify termination, and preserve partial evidence rather than launching a
  replacement run. A completion packet written before the final run is
  provisional — recompute artifact hashes and final exit statuses after the run
  and record whether the final result differs from it.

- **Reviewer output preservation and reconciliation discipline**: when the operator returns external reviewer verdicts, preserve the original outputs unchanged in a dedicated verdicts file with SHA-256 recorded. Verify each verdict names the exact current integrated candidate identities — recomputed from live file bytes, not copied from the packet. Reconcile findings into one list: confirmed contract/code defects, missing evidence, accepted bounded-prototype limitations, and nonblocking improvements. Do not upgrade verdicts (FAIL → PASS) or paraphrase reviewer text. A partially delivered verdict (e.g. a finding list cut off mid-transmission) is recorded exactly as delivered with the missing portion explicitly marked pending operator hand-carry; remediation work items derived from incomplete findings stay gated on the complete text, and the missing reviewer text is never reconstructed by re-running the reviewed tests — re-runs produce new evidence, not the reviewer's words. The original reviewer artifact is preserved byte-identical in the evidence directory with its sha256 and reviewed identity recorded alongside; a separate reviewer-issued receipt placed in that directory is permitted, while candidate source/test modification by the reviewer remains prohibited. If both reviewers identify blocking defects, propose one consolidated minimal work order addressing all blockers with exact scope, test commands, limits, and required permissions — no implementation until authorized. If neither review has blockers, return an operator decision for bounded-prototype acceptance only. Keep installation, activation, live execution, commit, push, merge, and deployment held regardless of verdict.
- **Receipt-to-hand-carry digest match (do not conflate verdicts across digests)**: the staged hand-carry packet names a `candidate_digest` and a list of per-file SHAs. The reviewer's verdict receipt is for SOME digest; it is for the hand-carried artifact only if its `candidate_digest` field is byte-equal to the one the hand-carry names. A receipt for digest B is not a verdict on hand-carry A, even when the names look similar (e.g. `a4519bd6…` planner digest vs `d9812fc7…` A6 v3 integrated overlay). When summarizing review status, name the digest and the receipt file path together, and never claim "verdict received" for a digest whose receipt is not on disk in the current session. If only a same-named verdict exists for a different digest, report both as separate items, not as one merged status.
- **Remediation-prompt staging discipline (operator hand-carry)**: when the operator authorizes a bounded remediation but dispatch requires operator hand-carry, stage the remediation prompt as a file explicitly marked STAGED / NOT DISPATCHED, report its path and sha256, and never claim dispatch. Ground each correction in a source-confirmed root cause (file:line from direct inspection, labeled confirmed vs pending — not inference); record the baseline suite result and a clean-worktree ownership check (`git status --porcelain` on every writable in-scope path) so no concurrent worker owns the same files; restate the hard constraints from the authorization verbatim (held gates, out-of-scope items such as separate hardening tasks); and put an explicit PENDING gate on any finding whose complete text has not arrived. After the bounded repair returns, require the full handoff (root causes + correction semantics, complete diff and file hashes, new snapshot digest + reconstruction recipe, focused regressions and applicable suite results, preserved historical review, remaining limitations) and route the new identity through fresh independent review of the same reviewer chain before any dependent reviewer runs.
- **Standing-goal resend is not a new authorization**: when the operator resends the standing goal verbatim, the existing held/blocked set is unchanged. Do not re-run an already-green test suite, do not re-list already-staged handoffs, and do not produce a new prose blocker digest. Instead, restate once: current state, specific blocker, required actor, and the next authorized action; then stop. The single restatement must be bounded (a small table or short list), not a long re-narration of every prior turn. If all remaining work is operator hand-carry, return the exact handoffs once and pause. A new tool result or a new operator instruction is the only signal that unblocks further action.
- **Explicit operator authorization letter supersedes self-restraint on the named action**: a standing rule (e.g. "do not add a remote on your own initiative") applies until a fresh operator instruction that names the same action in concrete terms. When the operator's message names an exact `git remote add` command with the exact URL, names the exact file path to write, or names the exact `gh` invocation, treat that letter as the explicit authorization and execute the named action once. Halt only on a real conflict (a remote by that name already exists with a different URL; a file path that is read-only; a different remote set already exists under that name). "Do not act on your own initiative" is a guard against inferring authorization from silence, not against carrying out an authorization that was spelled out in the same message.
- **Loop exhaustion reports must name an in-session next action, not just restate blockers**: when a turn is spent restating the held/blocked set, the report must also list (a) the smallest authorized action I can take without further approval and (b) the exact human input that would unblock the rest. A "blocked, awaiting operator" closing with no in-session action is the failure mode. The smallest authorized action may be a documentation update, a status file, a digest verification, or a skill patch — anything that does not require a new approval. After that one action, stop and let the operator direct the next.

- Overlay-byte source-of-truth discipline (drift-port proposals): for installation/port proposals, the packet's overlay manifest is the source of truth for the qualified source bytes; the destination's on-disk byte is the source of truth for what would be replaced. The dev source HEAD is informational only and is not the source of the qualified bytes. Re-derive every per-file operation (NO_OP / ADD / REPLACE) by comparing the on-disk destination byte to the qualified source byte from the manifest — never by comparing the on-disk byte to a dev source HEAD. A NO_OP classification derived from a wrong source comparison silently swallows REPLACEs as "already exact" and binds the wrong per-file decision matrix into the manifest. Verify the manifest's source by recomputing every per-file SHA-256 against the packet's reconstruction directory and the integrated overlay digest against the manifest's claimed recipe; if either check fails, the source of truth is broken and the proposal halts.

- **Destination-HEAD drift invalidation**: an installation/port proposal is bound to the destination HEAD it was inspected against. A drift between inspection and execution (a routine upstream sync, a maintainer push, a CI rebase, an external commit) invalidates the bound approval — the prior I-approve does not transfer to a different destination state. On first detection, halt before any write; do not restore the old HEAD; do not replay the original manifest; do not assume the new HEAD is "obviously intended." Preserve the original proposal unchanged and mark it SUPERSEDED for execution, then request the operator's choice between restoring the old HEAD, re-emitting the proposal bound to the new HEAD, or investigating unresolved issues. Only the operator's re-approval of the new manifest version authorizes the new write set.
- **Attribute a blocking gate failure before acting on it**: when a pre-commit hook, validator, or test gate refuses a commit, decide first whether the failure is pre-existing or introduced by your change — stash the work, re-run the gate on a clean tree at the same commit, and compare. A gate that fails identically there is a pre-existing repo defect; assuming your change caused it sends you editing files that were never wrong, and assuming it didn't sends you `--no-verify`-ing a real regression you introduced. Never `--no-verify` a gate you have not attributed: that converts a visible blocker into an invisible one. When attribution is clear, fix the pre-existing defect at its source rather than routing around it, and keep your own change's gates green in the same commit. See `references/pre-commit-gate-triage.md` for the stash-and-compare recipe and the escape decision.

- **When a validator reports the same error once per file across many files, check whether those files are generated before editing any of them**: a validator emitting one identical error per profile/spec is almost always reading a generated tree, not the source of truth. Check whether the flagged paths are tracked (`git ls-files <path>` empty means untracked) and whether the declared source of truth already carries the correct value — a stale gitignored generated tree reports errors against a source that is already right, and the real defect is that the tree was never regenerated. Repair by re-running the generator, never by hand-editing every flagged copy: hand-editing N copies is unverifiable, is overwritten by the next regeneration, and yields an empty commit because gitignored files are not committable. Verify by re-running the validator after regeneration, and report the fix as the generator invocation plus the resulting source-of-truth confirmation — not as the volume of lines changed. If the source of truth is ALSO wrong, fix that and regenerate; never edit generated bytes as the primary repair.
- **Pre-push scope-divergence check (do not push a branch that is not a narrow delta on destination main)**: before any push to an external destination, run a four-number scope check: `git rev-parse <local-branch>` (local tip), `git fetch <remote> main` then `git rev-parse <remote>/main` (destination tip), `git merge-base <local-branch> <remote>/main` (fork point), and the commit counts in each direction. If the local branch carries thousands of commits the destination does not have, the local branch is not a checkpoint delta — it is the destination's full upstream history (or close to it). Pushing under the operator-approved branch name in that case would publish upstream commits, authors, dates, and content the operator never authorized for that destination, and the prior authorization's "dev checkpoint" intent does not transfer. Halt before the push, name the divergence, and propose the smallest safe publication method (typically: branch from `remote/main`, replay the operator-approved delta as one or two new commits, then push that branch). A clean final-tree and a clean secret-pattern grep are necessary but not sufficient — the test is the history shape, not the working tree. Do not invent a "narrow delta" justification to paper over a measured divergence. See `references/pre-push-gates.md` for the executable recipe and the secret-scan method.

- Automatic repair–verify–review loop discipline: when the operator authorizes a complete bounded repair–verify–review loop (not just packet preparation), do not stop at "packet prepared" or require manual hand-carry when an approved safe reviewer route is available. At loop entry, preflight every required reviewer profile and exact provider/model route with a bounded no-side-effect identity probe; record the resolved route, reject automatic fallback outside the approved route set, and distinguish a runnable reviewer route from a merely installed profile. This prevents finishing implementation only to discover that a mandatory independent gate cannot run. If a profile default is unavailable but the operator already approved a specific alternate route, use a per-invocation `-m <model> --provider <provider>` override rather than editing global/profile configuration; do not infer that a route approved for one reviewer is approved for another. Treat fallback banners, quota refusals, and an interrupted partial inspection as route evidence—not a verdict—and never promote the partial inspection to independent approval. Dispatch long reviewer runs as tracked background processes from the outset; a foreground CLI timeout can terminate the reviewer before it writes a verdict, so a timeout is not evidence that review continued. For one-shot `hermes -p <profile> ... chat -q <prompt>` dispatch, use a non-PTY background process; reserve PTY for genuinely interactive sessions, because PTY mode invokes the full-screen UI, produces unusable ANSI heartbeat logs, and can leave a failed assistant initialization looking like a live worker. Verify startup by reading the process log for actual assistant/tool activity before labeling the task running. Run reviewers sequentially when they share one frozen working tree, and dependency-gate the next reviewer until the current reviewer returns a terminal verdict. Before the first dispatch, have the orchestrator independently verify every artifact-manifest entry and reproduce the candidate digest with the packet's documented byte-order algorithm; packet authorship and reviewer rehashing do not replace this control-plane check. Require each reviewer to rehash candidate files before and after its tests. When the packet preserves any non-green scope, name every failure in the review request and require an explicit classification as candidate defect, missing environment prerequisite, pre-existing/unrelated behavior, or blocking evidence gap; a narrative label from the implementer is not a disposition. Require the reviewer output—not merely process exit 0—to include full (not abbreviated) frozen identities, verdict, evidence classification, and any independently reproduced test exit. A running heartbeat or partial inspection is progress evidence only—never infer a verdict, and do not launch the dependent reviewer until the terminal output is preserved. Preserve the raw reviewer session after completion with `hermes -p <profile> sessions export <evidence-dir>/ --format md --session-id <id> --yes --force`, then hash the export; do not reduce the durable evidence to a paraphrased verdict. If safe reviewer execution is unavailable, identify that once at the start, finish all remaining authorized work, and return one precise route blocker naming reviewer, candidate, configured route, observed provider refusal, and the smallest missing permission/connectivity action—not another generic "operator-mediated packet ready" message. Authorize up to three repair–verification–review rounds including the first; stop early only for permissions/routes unavailable, required interface/security/design change outside scope, contradictory requirements needing operator decision, exhausted cycle/runtime/cost limits, or infrastructure/evidence integrity failure. Do not expand scope because a reviewer suggests optional improvements. Do not downgrade a blocking finding to finish faster. If code changes after a review, that review does not approve the new candidate. After each round, reconcile findings into: blocking contract/code defects, blocking evidence gaps, accepted prototype limitations, deferred nonblocking improvements.

- Point-3 mechanism inspection (do not preapprove unsupported controls): before implementing fail-closed authorization, profile attestation, or credential-attempt bounds, inspect the real Hermes source revision that will execute the request path, then record dirty status and cited source lines. Do not assume a reported upstream SHA is the installed runtime HEAD; verify `git rev-parse HEAD`, `git status --short`, and `git cat-file -e <sha>^{commit}`. For approved core-development work, clone a separate development checkout pinned to the verified upstream revision, re-verify the cited request-path files there before coding, and keep installed runtime/config untouched until a later explicit install gate. Trace the attestation environment and the spawn environment as one binding: record the exact `HERMES_HOME`, profile directory, identity-bearing file set, and manifest digest used by each; require them to identify the same bytes immediately before spawn. When fallback denial needs an isolated home, materialize the specialist identity there from an explicit allowlist and attest that isolated directory—never attest the installed profile and then launch a name-only or minimal replacement. Add a final-boundary negative regression that rejects installed/isolated manifest mismatch and a minimal `SOUL.md` containing only the profile name, because requested-profile equality alone does not prove the specialist instructions, tools, skills, or memory configuration loaded. Explicitly reject: parent-only helpers the child can bypass; attesting installed profile then launching a different minimal identity; file-level `fallback_providers: []` as proof of effective runtime state; wall-clock timeout as proof of a credential-attempt bound; success flags without an enforced request boundary. If the mechanism is missing, output an explicit BLOCKER with citation and a separately scoped core/integration proposal; never monkey-patch or silently edit core.

- Role separation and handoff: supervisor holds task ledger/verification/freezing/review-coordination; repair executes only in an independently authorized context (not through the defective launcher); provide a copy/paste external handoff text with profile-match verification (`requested_profile_id == loaded_profile_id`, HERMES_HOME isolation); the independent reviewer never implements its own findings; no live canary/execution/reconciliation/activation gates open until prerequisites pass.

## Reconciliation-blocked dispatch: vocabulary and retry discipline

- The inference spawn gate compares `approved_provider` to the policy
  **lane name** (for example `KIMI_CODE`), while the launcher passes the
  value to `hermes --provider` and into the isolated session config, where
  it must be a **Hermes provider name** (for example `kimi-coding`). The
  bridge is the lane block's explicit `hermes_provider:` field in
  `platform/inference-routing.yaml`, resolved by
  `InferenceRoutingEnforcer.hermes_provider_for_lane()` and applied at
  **both** launch sites (legacy `route_and_launch` and canonical
  `route_with_preflight`) before `_invoke_launch`; the reported-provider
  check compares against the mapped id. An unmapped lane passes the raw
  value through, so a lane without the binding still burns the launch
  attempt on a guaranteed spawn failure (reservation consumed,
  single-attempt budget exhausted) — verify the binding exists in the
  lane block before re-firing, and patch both launch sites together (the
  `_invoke_launch` blocks are textually identical; a single-site patch
  leaves the other path launching lane names). Retry a burned canary with
  a fresh idempotency key (`:r2` suffix); the failed launch already
  consumed the attempt budget on the old key and re-dispatch with it
  refuses `attempt_budget_exhausted`. Guard `is None` before `str()` when
  normalizing Optional policy values — `str(None).strip()` is the truthy
  string `'None'`, and `str(x).strip() or None` silently turns a missing
  key into that string; the unknown-lane regression caught exactly this.
- The approved pair is persisted in the launch **reservation**, not in
  the stored proposal, so a pair-only change keeps the idempotency key
  and epoch-resume valid; changing any stored-contract field makes the
  idempotent `propose` silently replay the old contract and requires a
  new key and new proposal. Verify the retry contract by reading the
  control-plane code (idempotent propose, reservation replay, epoch
  gate), never by live-probing a refusal.
- Reconciliation gates on a blocked profile are operator-policy
  boundaries, not execution errors to work around: prepare evidence,
  diffs, and retry-contract analysis read-only, stop for review, and let
  the operator's go-ahead bind only to the reviewed artifacts. See
  `references/blocked-dispatch-reconciliation.md` for the full procedure.
- Separate **mode authorization** from the **underlying policy verdict**.
  When an observe-mode result blocks bounded launch, trace its
  `reason_code` and policy finding before proposing enforcement; switching
  to `enforce` turns a would-deny into a real deny and must never be
  described as enablement. Verify the installed caller surface before
  claiming scope: if mode comes only from process environment, a one-shot
  CLI process with an inline setting is process-scoped (not task-scoped),
  while changing a long-lived plugin host affects every call in that host
  and requires its supported reload/restart lifecycle.
- Prove every numeric canary limit at the final child command/configuration
  boundary before requesting approval. A subprocess `timeout_s` enforces
  wall time, not model turns, requests, tokens, or USD spend; persisted or
  post-hoc usage fields are not pre-spend controls. If the canonical
  launcher does not forward the runtime's turn/budget flags or enforce a
  cost reservation, mark the envelope HOLD and request a bounded interface
  repair or an explicit requirement change—never claim a prompt enforces it.
- Close an undelivered task whose objective was completed through an
  explicitly permitted supervisor fallback with the real lifecycle
  `cancel` transition and a provenance-preserving reason. Never mark it
  succeeded, reuse its idempotency key, or edit JSONL; first prove its
  folded state permits cancellation, then read back the terminal event.

## Boundaries

Keep supervisor, executor, reviewer, and human approval authorities distinct.
Advisory systems, councils, scorers, reflections, and consensus outputs never
approve their own execution, deployment, publication, budget increases, or
canonical memory promotion. Scheduled/reflective workers must consume bounded
snapshots and emit quarantined proposals until reviewed. Do not weaken policy,
tests, or isolation to make rollout pass. Preserve unrelated changes and never
fabricate runtime, review, migration, or approval evidence. No commits, external
delivery, credential changes, provider purchases, service changes, or
installed-core patches beyond explicit applicable authorization.
