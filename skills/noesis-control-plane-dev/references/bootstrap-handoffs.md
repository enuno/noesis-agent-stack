# Independent bootstrap repair handoffs

Use when the dispatcher or executor admission path itself needs repair. This
is a handoff workflow, not a claim that any coding backend is available or that
an untested launch procedure works.

## Prepare in this order

1. Read both the original defect contract and any launcher-repair handoff.
   Preserve scope, acceptance criteria, attempt/time limits and non-goals.
   Identify exact files/functions from source; separate source-confirmed defects
   from reproduced failures and proposed repairs.
2. Inspect existing explicit-profile launch support without invoking inference.
   Distinguish profile resolution from running-child identity, configured model
   from policy eligibility, and an approved lane from current account access.
   Do not use a blocked launcher recursively to repair itself.
3. Verify checkout, baseline and worktree independently. A branch ref proves
   neither cleanliness nor the contents of an uncommitted candidate. Record
   `git status --short`, `git diff --stat`, `git diff --name-status`, and
   `git ls-files --others --exclude-standard` through an authorized context.
   Include relevant untracked files in the baseline manifest. A fresh worktree
   at HEAD may omit the very implementation being repaired; preserve the
   current candidate when creating isolation. Mark unavailable checks unknown.
4. Enumerate exact allowed repair files and evidence-output paths. Include the
   smallest necessary controller/store/schema/adapter/test seams rather than
   granting unrestricted repository access. Require escalation for scope growth.
5. Specify RED/GREEN regressions, targeted/full offline checks, actual exit-code
   capture, independent review, and stop conditions. Prevent test fixtures from
   issuing provider calls or modifying persistent profile state.
6. Deliver the complete task text in a durable package plus a copy/paste entry
   prompt. The receiving context records its actual owner/session/runtime,
   workspace, baseline, permission and budget provenance. Label it manually
   initiated bootstrap, never pretend it was routed as a specialist.
7. Require a separate eligible reviewer to inspect the candidate digest, diff,
   original requirements and actual verification logs. An implementation
   session, conversational approval, or backend exit cannot supply that review.
8. Keep normal rollout held until repair, independent review and required
   historical reconciliation pass. Bootstrap execution is not the model-driven
   routing canary, reviewed runtime demonstration, or persistent deployment.

## Package contents

- Original handoffs and complete task specifications, not only file pointers.
- Verified checkout and baseline plus explicit worktree/isolation uncertainties.
- Allowed files, non-goals, remaining limits, provenance and stop conditions.
- Launcher contract: explicit approved provider/model; configurable deadline;
  durable admission/assignment before spawn; result/artifact collection;
  explicit fallback denial or scoped permission; cancellation and confirmed
  cleanup; duplicate/restart safety; unknown usage handling.
- Review contract: positive stage-specific passing verdicts; malformed,
  missing, unknown and wrong-stage verdicts rejected or failing closed;
  revision/digest binding, findings and alternate-completion-path regressions.
- Offline test/compile commands, RED/GREEN logs and exact exit statuses.
- Independent-review requirements and expected artifact manifest.
- Audit findings, scope limitations and any separately gated record correction.
- A ready-to-paste prompt usable in an existing authorized human-operated
  coding session without requiring the broken launcher or an assumed backend.

## Historical audit discipline

Trace ledger defaults, explicit overrides, plugin writers and projections.
Read discovered task records and inspect candidate-specific reviews at the
acceptance event. Separate sandbox/demo records from live authority; a mock
session identifier or demo approval is not live provenance. Do not flag an
old REQUEST_CHANGES merely because a later candidate completed successfully.
Search tests for the actual verdict and predicate as well as related handlers;
absence of a direct assertion is a coverage gap, not evidence that no test can
exercise the behavior.

Report affected task IDs with ledger and event locations, or state that none
were identified within the enumerated scope. Include missing paths, unreadable
or truncated files, arbitrary external ledger overrides and deleted temporary
fixtures as coverage limitations where applicable. Never convert a scoped
negative search into a fleet-wide clean bill. Preserve original events; if a
safe append-only correction is unsupported, propose the exact invalidation and
downstream dependency handling before mutation.
