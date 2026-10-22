---
name: noesis-in-fleet-review
description: "Run Noesis Sentinel and Skeptic as in-fleet child sessions."
version: 0.3.0
author: noesis-orchestrator
license: MIT
metadata:
  hermes:
    tags: [noesis, review, sentinel, skeptic, delegation, control-plane, task-ledger]
    related_skills: [noesis-task-delegation, noesis-control-plane-dev, omh-code-review, subagent-driven-development]
---

# Noesis in-fleet review execution

The default for reviewing a Noesis implementation candidate is to dispatch
Sentinel and Skeptic as bounded child sessions through the same canonical
`Orchestrator.propose → approve → claim → start` lifecycle the implementer
used. The user does not hand-carry frozen review packets to fresh reviewer
contexts. This skill is the procedure; `omh-code-review` is the
shape-of-findings authority; `noesis-task-delegation` is the broader
delegation context.

## When to Use

- A Noesis implementation candidate has just returned
  `not_self_approved: true` and needs independent review before the
  orchestrator can accept it.
- A bounded bootstrap implementer (e.g. one direct `noesis-forge` session
  on an authorized provider/model lane) has produced a tracked diff
  against a documented baseline and the implementer result is at hand.
- The user has said "run sentinel", "needs review", "run skeptic on
  this", or otherwise directed the in-fleet review path.

Do not use for:
- Pure ad-hoc OMH review of arbitrary code; use `omh-code-review` and
  the `references/review-dispatch.md` flow it already documents.
- A pre-commit hook on the operator's own uncommitted changes; use
  `requesting-code-review`.
- A reviewer profile that is not installed or a provider/model lane
  with no authorized route — return a precise blocker instead.

## Procedure

1. **Freeze the complete candidate identity before review.**
   From the worktree, run:
   ```
   git rev-parse HEAD
   git diff --stat HEAD
   git diff HEAD | shasum -a 256
   git status --porcelain
   ```
   The baseline commit must equal the implementer receipt. Treat the hash of
   `git diff HEAD` as the **tracked** digest only. If `git status --porcelain`
   contains any in-scope untracked source, schema, fixture, or test, compute the
   path-prefixed combined digest from
   `references/verdict-schema-and-digest-recipe.md`; the tracked digest alone is
   not the candidate identity. Record the ordered candidate path set, baseline,
   tracked digest, combined digest, and separately hashed ignored/external
   receipts. If an implementer receipt reports a different combined-hash recipe,
   preserve and label that value as an alternate digest, then compute the
   path-prefixed review digest from the reference; never treat two recipes as
   interchangeable. Any mismatch is drift: halt and re-anchor rather than
   reviewing a different candidate.

   **Scope-check before writing the contract.** Compare `git status -s` and
   `git diff --stat HEAD` with both the contract's closed path set and the
   pre-dispatch status snapshot. A path outside the closed set is pollution only
   when it is new or changed relative to that snapshot; pre-existing unrelated
   tracked or untracked work belongs to the operator and must be preserved.
   Restore an attributable worker-owned out-of-scope path only when restoration
   is authorized, then recompute every digest and re-anchor the contract. Never
   reset, stage, or normalize pre-existing unrelated work to make the review
   tree look clean.

   When unrelated tracked changes exist, `git diff HEAD | shasum -a 256` is a
   useful full-worktree provenance checksum but is not the candidate identity.
   Also freeze a patch over only the ordered closed-set paths and compute the
   path-prefixed combined digest over every candidate file, including untracked
   receipts. Record all three values distinctly: full tracked-diff checksum,
   scoped frozen-patch checksum, and scoped combined candidate checksum. Put an
   `unrelated_state_unchanged` boolean in each verdict schema; require unchanged,
   not clean, so reviewers cannot confuse preserved operator work with candidate
   pollution.

