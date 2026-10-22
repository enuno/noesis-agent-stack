# Verdict schema and digest recipe

The exact contract-side and verdict-side record format for Sentinel
and Skeptic bound to the same candidate digest. Use this when
authoring a SENTINEL or SKEPTIC contract for a B-series (or any
revisioned) candidate.

## Required fields in the contract §1 "candidate identity" block

Both contracts name the same six fields, byte-identical, in this
order:

| Field | Value |
|---|---|
| `task_id` | the implementer task's UUID (e.g. `d84659de-d60d-47ac-a0b5-945f7524695f`) |
| `parent_task_id` | the B1 (or earlier) implementer task's UUID |
| `worktree` | absolute path to the worktree, not the repo root |
| `baseline_commit` | the 40-char hex hash the worktree HEAD equals, e.g. `7746e3ccc3846fe41601c24be34f81f648558914` |
| `tracked_diff_sha256` | the 64-char hex hash of `git diff HEAD | shasum -a 256` |
| `combined_sha256` | the 64-char hex hash of the tracked diff followed by each `??` candidate path, prefixed with `---UNTRACKED:<path>---\n`, in `git status --porcelain` order |

The `combined_sha256` folds in untracked candidate files that Git's tracked
patch omits, especially new tests. Include only `??` entries: adding modified
tracked paths again double-counts them and produces a misleading digest.
Ignored result receipts do not appear in `git status`; hash each required
receipt separately and record its path plus SHA-256 in the review contract.

## Required fields in the SENTINEL verdict file

The verdict file at `<artifacts_dir>/SENTINEL-VERDICT-<iter>.md` MUST
be exactly:

```
verdict: PASS | REQUEST_CHANGES | BLOCKED
reviewer: noesis-sentinel
reviewed_candidate:
  task_id: <the implementer task's UUID>
  parent_task_id: <the previous B-iteration's implementer task UUID>
  worktree: <absolute path>
  baseline_commit: <40-char hex>
  tracked_diff_sha256: <64-char hex>
  combined_sha256: <64-char hex>
  reviewed_at: <ISO-8601 UTC>
implementation_plan_md_clean: <true | false>
requirements:
  R1: <pass | fail | n/a> — <one-line evidence>
  ...
focused_tests: <N> passed in <duration>
full_suite: <passed>/<total> passed (excluding <env-fail>), <xfailed> xfailed, <xpassed> xpassed
secret_scan_findings: <integer>
findings:
  - severity: critical | important | minor
    location: <file>:<lines>
    rationale: <one sentence>
    remediation: <one sentence>
not_self_approved: true
```

The `implementation_plan_md_clean` line is the B2-era addition: it
forces the reviewer to verify that any unrelated prior-art file
named in the contract (e.g. an `IMPLEMENTATION_PLAN.md` from a
prior slice) is byte-for-byte unchanged from the baseline. If
`false`, the verdict must be `BLOCKED` even if every requirement
is `pass`. The reviewer is also required to run
`git diff --stat HEAD -- <plan-file>` and report the diff line
count in the one-line evidence.

## Required fields in the SKEPTIC verdict file

```
verdict: APPROVED | REQUEST_CHANGES | BLOCKED
reviewer: noesis-skeptic
sentinel_verdict_ref: SENTINEL-VERDICT-<iter>.md
implementation_plan_md_clean: <true | false>
reviewed_candidate:
  task_id: ...
  parent_task_id: ...
  worktree: ...
  baseline_commit: ...
  tracked_diff_sha256: ...
  combined_sha256: ...
  reviewed_at: <ISO-8601 UTC>
attack_findings:
  A_<class>: <pass-with-negative-result | finding> — <one-line evidence>
  ...
top_findings:
  - severity: ...
    location: ...
    rationale: ...
    remediation: ...
focused_tests: <N> passed in <duration>
full_suite: <passed>/<total> passed (excluding <env-fail>), <xfailed> xfailed, <xpassed> xpassed
not_self_approved: true
```

The `sentinel_verdict_ref` is mandatory: if it is missing, Skeptic
must write `BLOCKED` because the upstream gate was not verified.
The `implementation_plan_md_clean` field is a second-chance
verifier: even if Sentinel reported `true`, Skeptic re-checks
independently and writes `BLOCKED` if the file drifted between
Sentinel's run and Skeptic's.

## How to compute combined_sha256 (the recipe that worked)

Run, in the worktree cwd:

```bash
python3 - <<'PY'
import hashlib, subprocess
from pathlib import Path

diff = subprocess.check_output(["git", "diff", "HEAD"])
status = subprocess.check_output(
    ["git", "status", "--porcelain"], text=True
).splitlines()
untracked = [line[3:] for line in status if line.startswith("?? ")]
blob = bytearray(diff)
for rel in untracked:
    blob.extend(f"---UNTRACKED:{rel}---\n".encode())
    blob.extend(Path(rel).read_bytes())
print(hashlib.sha256(blob).hexdigest())
PY
```

The first chunk is the tracked diff. Each `??` candidate is prefixed with its
full worktree-relative path so the stream is self-describing and reproducible.
Do not use whitespace-splitting shell loops here: paths may contain spaces, and
`git status -s | awk '{print $2}'` also selects modified tracked paths unless
explicitly filtered. Sentinel and Skeptic must use the same byte recipe.

Hash ignored or external receipts separately; they are evidence artifacts, not
candidate source bytes. If the candidate gains or loses any untracked path,
recompute the combined digest and re-anchor both review contracts.

## Schema validation (orchestrator-side)

The orchestrator's `record_review` method is idempotent on
`(stage, reviewer, candidate_revision)`: re-calling with the
same triple updates the latest verdict without raising
`duplicate_review`. This is how the cross-reviewer pattern
works: Sentinel records `record_review(stage='spec',
reviewer='noesis-skeptic', candidate_revision=<sha>)` for the
Sentinel review-task; Skeptic records
`record_review(stage='spec', reviewer='noesis-sentinel',
candidate_revision=<sha>)` for the Skeptic review-task; both
record `record_review(stage='quality', ...)` with the same
cross-reviewer; the `succeed` path sees both stages present and
proceeds.

If the verdict file's `verdict:` line is missing, malformed, or
records a different digest than the contract, the orchestrator's
acceptance step (after both verdicts) refuses with
`stale_candidate: review candidate '<X>' != current '<Y>'`. The
verdict file must record the exact same `tracked_diff_sha256` and
`combined_sha256` as the contract. If they differ, re-launch the
reviewer (do not edit the verdict file in place — that breaks
the audit chain).

## What "not_self_approved: true" means

Every artifact in the review chain ends with `not_self_approved:
true` exactly. The orchestrator does not see the reviewer
authoring the verdict as authorization. The only authorizer is
the operator, acting on the orchestrator's own `record_review`
events with the cross-reviewer pattern. The line is a durable
claim by the reviewer session: "I did not self-approve; the
verdict is a single bounded child session's read-run-write
output; it is not an authorization to merge or activate anything."
A reviewer session that writes the verdict without this final
line has misbehaved; the orchestrator treats the verdict as
malformed and re-dispatches.
