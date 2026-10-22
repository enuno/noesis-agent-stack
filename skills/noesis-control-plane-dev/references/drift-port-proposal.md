# Drift-authorized installation/port proposal cycle

Use this reference when a previously approved installation or port proposal
must be re-emitted because the destination checkout has advanced between the
original inspection and the proposed execution, and the operator has
authorized a read-only drift assessment plus a revised proposal bound to the
new state.

This is **not** the same as a normal integration plan or a clean port: the
proposal is a binding contract that explicitly states the destination state
hash and HEAD it was inspected against. A drift invalidates that binding.

## 1. The drift event

A destination checkout (the place where overlay bytes would be written) can
advance between inspection and execution. Common causes:

- Routine upstream sync (`git pull` / `git merge` from `origin/main`).
- A maintainer push.
- A CI rebase.
- An external executor committing inside the same checkout.

A drift does **not** by itself authorize a re-port. The operator must
explicitly authorize a read-only drift assessment and a revised proposal.

## 2. Stop and request authorization on first detection

When preflight detects a destination HEAD that does not equal the bound HEAD
in the approval manifest:

1. **Do not write any file in the destination.** Not the new bytes, not
   `rm`, not `git checkout`, not `git reset`. The original approval is
   bound to the prior HEAD; a write to the drifted state is an
   unauthorized action.
2. **Do not restore the old HEAD.** Restoration is a separate decision
   that requires the operator's approval; it is not implied by the
   drift.
3. **Preserve the original proposal unchanged.** Mark it SUPERSEDED for
   execution, but keep every file and the original manifest byte-for-byte
   in the audit trail.
4. **Request the operator's choice between paths** (a 1-3-1 is the
   natural shape):
   - **Path A — restore the previous HEAD**: the original proposal
     becomes the binding proposal again.
   - **Path B — re-inspect against the new HEAD and re-emit the
     proposal**: the new proposal supersedes the old. The old is kept
     for audit, marked SUPERSEDED.
   - **Path C — investigate unresolved issues first**: hold both
     proposals and return specific evidence the operator requested.
5. The operator's reply is the new authorization. Do not infer it from
   the absence of objection, from a previous I-approve, or from a
   destination state that looks "obviously intended."

## 3. Inspect the drift, read-only

Once Path B is authorized:

- `git -C <dest> rev-parse HEAD` — record the new HEAD.
- `git -C <dest> status --porcelain` — record the worktree cleanliness
  (must be empty for an honest drift event; a non-empty porcelain
  means uncommitted changes were also introduced and that is a
  separate finding to surface).
- `git -C <dest> log OLD..NEW --oneline | wc -l` — record the commit
  count.
- `git -C <dest> diff --stat OLD..NEW` — record the file count and
  +/− line totals.
- `git -C <dest> log OLD..NEW --format='%H %an <%ae> %s'` — capture
  authorship for the new commits.
- `git -C <dest> reflog --date=iso | head -30` — capture the local
  operation history; this is the only audit log that distinguishes
  "operator pulled" from "an external sync."
- `git -C <dest> branch -vv` — confirm tracking and the merge base
  with `origin/main`.

Do **not** modify any destination file. Do **not** `git pull`,
`fetch`, `checkout`, `reset`, `clean`, or `stash`. Do **not** install
dependencies.

## 4. Re-emit the proposal bound to the new HEAD

The revised proposal is a fresh directory (e.g.
`workspace/orchestrator/<name>-revised-port-proposal/`) that:

- Binds a new manifest version (e.g. `a6-port-approval/v2`).
- Reuses every binding from the original — qualification report SHA-256,
  qualified successor digest, Noesis HEAD, Hermes dev HEAD — unchanged.
- Records the drift provenance: `from: <old>`, `to: <new>`, commit
  count, file count, +/− lines, reflog excerpt, branch tracking.
- Re-derives every per-file operation from the **on-disk destination
  byte at the new HEAD** vs. the **qualified source byte from the
  packet's overlay manifest**. NO_OP if equal, ADD if absent, REPLACE
  if different.
- Preserves the original proposal unchanged and marks it SUPERSEDED.
- Updates the preflight and post-install validation gates to refer to
  the new HEAD.
- Updates the rollback table to restore bytes from the actual
  destination at the new HEAD, not from `git show <NEW_HEAD>:<path>`
  (use the on-disk byte — they should match, but the discipline is
  to capture what is actually on disk).

## 5. Source-of-truth discipline for overlay bytes

The packet's `overlay-manifest.sha256` (or equivalent manifest in the
packet) is the **source of truth** for the qualified source bytes. It
is recomputed-verified against the packet's reconstruction directory
(e.g. `~/.hermes/.../cache/scratch/.../reconstruction/`).

**The Hermes dev source HEAD is informational only.** It is not the
source of the qualified bytes. Do not compare on-disk destination
bytes against the dev source HEAD and report the result as
"compatible with the source." That comparison produced a false
"everything is a NO_OP" answer in the past and silently swallowed a
6-file REPLACE. The only correct comparison is destination byte vs.
qualified source byte from the manifest.

To verify the source of truth is sound:

- Recompute every per-file SHA-256 from the reconstruction directory
  and compare against the manifest. All must match.
- Recompute the integrated overlay digest (using the packet's stated
  recipe — usually SHA-256 over the raw concatenation of overlay
  bytes in `integrated_overlay_order`, no separators) and confirm it
  equals the packet's claimed successor digest.

