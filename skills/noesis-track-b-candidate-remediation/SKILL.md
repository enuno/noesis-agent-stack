---
name: noesis-track-b-candidate-remediation
title: "Noesis Track B Frozen-Candidate Remediation"
description: "Bounded follow-ups on a frozen Track B candidate."
version: "1.0.0"
last_updated: "2026-10-10"
author: "noesis-forge"
license: "Proprietary"
---

# Noesis Track B Frozen-Candidate Remediation

## Overview

Execute operator-authorized bounded follow-ups (storage hardening, settlement semantics,
contention tests, durability evidence, cross-repo integration prototypes, checkpoint-branch
hardening implementations) on the Track B governed-mode runtime-enforcement candidate in
the dev checkout `/Users/elvis/projects/hermes-agent-track-b-runtime-enforcement`. The
candidate's identity model is handoff-specific: earlier handoffs froze it UNCOMMITTED at
baseline `8a33891bdd58c3e0795ebfb277bcdde1003e91ea`; checkpoint-branch handoffs freeze it
as git commits on `a6-checkpoint/…` and may authorize scoped LOCAL commits. Each follow-up
freezes the prior candidate as historical and produces a NEW candidate digest + diff +
manifest + evidence package for independent (Sentinel/Skeptic) review.

Hard rules that never relax:

- The prior candidate's evidence directories are read-only. New evidence goes in a NEW
  sibling directory under `workspace/orchestrator/track-b-evidence/<topic>/` in the Noesis
  checkout — never edit frozen packets, logs, or reports.
- VCS actions exactly as authorized by the handoff and nothing more: if it authorizes
  local commits on the checkout branch, commit locally with the handoff's message
  convention and report the SHA; if it does not, touch nothing in git. NEVER push — the
  `origin` is a `file://` remote into the installed runtime and is HELD by default. No
  merge/deploy/install/activate/canary, no installed-runtime changes, no Noesis
  main-source changes, no dependency preparation, no live provider calls from tests.
- `track_b_enforcement_interface/v1` dataclasses and the `AttemptLedgerStore` four-method
  signatures stay frozen; hardening changes behavior inside implementations, not the
  interface. Exception: an operator-authorized ADDITIVE interface change (plan + SHA) —
  implement exactly the authorized delta and nothing more; every other semantic stays frozen.
- Governed-mode fail-closed admission and the terminal `governed_denied` path must never be
  weakened — every new failure mode routes through `GovernedAdmissionDenied` or an explicit
  typed exception, never a silent default.
- Retain `not_self_approved: true`; apply no review verdict; do not carry prior verdicts
  forward to the new digest without re-check.

## When to Use

- A handoff file exists under `workspace/orchestrator/` (e.g. `track-b-storage-hardening-handoff.md`)
  authorizing a bounded follow-up with explicit scope, boundaries, and stop conditions.
- Re-running such a follow-up after review found gaps.
- A clarification request (with an operator approval manifest) asks for a
  **documentation-only** supplement answering review blockers against an existing
  candidate — see the dedicated section below; do not treat it as a code task.
- An operator authorizes a bounded cross-repo integration prototype (e.g. bridging the
  Noesis TaskStore to the Hermes `DurableAttemptAuthority`) with a plan + SHA and an
  explicitly authorized additive interface change — see the dedicated section below.
- An operator issues a bounded REPAIR turn: named defects (D-items), restricted files,
  prescribed verification commands, and required evidence items — see the dedicated section below.
- You are REVIEWING a candidate deliverable produced by another agent (verifying its
  claimed hashes, test results, and held operations) rather than producing one — load
  `noesis-candidate-acceptance-review` instead of this skill. This skill covers the
  implementer side; that one covers the independent acceptance verdict.
  section below.

## Pre-checks (fail-closed)

1. Identify the authorizing artifact — handoff, approval manifest, or plan file — and
   verify its SHA-256 against the hash quoted in the authorizing message BEFORE any edit
   (`shasum -a 256 <artifact>`). Mismatch → stop and report; never proceed on a stale or
   substituted artifact. Then read it fully: scope, required invariants, hard boundaries,
   stop conditions, and whether it demands plan approval before edits. If it does, STOP
   after the plan.
2. Confirm the profile/execution context satisfies the handoff's authorized context; if it
   does not, stop and report the mismatch — never change settings to fit.
