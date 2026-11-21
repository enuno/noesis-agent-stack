# Formal qualification rounds (operator-mediated)

A formal qualification round independently qualifies a **frozen candidate
digest** through a Sentinel receipt and then a Skeptic receipt, under an
operator action packet with explicit retained promotion holds. It is an
operator-mediated external event: the operator launches each reviewer as a
fresh one-shot session from their own shell; the orchestrator never
launches reviewer inference itself. This file is the orchestrator-side
procedure; `noesis-task-delegation` covers ordinary delegation and
`noesis-delegation-monitoring` covers timeout/requeue reconciliation.

## Round lifecycle

1. **Freeze the candidate.** Capture both source bases (commit SHAs), the
   tracked binary diff, the status manifests, and ordered per-file hashes
   of every included untracked path, using the round's freeze tooling
   (e.g. `tooling/freeze_candidate.py <evidence-dir> --verify <digest>`
   both produces and later re-confirms the canonical digest). Record the
   digest, recipe hashes, and membership explicitly; unrelated untracked
   directories are named but never read.
2. **Fresh stability verification against the LIVE worktrees before any
   reviewer launch — never `freeze_candidate.py --verify` alone.**
   `--verify` rehashes the evidence files stored in the evidence
   directory; it proves the stored evidence is self-consistent, not that
   the live worktrees still match it. A post-verdict edit to a live tree
   leaves `--verify` green while the candidate has silently changed (this
   has happened: a `--verify` MATCH coexisted with a live-tree fix that
   predated the round, and the drift was invisible until a full live
   comparison ran). The fresh-stability gate is a full live comparison,
   in this order:
   - both worktrees' `git rev-parse HEAD` equal the frozen source bases;
   - the current `git status --porcelain` output equals the frozen status
     manifest byte-for-byte;
   - the current `git diff HEAD` equals the frozen binary diff
     byte-for-byte;
   - every in-scope untracked path re-hashes to its frozen per-file
     SHA-256;
   - only then run `freeze_candidate.py <evidence-dir> --verify <digest>`
     as the final self-consistency check.
   Any mismatch stops the sequence. Frozen evidence is never rewritten
   to force a match — drift means re-freeze as a new digest round.
3. **Operator action packet** — one durable entrypoint document holding:
   current gate state, evidence/contract pins (path + SHA-256 for every
   contract and receipt), the exact reviewer launch commands, the receipt
   validation gates, and the retained-holds list. The orchestrator keeps
   the gate-state section current as each stage lands; a stale gate state
   is how a future session launches the wrong next step.
4. **Sentinel.** Default: the operator launches a fresh one-shot reviewer
   session from their own shell. Exception — only when the operator's
   authorization for that round explicitly delegates the launch ("if an
   existing authorized tool can launch the exact named reviewer session,
   use it"), the orchestrator may launch it, and then only after all of:
   - **Route readiness, static signals first:** the named profile's
     source manifest (SOUL.md, config.yaml, honcho.json) re-hashes to
     the packet's expected value; the provider appears in the global
     auth store's provider/credential-pool lists (a provider can resolve
     globally even when the profile's own auth.json lacks it — absence
     at profile level is not refusal evidence); the model appears in
     the runtime model cache for that provider. Do not spend a probe
     inference call to test readiness — an authorized launch that dies
     pre-delivery costs nothing and is itself the decisive readiness
     test.
   - **Route amendment recorded before launch** (round-1 pattern):
     provider/model pair, attempt number continuing the round's
     chronology, fallback prohibited, tool scope, contract path + hash.
     Refused routes are never retried without new readiness evidence.
   - **Launch evidence captured, not assumed:** run the session bounded
     (`--max-turns`, tool scope `file,terminal`, `--ignore-user-config`
     + explicit provider/model pin, `--query-file` never inline),
     background with exit notification. Confirm from the stream-json
     session log — not from hope — the init event's `"model"` field
     names the authorized model, and record PID, session id, and the
     first observed tool calls. A pre-delivery refusal, a missing
     verdict, or a timeout stops the round and is reported verbatim.
     Receipt lands at the documented path.
   - **Disclose unenforceable limits.** The gateway does not support
     `--run-budget`, so a wall-clock bound cannot be enforced by flags;
     a review under `--max-turns 300` can run for hours. State that in
     the amendment instead of implying a bound that does not exist.
