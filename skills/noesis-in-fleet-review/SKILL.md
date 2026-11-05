---
name: noesis-in-fleet-review
description: "Run Noesis Sentinel and Skeptic as in-fleet child sessions."
version: 0.4.0
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

**Scope boundary — formal qualification rounds are operator-mediated.**
The in-fleet default above governs ordinary implementation reviews. A
*formal qualification round* — an independent Sentinel then Skeptic receipt
chain bound to a frozen candidate digest, with an operator action packet
and retained promotion holds — is an operator-mediated external event by
standing operator policy: the operator hand-carries the frozen packet, and
each reviewer runs as a fresh one-shot session; the orchestrator never
launches reviewer inference itself unless the operator's authorization
for that round explicitly delegates the launch. On that class,
the orchestrator's duties are packet preparation, receipt validation, gate
state maintenance, remediation-round staging, and synthesis — see
`references/formal-qualification-rounds.md`. Everything else in this skill
(propose/claim/launch mechanics, verdict schema, cross-reviewer pattern,
remediation cycle) still applies to the operator-launched sessions as
contract shape, not as orchestrator-side launch steps.

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
- Formal qualification rounds (frozen-candidate Sentinel/Skeptic receipt
  chains): those are operator-mediated external events — use
  `references/formal-qualification-rounds.md` for the orchestrator-side
  duties; this skill supplies only contract shape.
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
   - Every count, size, and digest in that identity block GENERATED from the
     artifacts, never typed. A hand-typed count or size is the most common
     cause of a reviewer BLOCKING at the identity gate before it reviews
     anything. Generate the block with `scripts/packet_identity.py render`
     and gate the dispatch with `scripts/packet_identity.py verify` -- see
     `references/review-packet-identity.md`.
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
     --max-turns 300 \
     --format stream-json \
     --reasoning high
   ```
   (No `--run-budget`: the installed gateway CLI rejects it; see
   `references/bounded-session-launch.md`.)
   Run it as `background=true`, `notify=true`, with
   `persist_on_release=true` so the verdict is preserved across
   compaction.   The `--ignore-user-config` + explicit provider/model
   pattern keeps the profile's config layer out of the launch while
   preserving Sentinel's profile identity and rules. Sentinel runs are
   *not* exempt from the no-fallback rule, and the flag is not proof
   the chain is gone: verify the effective route after the fact from the
   session's own billing rows (see the positive route-verification rule
   below) rather than inferring it from the flag. Use the lane the governing
   policy alias makes eligible and that the operator's envelope names;
   when the alias requires the review route to DIFFER from the
   implementation route, a lane identical to the implementer's is not
   compliant even though it is the launcher's historical default.
   Provider/model approval
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

   **Retry and substitution authority is five separate mechanisms — state
   each one, because "the review needs many turns" is permission for none
   of them.** (i) retries WITHIN a model request (`agent.api_max_retries`),
   (ii) transport/stream reconnection (`HERMES_STREAM_RETRIES` plus the
   provider runtime's own transport-error retry), (iii) automatic recovery
   cycles (`agent.auto_recovery_cycles`), (iv) provider/model fallback,
   (v) replacement review sessions. A review legitimately needs many model
   TURNS — that is the work, not authority for (i)–(v). Only (v) consumes a
   review session, and only the envelope can authorize it. Reaching (i) or
   (iii) normally means editing a live profile config, which the envelope
   may not authorize: when it does not, record the runtime default as a
   disclosed limit instead of editing the profile to reach a nicer number.
   Only (ii) has a supported per-invocation switch that touches no file.

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
   on a critical requirement, or a `BLOCKED` verdict all halt the chain.
   Classify the `BLOCKED` before routing: one that stopped at the
   prerequisite identity gate reviewed nothing and goes back to the packet,
   not the implementer; one that carries findings routes to the implementer.
   A `PASS` opens the gate for Skeptic.

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
   5a. **Replay the reviewer's exact adversarial suite against the
       repaired candidate before accepting the repair cycle.** Run the
       reviewer's file verbatim — the one it wrote, not an
       implementer re-expression of it — and compare the per-test result
       against the implementer's own report row for each test. The
       reviewer's file is the spec; the implementer's report is a claim
       about it. When the repair cycle also closed a repeated finding
       shape, require the class sweep table in the same receipt and treat
       a missing table as an incomplete cycle.
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

8b. **When the remediation-cycle budget is spent, end the workstream with a
   concrete blocker instead of starting another cycle.** The budget counts
   implementation/review repair cycles, not reviewer verdicts, and it is
   spent whether the cycle produced a PASS or a REQUEST_CHANGES. Once the
   last allowed cycle's candidate has had its full review chain, a
   publication-affecting negative verdict ends the workstream: record the
   blocker with the file, the line, the concrete failure sequence, and the
   remediation that would fix it, preserve the final candidate and every
   verdict as evidence, and report the workstream as blocked. Do not
   dispatch a third implementer, and do not re-review an earlier digest —
   the earlier verdicts are superseded, not reusable. Distinguish this from
   a mid-chain negative verdict, which routes back to the implementer
   normally. Also note when the final candidate passed one reviewer and
   failed the other: that asymmetry is the strongest evidence that the
   remaining gap is real and is worth naming, because the passing reviewer
   had already cleared the specification while the adversarial reviewer
   found a path the specification did not cover.

   **Read the bound's exact wording before declaring it spent.** A budget
   phrased as "N cycles per newly discovered issue group" grants N cycles
   per group, not N cycles for the whole workstream, and "per" is doing
   real work. Classify each round's findings as a newly discovered group
   or a re-surface of an open one, and track consumption per group. If you
   already told the operator a budget was exhausted and then read the
   bound and find it says otherwise, correct it plainly: quote the
   wording, state the reading you are now applying, and say whether to
   continue. Do not silently reinterpret the bound in either direction,
   and do not open another group's budget without saying so.

## Pitfalls

- **Do not require the operator to hand-carry the review packet —
  except in formal qualification rounds, where that IS the authorized
  path.**
  For ordinary implementation reviews the user has stated the preference
  explicitly and emphatically: never ask the operator to transport prompts,
  packets, or receipts between agents. If the in-fleet reviewer route is
  genuinely unavailable, return one precise blocker naming the missing
  profile, lane, or permission — do not freeze a packet and ask the
  operator to run the review manually. The default for "needs review" is
  to dispatch Sentinel and Skeptic as in-fleet child sessions through
  the same canonical `Orchestrator.propose → approve → claim → start`
  lifecycle the implementer used. For a formal qualification round the
  framing inverts: the operator-mediated launch is the authorized
  reviewer path (the packet says so), and launching reviewer inference
  from the orchestrator would itself be the deviation. Keep the two
  classes distinct and never silently apply one class's routing to the
  other.

- **Do not launch the reviewer with the orchestrator's own
  provider/model lane as a default.** Use the lane the governing policy
  alias makes eligible and the operator's envelope names. A reviewer
  running on an unapproved lane is an undeclared configuration change.
  When the approved lane dies mid-mission, follow the substitution
  procedure below rather than retrying it.

- **A provider safety filter can refuse the reviewer mid-session, and the
  analysis survives even though the verdict does not.** This is a third
  refusal class, distinct from an entitlement block and from a model-support
  error: the lane authenticated, the provider answered, and a CONTENT filter
  refused the request — typically on the turn that would have written the
  verdict, after the reviewer has completed its whole analysis. Segment the
  session stream by `session_id` and count the tool calls that DID complete
  before treating the attempt as empty; preserve the raw stream and the
  reviewer's own scratch artifacts with their digests. Then recover with a
  CONCLUSION dispatch on the SAME lane, same provider, same model, same
  reviewer profile: hand the reviewer its own observed results so it need not
  re-run the analysis, forbid re-reading the preserved suites and authoring
  new probe code, require preserved cases to be referenced by short
  identifier or suite sha256 rather than by quoting their fixture literals,
  and authorise a BLOCKED verdict whose sole reason is the refusal class if
  the filter recurs. A refusal that produced no verdict consumed no verdict,
  so it does not consume the authorised review — but a second refusal on the
  same lane ends the round and needs one consolidated authorization request,
  because switching providers is a substitution and repeating the same
  content against the same classifier is not a fix. See
  `references/reviewer-evidence-verification.md`.

- **A provider quota window is a FOURTH refusal class, and it is
  self-resetting.** HTTP 429 `usage_limit_reached` is not an entitlement
  block, not a model-support error, and not a content filter. Read the
  provider's own fields in the refusal body: `plan_type`,
  `limit_window_minutes` (a value of 300 is a five-hour rolling ACCOUNT
  window, not a per-model one) and `resets_at`. Because the cap is
  account-level, switching to a different model on the same subscription
  does not help — the honest options are to wait for the window or to change
  provider, and changing provider is a substitution needing its own
  authority. When the window is yours to wait out, recover with a SINGLE-FIRE
  re-dispatch scheduled at `resets_at` plus a small margin, on the SAME lane,
  same model, same reviewer profile, gated by the frozen-identity check so a
  delayed dispatch cannot review drifted bytes. Record the outcome as
  `dispatch_not_delivered`: zero tokens and zero tool calls mean the
  authorised review is OUTSTANDING, not consumed, so the envelope still holds
  its review in hand. Do not reset, raise or purchase a limit to avoid
  waiting, and do not let the wait become an unbounded retry loop.

- **When the reviewer's approved lane dies on an entitlement block,
  substitute within the policy — never purchase, never silently retry,
  and never treat the failed dispatch as a verdict.** An HTTP 403
  `spending-limit` or an HTTP 400 "credit balance is too low" is an
  account-level block: retrying the same lane burns the same exhausted
  pool and the candidate gains zero reviews. A failed dispatch is
  `dispatch_not_delivered`, never a verdict and never a partial review.
  Survey before choosing:
  1. `hermes auth list` prints each provider's credential labels,
     priority and exhaustion/cooldown state without secret values — use
     it rather than the raw config or `.env`.
  2. Read the governing alias in the repo's own policy file (for Noesis,
     `shared/model-aliases.yaml` → `capability_aliases.code_review_parallel`):
     it fixes the allowed provider class, the candidate providers, and
     whether the review lane must differ from the implementation route. A
     metered exception path is not eligible for a subscription-only alias.
  3. Distinguish a **model-support refusal** from an **entitlement
     refusal**. A 400 saying the model is not supported on the account
     means the lane authenticated and the provider answered — that is a
     model-id problem, not an exhausted pool, and it does not
     disqualify the lane.
  4. Resolve exact model identifiers instead of guessing: the Nous
     Portal catalog is readable unauthenticated at
     `GET https://inference-api.nousresearch.com/v1/models` (see
     `hermes-agent` → `references/providers-and-models.md`), and a
     provider that answers "model not found" names what it actually
     serves.
  5. Preflight the exact lane with a trivial foreground turn
     (`hermes -p <profile> --provider <lane> --model <id> --ignore-user-config chat -q 'Reply exactly READY. Do not call tools.'`)
     and require the literal `READY` text. A zero exit code is not
     availability — a failed model connection can exit 0 after printing
     an error. `--ignore-user-config`/`--safe-mode` refuses to run
     without an explicit `--model`, so both flags are mandatory there.
     **A probe is an inference call and spends the account's window.**
     Use one only when the envelope budgets one; when the launch is
     operator-mediated, or the review budget is a single session, prefer
     the static route-readiness signals in
     `references/operator-mediated-launch-and-readiness.md` and treat a
     launch that dies pre-delivery as the decisive readiness test.
  6. Substitute only when the governing policy or an operator amendment
     already authorizes the replacement lane. Changing lanes without
     that authority is an undeclared configuration change and needs an
     explicit operator amendment; when the policy already names a
     candidate set, the next live candidate is inside the granted
     authority.
  7. Record the dead lane, the survey evidence, the substitution and the
     preflight session id. The review contract should require the
     reviewer to name the provider and model it actually used, so the
     substitution is visible in the verdict itself.
  8. Write each attempt's log to its own per-lane file and segment any
     shared log by `session_id` before counting tool calls. A log
     appended across attempts will otherwise attribute one attempt's
     tool calls to another; a failed attempt's zero tool calls are the
     proof that nothing partial happened.

     - **When the alias's candidate set collapses to one live lane, both reviewers
     may share it — but record the collapse instead of hiding it.** The alias
     requirement is that the review route DIFFERS from the implementation route,
     so an implementation lane plus one live review lane still satisfies it, even
     when Sentinel and Skeptic must both run on that single lane. Independence
     then rests on profile, session, context and review focus rather than on the
     provider. Name the blocked lanes and their refusal classes in the ledger and
     in the final report. Do not quietly present a single-provider review pair as
     provider-diverse, and do not purchase, raise a limit, or change a
     credential to manufacture a second lane.

     - **Ask the reviewer for a failing reproduction per finding, and reproduce each
     finding yourself before dispatching a repair.** A finding backed by a test
     that FAILS against the candidate is evidence; a finding stated in prose is a
     claim. Require the review contract to have the reviewer write its own
     adversarial test per finding and report the failure output. Then reproduce
     the findings against the current bytes before writing the repair contract: a
     repair dispatched on an unreproduced finding can burn a bounded cycle on a
     non-defect, and the repaired bytes then need a fresh identity and fresh
     review. When a repair cycle itself opened the defect its predecessor fixed,
     name that prior fix and the mechanism it opened in the next repair contract
     so the executor does not repeat the pattern.

