# Review-task state machine: drive verdict → ledger

After a direct reviewer child session writes its receipt, the orchestrator must
durably reconcile that out-of-band result into the canonical ledger. A process
exit, transcript, or verdict file is evidence, not a state transition. Re-open a
fresh `Orchestrator` over the canonical ledger, read the review task's persisted
attempt epoch, then drive `submit_candidate → submit_handoff → record_review →
succeed|fail` in order. Bind every call to the full candidate identity the child
actually reviewed (tracked digest plus combined digest when untracked candidate
bytes exist), attach the receipt path and hash, and read back the terminal state
from another fresh replay before reporting it. Never edit JSONL directly or
infer reconciliation from the child's self-report.

For dependency topology, Sentinel is lineage-linked to an implementation in
`awaiting_review` but does not depend on that implementation succeeding;
otherwise review and success wait on each other. Skeptic depends on the Sentinel
review task and may claim only after Sentinel's receipt has been validated as
`PASS`. Cancel and supersede any pre-created task with the circular dependency
rather than mutating its ledger record.

## Required state machine per review-task

For each of the two review-tasks (Sentinel and Skeptic), drive it
through the canonical lifecycle in this order:

```python
from pathlib import Path
from app.control_plane import Orchestrator

o = Orchestrator(Path('<artifacts_dir>/tasks.jsonl'))
review_task_id = '<the task_id returned by o.propose>'
candidate_sha   = '<tracked_diff_sha256 from the contract>'
combined_sha    = '<combined tracked+untracked sha256, if recorded>'
profile_of_implementer = 'noesis-sentinel'  # or 'noesis-skeptic'
cross_reviewer          = 'noesis-skeptic'   # the OTHER reviewer-only profile

# 1. enqueue -> claim -> start (move from approved to running)
o.enqueue(review_task_id)
o.claim(review_task_id, claimed_by=profile_of_implementer)
o.start(review_task_id)

# 2. submit_candidate: bind the review-task's delegation.candidate_revision
o.submit_candidate(
    review_task_id,
    candidate_revision=candidate_sha,
    candidate_digest=combined_sha or candidate_sha,
    attempt_epoch=1,                       # or the review-task's current epoch
)

# 3. submit_handoff: the verdict file IS the artifact; required keys below
o.submit_handoff(
    review_task_id,
    handoff={
        'summary': f'{profile_of_implementer} review of <short-name>: <verdict>',
        'artifacts': [
            {'path': '<SENTINEL-VERDICT-...>.md', 'role': 'review_verdict'},
        ],
        'verification_result': {
            'passed': True,
            'focused_tests': '<N> passed in <duration>',
            'full_suite': '<M>/<M> passed (excluding <env-fail>)',
            'candidate_revision': candidate_sha,
            'evidence': '<SENTINEL-VERDICT-...>.md',
        },
    },
)

# After submit_handoff the task transitions to awaiting_review.
# Now record the cross-reviewer's verdict. Note the cross-reviewer is
# NOT the implementer of the review-task; the policy rejects self-review
# with 'reviewer_not_independent: reviewer must differ from the implementer'.

o.record_review(
    review_task_id,
    stage='spec',                              # NOT 'spec_review'
    verdict='PASS',                            # or REQUEST_CHANGES / BLOCKED
    reviewer=cross_reviewer,                   # the OTHER reviewer profile
    candidate_revision=candidate_sha,
    findings=[{'severity': 'minor', 'location': '<file>:<line>', 'rationale': '...'}],
)

# For Sentinel's review-task, the cross-reviewer is Skeptic.
# For Skeptic's review-task, the cross-reviewer is Sentinel.
# If a quality review is also required (and the policy's delegated
# review gate is set to require it for the review-task's risk tier),
# record it as well. With only two reviewer-only profiles available,
# both stages are by the cross-reviewer:

o.record_review(
    review_task_id,
    stage='quality',                           # NOT 'quality_review'
    verdict='APPROVED',                        # only after Sentinel is PASS
    reviewer=cross_reviewer,
    candidate_revision=candidate_sha,
    findings=[],
)

# 4. succeed or fail based on the verdict
if verdict in ('PASS', 'APPROVED'):
    o.succeed(review_task_id)
else:
    o.fail(review_task_id, reason=f'{verdict} - see <verdict-file>')
```

