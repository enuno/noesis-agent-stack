# Bounded-adaptation flow: operator-authorized v2 → v3 candidate

Use this reference when the operator has reviewed a prior
installation/port proposal (e.g. v2), identified material
non-annotation, non-additive changes that warrant a per-file call,
and authorized a "Request a bounded adaptation candidate" — a new
candidate with a small, operator-named set of behavior-preserving
edits.

This is **not** the same as `references/drift-port-proposal.md`
(destination moved → re-emit the same proposal bound to a new HEAD;
the digest is preserved) or `references/bounded-compat-check.md`
(verify a composition in isolation; the digest is already bound). It
is a third flow: **modify a small set of overlay bytes and emit a
new candidate with a new manifest version, a new qualified
successor digest, and a new operator approval gate.**

## 1. The operator's authorization pattern

The operator's authorization is typically a 1-3-1 decision packet that
identifies:

- The parent qualified successor digest (e.g. `e8c33bb…`).
- The installed-baseline reference (e.g. `c5733167…`).
- A short list of explicit behavior-preserving edits (e.g. "restore
  `overflow_reason=classified.reason.value` to `_compress_context`;
  restore `with_session_yolo(...)` in `_session_row_model_config`").
- A blanket prohibition on source adaptations outside the named edits,
  dependency installation, plugin enablement, and live canary.
- A requirement to inspect the actual helper/call contracts first
  and report any enforcement-invariant conflict before editing.
- A requirement for focused regression tests covering only the
  adapted surfaces.
- A requirement to re-run the bounded compat check (items 1-7 of
  `references/bounded-compat-check.md` §6) against the new
  composition.

## 2. Pre-edit: inspect the call contracts

Before changing any source byte, read the actual callee signature
and the call site. For each named edit:

- Find the symbol in the destination at the bound installed
  baseline (`git show <BOUND_HEAD>:<rel>` for the call site; the
  current on-disk byte may have drifted from HEAD but the
  proposal compares against the qualified source, not HEAD).
- For helper modules (`agent.runtime_enforcement`,
  `tools.approval_yolo`, `agent.compression_facade`), read the
  helper's source and confirm the proposed edit is signature-safe.
- If the proposed edit conflicts with an enforcement invariant
  (e.g. restoring an upstream keyword would re-introduce a
  contract that the A6 packet explicitly documents as removed),
  report that specific conflict and stop. Do not silently choose a
  behavior.

## 3. The three-layer staging model is the same

The bounded-adaptation check uses the same three-layer staging
described in `references/bounded-compat-check.md` §2:

- Hermes layer: a new isolated git worktree (`git worktree add
  --detach` at the bound installed baseline HEAD), distinct from
  the v2 worktree. Do not reuse the v2 worktree — the v2 worktree
  holds v2's overlay; the v3 worktree holds v3's overlay.
- Noesis layer: the same clean git worktree at the bound Noesis
  HEAD with the same 3 Noesis overlay writes (`models.py` from
  the operator's on-disk byte, `store.py` and `control_plane.py`
  from the reconstruction). Re-using the v2 staging is fine if
  the v2 staging was preserved unchanged.
- A6 layer: the same staging from the packet's reconstruction.

## 4. Apply the v2 base, then the v3 adaptations

In the new isolated worktree:

1. Apply the v2 base — the 6 REPLACE writes and 6 ADD writes from
   the v2 manifest. Use the qualified source bytes from the
   reconstruction. The 24 entries (14 NO_OP + 6 REPLACE on
   non-adapted files + 6 ADD) are byte-identical to v2.
2. Apply the v3 adaptations — for each operator-named edit,
   read the v2 byte at that path in the worktree, then apply the
   v3 modification. Source-edit scope is limited to:
   - The call site of the v3 edit (e.g. the body of
     `_session_row_model_config`).
   - Immediately necessary imports (e.g. `from
     tools.approval_yolo import with_session_yolo`).
   - Focused regression tests (see §5).

Do NOT refactor unrelated code. Do NOT touch Noesis. Do NOT add
new A6 files. Do NOT install dependencies.

## 5. Focused regression tests

Write a new test file (e.g.
`tests/agent/test_<scope>_adaptation.py`) that covers only the
adapted surfaces. Use the four-surface pattern:

1. **The behavior-preserving edit**: e.g. that
   `overflow_reason=classified.reason.value` is now passed at the
   `long_context_tier` recovery path. Source-level check (read the
   file) is often sufficient and avoids the
   `hermes_bootstrap`-triggering import chain.
2. **The retained behavior**: e.g. that `with_session_yolo` is now
   called instead of the v2 try/except body. Import `tools.approval`
   and `tools.approval_yolo` directly — they are safe to import
   without triggering `hermes_bootstrap`.
3. **Configuration preservation / mutation / exception semantics**:
   e.g. that `with_session_yolo(None, session_key)` returns
   `{"yolo_mode": True}` when YOLO is enabled, and that the input
   dict is not mutated.
4. **A6 governance surface retention**: e.g. that
   `AIAgent.__init__` still accepts `governed_enforcement=None`,
   that `deregister_governed_session` is still called in the session
   close path, that `FailoverReason.governed_denied` is still
   defined, and that `INTERFACE_VERSION` is still
   `"track_b_enforcement_interface/v1"`. Source-level checks work
   here too; only the `INTERFACE_VERSION` test needs to import
   `agent.runtime_enforcement` (which is safe).

Prefer source-level checks over import-driven tests for files that
import `hermes_bootstrap` (e.g. `run_agent.py`). The
`tests/home_io_guard.py` guard classifies the staging noesis path
as a real hermes home and will fail any test that triggers a
`Path.is_file()` on the staging path; see the
"Worktree-path interception by `tests/home_io_guard`" pitfall in
the SKILL.md.

## 6. Re-run the bounded compat check against the new composition

Per `references/bounded-compat-check.md` §6:

- Item 1 (imports resolve to the new layers): 9/9 modules OK; 0
  dirty.
- Items 2-4 (A6 D1-D4, E1, full suite): all pass.
- Item 6 (Hermes enforcement battery): same battery as v2, 60
  tests. The 1 known environmental failure (a test that
  constructs an `AIAgent` and triggers the `home_io_guard` on
  the staging path) is preserved as an environmental defect, not a
  port regression.
- Item 7 (identity verification): `INTERFACE_VERSION` matches.

Run the new focused regression tests separately — they are part of
the v3 evidence, not the v2 battery.

## 7. Compute the new candidate identity

The integrated overlay digest changes. The new manifest's
`qualified_successor.integrated_overlay_digest` is the SHA-256 over
the raw concatenation of overlay file bytes in
`candidate-identity.json::integrated_overlay_order`, computed from:

- 24 entries at v2's bytes (3 Noesis NO_OP + 11 A6 NO_OP + 4 of 6
  Hermes REPLACE on non-adapted files + 6 of 6 Hermes ADD).