3. Verify starting identity BEFORE any edit:
   - `git rev-parse HEAD` equals the handoff's baseline commit. Capture the hash into a
     variable (`BASE=$(git rev-parse HEAD)`) and use the variable in later commands —
     never retype a 40-char hash by hand; one wrong character fails as `bad object`
     with no hint whether the commit or the typing is wrong.
   - Recompute the frozen candidate digest and confirm an exact match:
     `cat <files in the manifest's exact order> | shasum -a 256` (the manifest order is
     the digest order — sorted-by-path only when the manifest says so).
   - Treat historical evidence dirs (e.g. `track-b-evidence/` inside the dev checkout) as
     read-only; they are outside the source/test manifest.
4. Grep the test tree for EVERY call site of any constructor/helper whose default semantics
   you are about to change (e.g. silent-create → explicit `create=True`) — shared fixtures
   like `_ledger()` hide call sites, and stale ones fail on shards you did not run.

## Procedure

### 1. Code-grounded opening plan (leads the returned result)

Ground every claim in the actual code, then state: actual profile/execution context;
working directory and verified starting identity; current connection/autocommit/commit
behavior; exact settlement and admission failure paths (what raises, what is swallowed,
what leaves state un-settled); provisioning-vs-reopen semantics as found; trusted-owner/
filesystem assumptions as found; proposed files/tests; explicit max process count and
wall-clock limits; any handoff ambiguity or conflict. If the handoff does not impose a
plan-approval gate, proceed within its authorization and stop conditions — and say so.

### 2. Pre-change baseline

Run the affected battery BEFORE editing and record it:
`env -u HERMES_HOME -u HERMES_RUNTIME_DIR scripts/run_tests.sh <files> -q`
(the env unset is a one-off workaround for the dev tooling's bootstrap-python lookup not
following a non-default ambient `HERMES_HOME`; it is not a persistent config change).

### 3. Implement within boundaries

- Surgical edits: every changed line traces to the handoff. Do not "improve" adjacent code.
- Keep new tests purpose-built and small: no parallel full-file stress suites; bound thread
  counts (≤2 per test) and subprocess counts; use injected/fake stores and raw-sqlite lock
  holders, never live providers.
- Map each handoff acceptance requirement to honored-and-tested / honored / limitation;
  disclose limitations explicitly rather than hiding them (e.g. pin a same-format-replacement
  gap as a named test when it is the honest extent of detection).

### 4. New candidate identity + evidence package

1. Run the full affected battery + the integration regression file (`tests/agent/test_run_agent.py`)
   and capture real exit statuses and logs.
2. Build the complete diff — for EACH file decide strategy by trackedness
   (`git ls-files --error-unmatch <file>`), because **`git diff <base> -- <file>`
   prints NOTHING for untracked files**: a combined diff assembled in a section loop
   can carry 12 headers with empty bodies and look plausible while missing every new
   file. Tracked files via `git diff HEAD -- <files>`; new files via
   `git diff --no-index /dev/null <file>` appended (exit 1 is the EXPECTED difference
   signal, not a failure). Then SANITY-CHECK the assembled diff: section count equals
   the file count, and total line count is in the same scale as the prior packet's
   diff (a 12-section diff of a few hundred lines where the predecessor had thousands
   means content went missing).
3. Compute, over the NEW changed-file set sorted-by-path:
   - candidate content digest: `cat <files> | shasum -a 256`
   - per-file manifest (`changed-files-sha256.txt`) and its sha256
   - diff file sha256
4. Write the completion packet into the NEW evidence directory:
   - `.md` report + `.json` machine-readable packet.
   - New identity triple (digest/diff/manifest) with the reproduce command.
   - Real test exit statuses + log copies.
   - Frozen-preservation PROOF, not just an assertion: hash every file under the frozen
     directories to a temp file BEFORE any edit (`find <dirs> -type f | sort |
     xargs shasum -a 256 > /tmp/frozen-before.txt`), repeat after all writes with the
     SAME path style, and `diff` the two files — an empty diff is the evidence; quote
     it in the packet. If the two snapshots were unavoidably written with different
     path prefixes (relative vs absolute), compare hash columns only
     (`diff <(awk '{print $1}' a.txt) <(awk '{print $1}' b.txt)`) — a byte diff of
     identical content with different path text reports a false mismatch.
   - Acceptance-requirement disposition table and A-item closure table (observed, untouched).
   - Explicit remaining limitations; boundaries compliance list; `not_self_approved: true`.
   - Statement that prior verdicts do not carry forward across digests.