- **Verify the route positively, from the runtime's recorded billing
  identity — not from the configured string, and not by excluding
  forbidden providers.** The runtime records a provider alias and a billing
  identity that may differ from what you configured. Learn the
  alias→billing mapping from prior REAL sessions on that lane, and require
  the init event's model, the session row's model, every conversation usage
  row's billing provider/base URL/mode, and the absence of a
  provider-fallback notice. A substituted turn bills a different provider,
  so the billing rows catch substitution that no config-layer argument can.
  Unknown, missing, or unmapped identity BLOCKS the round — never read it
  as probably fine. The mapping and the checklist are in
  `references/operator-mediated-launch-and-readiness.md`.

- **A reversible mutation of a live shared profile is not authorized by an
  envelope that does not authorize it.** Byte-exact restoration is a
  rollback guarantee, not permission: an envelope to "review this
  candidate" does not extend to editing
  `~/.hermes/profiles/<reviewer>/config.yaml`, not even for the duration
  of one launch and not even with a verified restore. The same holds for
  permission bits — do not `chmod` a frozen candidate tree to implement
  read-only reviewer access. Get read-only access contractually (the
  reviewer is told to work in a disposable copy) and verify it (re-hash
  the whole tree before and after), not by mutating shared state. When a
  setting can only be reached by editing a shared file, either find a
  launch method that does not need it or return the limitation with the
  exact edit named — do not perform it.