5. **Receipt validation (orchestrator).** Lexical gates: first line is an
   allowed verdict token; last line exactly `not_self_approved: true`;
   reviewer, candidate digest, both source bases, profile-source manifest
   hash, `candidate_unchanged`, and session provider/model present.
   Semantic read: A/B/C conclusions, per-finding disposition, test
   chronology (including environmental-defect runs), identity binding.
   Then update the packet gate state.
6. **Skeptic — hard dependency, unless the operator requires parallel
   independent finalization.** Default: the contract requires a validated
   Sentinel `PASS` for the exact digest; `REQUEST_CHANGES` or `BLOCKED`
   hard-blocks Skeptic. Never launch or stage the dependent reviewer
   against a non-PASS receipt, and never reinterpret the verdict to
   unblock it. Exception: when the operator requires that neither reviewer
   see the other's findings before both finalize, do not hard-gate Skeptic
   and do not put the other receipt in either contract. Launch both against
   the same frozen digest, record the override, and reconcile only after
   both receipts exist.

   **Second-reviewer route-policy determination — cite written policy,
   never assume.** When the operator names a preferred route for the
   second reviewer, first determine WHAT independence the applicable
   policy requires: the usual written rule binds the REVIEWER's
   provider family to the IMPLEMENTER's/authors' families (anti
   self-review), not reviewer to reviewer — but read the actual policy
   text for the mission instead of assuming, and never silently waive
   a different-provider boundary the text does require. If the named
   route satisfies the written rule (e.g. both reviewers on one family
   that differs from every authoring family), record the determination
   with its citations in the route amendment, and disclose the residual
   common-mode correlation explicitly — both reviewers sharing one
   provider family is a correlation risk the record must carry, not a
   model diversity claim. If the route violates the written rule, stop
   the launch and return the exact restriction plus ONE eligible
   alternative proposal; do not silently substitute or retry refused
   routes without new readiness evidence.
7. **Outcome.** PASS + APPROVED → qualified *for the offline package
   only*, with retained holds named explicitly (production installation,
   live delegation, credential-resolver binding, plugin field forwarding,
   canonical ledger configuration, unenforced spend/request/token
   controls). Any other disposition → operator decision: bounded
   remediation round, or terminal disposition for that digest.

## Orchestrator-executed delegated launch (operator explicitly delegates)

When the operator's round authorization explicitly delegates the launch
("use an existing authorized tool to launch the exact named reviewer
session"), the orchestrator executes the launch itself, in this order.
The operator-mediated default above and this exception are the only two
legal shapes; nothing else may launch reviewer inference.

1. **Coordinator preflight (never a substitute for reviewer
   verification).** Resolve the mirror, worktree, branch, and HEAD; confirm
   `git status --porcelain` matches the frozen membership exactly (no
   untracked files); confirm `git diff` byte-matches the frozen patch;
   re-hash the verifier script against the recorded SHA-256; take the full
   combined digest from the verified manifest, never from an abbreviation.
   Coordinator preflight does not replace the per-reviewer identity
   verification each contract demands.
2. **Policy determination before choosing the route.** Read the approved
   lanes in `platform/inference-routing.yaml` and confirm the chosen lane
   permits the reviewer profile types (`security`, `qa`) and task classes
   (`code_critique`, `qa_analysis`) and pins the model. A
   `runtime-reconciliation.yaml` row with `resolution.state: blocked`
   concerns the profile's repo-declared lane (typically a disabled
   OpenRouter route) and fires at the control-plane spawn gate for THAT
   route — it does not block a different, operator-authorized lane. Record
   which lane is used and why; never edit route declarations, profile
   configs, or the freeze to make a route work.
3. **Route amendment recorded BEFORE launch**, containing: provider/model
   pair and its policy-lane name plus the registry provider id (lane names
   are not provider ids — resolve via `hermes_provider_for_lane` or the
   registry); attempt chronology continuing the round; fallback prohibited;
   tool scope; the honest wall-clock disclosure (`--max-turns` bounds
   iterations only, no `--run-budget` exists); common-mode correlation
   disclosure when both reviewers share one lane (a recorded risk, not a
   diversity claim); and path + SHA-256 pins for every contract. Also
   record any resolved-reading deviations the operator's text instructs
   (e.g. parallel launch instead of the ordered default) — disclose which
   clause governs, never silently reinterpret.