5. Return control: state the contract is complete, name the evidence location, select no
   next task, apply no review verdict.

## Bounded cross-repo integration prototypes (adapter work)

A distinct class: the operator authorizes a bounded prototype bridging the Noesis
TaskStore to the Hermes `DurableAttemptAuthority` (or a similar cross-repo adapter),
with a plan file + SHA, an explicitly authorized additive interface change, and hard
boundaries (prototype scope, strong-isolation or production acceptance explicitly out
of scope).

Procedure:

1. Verify the plan's SHA-256 against the hash in the authorizing message; read the
   plan and its appendices fully. Where the spec contradicts itself, resolve minimally
   TOWARD the plan's own stated test expectations and record the resolution as a
   disclosed deviation — do not silently pick a reading. (Recurring shapes: a field
   declared `= False` whose validation checks `is None` cannot both be literal —
   implement `Optional[bool] = None` with explicit-on-admit validation; a limit
   phrased per-identity whose own test expects a cross-identity denial reduces to a
   per-task limit when the key already folds the identity.)
2. Create the isolated workspace (`workspace/<name>/` in the Noesis checkout) and
   implement the adapter implementing `AttemptLedgerStore`, keeping the TaskStore
   strictly read-only. Noesis-side store semantics that shape the bridge are in
   references/noesis-taskstore-bridging.md.
3. Apply the authorized interface delta exactly and additively — nothing beyond the
   authorized change. When the new signal must reach store implementations WITHOUT
   widening the frozen protocol, add an OPTIONAL duck-typed capability (e.g.
   `try_reserve_fresh` returning an extended tuple with a freshness flag) so legacy
   stores keep v1 behavior and the pre-existing suite passes byte-unchanged.
   Hand-rolled test fakes must then exercise BOTH protocol shapes, or the legacy
   fallback path is untested.
4. Write the suite in the workspace: `tests/conftest.py` wires `sys.path` to both
   repos; purpose-built fake stores and fake transports; concurrency proven with two
   agents and gated thread wrappers, never stress loops. Run it with the discovered
   test interpreter (see the bridging reference — plain `python3 -m pytest` has no
   pytest in this environment).
5. Regression-check the Hermes battery read-only (enforcement files +
   `tests/agent/test_run_agent.py`) after the interface change; a green new suite
   over a red battery is a failed turn.
6. Compute identities (per-file sha256 of every new/changed file), write the
   completion packet (`.md` + `.json`) in the workspace with deviations, findings,
   boundaries compliance, and `not_self_approved: true`; verify frozen evidence dirs
   byte-identical; return control without selecting the next task.

## Operator-issued repair turns (D-item defects)

A distinct class: the operator names blocking defects (D1, D2, …), restricts the
writable file set, prescribes exact verification commands, and requires evidence
items (E-items). The deliverable is a review-ready candidate, not an exploration.

Procedure:

1. Treat the repair prompt itself as the authorizing artifact: capture its
   identity (task id, authorization handle) in the completion packet; the
   restricted-file list is exhaustive — any additional file needs concrete
   justification recorded in the deviations.
2. Read each named defect site BEFORE editing (the prompt's line numbers drift —
   grep the symbol). Fix exactly the defect; preserve pre-existing strings and
   semantics byte-identical outside the delta (see the piggyback pitfall).
3. For every fail-closed gate added or tightened, update every hand-rolled double
   in the same change (fakes AND subprocess worker snippets), or the suite fails
   on a shard you did not run.
4. When a defect's required behavior is the OPPOSITE of an existing test's
   encoded expectation, replace the test in the same turn — never leave the old
   behavior pinned green.
5. Evidence items rule of thumb: "real production path" means drive the actual
   production handler through its real entrypoint with only the documented
   process/external boundary doubled, and assert the full chain (durable record
   shape → restart → admission denied → dispatch denied → zero transports →
   consumption unchanged). Harness recipes for the Noesis control plane are in
   references/noesis-taskstore-bridging.md.
6. Return a defect-closure mapping table (each D-item: status, fix, evidence
test), the evidence items, changed/new file hashes, logs with real exit codes,
integrated candidate identities, deviations, and `not_self_approved: true`.