If either check fails, the source of truth is broken; stop and
report. Do not paper over with the dev source bytes.

## 6. Detached-HEAD and on-disk byte discrepancy

A checkout may be in a state where `git show <HEAD>:<path>` returns a
different byte than the on-disk file (e.g. a detached HEAD with a
dirty file, or an index that has been mutated). When this happens:

- The **on-disk byte is the authority** for the port. The proposal
  compares on-disk destination vs. qualified source, not HEAD blob
  vs. qualified source.
- Document the discrepancy in the proposal: name the file, the
  HEAD-blob SHA, the on-disk SHA, and the reason the on-disk byte
  is the one that matters.
- If the file is part of the qualified overlay and the on-disk byte
  happens to equal the qualified source, the file is a NO_OP — but
  the proposal must also note that the A6 candidate (or whatever
  overlay) is reproducible from the packet's reconstruction but
  **not** from a clean source HEAD. This is the Sentinel BLOCKED
  defect for a dirty-dependency overlay.

## 7. Dirty-file dependencies must be acknowledged, not silently passed

When an overlay entry's destination file is `M` (modified) in the
worktree but the on-disk byte happens to equal the qualified source,
the file is a NO_OP for the port, but the A6 candidate has a
reproducibility defect:

- A clean verifier who checks out the source HEAD and runs
  `git show HEAD:<file>` will see a different byte than the qualified
  source.
- A packet that documents the overlay as "install at HEAD" is
  inconsistent with the worktree state.

The proposal must:

- Add the dirty file to `explicit_exclusions` in the manifest.
- Add a `non_green_scopes` entry naming the file, the
  HEAD-blob-vs-on-disk discrepancy, and the fact that the candidate
  is reproducible from the packet's reconstruction but not from a
  clean HEAD.
- Label the defect as **inherited** (already present in the packet)
  rather than a regression introduced by the proposal. The proposal
  preserves the on-disk byte; it does not fix the defect.
- State that fixing the defect requires a re-issued overlay whose
  every byte is reproducible from a clean source HEAD.
- **Always re-verify the disposition with `git -C <dest> status --porcelain -- <path>`** before declaring the proposal complete. Memory may say the file is "clean" or the prior proposal may have excluded it; the porcelain line is the only authoritative current state. Add the file to `explicit_exclusions` only if the porcelain line is `M` (or ` M`); a clean porcelain means the file no longer needs the exclusion and the proposal's manifest must be updated.

## 8. Per-file decision matrix template

| overlay key | qualified source SHA-256 | destination on-disk SHA-256 | destination HEAD blob (informational) | operation |
|---|---|---|---|---|
| ... | ... | ... | ... | NO_OP / ADD / REPLACE |

The matrix is the single source of truth inside the proposal. Every
section that lists per-file actions must agree with this matrix. A
mismatch between the matrix and a downstream section is a proposal
defect; re-derive the matrix from the on-disk bytes, not from prior
narrative.

## 9. Preflight gate for the revised proposal

Re-run all preflight gates against the new state:

- The qualification report SHA-256 still matches the bound value.
- The integrated overlay digest still recomputes from the
  reconstruction.
- The destination HEAD equals the bound value in the new manifest.
- The source HEADs (Noesis, Hermes dev) match their bound values.
- For every overlay entry, the on-disk destination SHA-256 still
  matches the qualified source SHA-256 (or is absent for ADDs).
- The dirty file exclusions are still in the manifest.
- The internal manifest consistency check (every overlay entry has
  a restoration row whose `mode` matches the operation) passes.

If any preflight gate fails, halt; do not write any file in the
destination.

## 10. Awaiting the operator's re-approval

The drift invalidates the original approval. The operator must
explicitly approve the revised proposal. Do not self-approve, do not
rely on the prior I-approve, do not proceed when the operator has not
re-confirmed.

The new approval binds:

- The new manifest version.
- The new destination HEAD.
- The per-file operations (especially the 6 REPLACE files that the
  prior proposal mischaracterized as NO_OP).
- The acknowledged inherited defects (e.g. the models.py dirty
  dependency).

## Common failure modes to avoid

- **False NO_OP from a wrong source comparison.** Comparing on-disk
  bytes against the dev source HEAD instead of the qualified source
  bytes will produce a systematically wrong "everything matches"
  answer. Always re-derive the per-file operations from the
  packet's manifest.
- **Re-approval assumed from prior I-approve.** The previous approval
  bound a different destination HEAD. The new manifest binds a new
  HEAD. They are separate approvals.
- **Replaying the original manifest as if it were the new one.** The
  new manifest is a different file with a different version
  (`v2`), a different `from:`/`to:` provenance block, and a
  different per-file decision matrix.
- **Silently passing through a dirty dependency.** If the on-disk
  byte of a modified file happens to equal the qualified source, the
  file is still a NO_OP for the port, but the dirty state is real
  and the proposal must acknowledge it.
- **Resetting the destination to a clean state without explicit
  authorization.** The original drift assessment says "do not reset,
  checkout, clean, stash, fetch, update, install dependencies, or
  modify destination files." The reassessment inherits this constraint
  unless the operator explicitly widens it.
- **Treating the Sentinel BLOCKED verdict as a property of the
  drift.** Sentinel's verdict is about the A6 candidate's
  reproducibility; the drift does not fix or worsen it. The proposal
  must label the defect as inherited and acknowledge it.