2. **Write a SENTINEL contract to a file.** Include:
   - The candidate identity (task ID, worktree, baseline commit, ordered path
     set, tracked diff SHA-256, and combined SHA-256 whenever untracked
     candidate bytes exist).
   - The list of in-scope files and lines.
   - The requirements the implementer was held to (R1..RN), each as a
     one-line pass condition naming the test that proves it.
   - The acceptance commands the reviewer must run (focused suite, then
     full suite with the documented exclusion).
   - The strict verdict schema the reviewer must write, including
     `verdict: PASS | REQUEST_CHANGES | BLOCKED`, the per-requirement
     pass/fail, focused/full test counts, the
     `tracked_diff_sha256` the reviewer actually saw, and a final
     `not_self_approved: true` line.
   - The exact path the reviewer must write the verdict file to
     (e.g. `<artifacts_dir>/SENTINEL-VERDICT-A1.md`).
   - The held-operations list: no commits, pushes, merges, dependency
     installs, profile mutations, schedule activations, provider
     calls beyond this session, or live worker launches. The reviewer
     may only read, run `pytest`, and write its verdict file.
   - Verify implementer claims about provider/model use against the exact
     dispatch command and preserved session result; do not copy a blanket
     “no provider call” claim from a receipt when the run evidence shows
     inference. Preserve the original receipt and bind a separately hashed
     provenance clarification into the review packet. Distinguish development
     or review inference from live product-worker inference and external effects.

3. **Propose the Sentinel task through the orchestrator.** Use
   `Orchestrator.propose(...)` with:
   - `assignee_profile='noesis-sentinel'`
   - `required_capability` = the declared capability from Sentinel's
     installed profile or the canonical roster. For Noesis this is
     `code_review`. A wrong string is rejected with
     `capability_mismatch`; do not guess.
   - `reviewer_profile='noesis-skeptic'` (the other reviewer). The
     orchestrator profile and other non-reviewer profiles are not
     valid as `reviewer_profile`; the policy rejects them with
     `reviewer_must_be_reviewer_only`. The cross-reviewer pattern
     (Sentinel reviews Skeptic's task, Skeptic reviews Sentinel's
     task) keeps the chain independent when only two reviewer
     profiles exist.
   - `idempotency_key` unique to this review (`<user>:sentinel-review-<short-hash>:<date>`).
   - `parent_task_id` = the implementer task, for lineage only.
   - Do **not** set `depends_on=[implementer_task_id]` on Sentinel. The
     implementation is normally `awaiting_review`, so that dependency would
     require success before the very review needed to permit success. Propose
     Sentinel only after the implementation candidate and handoff are frozen.
   - `risk_tier='r0'`, bounded `timeout_s`, `max_attempts=1`,
     `labels=['review','sentinel','offline_only']`.
   - An acceptance criterion that the verdict file exists and the
     recorded `tracked_diff_sha256` matches the contract's digest
     byte-for-byte.
   - `approval_required=True`; immediately call `o.approve(...)` with
     the same `AUTH-A-IMPLEMENTATION-MANIFEST` (or equivalent) digest.

4. **Launch Sentinel as a tracked background process.** The exact
   invocation shape that works:
   ```
   hermes -p noesis-sentinel chat \
     --query-file <contract.md> \
     --oneshot \
     --provider <authorized-lane> \
     -m <authorized-model> \
     -t file,terminal \
     --ignore-user-config \
     --in <worktree> \
     --run-budget 1800 \
     --max-turns 300 \
     --format stream-json \
     --reasoning high
   ```
   Run it as `background=true`, `notify=true`, with
   `persist_on_release=true` so the verdict is preserved across
   compaction. The `--ignore-user-config` + explicit provider/model
   pattern is what preserves Sentinel's profile identity and rules
   while dropping its configured fallback chain. Sentinel runs are
   *not* exempt from the no-fallback rule. Use the same provider/model
   lane the implementer used, unless the operator has explicitly
   authorized a different lane for reviewers. Provider/model approval
   is scope-bound: approval for an implementer does not automatically
   authorize reviewer inference, another reviewer profile, or a fallback.
   Before each reviewer launch, bind authorization to the named reviewer(s),
   exact provider/model, attempt count, time limit, and fallback rule in a
   hashed route amendment; dispatch only the reviewer currently unblocked by
   the ordered gate. Preserve model identifiers literally. If a provider
   rejects one as unsupported, record the pre-delivery refusal and zero-token
   evidence if returned; do not silently normalize it or try another model.
   Obtain an explicit operator correction before a corrected retry, and do
   not count the rejected pre-delivery attempt as a verdict.