## Documentation-only clarification supplements

A distinct, lighter class: answer review blockers in prose, cited to EXISTING
evidence only. The contract is honesty about gaps, not closing them.

Procedure:

1. Verify the approval manifest first: `shasum -a 256 <manifest>` must equal the
   hash quoted in the authorizing message, and its `candidate_content_digest`,
   `baseline`, permitted-write path, and forbidden list must match what you were
   told. Mismatch → stop and report; never proceed on a stale manifest.
2. Read the clarification request fully. Bind the supplement to the full identity
   quadruple: candidate digest, diff sha256, manifest sha256, baseline commit.
3. Answer every item from existing source/test/log/receipt files only. Where the
   named test does not actually demonstrate the claimed invariant (read the test
   body — names overclaim), enumerate what it DOES prove and mark the item
   `UNRESOLVED`. Never write "partially addressed" when the finding's core demand
   is untested.
4. Distinguish **DOCUMENTATION COMPLETE** (every request item answered) from
   **TECHNICAL FINDINGS CLOSED** (they are not, when anything is UNRESOLVED) —
   state both labels explicitly in the document.
5. Correct your own packet's overclaims in the supplement rather than repeating
   them. The recurring one: an unqualified `no_live_provider_calls` claim is false
   for the authoring session (it makes live model calls by definition). Narrow it
   to the tests, state the proof basis (stub inspection, logs, cleanup checks)
   AND its limit (no network audit was run, so zero test traffic is supported,
   not proven).
6. Recompute every count yourself. If an upstream receipt or the request says
   "nine byte-identical files" but the manifests verify eight, list the real
   hashes and flag the discrepancy — do not adopt arithmetic you cannot reproduce.
7. Never relabel a historical failure (e.g. a timeout under concurrent stress) as
   a contention result because new bounded contention tests now exist; enumerate
   what each test proves and leave the historical cause unknown unless evidence
   says otherwise.
8. Write exactly the one permitted file. End with `not_self_approved: true`, a
   statement that no old reviewer verdict carries to the successor digest, and a
   confirmation (paths + mtimes + `git status`) that no other file was written.

## Operator implementation handoffs (checkpoint-branch hardening)

A newer class: the operator dispatches a copy-ready implementation packet (task identity,
verified baseline SHA, exact scope, permitted-files list, TDD acceptance steps, execution
limits, exact result-block return contract) against the committed checkpoint branch.
Publication remains with the orchestrator's separate checkpoint process.

Procedure:

1. Preflight exactly what the packet enumerates, before any edit: `git rev-parse HEAD`
   equals the packet's baseline, `git status --short` empty, interface string unchanged,
   and no competing owner (`git worktree list`, no `.git/*.lock`). Any mismatch → stop
   and report; do not branch, edit, or commit around it.
2. Verify the packet's DATA against the live checkout before deriving anything from it:
   recompute every quoted per-file SHA from disk; reproduce any recorded integrated
   digest from live bytes (for pinned foreign commits use `git show <sha>:<path>`).
   Mismatches are surfaced deviations with the resolution evidence — never silently
   substitute corrected values, and never invent values the manifests don't carry.
3. Implement test-first per the packet's acceptance list: RED run proving the expected
   failure reason (missing feature, not a typo), then the smallest change, then GREEN.
4. Run the packet's full battery with real exit capture; for any failure, attribute it
   BEFORE acting: `git stash -u`, re-run on the pristine baseline, `git stash pop`.
   Identical red = pre-existing — report it (with root cause if found) instead of fixing
   it when the fix is outside the permitted file set.
5. If all checks pass and the packet authorizes local commits, commit with its message
   convention; otherwise leave the tree dirty. Return the packet's exact result shape
   (status, baseline/final revisions, files changed, implementation paths, digest
   recipe, per-command test results with exit codes, deviations, unverified boundaries,
   remaining risks, commit SHA or `not committed`), then return control — select no
   next task, apply no review verdict.

## Stop Conditions

Stop and report a blocker (never guess) when a required guarantee is impossible within the
boundaries — e.g. needs a new dependency, an installed-runtime change, or crypto
infrastructure the handoff forbids. Report the exact missing mechanism and scope a separate
proposal; do not silently weaken the claim.