4. **Contract authoring.** One file per reviewer, Rich-safe (run the
   fence-aware audit; zero `[ ] < >` outside code fences — see
   `noesis-task-delegation` for the audit one-liner). Each contract
   carries: the exact identity bindings (worktree, base SHA, full combined
   digest, patch/manifest/packet paths + hashes, verifier path + expected
   bytes); a numbered self-run verification procedure with expected values
   per step and an ABSTAIN-on-mismatch rule; the role's question IDs
   verbatim; explicit finding-disposition requirements; any discrepancy
   facts labeled as orchestrator-reported and marked verify-independently
   (the reviewer must not trust coordinator claims); a single declared
   receipt path and the receipt's lexical gates (line 1 verdict token,
   final line `not_self_approved: true`, digest and identity fields);
   read-only discipline including `PYTHONDONTWRITEBYTECODE=1` and
   `pytest -p no:cacheprovider` if tests run, plus candidate-unchanged
   before/after diff hashes; and an embedded expected profile-manifest
   SHA-256 (hash of the profile dir's `SOUL.md` concatenated with
   `config.yaml`) so the reviewer self-attests the loaded identity.
   Give neither reviewer the other's findings or verdict.
5. **Ledger lifecycle without `route_and_launch`.** Persist the full
   canonical walk — `propose → approve → enqueue → claim → start` —
   against the authoritative ledger (`enqueue` is a real state; `claim`
   from `approved` is refused). Label `degraded_dispatch` and record the
   route deviation in the intent. Make the driver re-runnable by reusing
   the already-proposed task ID looked up from the ledger by idempotency
   key. Take a byte-copy of the ledger before the first write and read
   every appended event back.
6. **Launch and capture evidence.** Tracked background one-shot sessions,
   `--query-file` never inline, pinned provider/model, stream-json logging.
   From each log confirm the init event's `model` field names the
   authorized model, record PID/session, and grep for the exact
   `Model fallback` marker (bare-word counts are dominated by file
   content). A pre-delivery refusal is `dispatch_not_delivered` at zero
   cost — record the child's captured error verbatim and stop the round;
   do not retry a refused route without new readiness evidence and do not
   spend a probe inference call on readiness.
7. **Record-keeping traps.** Append audit rows only to the ledger you
   verified by path AND expected shape (line count or a known anchor):
   identically named ledgers can exist in the profile workspace and the
   mission artifact directory, and a row written to the wrong one is a
   silent fork of the record. Report inference usage from the profiles'
   `state.db` usage rows after the run; anything not observed stays
   unknown.

After both receipts land: validate lexical gates first, then read
semantically; record the reviews through the control plane; reconcile
findings individually (never by majority); and keep the per-reviewer
status explicit in the ledger.

## Remediation round → new digest

- Fixes land on the candidate worktree under a bounded contract (closed
  in-scope file set, TDD, no commits, no freeze-evidence edits); the
  frozen digest is intentionally invalidated — the orchestrator re-freezes
  afterwards, never the implementer. When the canonical implementer
  launcher is credential-blocked, a separate-session `delegate_task` child
  is an eligible bootstrap development executor — record its delegation id
  and model in the packet and require them in the receipt's provenance
  block; do not impersonate the unavailable profile.
- Verify every command in the orchestrator-authored contract by running it
  once before dispatch (exact interpreter, exact env prefix). A wrong path
  or a missing PATH prefix sends the worker into an environmental failure
  that reads as a candidate defect and pollutes the test chronology.
- Discrimination binds to EVERY predecessor form of the defect, not just the
  original. A fix's new tests must fail against each historical form (e.g.
  both the original passthrough AND an intermediate partial fix), not only
  the first failure a reviewer reproduced — a test that passes against an
  intermediate predecessor form cannot prove the final fix closes the
  defect. Name each predecessor form in the contract and require per-form
  reversion evidence in scratch copies.
- When the operator requires it, the review contract carries a dedicated
  PROVENANCE ASSESSMENT section with five mandatory judgments: established
  provenance, what remains unknown, the policy applied, whether additional
  evidence is required, and the qualification consequence — with
  content verification and provenance-policy acceptance reported as
  separate verdicts. Receipt validation checks the section exists and
  answers all five.
- **Move every receipt/result artifact out of the candidate worktree
  BEFORE capturing freeze evidence.** An in-worktree receipt is an
  untracked file: it pollutes the status manifest and changes the
  combined digest, and a capture taken before the move freezes the wrong
  membership. Order: worker finishes → move the result receipt to the
  durable artifact directory → capture → compute the digest → only then
  write contracts that cite the digest. If a capture already ran with
  the artifact in-tree, re-capture, recompute, and record the change —
  see the superseded-digest rule below.
