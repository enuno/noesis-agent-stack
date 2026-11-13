# Council Phase E bounded canary contract — DRAFT, NOT EXECUTABLE

Status: DRAFT with UNRESOLVED fields marked. This contract is not executable
until every UNRESOLVED field is resolved and the exact human authorization
at the bottom is given. Nothing here retrieves credentials, contacts a
provider, or launches a worker.

Derived from `docs/council-phase-e-canary-proposal.md` (defaults unchanged)
and `docs/council-phase-e-spend-control.md` (T10 decision D1/D2/D3).

## Objective and exact acceptance evidence

- Objective: prove one governed seat can complete one launch end to end on
  the pinned runtime with credential admission, attempt fencing, budget
  gate, and cleanup all observed.
- Acceptance evidence: LaunchResult blocker code (if refused) or captured
  stdout digest matching the single-word reply; credential-scope category
  (never the value); recorded pid/pgid if a child started; cleanup_state;
  attempt fence state `closed` in the authoritative ledger after the run;
  observer usage for exactly one request. No secret values anywhere.

## Approved profile identities and compatible revisions

- Profile: noesis-skeptic only. One seat. (noesis-architect excluded per
  proposal.)
- Compatible revision: agent-stack at the Phase E activation revision —
  UNRESOLVED until activation names it; must include PR #33 and PR #35
  (fencing, T5) and the T6/T10 readiness wiring.

## Task/seat/round/attempt identities

- parent_task_id: UNRESOLVED (operator-assigned UUID at execution time).
- seat_id: "skeptic-canary". round: 1. attempt id: produced by
  `HermesCouncilSeatLauncher.attempt_key(seat_id, round_n)`
  (seat_credentials.py), i.e. "<parent_task_id>|skeptic-canary|round-1|attempt-1".
- Fencing: schema-fence events through the authoritative TaskStore;
  timeout/refusal/exception settle `uncertain` and are not retried.

## Independent reviewer

- UNRESOLVED: named reviewer (Sentinel or Skeptic profile, or operator-
  mediated review per fleet convention) who was not the implementer and
  reviews the canary receipt after execution.

## Target host/environment

- UNRESOLVED: host identity. Dedicated/isolated only. If the host is Linux,
  T11 qualification (docs/council-phase-e-linux-qualification.md) must have
  passed on the pinned runtime first; a Darwin host does not satisfy T11.

## Provider/model route and privacy classification

- Route: the operator's already-approved pair for noesis-skeptic;
  UNRESOLVED until named at authorization. Fallback policy deny; isolated
  empty fallback chain.
- Privacy classification: the prompt is exactly the JSON object
  `{"ask": "pong"}` (serialized by the seam with sort_keys, so the literal
  prompt string is `{"ask": "pong"}`); the expected captured stdout is
  exactly the four bytes `pong`. No personal data, no repository content;
  the seat payload carries no operator data. The acceptance digest in the
  receipt is taken over those four bytes.

## Credential source and approved injection boundary

- Source: SeatCredentialContract scope api-key-env, one required env name
  chosen by the operator at execution time; value supplied in process
  memory for that call only. UNRESOLVED: the env name and who supplies it.
- Boundary: value never written to the isolated home beyond the contract's
  `.seat-credentials` file (mode 0600, unlinked in the spawn finally);
  never logged; never copied from auth.json/.env or the parent environment
  (T5 allowlist enforced).

## Limits

- Requests: 1 launch. Turns: 1. Concurrency: 1.
- Tokens: max_output_tokens 64; session ceiling estimated_tokens 64
  (budget gate refuses anything larger before inference). If usage cannot
  be observed, abort; do not invent zeros.
- Duration: timeout_s 60, remaining_lease_s 60. No retry after timeout.
- Monetary ceiling: 1 USD proposed. Enforcement mechanism: UNRESOLVED —
  must resolve T10 decision D1 (provider/account cap with evidence receipt)
  or D2 (operator accepts manual stop in writing). D3 defers the canary.

## Prerequisites and dependencies

1. T10 decision resolved (D1 or D2 recorded with the authorization).
2. Pinned runtime + revision recorded; installed revision matches the
   agent-stack revision under test.
3. T11 passed if the target host is Linux.
4. Production dispatch wiring (T6) selected and reviewed.
5. Operator authorization text naming this contract, the profile, the
   provider/model pair, the credential env name, and the monetary ceiling
   mechanism.

## Stop conditions

Abort on: credential_unavailable; fallback_unenforced; output_cap_unsupported;
timeout; nonzero exit; stdout that is not exactly the agreed single-word
reply; any second launch attempt; budget gate refusal; manual operator abort.

## Timeout and ambiguous-execution treatment

- Timeout settles the attempt `uncertain`; reconstruction must show it not
  re-fenceable; no automatic retry.
- Ambiguous execution (unknown whether the provider call happened) is
  treated as consumed: the attempt is uncertain, the round does not rerun,
  and the receipt says so explicitly.

## Cleanup, recovery, and rollback

- `remove_seat_credential_files` on the spawn finally path (creation-
  directory-anchored, PR #33).
- `cancel_managed` only for the recorded pid/pgid of the canary child.
  Never kill by process name.
- Rollback: remove the canary workspace; the canary mutates no operational
  ledger beyond its own parent task record, which is retained as evidence.

## Evidence and redaction requirements

- Receipt: launch outcome, blocker code or stdout digest, usage (observed,
  never invented), fence states, cleanup_state, credential-scope category.
- Redaction: declared contract values replaced first, then `_SECRET`
  shapes (PR #33); scan the receipt with the repo secret scanner before
  retention.

## Exact human authorization required (template — not yet given)

UNRESOLVED. The operator must state, in one message: authorization of this
contract; the named provider/model pair; the credential env name and its
supplier; the monetary ceiling mechanism (D1 or D2); the target host; and
the parent task UUID. A draft with unresolved fields is not executable.