- 2 entries at v3's bytes (the 2 adapted Hermes REPLACE files).

Record the parent digest (`e8c33bb…`) as
`parent_qualified_successor_digest` in the v3 manifest for audit.

## 8. Issue a new manifest version

The new manifest is a separate file at a separate path:

- File: `a6-port-approval-v{N}-manifest.md` (e.g. `a6-port-approval-v3-manifest.md`).
- Manifest version: `a6-port-approval/v{N}` (e.g. `a6-port-approval/v3`).
- `parent_qualified_successor_digest`: the v2 digest.
- `parent_qualified_successor_sha256`: full hash of the v2 digest.
- `parent_manifest_version`: `a6-port-approval/v2`.
- `parent_manifest_file`: relative path to the v2 manifest.
- `parent_manifest_file_sha256`: full hash of the v2 manifest file.

Do NOT silently edit the v2 manifest. The v2 manifest is preserved
unchanged for audit; the v3 manifest is a new file.

## 9. Issue a new proposal directory

The new proposal directory is named separately (e.g.
`a6-adaptation-port-proposal/`), parallel to the v2 proposal
directory. It contains:

- `00-index.md` — bound baselines, source of truth, file inventory.
- `01-source-destination-mapping.md` — per-file current and qualified
  source SHAs. Mark the 2 adapted files as `v3 source: <path>`
  and the 24 unchanged files as `v2 source: <path>`.
- `02-destination-baselines-and-current-hashes.md`.
- `03-proposed-diffs-and-conflicts.md` — the v2 → v3 per-file deltas
  for the 2 adapted files, with rationale.
- `04`–`08` — same structure as v2, abbreviated if unchanged.
- `09-approval-manifest.md` — symlink to the v3 manifest file.
- `10`–`11` — exclusions and non-green scopes (carry forward v2
  unchanged; non-green scope entries do NOT change unless the
  adaptation specifically addresses one).
- `12-change-vs-v2.md` — what changed between v2 and v3, with
  rationale; what did NOT change; what requires fresh review.
- `13-adaptation-test-evidence.md` — the 12 focused regression
  tests, the bounded compat re-run, the v3 composition digest, the
  per-function review, the Sentinel verdict (carried forward as
  provenance; v3 needs fresh reviews).

## 10. The carried-forward items that DO NOT change

- 14 NO_OP entries (3 Noesis + 11 A6) — byte-identical to v2.
- 6 ADD entries (5 runtime_enforcement test files +
  `agent/runtime_enforcement.py`) — byte-identical to v2.