## Pitfalls

- **sqlite silently creates missing files on connect.** Any "reopen" path that reaches
  `sqlite3.connect` on a deleted/absent file re-provisions an EMPTY database. Guard with an
  identity row (`format`/`schema_version`/`ledger_id`) re-verified INSIDE every write
  transaction, and an existence pre-check at open. The full rule set with recipes is
  in references/sqlite-ledger-hardening.md.
- **Corrupt-file errors surface at the first statement or pragma** (`PRAGMA journal_mode=WAL`
  included), not at `connect` — classify connect-time errors too, or denial reasons leak as
  raw sqlite text.
- **`isolation_level=None` means autocommit**: DDL outside an explicit `BEGIN…COMMIT` commits
  per statement, leaving partial schemas on failure. Wrap schema init in a transaction.
- **Shared test fixtures hide call sites.** Changing a helper's default semantics (e.g.
  `at_path` create→open) breaks every fixture user; grep all test files and child-process
  snippets, not just the file that defines the helper.
- **Never weaken a settlement/admission invariant to make tests pass** — update the test to
  the explicit semantics instead.
- **Piping test-runner output through `tail`/`grep` destroys the exit code** — `$?`
  is the last pipe stage's status. Capture the pipeline's own exit immediately:
  bash `${PIPESTATUS[0]}`, zsh `${pipestatus[1]}` (lowercase array, 1-indexed). In
  a zsh session `PIPESTATUS` silently expands to nothing, so verify the captured
  variable is non-empty before trusting it; when it is empty, the runner log's own
  summary line (`N passed`) is the dispositive record — say so honestly instead of
  implying a captured exit code. Record exit statuses in the log itself: reviewers
  verify from session receipts, not from exit markers they cannot see.
- **Prescribed verification commands can be environment-incompatible** (an
  interpreter missing a third-party import, a path that does not exist in this
  checkout). Run the command exactly as prescribed first and capture its honest
  exit code in a log — that record is itself evidence — then run the corrected
  equivalent (right venv per references/noesis-taskstore-bridging.md, real test
  path) and label both in the deviations. Never silently substitute the working
  command for the prescribed one, and never let a prescribed EXIT:2/EXIT:4 go
  unreported because the equivalent passed.
- **The robust exit-capture shape is `bash -c '{ pytest ...; echo "EXIT:$?"; } 2>&1 | tee log'`** —
  the echo runs inside the braces before any pipe stage, so `$?` is pytest's real
  status and the tee only affects display. This avoids both the zsh `PIPESTATUS`
  expansion trap and the pipeline-stage-status trap in one form; it is the shape
  to reach for when the operator prescribes EXIT capture.