- **Verify the whole tree, not only the candidate paths, and parse porcelain
  without losing a column.** `git status --porcelain` collapses an
  untracked directory into a single entry, so a new test file inside it is
  invisible to the changed-path set — use `--porcelain -uall` whenever the
  changed-path set IS the identity. When you slice a path out of porcelain
  output, do not `.strip()` the whole command output first: the leading
  two-column status of the FIRST line carries the space that makes
  ` M path` parseable, and stripping it shifts every path by one
  character. Split lines, then slice.

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

- **Do not put GitHub Actions expressions in a double-quoted `-q`
  argument.** `${{ ... }}` is a brace expansion the shell tries to
  substitute, so the launch dies with a `bad substitution` error
  before the reviewer ever runs — and because the reviewer then
  produces no verdict file, the failure looks like a slow or absent
  reviewer rather than a launch bug. When the contract or prompt must
  quote a workflow expression, pass the prompt through a FILE and
  reference it: `-q "$(cat <prompt-file>)"`. A prompt file is also
  the right channel for any prompt carrying `$`, backticks, or newlines.

- **Read the launch's own output when the expected artifact does not
  appear.** A background reviewer that exits without writing its
  verdict file has usually failed at launch, not at review. Read the
  process log before re-dispatching, so a launch bug is fixed once
  instead of being re-run into the same failure.

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

