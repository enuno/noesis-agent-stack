# Verification boundaries for routing and durable execution

Use this matrix when designing regression coverage or judging a milestone.
These are required checks, not claims that existing code implements them.

| Claim | Required evidence | Insufficient substitute |
|---|---|---|
| No duplicate execution | Counting launcher test across duplicate calls, restart, and uncertain launch intent | One task ID or one ledger contract |
| Crash-safe launch | Assignment and launch intent durable before side effects; explicit reconciliation for unknown handles | Recording running state after launch returns |
| Quarantine survives restart | Quarantine written via a replayed path (task mutation, or a control-event type the replay handler explicitly folds into effective state); reload and verify the quarantined task is still blocked from admit/dispatch | Appending a control event the replay handler ignores — durable on disk but never restored into any field the control plane checks |
| Same-process quarantine effective | After append_control_event("quarantine", ...), the SAME live store instance denies admission and dispatch without requiring a restart/replay cycle | Only testing with a fresh TaskStore instance; append_control_event that writes JSONL but never updates the in-memory quarantined_tasks set |
| Production quarantine path wired | Every production failure path that should quarantine calls the canonical writer (append_control_event with event="quarantine") and fails closed if that write fails; tests drive the production handler, not a test-side event injection | Tests that call append_control_event directly and assert the gate — this proves the gate works when fed, not that the production path feeds it |
| Malformed quarantine state fails closed | Missing, null, or non-string task_id on a quarantine event sets replay_error and denies both admission and dispatch; test asserts the deny, not merely that replay continues | Ignoring malformed quarantine records and continuing with replay_error is None; a stripped task_id silently drops the quarantine while admitting and dispatching |
| Duck-typed gate methods fail closed | Adapter/integration fails closed when a required gate method (e.g. is_quarantined) is absent on the store; no silent skip | Duck-typed method check that treats absence as "no quarantine" and admits |
| Process exit status captured | Every cited test run captures the real shell exit status (e.g. bash -c '...; echo EXIT:$?') — pytest summary alone is not process-status evidence | Asserting exit 0 from a pytest summary line when no captured $? exists; zsh PIPESTATUS is not portable — use bash |
| Single authority | Enumerate all writers/readers; legacy store cannot independently change lifecycle; projection regenerated from authority | Adding a projection export method |
| Review gate enforced | Negative tests for BLOCKED, REQUEST_CHANGES, missing/unknown verdicts through review and acceptance handlers | Happy-path PASS/APPROVED tests |
| Acceptance is exclusive | Audit and test every completion API, including legacy succeed and direct mutation paths | A new accept method with checks |
| Revision binding | Reject changed digest even with reused revision label; invalidate affected reviews and approval evidence | Comparing revision label alone |
| Independent/authenticated review | Bound authorized reviewer session and reviewed artifact; verify actor at the trusted boundary | Different sender/profile strings in payload |
| Safe retry/cancellation | Confirm prior termination or enforced isolation; uncertain cleanup prevents conflicting reuse | Lease expiration or process timeout alone |
| Budget control | Atomic shared reservation before admission, bounded attempts/sessions/deadline, explicit partial/unknown usage | Counters checked only at acceptance |
| Model-facing tool exposure | Real loader and final schema assembler; exactly one valid schema; disabled/invalid cases; isolated profile | Registry entry or direct handler call |
| Startup warning diagnosed | Reproduce actual warning with controlled cache/loading order, then inspect final inventory | Cache contains toolset after discovery |
| Live routing canary | Model invokes real dry-run tool through normal entrypoint with effective profile/lane provenance | Profile-show or mocked adapter |
| Deployed and observed | Exact affected service/config, actual activation, persistent-entrypoint smoke, measured observation interval | Installed files or CLI-only test |

## Failure-injection order

1. Persist assignment, interrupt before launch, reload, and verify safe disposition.
2. Interrupt after launch intent but before runtime handle persistence; require
   reconciliation instead of treating missing acknowledgment as permission to retry.
3. Replay duplicate results and stale task versions/epochs; verify no mutation.
4. Change candidate content; require renewed ordered reviews.
5. Interrupt between review and acceptance; reload without inventing acceptance.
6. Interrupt cancellation before termination confirmation; preserve partial
   artifacts and block workspace reuse.

Use real persistence and transition handlers with a counting/failing adapter.
Keep synthetic fixtures and assertions separate from live evidence. Do not
claim exactly-once external execution without an adapter-level guarantee.