- **If the digest changes after it reached any contract or packet,
  declare the superseded value.** A re-capture (extra untracked file,
  reordered membership) changes the digest; every intermediate digest
  that ever appeared in an artifact must be recorded in the receipt
  chronology as superseded with its reason, so the record explains every
  digest that ever existed. An unexplained digest swap looks like
  evidence tampering to the next reviewer.
- **Declare unrecorded pre-dispatch edits; never conceal them and never
  silently revert them.** When git shows a change no session recorded
  (e.g. an earlier session applied the reviewer-prescribed fix and
  exited without a ledger or receipt event), keep the change if and
  only if it matches the reviewer's prescribed remediation exactly, and
  declare it in the fresh-stability receipt — file, approximate time,
  originating session unknown. Concealing it invalidates the evidence
  chain; reverting it recreates the defect the reviewer ordered fixed.
- **Cross-check the remediation worker's reported changed-paths against
  git before freezing.** A worker's self-reported `changed_paths` can
  omit a file that did change; `git status -s` and `git diff --stat
  HEAD` in the worktree are the authoritative changed set (see the
  `delegate_task` self-report pitfall in `noesis-task-delegation`).
  Resolve every git-reported change the receipt does not account for —
  as a reporting gap or as a pre-dispatch edit to declare — before
  computing the round digest.
- When the prior round's candidate is frozen review history that must
  stay untouched, repair in a NEW worktree and gate the first edit on
  lineage reproduction. Create the successor worktree at the same base
  SHA, `git apply` the prior round's frozen patch, and recompute the
  path-prefixed combined digest over the changed-file set BEFORE any
  repair edit: it must reproduce the prior round's frozen digest
  byte-for-byte. Only then edit. Three mechanics bite reliably: fetch
  the base SHA from `origin` (a local mirror remote can be many commits
  stale and checks out the wrong tree); run `git worktree add` from
  inside a repo (`git -C <repo> worktree add ...` — run from an ordinary
  directory it fails with `fatal: not a git repository`); and capture
  the branch name from `git branch --show-current` into the manifest
  and packet at freeze time instead of typing the intended name — a
  typed-name/disk-name mismatch is cosmetic but costs every reviewer an
  identity observation.
- Successor packets correct the record; they never edit the old packet
  to make its claims look right. When the prior repair fixed a different
  instance than the finding named (a different file or field), the
  successor packet must re-frame the finding to its original reported
  subject (exact file + field + line) and require reviewers to verify
  byte-level change at THAT location — not at the location the prior
  repair happened to touch. The prior packet stays frozen as history.
- Re-run the full offline battery, freeze a **new** digest, run fresh
  stability, and stage a new Sentinel+Skeptic round against the new
  digest with fresh contract/receipt filenames.
- **Never carry a verdict, finding disposition, or per-finding closure
  across digests.** Prior-round receipts are inputs only; each round is
  judged on its own digest.
- Ledger reconciliation uses explicit per-reviewer status (e.g.
  `SENTINEL_REQUEST_CHANGES` / `SKEPTIC_BLOCKED`) and preserves the
  complete test chronology, including failed and environmental-defect
  runs, in order.

## Artifact locations

Freeze evidence (status/diff manifests, per-file hashes, freeze tooling,
digest file) lives in a `round<N>-evidence/` directory inside the
candidate worktree's workspace — it is part of the frozen identity.
Contracts, verdicts, receipts, the fresh-stability verification, and the
operator action packet live in the main checkout's `formal-qualification/`
directory: durable, outside the candidate, and never mixed into the
freeze membership. Scratch/cache directories are never authoritative —
they are pruned; anything a future session must re-derive (hash recipes,
launch commands) should be copied into the durable evidence directory.

## Orchestrator never

- launches reviewer inference itself, except when the operator's
  authorization for that round explicitly delegates the launch — and
  then only with the route-readiness checks, pre-recorded route
  amendment, and session-init evidence above;
- rewrites or regenerates frozen evidence to force a match — drift stops
  the sequence;
- stages the dependent reviewer against a non-PASS receipt;
- counts downstream production/live holds as defects in the offline
  package, or lets them inflate/conceal a package-level disposition;
- treats a receipt's static fields (`model_driven_canary`,
  `verification_pending`) as live provider state when diagnosing a
  refused launch — read the child process's captured error text instead
  (see `noesis-delegation-monitoring`).
