# Frozen-Candidate Installation / Port / Rollout

Workflow for deploying a candidate that has already passed qualification
(frozen identity digest, Sentinel PASS + Skeptic APPROVED) when the operator
intends to authorize installation, porting, and/or production rollout.
Two-stage shape: (1) read-only proposal by the architecture specialist,
(2) explicit operator final-approval gate, (3) phased execution by the
implementer with per-phase verification and rollback.

## Stage 1 — Proposal (architecture specialist, strictly read-only)

Hard boundary: read-only discovery plus proposal artifacts only. No
installation, source/runtime/profile change, activation, canary, live
inference, commit, push, merge, restart, or deletion. `approval_state`
stays `pending` in every artifact. `not_self_approved: true` everywhere —
the architect never approves its own proposal.

Artifacts (durable directory under the orchestrator workspace, never
profile `cache/scratch`):

1. `installation-port-proposal.md` — destination surfaces table,
   per-surface baselines + preimage hashes, live service bindings
   (which launchd services import which destination), phased plan
   (P/I/V/C/R) with executors, reviewers, allowed writes, stop
   conditions, rollback plan, named blockers.
2. `byte-manifest.json` — one entry per destination file: src sha256,
   dest path, `dest_preimage_sha256`, operation (`REPLACE`,
   `REPLACE_NOOP`, `ADD` with preimage `ABSENT`, or
   `BLOCKED_PORT_REQUIRED`), phase, owner, rationale; plus an
   `excluded` list for dirty/unfrozen files.
3. `execution-approval-manifest.json` — `approval_state`, binds
   (candidate identity, baselines, artifact hashes, destination
   baselines), phases, `rollback_plan`, `safety_invariants`,
   `held_gates`, approval-request scope.
4. `final-artifact-manifest.sha256` — sha256 of the three files above.

Key discovery rules:

- **Check lineage of every destination against the qualified baseline.**
  If a destination (e.g. an installed runtime) is a DIFFERENT lineage
  than the baseline the candidate was qualified against, mark all its
  entries `BLOCKED_PORT_REQUIRED` behind a re-qualification gate: the
  port must be produced in staging and re-qualified (fresh independent
  review) under a new ported identity digest before any write there.
  Never byte-copy a candidate across lineages.
- **Hash every destination; separate real deltas from already-applied
  bytes.** Entries whose live preimage already equals the candidate
  hash are no-op REPLACEs — keep them in the manifest for completeness
  but do not count them as writes.
- **Re-hash live dirty files at discovery time.** Task-cited dirty
  hashes drift; record both the observed and the cited value, keep the
  exclusion either way.
- Verdict vocabulary: `READY_FOR_FINAL_APPROVAL` / `NEEDS_REVISION` /
  `BLOCKED`, with held gates named explicitly.

The orchestrator independently recomputes every artifact hash before
presenting anything to the operator — a child's self-reported SHA-256 is
a self-report.

## Stage 2 — Operator final approval gate

Present the proposal summary (artifact paths + recomputed hashes, key
discoveries, blockers) and ask explicitly which phases are authorized.
Default scope: staging + source-repo apply + offline validation, with
canary, rollout, and every cross-lineage destination held behind their
gates. Record the approval as a structured ledger event (approved
phases, held phases, reason), then update
`execution-approval-manifest.json` (`approval_state: approved` plus an
approval block naming approver, timestamp, scope) and recompute
`final-artifact-manifest.sha256`.

## Stage 3 — Phased execution (implementer, one task file + dispatch per phase)

- **Phase P (staging).** Rebuild the reconstruction from git archives of
  the frozen baselines plus packet overlays into a fresh staging dir;
  verify every overlay hash, component digest, and the integrated
  digest == the frozen identity; then port in staging only onto the
  other lineage and emit a ported-identity manifest (digest NOT
  predicted in advance). Allowed writes: staging dir only. Surface
  deviations (e.g. `git apply` falling back to `patch -p1`) in the
  completion report instead of hiding them.
- **Phase I (source apply).** Preflight (pinned HEADs, clean trees,
  preimages match manifest) → quiesce importing services (`launchctl
  bootout`; "No such process" is an acceptable outcome — record and
  continue) → back up the preimages with hashes → atomic temp-write +
  `mv` per file → hash-verify ALL manifest entries, not only the
  replaced ones → relaunch services and verify labels only, no
  inference. If `bootstrap` fails with errno 5 (I/O error), the label
  is `disabled`: run `launchctl enable gui/501/<label>` first, then
  bootstrap. Any stop condition triggers immediate rollback: restore
  preimages, re-hash against the manifest, relaunch, record a rollback
  receipt.
- **Phase V (validation).** Test batteries with actual exit capture,
  digest recompute from the applied destinations == frozen values,
  negative tests (unset env roots must not silently pass via developer
  defaults), service health via launchctl labels + loopback TCP only —
  no live inference.

Candidate bytes come ONLY from the verified staging dir — never from a
dirty worktree, never from the destination tree itself.

After any phase exits 0, the orchestrator re-verifies independently —
destination hashes, repo HEADs and bounded modification counts, backup
integrity, service load states — before appending the phase-complete
ledger event. A worker's exit code and self-reported hashes are claims,
not evidence.

### Dispatch routes for phase execution

Short discovery tasks work as inline `-q` prompts; bounded executor
phases are more reliable as self-contained contract files dispatched
with the long-haul pattern:

    hermes -p <profile> chat --query-file <contract.md> --oneshot \
      --provider minimax-oauth -m MiniMax-M3 -t file,terminal \
      --ignore-user-config --in <workdir> --run-budget 5400 \
      --max-turns 500 --format stream-json --reasoning high

The contract file restates the binding constraints, discovered live
state, exact byte hashes, procedure, prohibitions, and rollback — the
executor never re-derives context from chat history.

Circuit-breaker: two consecutive identical stalls on a route is a
route defect — switch routes, never attempt a third time. Recognized
stall signature: last log line mentions refreshing credentials and
retrying, followed by ~600s of silence, then a liveness-watchdog abort
(exit 130) "waiting for model response". Such a turn yields zero
worker writes; treat it as `dispatch_not_delivered` and recover per
Interruption recovery below.

## Interruption recovery

If an executor process is watchdog-aborted or stalls mid-phase (e.g.
exit 130 after a provider-side API timeout), do NOT assume what it did
and do NOT blindly resume. First verify the protected state is
unchanged: repo HEADs and cleanliness, preimage hashes of every
not-yet-applied file, service load states. Record the interruption as
its own ledger event carrying that verification evidence. Then
re-dispatch fresh with discovered live state folded into the prompt
(e.g. "services not loaded — quiesce will report No such process;
record and continue"; "prior attempt verified preflight with zero
writes"). A fresh dispatch beats a resume when the interrupted session
completed only read-only preflight; a resume is for sessions that hold
real in-flight progress worth carrying forward.

## Ledger

Append a structured JSON event at every transition: proposal-ready,
operator-approval, phase-complete (artifact paths + hashes + surfaced
deviations), interruption (with state-verification evidence), rollback.
The ledger is the chronology of record; chat history is not.
