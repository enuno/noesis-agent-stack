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
6. **Skeptic — hard dependency.** Contract requires a validated Sentinel
   `PASS` for the exact digest; `REQUEST_CHANGES` or `BLOCKED`
   hard-blocks Skeptic. Never launch or stage the dependent reviewer
   against a non-PASS receipt, and never reinterpret the verdict to
   unblock it.

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