- **The reviewer's adversarial test file is the spec artifact; a rewritten
  copy of it is not evidence.** When the reviewer writes its own failing
  test per finding, that file states in executable form what "refused"
  means. Stage it as a canonical hash-bound artifact and copy it
  BYTE-FOR-BYTE into the candidate suite; never let the implementer
  rewrite it into an equivalent-looking variant. An implementer that
  rewrites the reviewer's assertion into one its own implementation
  happens to satisfy, then reports the reviewer's test as PASSED,
  produces a true-looking report row over a candidate that still fails
  the spec — the rewrite hides the gap instead of closing it. After every
  repair cycle, replay the reviewer's exact file against the candidate and
  diff it against the implementer's own report; a divergence is a
  reporting-accuracy defect and is recorded as one, even when the
  underlying behaviour is already fail-closed. See
  `references/reviewer-evidence-verification.md`.

- **Triage a failing reviewer test into "missing refusal" and "refusal
  present, spec vocabulary differs" before you call it a defect.** A
  negative test can fail because the decision is still ALLOWED (a real
  hole), because the refusal uses a different code name than the
  reviewer's expected set (behaviour is fail-closed, vocabulary differs),
  or because the function raises where the spec expects a returned denial
  (behaviour is fail-closed, API shape differs). Read the actual assertion
  failure before writing the repair contract: the first needs a
  behavioural fix, the second needs the code name aligned to the
  reviewer's expected set, and the third needs the denial converted to a
  returned value. Reporting all three as "the fix did not work" sends the
  executor to repair the wrong thing and burns a bounded cycle.