5. **Read the verdict file and validate the schema.** When the process
   completes, open the file at the documented path. Confirm:
   - The file begins with `verdict: PASS | REQUEST_CHANGES | BLOCKED`
     and the value is one of those three.
   - `tracked_diff_sha256` matches the contract's tracked digest byte-for-byte;
     when the contract records a combined digest, `combined_sha256` also matches
     using the same ordered, path-prefixed byte recipe.
   - All requirements have an explicit pass/fail.
   - Focused-tests count equals the expected number (the reviewer
     reproduced the implementer's count, not their own count).
   - The file ends at `not_self_approved: true` with no prose after.
   - The reviewer did not write to any file in the candidate worktree
     (`git status --porcelain` shows no changes).
   A verdict that fails schema validation, a `REQUEST_CHANGES` finding
   on a critical requirement, or a `BLOCKED` verdict all halt the
   chain and route the work back to the implementer. A `PASS` opens
   the gate for Skeptic.

6. **Propose and dependency-gate Skeptic.** Repeat steps 2-5 with a
   SKEPTIC contract that:
   - Reads SENTINEL-VERDICT-A1.md first; refuses to proceed if
     `verdict:` is not `PASS`.
   - Names a different set of attack classes (hidden self-cloning /
     silent fallback, frozen configuration drift, capability snapshot
     tampering, readiness evidence spoofing, plugin ledger bypass,
     isolated attempt home TOCTOU, auditor escaping report-only,
     test weakening, hidden credential capture). Sentinel accepts
     happy-path evidence; Skeptic must try to break each one.
   - Verdict schema uses `verdict: APPROVED | REQUEST_CHANGES | BLOCKED`.
   - `assignee_profile='noesis-skeptic'`, `required_capability='adversarial_review'`
     (NOT `code_review`), `reviewer_profile='noesis-sentinel'`.
   - `depends_on=[<sentinel_task_id>]` on the proposal; only call
     `o.claim` / `o.start` after the Sentinel verdict file shows
     `verdict: PASS`.

7. **Accept the implementer task only after both verdicts land.**
   The orchestrator's `accept` is the only transition to `completed`.
   Verify, in order:
   - Both verdict files exist at their declared paths and pass schema
     validation.
   - Both recorded tracked and combined digests match the contract identity
     byte-for-byte; the combined digest is mandatory when untracked candidate
     bytes exist.
   - Sentinel verdict is `PASS` and Skeptic verdict is `APPROVED`.
   - No open `critical` or `important` finding in either verdict.
   - The candidate worktree is unchanged (`git status --porcelain`
     shows only the in-scope diff; no new files, no new commits).
   Then call `o.accept(<implementer_task_id>, operator='elvis')` and
   record the canonical `task_accepted` event in the ledger.

8. **When Skeptic returns REQUEST_CHANGES, run the bounded remediation
   cycle instead of accepting or re-using the failed candidate.** The
   implementer is not self-correcting; the failed candidate stays
   `failed` in the ledger and is never accepted. The canonical recovery
   sequence is:
   1. `o.record_review(skeptic_task_id, stage='quality',
      verdict='REQUEST_CHANGES', reviewer='noesis-sentinel',
      candidate_revision=<the same tracked_diff_sha256 Skeptic checked>,
      findings=<Skeptic's top_findings>)`. The reviewer name passed to
      `record_review` is the cross-reviewer (Skeptic's task is
      implemented by Skeptic, so the meta-reviewer must be Sentinel).
   2. `o.fail(skeptic_task_id, reason='REQUEST_CHANGES — see
      <SKEPTIC-VERDICT-...>.md')` to durably close Skeptic's task.
   3. `o.fail(implementer_task_id, reason='skeptic_request_changes:
      <one-line summary of the important finding> — see
      <SKEPTIC-VERDICT-...>.md')`. The parent task's failure
      `reason` is the durable event payload; a future operator
      recovering from the ledger will see what blocked acceptance.
   4. Propose a remediation task:
      `o.propose(title='<name> remediation <iteration-letter>: <fix
      scope>', intent='Fix <each important finding> in the same worktree.
      Strict TDD: failing test first. No edits outside the in-scope
      files. not_self_approved: true.',
      assignee_profile=<same implementer profile>, required_capability=...,
      verification=..., idempotency_key='<user>:<name>-remediation-<letter>:
      <date>', risk_tier='r1', timeout_s=5400, max_attempts=1,
      reviewer_profile=<the other reviewer>, parent_task_id=<implementer_task_id>,
      labels=['control_plane','remediation','offline_only','<name>_remediation'])`.
      Then `o.approve(...)` against the same authorization manifest.
   5. The bounded implementer produces a new result file at
      `IMPLEMENTER-RESULT-<iteration>.md` with a fresh
      `tracked_diff_sha256`. The orchestrator does NOT modify the
      original implementer task; the new task is a sibling in the
      ledger.
   6. Re-anchor: write fresh SENTINEL and SKEPTIC contracts bound to
      the new `tracked_diff_sha256` (and the new combined digest, if
      you compute it). The contracts name the new digest in their
      candidate identity block; the reviewer reports
      `BLOCKED` if the diff has drifted between the contract and the
      worktree.
   7. Re-run the in-fleet review pair against the new digest, same
      cross-reviewer pattern, same verdict schema. Iterate the
      remediation cycle (step 8.4–8.6) until both verdicts pass.
   8. Only on a clean `SENTINEL=PASS` and `SKEPTIC=APPROVED` against
      the latest digest does the orchestrator `accept` that digest.
      The accepted digest is the one bound to the published
      implementation; earlier rejected digests stay in the ledger as
      part of the audit trail.
   This cycle is bounded: each remediation run reuses the same
   worktree, the same authorization manifest, and the same provider/model
   lane. The user does not need to re-authorize per iteration; only the
   `idempotency_key` and the iteration letter change.

## Pitfalls

- **Do not require the operator to hand-carry the review packet.**
  The user has stated the preference explicitly and emphatically:
  never ask the operator to transport prompts, packets, or receipts
  between agents. If the in-fleet reviewer route is genuinely
  unavailable, return one precise blocker naming the missing profile,
  lane, or permission — do not freeze a packet and ask the operator to
  run the review manually. The default for "needs review" is to
  dispatch Sentinel and Skeptic as in-fleet child sessions through
  the same canonical `Orchestrator.propose → approve → claim → start`
  lifecycle the implementer used. The operator preference is not
  negotiable; the moment you reach for "the operator will run this
  manually," you have already lost the right framing for the task.

- **Do not launch the reviewer with the orchestrator's own
  provider/model lane as a default.** Always use the lane the
  implementer used, or the lane the operator explicitly named for
  reviewers. A reviewer running on a different lane than the
  implementer is an undeclared configuration change.

- **Do not guess `required_capability` strings.** Look up the
  reviewer's declared capability from its installed profile or the
  canonical roster. Common pairs: `noesis-sentinel` → `code_review`;
  `noesis-skeptic` → `adversarial_review`. A made-up token is a hard
  `capability_mismatch` at admission; a token that happens to also
  be in the reviewer's declared set but is the wrong one will be
  silently accepted.

- **Do not name the implementer as `reviewer_profile`.** Cross-review
  (Sentinel reviews Skeptic's task, Skeptic reviews Sentinel's task)
  is the default. Even with three or more reviewers, never name the
  implementer profile, the orchestrator profile, or any other
  non-reviewer profile as `reviewer_profile`. The policy rejects
  non-reviewer profiles with `reviewer_must_be_reviewer_only`.

- **Do not accept the implementer task on a green reviewer exit
  alone.** The reviewer writes a verdict file; the orchestrator reads
  it, validates the schema, verifies the recorded digest matches the
  contract digest, and only then calls `accept`. A green process
  exit is not completion when the verdict file is missing, malformed,
  or records a different digest.

- **Do not let the reviewer edit the candidate worktree.** Reviewers
  may read files, run tests, and write their verdict file at the
  documented path. Anything else (`git status --porcelain` shows
  changes in the worktree after the reviewer exits) is a
  contract violation; treat it as `BLOCKED` and re-dispatch with
  explicit guard.

- **Do not lose the implementer worktree's identity across
  reviews.** After Sentinel finishes and before Skeptic starts, the
  candidate diff SHA-256 must still match the contract. A working
  tree that has drifted (an external commit, a clean, a checkout of a
  different branch) is a different candidate; re-bind the contract
  with the new digest or halt the chain.

- **Do not paste the review contract on the command line.** Use
  `--query-file <contract.md>`. Rich-markup-shaped tokens
  (`[...]`, `<...>`) in a `-q` argument crash the CLI before the
  model is invoked. The contract is too long and too structured to
  survive shell parsing; the file is the safe channel.

- **Reconcile the complete status against the closed in-scope path set before
  review.** Run `git status --porcelain` and `git diff --stat HEAD`; do not inspect
  tracked paths alone because new tests and source files are commonly untracked.
  Preserve unrelated work rather than silently resetting it. If an out-of-scope
  change belongs to the bounded worker and restoration is authorized, restore
  that path, recompute every affected digest, and rewrite both reviewer contracts
  before launch; otherwise stop for ownership resolution. Put explicit clean-file
  booleans in both verdict schemas for protected unrelated artifacts so any
  post-freeze drift yields `BLOCKED`.

- **Never dependency-gate Sentinel on the implementation task it must
  review.** Freeze the implementation handoff and candidate first, leaving
  the implementation in `awaiting_review`; give Sentinel
  `parent_task_id=implementer_task_id` for lineage but no `depends_on` entry.
  Otherwise `claim` requires the implementation to succeed before review,
  while implementation success itself requires that review—a circular gate.
  Dependency-gate only Skeptic on the Sentinel review task, then claim Skeptic
  after Sentinel's validated `PASS`. If pre-created templates used the
  circular dependency, cancel them through `Orchestrator.cancel` with a typed
  supersession reason and create fresh review tasks; never edit the ledger or
  bypass `propose → approve → enqueue → claim → start`.

- **Do not coerce authoritative booleans through `bool()` at
  replay.** The verdict file's recorded fields are durable evidence;
  reading them with `bool("yes")` or `bool("false")` silently flips
  the meaning. Parse the verdict with the same shape the reviewer
  wrote; do not "normalize" before validating.

- **Do not label a green reviewer run as "complete" while a finding
  is open.** `verdict: PASS` (Sentinel) or `verdict: APPROVED`
  (Skeptic) is required. `REQUEST_CHANGES` is not a pass even when
  the reviewer exited 0. A `BLOCKED` verdict halts the chain.

- **Convert `UUID` fields to `str` before formatting ledger output.**
  `print('task_id=' + task.task_id)` raises
  `TypeError: can only concatenate str (not "UUID\") to str`. Coerce
  with `str(...)` or use an f-string. The ledger survives; the
  diagnostic output breaks first.

- **Do not steer a running implementer mid-session to relax tests
  or relax acceptance criteria.** When the implementer's first test
  run shows a regression (e.g. 27 failed / 438 passed) and they say
  "let me relax the check to allow backward compatibility", trust the
  TDD cycle: do not inject steering text, do not narrow the
  contract, do not rephrase the acceptance criteria. The bounded
  contract plus their own discipline is the only path that produces a
  candidate the reviewers will accept. A reprieve now creates a
  green test that does not actually verify the fix, and the
  rejection-then-rework round-trip costs more wall-clock than the
  implementer's own recovery. The orchestrator's only legitimate
  interventions during the implementer run are: stop, restart with a
  fresh idempotency_key, or escalate a precise blocker.

- **Bind both tracked and combined digests when untracked candidate bytes
  exist.** `git diff HEAD | shasum -a 256` covers tracked changes only; it can
  stay unchanged while a new source file or test changes. Always record and
  reproduce the tracked digest. When any in-scope candidate path is untracked,
  the contract and verdict must also record the combined digest over the tracked
  diff plus ordered, path-prefixed untracked bytes. Neither digest substitutes
  for the other, and a reviewer that cannot reproduce both must return
  `BLOCKED`.

- **Iteration-letter the artifact filenames.** The first implementer
  writes `IMPLEMENTER-RESULT-A1.md`; the first Sentinel writes
  `SENTINEL-VERDICT-A1.md`; the first Skeptic writes
  `SKEPTIC-VERDICT-A1.md`. On the second iteration, shift to
  `B1` (`IMPLEMENTER-RESULT-B1.md`,
  `SENTINEL-VERDICT-B1.md`, `SKEPTIC-VERDICT-B1.md`). The
  contracts name the expected verdict-file path; the orchestrator's
  accept criteria check the file at the named path. Do not overwrite
  an earlier verdict file with a later one; a fresh iteration gets a
  fresh letter.

- **When recording an external verdict file into a review-task's
  ledger state, drive the task through its own handoff lifecycle
  first.** The review-task's `delegation.candidate_revision` must be
  set via `o.submit_candidate(review_task_id,
  candidate_revision=<the candidate digest the reviewer checked>,
  candidate_digest=<same>, attempt_epoch=<the review-task's current
  attempt_epoch>)` BEFORE `o.record_review(...)` is called;
  otherwise the policy raises `stale_candidate: review candidate
  '<new>' != current 'None'`. The handoff payload for the
  review-task itself must include `summary`, `artifacts` (with
  `path` and `role` per entry), and `verification_result` with
  `passed: True`; otherwise `o.succeed(...)` raises
  `handoff_incomplete: handoff is missing required field ...`. The
  reviewer name passed to `record_review` is the *cross-reviewer*
  profile, not the implementer of the review-task: a Sentinel
  review-task is implemented by Sentinel, so its meta-reviewer is
  Skeptic; the policy raises `reviewer_not_independent: reviewer
  must differ from the implementer` if you pass
  `reviewer='noesis-sentinel'`. Set the review-task's
  `reviewer_profile` to the cross-reviewer at propose-time
  (`reviewer_profile='noesis-skeptic'` for Sentinel's task, and
  vice versa), AND pass `reviewer=<cross-reviewer>` to
  `record_review`. Both must agree.

## References

- `references/bounded-session-launch.md` — the exact `hermes -p <profile> chat --query-file ... --oneshot --provider <lane> -m <model> -t file,terminal --ignore-user-config --in <worktree> --run-budget <s> --max-turns <N> --format stream-json --reasoning <level>` invocation, per-flag notes, background-process parameters, and failure modes.
- `references/review-task-state-machine.md` — the exact `Orchestrator` method sequence to close a review-task on the canonical ledger after the verdict file lands: `enqueue → claim → start → submit_candidate → submit_handoff → record_review(stage='spec') → record_review(stage='quality') → succeed` (or `fail` on `REQUEST_CHANGES`/`BLOCKED`). Includes every PolicyViolation the orchestrator raises and the trigger that raises it, plus the cross-reviewer pattern for `record_review` (reviewer argument must differ from `assignee_profile`).
- `references/verdict-schema-and-digest-recipe.md` — the byte-exact verdict-file schema (Sentinel and Skeptic), the candidate-identity block both contracts must mirror, the `implementation_plan_md_clean: <true|false>` boolean gate, the cross-reviewer mirror of the same field on Skeptic's verdict, and the recipe to compute `combined_sha256` from `git diff HEAD` plus each untracked file's contents. Use this when authoring a B-series contract.

## Verification

Prove the skill worked with these checks (all read-only):

```bash
# 1. Both verdict files exist and match their schemas
ls /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SENTINEL-VERDICT-*.md
ls /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SKEPTIC-VERDICT-*.md

# 2. Each verdict file begins with the correct verdict token and ends with not_self_approved: true
head -1 /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SENTINEL-VERDICT-*.md
tail -1 /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SENTINEL-VERDICT-*.md

# 3. Both recorded tracked_diff_sha256 values match the contract digest
grep tracked_diff_sha256 /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SENTINEL-VERDICT-*.md
grep tracked_diff_sha256 /Users/elvis/.hermes/profiles/noesis-orchestrator/artifacts/<deliverable>/SKEPTIC-VERDICT-*.md
git -C /Users/elvis/.hermes/profiles/noesis-orchestrator/workspace/worktrees/<name> diff HEAD | shasum -a 256

# 4. The candidate worktree is unchanged by the reviewers
git -C /Users/elvis/.hermes/profiles/noesis-orchestrator/workspace/worktrees/<name> status --porcelain
# expected: the implementer's in-scope diff only; no new files, no new commits

# 5. The implementer task has transitioned to completed through the orchestrator, not by hand
PYTHONPATH=orchestration/orchestrator python3 -c "
from app.control_plane import Orchestrator
from pathlib import Path
o = Orchestrator(Path('<ledger_path>'))
t = o.store.get('<implementer_task_id>')
print(t.state, t.accept.operator if t.accept else None)
"
# expected: completed elvis
```

## Related skills

- `noesis-task-delegation` — broader delegation procedure; the review
  step there now embeds this skill's pattern as the default.
- `noesis-control-plane-dev` — control-plane development, lease and
  bootstrap handoff rules.
- `omh-code-review` — shape of findings, verdict schema reference,
  `references/review-dispatch.md` for OMH review-dispatch semantics.
- `subagent-driven-development` — fresh implementer per task; review
  chain in this skill composes with that workflow.