For the **implementer task** (the bounded worker's task), the same
shape applies but with the implementer profile as the claimer:

```python
implementer_task_id = '<id from o.propose at the start>'
o.enqueue(implementer_task_id)
o.claim(implementer_task_id, claimed_by='noesis-forge')   # or whichever implementer
o.start(implementer_task_id)
o.submit_candidate(
    implementer_task_id,
    candidate_revision=candidate_sha,
    candidate_digest=combined_sha or candidate_sha,
    attempt_epoch=1,
)
o.submit_handoff(
    implementer_task_id,
    handoff={
        'summary': 'bounded implementer of <short-name>: <status>',
        'artifacts': [{'path': 'IMPLEMENTER-RESULT-<iter>.md', 'role': 'implementer_result'}],
        'verification_result': {
            'passed': True,
            'focused_tests': '<N> passed in <duration>',
            'full_suite': '<M>/<M> passed (excluding <env-fail>)',
            'candidate_revision': candidate_sha,
            'evidence': 'IMPLEMENTER-RESULT-<iter>.md',
        },
    },
)
# Two reviewers exist; both stages go to the cross-reviewer when the
# implementer is neither, but here the implementer IS the implementer,
# so the reviewers must be Sentinel and Skeptic. Order:
o.record_review(implementer_task_id, stage='spec',  verdict='PASS',     reviewer='noesis-sentinel', candidate_revision=candidate_sha, findings=[...])
o.record_review(implementer_task_id, stage='quality', verdict='APPROVED', reviewer='noesis-skeptic',  candidate_revision=candidate_sha, findings=[...])
o.succeed(implementer_task_id)
```

## What the policy checks at each step

The Orchestrator enforces these at every transition; if you skip
a step, the next call raises one of these PolicyViolations:

- `Orchestrator.propose(...)` with `assignee_profile='noesis-orchestrator'`
  on an `r1+` risk-tier task: `supervisor_cannot_execute: 'noesis-orchestrator' is a supervisor profile and must delegate, not execute`. The meta-supervisor must NOT be the implementer of a review-task. Use the actual reviewer profile.
- `Orchestrator.propose(...)` with `reviewer_profile='noesis-orchestrator'`:
  `reviewer_must_be_reviewer_only: 'noesis-orchestrator' is not a reviewer-only profile`. The cross-reviewer must be a reviewer-only profile.
- `Orchestrator.propose(...)` with `required_capability='review_spec'` when the assignee is `noesis-sentinel`:
  `capability_mismatch: 'noesis-sentinel' does not declare capability 'review_spec' (declared: ['block_merge', 'code_review', 'security_review', 'severity_classify', 'test_design'])`. Use `'code_review'` for Sentinel, `'adversarial_review'` for Skeptic.
- `Orchestrator.record_review(task_id, stage='spec_review', ...)`:
  `unknown_review_stage: unknown review stage 'spec_review'`. The stage constants are the compact form: `'spec'`, `'quality'`, `'integration'`.
- `Orchestrator.record_review(task_id, stage='spec', reviewer='noesis-sentinel', ...)`
  on a task whose `assignee_profile='noesis-sentinel'`:
  `reviewer_not_independent: reviewer must differ from the implementer`. The reviewer of Sentinel's review-task MUST be Skeptic.
- `Orchestrator.record_review(task_id, stage='quality', verdict='APPROVED', ...)`
  on a task whose previous reviews are missing the spec stage:
  `spec_required: quality review cannot begin before current-candidate spec PASS`. Always record spec first, then quality.
- `Orchestrator.record_review(task_id, stage='spec', ...)` when
  `task.delegation.candidate_revision` is `None`:
  `stale_candidate: review candidate '<X>' != current 'None'`. Submit a candidate first.
- `Orchestrator.succeed(task_id, ...)` with no handoff:
  `handoff_required: structured handoff evidence is required before success`. Always submit a handoff first.
- `Orchestrator.succeed(task_id, ...)` with handoff missing `summary`:
  `handoff_incomplete: handoff is missing required field 'summary'`. All of `summary`, `artifacts`, `verification_result` are required.
- `Orchestrator.succeed(task_id, ...)` with `verification_result.passed` falsy:
  `verification_failed: verification_result.passed is false`. The handoff's verification result must be `{passed: True, ...}`.
- `Orchestrator.succeed(task_id, ...)` with the task in `awaiting_review`
  and no `record_review` for `quality`:
  `quality_review_required: cannot accept without current-candidate quality APPROVED`. Both stages required.
- `Orchestrator.fail(task_id, reason=...)` from `approved` state (not allowed by state machine):
  `Illegal transition approved -> failed (allowed: ['blocked', 'cancelled', 'queued'])`. The fail path only works from `running` or `awaiting_review`. If the task is in `approved`, enqueue -> claim -> start -> submit_handoff -> fail.

## Pitfalls at this layer

- **The review-task's `assignee_profile` is the meta-supervisor
  (e.g. `noesis-orchestrator`) and the actual reviewer is recorded as
  `reviewer_profile=cross-reviewer`.** Then the implementer of the
  review-task is the meta-supervisor, and the cross-reviewer is
  independent. Wait — this fails the `supervisor_cannot_execute` rule
  on the implementer side. The only way to keep both the implementer
  as a reviewer profile and the cross-reviewer independent is to
  set `assignee_profile=<reviewer>` (e.g. `noesis-sentinel`) and
  `reviewer_profile=<cross-reviewer>` (e.g. `noesis-skeptic`).
  The "implementer" of the Sentinel review-task is Sentinel, even
  though Sentinel is only writing the verdict file to disk; the
  cross-reviewer is Skeptic. Both `assignee_profile` and
  `reviewer_profile` are role fields, not literal implementer
  identities.

- **The `reviewer=` argument to `record_review` is the cross-reviewer
  profile, not the profile that wrote the verdict file.** The policy
  check is: `reviewer != assignee_profile`. Sentinel implements
  Sentinel's review-task, so the reviewer recorded on that task is
  Skeptic. Skeptic implements Skeptic's review-task, so the reviewer
  on that task is Sentinel. The verdict file is a side effect;
  the ledger entry is the audit record.

- **A single `record_review` with stage='spec' is not enough to
  succeed.** The delegated review gate is configured to require both
  spec and quality stages when a `reviewer_profile` is set. If
  `o.succeed` raises `quality_review_required`, you missed the
  quality-stage `record_review`. Add it with
  `stage='quality', verdict='APPROVED', reviewer=<cross-reviewer>`.

- **The handoff's `verification_result` must include the candidate
  digest and test counts as fields, not in a free-text summary.** The
  policy reads `result.get('passed')`; if `passed` is missing or
  falsy, the success path raises `verification_failed`. Including
  the digest and counts as structured fields makes the ledger
  self-describing for future replay.

- **Use `o.fail(..., reason=...)` for REQUEST_CHANGES / BLOCKED,
  not `o.succeed(..., reason=...)`.** `fail` is the only transition
  allowed from `running` / `awaiting_review` to a terminal failure
  state. Trying to call `succeed` after a non-pass verdict raises
  `quality_review_required` or `unmet_acceptance_criteria`.

- **Do not delete or modify the verdict file after recording it.**
  The verdict file's recorded `tracked_diff_sha256` is the audit
  chain. If you want to re-record with a different verdict, the
  `record_review` method is idempotent on
  `(stage, reviewer, candidate_revision)`: re-calling it with the
  same triple updates the latest verdict. The file itself can stay;
  do not overwrite the verdict file with a different verdict without
  also reflecting that change in the ledger.
