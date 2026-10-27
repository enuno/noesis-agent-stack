---
name: noesis-candidate-acceptance-review
title: "Noesis Candidate Acceptance Review"
description: "Review a candidate deliverable and issue a verdict."
version: "1.0.0"
last_updated: "2026-10-25"
author: "noesis-forge"
license: "Proprietary"
metadata:
  hermes:
    tags: [review, candidate, acceptance, verification, noesis]
    category: software-development
    related_skills: [noesis-track-b-candidate-remediation, omh-code-review, omh-verification-gate]
---

# Noesis Candidate Acceptance Review

## Overview

Independently verify an **agent-produced candidate deliverable** before it is
accepted, committed, or merged. The entry point is an implementer result report
that asserts: candidate diff hashes, per-file hashes, test counts and suite
outcomes, and a list of held operations that were *not* performed.

Your job is to **reproduce those claims from source**, not to re-read the report.
Every claim is either VERIFIED (you reproduced it) or ACCEPTED (you are taking
the report's word for it) — never blurred.

This is the reviewer-side counterpart to `noesis-track-b-candidate-remediation`
(implementer side). Fleet protocol: Sentinel reviews first, Skeptic second, each
verdict bound to the candidate hash it actually inspected; `not_self_approved:
true` travels with the candidate throughout.

## When to Use

- An implementer result report exists and asks for independent acceptance,
  verdict, or "conditions before commit".
- A candidate is anchored to a diff hash and a reviewer must confirm that hash.
- A candidate was remediated after a REQUEST_CHANGES verdict and the new
  candidate needs re-anchoring and re-review.
- You are asked to verify that held operations (no commit, no provider calls,
  no credential reads, no live-profile writes, no schedule activation, no
  dependency installs) actually held.

Do NOT use for: implementing the fix yourself (that is the implementer skill),
or reviewing your own work.

## Read-Only Mandate

Unless the request says otherwise, the review is strictly read-only:
**no edits, no staging, no commits, no pushes, no provider/model calls, no
credential reads, no live-profile writes, no scheduler or plugin activation,
no dependency installation.**

Verify against **scratch copies**, never the live worktree, checkout, or
profile tree. A review that mutates what it reviews destroys the evidence it
was commissioned to establish.

## Procedure

### 1. Establish provenance state BEFORE verifying any claim

Read the report's stated repo state, then read the actual state, and diff them:

```bash
git -C "$WT" status --short
git -C "$WT" log --oneline -3
git -C "$WT" reflog --date=iso | head -20
git -C "$WT" worktree list
git -C "$WT" branch -r --contains <candidate-commit>
git -C "$WT" log -1 --format='%H %ad %an' <candidate-commit>
```

The report usually describes an **uncommitted** candidate (a `git status --short`
block of ` M` and `??` lines). If the worktree is instead clean at a commit —
especially one already **pushed** to a remote branch — then the artifact on
disk is not the artifact under review. That is a **top-line finding**, not a
footnote, and it conditions the whole verdict: report it first, then verify the
candidate the report actually describes.

### 2. Anchor the candidate identity

Collect every identity the report asserts: combined diff hash, tracked-only
diff hash, per-file SHA-256 table, baseline commit, worktree path. These are
the things you will independently reproduce.

### 3. Reconstruct the candidate if it is no longer in the worktree

When the candidate has been superseded, its exact bytes usually survive as
**unreachable git objects**. Search the object DB by content hash rather than
declaring the candidate unverifiable. Full recipe and the diff-hash recipe
matrix: `references/candidate-reconstruction.md`.

Helper: `scripts/reconstruct_candidate.py` rebuilds the tree and prints every
diff-hash recipe variant so a claimed hash can be matched to the recipe that
produced it.

### 4. Reproduce the claimed hashes

A candidate's "the diff" is **not one hash**. The same bytes hash differently
depending on how the diff was produced:

| Recipe | Produces |
|---|---|
| index-vs-worktree, new files untracked | tracked-only hash |
| index-vs-worktree with new files intent-to-add (`git add -N`) | tracked + new files as additions |
| index fully staged (`git add -A`, then `git diff --cached <base>`) | full base→candidate content diff |
| `git diff <base> <commit>` (tree-to-tree) | full base→candidate content diff |
| any tracked diff + `--- new files ---` + concatenated new-file bodies | "combined" hash |

**Enumerate the recipe variants before calling a claimed hash wrong.** A
mismatched hash is a finding about the *recipe or the report*, not proof of
tampering — and in a review where the report's hash is right and your recipe
is wrong, reporting "hash mismatch" is a false positive that costs a cycle.

### 5. Reproduce the claimed test results

Run the suite in the reconstructed scratch tree with the **project's own
interpreter**, not the ambient one. Reconcile counts, don't just eyeball them:
`collected = passed + failed`, and the delta between base and candidate
collections should equal the number of new tests claimed.

### 6. Attribute every failure

A failure that also fails on the base commit is *not yet* proven environmental.
Run the **positive control**: supply the missing fixture (often a gitignored
file that exists only in the primary checkout) into **both** the base tree and
the candidate tree, and re-run. If it passes on both, the failure is proven
environmental and pre-existing; the report's "environment-population issue,
not a regression" claim is then VERIFIED rather than ASSUMED.

### 7. Independently probe each behavioral claim

Do not accept "the code looks like it does X" for a claim you intend to mark
verified. Write a throwaway probe per behavioral claim — report-only auditors,
admission gates, stale-evidence rejection, write confinement. Probe recipes and
the held-operation static scan: `references/claim-verification-probes.md`.

### 8. Audit the held-operation claims

Each "no X was performed" claim needs both a static and a dynamic check:

- **Static**: scan the changed/new modules' import and write surfaces for
  network, credential, subprocess, scheduler, and live-path tokens.
- **Dynamic**: snapshot the target directory before/after the operation and
  prove nothing outside the declared write set changed; check live-profile
  mtimes across the claimed implementation window.

### 9. Verify chain of custody

- Does the hash the reviewers bound to their verdicts equal the hash of what is
  actually committed and pushed?
- Does the **commit message's own quoted hash** recompute? A commit message
  hash is a claim, not evidence.
- Did the reviews **precede** the commit? (Compare timestamps; do not trust
  narrative ordering.)
- Do the ledger records bind the verdict to the candidate hash, and are earlier
  (now-superseded) candidates marked as such?

### 10. Write the verdict

## Output Contract

The deliverable shape is fixed by the requester. Expect:

1. **VERDICT** — one of `ACCEPT` / `ACCEPT WITH LIMITATIONS` / `BLOCK`, stated
   up front, and scoped to *which* candidate it covers (the named hash).
2. **Findings** — each with file/line references, severity, and the evidence
   that establishes it.
3. **Verified vs accepted** — an explicit split: what you reproduced from
   source, and what you took from the report without re-deriving (e.g. RED→GREEN
   history, verbatim console output, narrative test intent). Never let a
   verified claim imply an accepted one.
4. **Conditions before commit** — concrete, actionable, ordered.

When the artifact on disk is **already committed and pushed**, say so plainly:
"conditions before commit" is then partly moot, so re-frame the conditions as
pre-merge gates and state what the commit/push override was.

## Always-On Rules

- Reproduce; do not re-read. A claim you did not independently derive is
  ACCEPTED, and must be labeled that way.
- A defect you **reproduced yourself** outranks a defect you read about in
  someone else's verdict. Drive the real code path, not a re-implementation.
- The report's stated repo state and the actual repo state are two different
  facts; a divergence between them is a finding, reported at the top.
- Findings come before summaries; every finding cites file/line or a command.
- Never let a candidate's own re-run count as independent review, and never
  sign off your own work.
- Do not apply or carry forward a review verdict; you are producing one.
- Return control when the contract is done. Do not select the next task.
- `not_self_approved: true` travels with the candidate; do not assert approval
  on the implementer's behalf.

## Pitfalls

- **A candidate's bytes outlive its worktree.** Unreachable git objects keep a
  superseded candidate recoverable by content hash, so search the object DB
  before reporting a candidate as unverifiable — otherwise you hand back a
  BLOCK on a missing-evidence technicality when the evidence was one command
  away.
- **"The diff" is not one hash.** Index-vs-worktree, tree-to-tree, and
  intent-to-add each yield a different SHA-256 for identical content; enumerate
  recipes before declaring a hash mismatch.
- **Never verify inside the live worktree.** Drive git with
  `GIT_INDEX_FILE` + `GIT_WORK_TREE` against a scratch copy — a review that
  mutates the candidate cannot certify it.
- **"Fails on base too" is not yet "environmental."** Run the positive control
  (supply the missing fixture to both trees) — the control, not the parallel
  failure, is what establishes causation.
- **Grep proves absence of a token, not absence of behavior.** Each behavioral
  claim you mark verified needs a probe that drives the real path.
- **A permissive JSON schema hides shape drift.** `additionalProperties: true`
  accepts both the old and the new shape, so schema-conformance tests stay
  green across a runtime type change; validate the stored value against the
  property's own subschema, not the whole document.
- **Ambient python may not be the project's python.** Resolve the project venv
  explicitly and neutralize a leaked `PYTHONPATH`, or a mismatched
  site-packages breaks an import that works under the venv.
- **Read the real signature before writing a probe.** A guessed kwarg or a
  missing required field turns "no finding" into a probe crash; distinguish a
  probe error from a real defect, and read the exception type rather than
  assuming the probe proved the guard.
- **A commit message's quoted hash is a claim, not evidence.** Recompute it.
- **Reviews preceding the commit do not license a commit the manifest held.**
  Surface the override as an operator decision to confirm explicitly.
- **A retired assertion may have been replaced, not weakened.** Diff the test
  file against base and read what the new assertion actually pins before
  reporting a removed check as a coverage loss.

## Supporting Files

- `references/candidate-reconstruction.md` — object-DB recovery recipe, the
  diff-hash recipe matrix, the combined-patch recipe, and chain-of-custody
  checks.
- `references/claim-verification-probes.md` — probe recipes (stale-evidence
  rejection, report-only write confinement, admission gates, guard precedence,
  credential non-capture, schema drift) plus the held-operation static and
  dynamic scans.
- `scripts/reconstruct_candidate.py` — rebuilds a superseded candidate from the
  object DB and prints every diff-hash recipe variant against the claimed
  hashes.

## Verification Checklist

- [ ] Actual repo state read and compared against the report's stated state
- [ ] Candidate identity list collected (combined hash, tracked hash, per-file
      table, baseline commit)
- [ ] Candidate reconstructed from object DB if it is no longer in the worktree
- [ ] Claimed hashes reproduced, or the recipe mismatch reported as such
- [ ] Test counts reproduced in scratch with the project interpreter
- [ ] Every failure attributed with a positive control
- [ ] Every behavioral claim probed, not read and assumed
- [ ] Every held-operation claim checked statically AND dynamically
- [ ] Chain of custody verified (reviewer hash = committed hash; reviews
      preceded the commit; commit-message hash recomputed)
- [ ] Verdict, findings with file/line, verified-vs-accepted split, and
      conditions all present
- [ ] Live worktree, primary checkout, and live profiles untouched