- **Converge a repeated finding shape with a class sweep, not another
  instance fix.** When consecutive review rounds surface the same SHAPE of
  defect — a caller-supplied or weakly-observed value steering a decision
  that must be bound to an authoritative source — repairing one instance
  invites the next one. Require the implementer to enumerate every
  caller-supplied value that can influence a decision and, for each,
  either bind it to an authoritative source or refuse it, reported as a
  table. Treat the next same-shape finding as an incomplete cycle rather
  than a newly discovered issue group, so one defect's instances cannot be
  counted as separate groups to keep spending the bound. **If the class
  sweep itself converges on nothing — the next same-shape finding appears
  anyway, and the failing instances sit in a surface the operator never asked
  for — the right response is to REDUCE SCOPE, not to cycle again: propose
  shrinking the candidate to the surface that answers the operator's actual
  question, and let the operator choose between that, a binding-model
  redesign, and stopping. See the `noesis-control-plane-dev` skill's
  `references/scope-reduction-and-binding-table.md`.

- **Classify a `BLOCKED` verdict by WHERE it stopped, not by the token
  alone.** `BLOCKED` is not one thing. A verdict that stops at the
  prerequisite identity gate -- before the reviewer ran the suite or examined
  any boundary behaviour -- reviewed nothing, and the cause is usually the
  supervisor's own packet: a file count that omits a `conftest.py`, a
  character count labelled as a byte count, a digest quoted from an earlier
  round. Diagnose that as a PACKET defect, not as a candidate finding: fix
  the packet, keep the candidate bytes UNCHANGED, and write any subsequent
  verdict to a DIFFERENT path so the BLOCKED verdict is preserved unmodified.
  A verdict that carries per-requirement findings or test results IS
  substantive -- it routes to the implementer. Record which of the two you
  found, and record the attempt's measured token and tool-call usage against
  the ceiling either way.

  **Diagnosing where a verdict stopped does NOT authorize the next
  dispatch.** A DELIVERED verdict consumed the review session whatever it
  stopped at: the reviewer ran, the provider billed, the lane was used.
  Whether a second session is permitted comes from the envelope's
  authorization language, not from the verdict's content. An envelope that
  names one review and forbids automatic replacement or continuation
  sessions requires you to RETURN one request naming the re-dispatch you
  want, not to make it. The only case where the session is demonstrably
  still outstanding is a dispatch that never reached the model -- zero
  tokens, zero tool calls, no session row -- because nothing was consumed.
  Precedent from an earlier envelope is never authorization for this one;
  if you dispatch anyway, record it as an authorization deviation rather
  than folding it into the review chronology as if it had been authorized.

- **Gate the dispatch on the PACKET, not only on the candidate bytes.** The
  frozen-identity gate proves the candidate did not move; it cannot prove the
  packet describes those bytes correctly. Run a second check that
  cross-checks every number the packet declares against the artifacts and
  refuses the dispatch on a mismatch, before any provider call. Prove both
  refusal paths with a stub launcher so the refusal is known to happen
  before inference, and keep the stub's output on a separate log so it
  cannot be counted as the session's.

- **Do not label a green reviewer run as "complete" while a finding
  is open.** `verdict: PASS` (Sentinel) or `verdict: APPROVED` (Skeptic)
  is required. `REQUEST_CHANGES` is not a pass even when the reviewer
  exited 0. A `BLOCKED` verdict halts the chain.