- 4 of 6 Hermes REPLACE entries (`agent/agent_init.py`,
  `agent/error_classifier.py`, `agent/turn_api_call.py`,
  `agent/turn_api_error.py`) — byte-identical to v2.
- A6 governance surface: `governed_enforcement` keyword,
  `FailoverReason.governed_denied` enum, `report_usage` /
  `enforce_admission` hooks, `deregister_governed_session` lifecycle
  cleanup. **All retained in v3.**
- Excluded dirty files: `specialist_routing.py`,
  `hermes_cli/config.py`, `models.py`. The on-disk `models.py`
  byte is still byte-identical to the qualified source; the
  dirty-dependency defect is still inherited.
- Non-green scopes: `ruamel_missing_in_noesis_venv`,
  `test_run_agent_skill_manage_vs_skill_view`,
  `strong_worker_write_isolation_unsatisfied`,
  `a6_models_py_dirty_dependency`. All carried forward unchanged.

## 11. Sentinel verdict and the memory discrepancy

The Sentinel verdict recorded for the v2 candidate is "PASS, no
blocking findings, on successor identity `e8c33bb…`." That
verdict is a property of the v2 candidate. The v3 candidate has
a different digest; the v2 verdict does not transfer. The v3
manifest must record the v2 verdict verbatim as provenance, label
it as "v2 verdict; v3 requires fresh reviews," and not claim
endorsement of the v3 candidate by the v2 reviewer.

The system memory at session start may describe the v2 verdict
differently (e.g. "BLOCKED"). When this happens, report BOTH: the
recorded v2 verdict from the artifact, and the memory claim as
"preserved provenance note, not an independent reviewer verdict."
Do not reinterpret a recorded PASS as BLOCKED or vice versa.

## 12. The next required decision

The v3 manifest is bound to a new candidate identity. The operator
must explicitly approve the v3 candidate before any installation.
The operator's approval of v2 does not transfer to v3 because v2
and v3 are different candidates with different digests.

The next-step options presented to the operator:

- **Approve the v3 candidate for installation** — the v3 source
  bytes are the binding bytes; the v3 restoration table restores
  the v3 bytes; the v3 manifest SHA-256 is the binding identity.
- **Request a different bounded adaptation** — specify the
  changes. I do not implement; the v3 manifest is rewritten.
- **Decline and stop** — the v2 candidate is preserved unchanged
  for audit; no installation is performed.

A passing compat check does not authorize installation. No
destination writes, installation, dependency installation, plugin
enablement, activation, live canary, commit, push, merge, or
deployment is performed by this packet.

## Common failure modes to avoid

- **Reusing the v2 staging for the v3 worktree.** v2 holds v2's
  overlay; the v3 worktree must be a separate `git worktree add
  --detach` at the bound baseline. Reusing the v2 staging
  silently keeps v2's overlay bytes in place and makes the v3
  edits non-applied.

- **Classifying the 1 known environmental failure as a v3
  regression.** The Hermes enforcement battery's
  `test_rebuild_with_matching_governed_context_succeeds` fails
  in this environment because `tests/home_io_guard.py` classifies
  the staging noesis path as a real hermes home. This is the same
  failure mode in v2 and v3. It is environmental, not a v3
  regression. Editing `home_io_guard.py` is outside the authorized
  source-edit scope.

- **Claiming the v2 Sentinel verdict applies to v3.** The v2
  verdict is on `e8c33bb…`; v3 is on `d9812fc7…`. They are
  different candidates. The v3 manifest records the v2 verdict
  as provenance and explicitly requires fresh reviews.

- **Silently altering the v2 manifest instead of issuing v3.** v2
  is preserved unchanged. v3 is a new file at a new path with a
  new manifest version. The operator's prior approval of v2
  does not transfer to v3.

- **Touching source outside the operator-named edits.** v3 source
  edits are limited to the call sites / functions / immediately
  necessary imports / focused tests named by the operator.
  Refactoring unrelated code is out of scope.

- **Treating "the proposal works on the operator's installed
  checkout" as a license to write there.** The v3 worktree is
  read-only evidence; the installation is a separate step
  requiring a separate operator approval.

- **Assuming the Hermes dev source HEAD is the source of the
  qualified bytes.** The packet's `overlay-manifest.sha256` is
  the source of truth. The Hermes dev source is informational
  only. v3's two adapted files come from a hand-applied edit in
  the v3 worktree, sourced from upstream patterns; the
  reconstruction does not contain v3 bytes.

- **Carrying the v2's `models.py` "no longer reproduces" defect
  forward as "still a defect" without re-verifying the on-disk
  byte.** The v3 manifest records the inherited defect in
  `non_green_scopes.a6_models_py_dirty_dependency` and in
  `explicit_exclusions`. Always re-run `git status --porcelain`
  to confirm the file is still `M` at v3's bound baseline.
