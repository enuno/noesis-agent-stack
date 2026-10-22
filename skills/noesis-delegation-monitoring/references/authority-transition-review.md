# Authority Transition Review Matrix

Use this reference when a candidate changes leases, attempt epochs, acceptance, review invalidation, or optimistic concurrency.

## Review order

1. Freeze the exact commit, changed-file hashes, digest recipe, ledger hash, and complete RED/intermediate/GREEN chronology.
2. Trace every permission-dependent action from public control-plane entrypoint to persistent write. List actor input, required epoch/version, release/revocation checks, and event emitted.
3. Prove one-way release: after candidate submission or equivalent release, worker start/resume, consume, observe, renew, and resubmit remain denied until an authority-owned new-attempt transition persists a fresh epoch.
4. Prove new-attempt authority: workers cannot increment an epoch by omitting a fence, changing a candidate, replaying legacy records, or repeating an idempotent request. The grant must bind current version, assignee, and intended candidate context and invalidate old reviews.
5. Prove optimistic concurrency at the real boundary:
   - stale deep-copied snapshot;
   - mutable object returned by `get()`;
   - two controller/store instances sharing one ledger;
   - two processes sharing one ledger;
   - accept versus candidate mutation;
   - review versus grant;
   - budget mutation versus release/revocation.
6. Restart every winning/losing outcome and verify replay preserves the same authority state and candidate.
7. Probe malformed and legacy data: missing fields, booleans-as-integers, floats, negatives, timezone-naive timestamps, malformed revocation, duplicate/out-of-order records. Malformed presence fails closed; absence remains readable but grants no new authority.
8. Only after focused probes pass, run affected integration suites and the complete relevant suite. Preserve every failed run in the receipt.

## Acceptance table

| Property | Passing evidence | Common false positive |
|---|---|---|
| Mandatory epoch fence | Omission/stale/future/malformed values fail after restart | Tests pass only when callers voluntarily supply the fence |
| Explicit new attempt | Only authority grant increments epoch and clears release | Different candidate or worker start implicitly increments |
| One-way release | Reviews and worker calls cannot revive permission | Non-pass review returns to `running`, then start clears release |
| Atomic CAS | Losing process changes neither disk nor memory | File lock protects append but compares stale per-instance cache |
| Candidate-bound reviews | New attempt/candidate clears old reviews on replay | In-memory list cleared but stale writer restores it |
| Legacy compatibility | Old record reads without gaining authority | Missing epoch treated as permission to mint epoch 1 |

## Receipt requirements

Bind the verdict to the exact candidate digest. Separate implementer-reported chronology from reviewer-reproduced evidence. State what was inspected, executed, and not assessed. If the bounded repair budget is exhausted, require a materially changed design proposal rather than another local patch.