- **Do not promote a review outcome into a readiness or release claim.**
  `verdict: PASS` or `verdict: APPROVED` certifies only that this reviewer
  found no defect in the frozen bytes it examined. It is not a qualification,
  not a production-readiness statement, and not a publication approval — and
  a green suite is not a qualification of an invariant that suite does not
  measure. Name the disposition in those terms, report the measured usage
  against every ceiling the authorization named (including a ceiling that was
  breached, and the session that died before writing its own report), and
  end a bounded envelope with ONE exact next decision the operator can
  answer — a specific request — not a menu of options. When a finding
  survives, preserve the candidate and the findings, stop, and state the
  boundary that remains blocked; a preserved failed candidate is evidence,
  and a passing suite on its own is not.

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

- **Do not confuse an in-scope untracked path with out-of-scope pollution,
  and do not confuse a sibling workstream's files with yours.** A new file
  inside the closed candidate set is candidate content and must be in the
  digest. A file belonging to a different, possibly blocked workstream is
  not yours to stage, revert, or cite as evidence; if it shares the working
  tree, leave it exactly where it is and say in your receipt which paths
  you did not touch.

- **Iteration-letter the artifact filenames.** The first implementer
  writes `IMPLEMENTER-RESULT-A1.md`; the first Sentinel writes
  `SENTINEL-VERDICT-A1.md`; the first Skeptic writes
  `SKEPTIC-VERDICT-A1.md`. On the second iteration, shift to
  `B1` (`IMPLEMENTER-RESULT-B1.md`,
  `SENTINEL-VERDICT-B1.md`, `SKEPTIC-VERDICT-B1.md`). The
  contracts name the expected verdict-file path; the orchestrator's
  accept criteria check the file at the named path. Do not overwrite
  an earlier verdict file with a later one; a fresh iteration gets a
  fresh letter. The letter must not live only in a hand-managed contract:
  when a freeze tool regenerates the contract each round, key the filename to
  the candidate digest so the generator cannot reintroduce a fixed path and
  the reviewer's correct compliance silently destroys the prior verdict.

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
- `references/operator-mediated-launch-and-readiness.md` — the
  operator-mediated launch shape (bounded flags, explicit route pin,
  `--query-file`), the static route-readiness signals that cost no
  inference call, the alias→billing identity mapping with the positive
  route-verification checklist, the single-fire schedule plus the
  disable-and-verify-it-cannot-fire recipe, and the monitoring/accounting
  pitfalls that make a monitor's own exit code meaningless.
- `references/formal-qualification-rounds.md` — the operator-mediated
  qualification lifecycle: freeze/stability, packet gate-state
  maintenance, receipt validation, Skeptic hard-dependency, remediation
  rounds on a new digest, and the never-carry-verdicts-across-digests
  rule.
- `references/provenance-attribution.md` — read-only archaeology for an
  unrecorded edit (session stores, shell history, mtimes; circumstantial
  vs attribution) and the P1 attestation / P2 risk-acceptance / P3
  re-author resolution menu for installation assurance.
- `references/reviewer-evidence-verification.md` — proving a repair cycle
  closed what the reviewer found: staging the reviewer's adversarial suite
  as a canonical hash-bound spec artifact and copying it byte-for-byte,
  replaying it with the import origin proven, the three failure classes
  (missing refusal, refusal-code vocabulary, denial API shape), mutation
  teeth, the class sweep that converges a repeated finding shape, and
  reading a per-issue-group cycle bound literally.
- `references/review-packet-identity.md` — the packet's declared numbers are
  load-bearing: how a wrong file count or a character count labelled as a
  byte count blocks a review at the identity gate, how to generate the
  identity block instead of typing it, the two pre-dispatch gates, and how
  to classify and re-issue a gate-blocked review.
- `scripts/packet_identity.py` — measures a candidate's frozen identity and
  cross-checks a review packet against it: `render` prints the measured
  identity block to paste into the packet, `verify` exits non-zero when the
  packet's declared counts, sizes, or digests disagree with the artifacts.

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

```bash
# 6. The review packet's declared identity agrees with the artifacts
#    (run before EVERY review dispatch; exit 0 required)
python3 <skill_dir>/scripts/packet_identity.py verify \
  --manifest <per-file-digests.json> --root <candidate-root> \
  --packet <review-packet.md> --artifact design=<design-artifact.md>
# expected: exit 0 and "PACKET IDENTITY: CONSISTENT with the artifacts"

# 7. A superseded or gate-blocked verdict is preserved, not overwritten
ls -1 <artifacts_dir>/reviews/*VERDICT*.md
# expected: one file per attempt, each at its own path
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