- **Stdlib `Mock` has `assert_called_once` but no `assert_called_twice`** — reaching
  for it raises AttributeError at RUN time, not when the test is written. Assert
  `mock.call_count == N` instead. When counting invocations at an instrumented
  boundary, account for every legitimately distinct call first: N distinct attempt
  identities produce N transports, so assert the exact expected count ("never a
  third"), never a bare `assert_called_once` after more than one distinct call —
  that mistake is an under-count of correct behavior, not a source bug.
- **Don't assert on framework state pointers after a settled call** — the boundary
  clears its "last reservation" attribute on success; post-completion assertions
  belong on durable state (ledger rows, budget counters, transport mock counts), not
  on attributes that were nulled by the code path under test.
- **The finding namespace matters.** A completion packet's "A1–A4 closure table"
  may be the orchestration critical-path gates, not the reviewer's findings — if no
  artifact labels the actual findings, declare the mapping you use instead of
  silently answering the wrong table.
- **Plain `python3 -m pytest` fails "No module named pytest"** — the system python and
  the Hermes tools python both lack pytest, and bounded turns forbid installs. Discover
  the checkout's synced test venv via `python3 -m pm.environments --format sh`
  (`__HERMES_TEST_PYTHON`) and run `"$__HERMES_TEST_PYTHON" -m pytest ...`. A filesystem
  `find -type f` misses it because the venv interpreter is a symlink — query the package
  manager, don't scan the tree.
- **A frozen protocol still needs the new signal** — carry it as an optional duck-typed
  capability (extended method, or an extended return tuple legacy callers ignore) so
  existing store implementations and the existing suite keep working. Widening the
  frozen protocol, or accepting a red pre-existing suite to land the signal, is never
  the bounded-turn answer.
- **Patch-scope piggyback breaks pre-existing tests that pin old strings.** When a
  patch's `old_string` spans adjacent lines, re-emit the non-target lines
  byte-identical — an "improvement" smuggled inside an authorized delta fails a
  regression test that matches on the old denial reason/string, and the failure
  surfaces as an unrelated reason, not as your edit. Review your own diff before
  applying; anything outside the authorized delta gets its own explicit decision.
- **Prove fail-before/pass-after inside the same turn by staging.** Land the
  scaffolding, new interfaces, and new tests first, run them to capture genuine red
  against the not-yet-fixed code, then apply the one behavioral fix and re-run to
  green. Do not leave the red demonstration to a reviewer, and never simulate it by
  re-ordering asserts or weakening the pre-fix run.
- **Read the real API signatures before authoring behavior tests against a repo's
  control plane** — grep `def <method>` and the exception classes, and copy shapes
  from the repo's own tests: dataclasses mutate in place (no `model_copy`), typed
  exceptions expose named attributes (not positional `args[0]`), method kwargs are
  exact (`put(task, event=...)`, no `actor`), and policy validation rejects
  capability strings the assignee profile does not declare. Each guessed signature
  costs one fix/verify cycle; bounded turns allow at most two.
- **Handoff data can name bytes that exist nowhere.** A packet's SHA table may have been
  recorded from a since-removed staging worktree, so live files mismatch the "authoritative"
  table on a clean baseline. Recompute from disk, resolve against the binding manifest
  (e.g. the overlay manifest that recorded the qualified bytes), and reproduce the recorded
  integrated digest to confirm which side is authoritative — then disclose the correction
  as a deviation in the commit body and result block.
- **An integrity check cannot pin its own defining file.** When a gate walks N files
  including the file the gate lives in, the post-edit hash of that file is a SHA-256 fixed
  point (uncomputable). Gate on attestation semantics instead — measure the integrated
  digest of the walked set and require equality with the asserted digest — and demote the
  pinned per-file table to drift diagnostics that name files (paths only) in the failure
  reason. This keeps the gate self-consistent on any legitimate tree state.
- **New attestation/gate fields must not leak into evidence surfaces.** Give the field
  `repr=False` (dataclass) or equivalent, never serialize it into ledger/audit rows or
  request state, and prove absence with a leak test that scans repr, log records, denial
  reasons, and the raw ledger DB bytes for the sentinel value.
- **Plan sketches can contradict themselves.** When the literal spec is unimplementable
  (a default that makes its own validation dead code; a limit phrased per-identity
  whose test expects cross-identity denial), resolve minimally toward the plan's test
  expectations and disclose the resolution as a deviation in the completion packet —
  never silently choose a reading, and never stop while one consistent reading exists.

## Output Packet (all in `workspace/orchestrator/track-b-evidence/<topic>/`)

- `*.diff` — full patch (all sections: tracked + new).
- `changed-files-sha256.txt` — per-file manifest, sorted-by-path.
- `test-evidence-*.log` — real runner output with exit statuses.
- `*-completion.md` / `*-completion.json` — report and machine-readable packet with
  `not_self_approved: true`.

## Verification Checklist

- [ ] Starting digest recomputed and matched before any edit; baseline HEAD confirmed.
- [ ] Pre-change baseline battery recorded.
- [ ] Historical evidence untouched; new evidence in a new sibling directory.
- [ ] Interface v1 frozen; fail-closed admission and terminal `governed_denied` intact.
- [ ] Full battery + `test_run_agent.py` exit 0, logs preserved.
- [ ] New digest/diff/manifest computed with reproduce commands; JSON validates.
- [ ] Acceptance table, closure table, limitations, boundaries list present.
- [ ] Authorizing artifact (handoff / manifest / plan) SHA-verified before any edit.
- [ ] Any interface delta additive-only and exactly as authorized; spec-contradiction
      resolutions disclosed as deviations.
- [ ] Cross-repo suite green under the discovered test interpreter; Hermes battery
      regression-checked read-only after interface changes.
- [ ] `not_self_approved: true`; VCS actions exactly as authorized (local-commit handoffs:
  commit SHA reported, no push; all others: no commit); control returned without
  selecting the next task.
