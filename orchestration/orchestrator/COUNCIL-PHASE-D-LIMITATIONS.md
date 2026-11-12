# Council Phase D limitation ledger

Status: closing set for the ADR Phase D / Phase E rollout. Records what Phase D verifies on
the offline candidate, what stays open, and which ADR items Phase D does not attempt.
No live canary, no credential hydration, no gateway restart, and no Phase E activation are
part of this ledger.

## Controls

| Control | Status | Evidence | Owner |
| --- | --- | --- | --- |
| T1 parent-env leak into the inference child | Closed | `build_spawn_env` baseline allowlist plus declared contract values only; `test_spawn_env_does_not_inherit_undeclared_secret`, `test_launch_propagates_only_declared_synthetic_credential` | Hermes runtime adapter |
| T2 missing required credential starts a child | Closed on the explicit-contract path | `validate_seat_credential_contract` before any spawn; `test_launch_refuses_missing_credential_before_any_process` | Hermes runtime adapter |
| T3 credential file survives the spawn, or cleanup follows a renamed path | Closed | mode 0600, single path segment, unlink anchored to the creation directory file descriptor; `test_two_seats_do_not_share_credential_files`, `test_cleanup_follows_creation_directory_not_later_path`, `test_write_failure_cleanup_keeps_creation_directory_fd` | Hermes runtime adapter |
| T4 identity bytes treated as credentials, or credentials copied from the parent store | Closed | `_bind_spawn_identity` copies only SOUL.md and honcho.json; credential files come only from contract.files; `write_isolated_fallback_session` refuses path traversal | Hermes runtime adapter |
| T5 attestation child inherits the parent environment | Closed | `_env()` is a baseline-name allowlist with newline/NUL rejection; `test_profile_show_env_is_allowlisted_no_parent_secret_inheritance` | Hermes runtime adapter |
| T6 dispatch bypass of the credential seam | Residual, named | `HermesCouncilSeatLauncher` is the governed seam and is tested; the injected callable remains the offline test contract; no production caller constructs `CouncilSeatDispatch` today. Universal enforcement would break the offline contract. Production wiring is Phase E activation work. | Activation owner |
| T7 stream-json readiness | Residual, named | Canonical argv shape is verified; a stub stdout without a usage object is rejected, not converted into invented tokens. A future stream-json protocol is not claimed. | ADR runtime integration owner |
| T8 seat claims usage without canonical fields | Closed | bool/type/negative rejection, missing-field refusal, `cost_ceiling` is a token estimate, `currency_value` is null in fixtures | Hermes runtime adapter |
| T9 secret in captured stdout or stderr | Closed for declared and `_SECRET`-shaped values | declared contract secrets replaced first (longest first), then `_SECRET` regex; composite-string tails covered; `test_redact_strips_synthetic_secret_from_child_stdout` and declared-secret redaction tests in `test_seat_credentials.py` | Hermes runtime adapter |
| T10 monetary ceiling | Open, ADR open question 1 | `credential_attempt_exhausted` is an attempt lock, not currency enforcement; no live spend control. A unit test of the lock is not monetary enforcement. | ADR owner, before any live canary |
| T11 production process control | Open, Phase E scope | Tested observations are from a macOS offline harness; Linux PID-1 zombies and production kill are not qualified | Phase E harness owner |
| T12 repo-wide no-live-call guarantee | Residual, named | Credential and council paths use synthetic recording transports only; no repo-wide scanner was added; a future test that forgets `process_runner` would execute the real binary | Test harness owner |
| Durable attempt fencing across restart | Closed | schema-fence events replayed through the authoritative TaskStore; closed/uncertain attempts are not re-fenceable; malformed records fail closed; `tests/test_credential_attempt_fence.py`, `tests/test_fallback_denial.py` | Orchestrator runtime |

## Exit reading

Every row above has an owner and evidence. No row is silent, and none was relabeled to
make the count look clean.

Phase D exit "threat-model mitigations verified; limitation ledger updated" is satisfied
for T1, T2, T3, T4, T5, T8, T9, and durable attempt fencing, on the merged source plus this
qualification change, verified offline (full suite 931 passed, 2 skipped, 2 xfailed on the
final bytes).

Open or residual rows are T6 (dispatch seam enforcement at activation), T7 (future
protocol), T10 (monetary enforcement, ADR open question 1), T11 (Linux process control,
Phase E), and T12 (repo-wide no-live-call scanner). These are not relabeled as passed.
The operator's explicit risk-acceptance decision on these residuals is recorded verbatim
below.

## Operator acceptance (recorded verbatim)

Bound to: merge commit e0a6fdb107a52886504aea883628d42324dca5da (PR #35, head
0d73820c88b3f510703a44e8481fa03069980a7c); candidate digest
0e6f9cef9d665e4f1d979d96835ecab57d285835503dc34550246c5932d3a287; final
file-tool review receipts deleg_0fcf313c (round 1, APPROVE x2) and
deleg_81c96984 (round 2, APPROVE x2); post-merge run 43146449328 (success);
this ledger; docs/council-phase-d-threat-model.md.

---

HUMAN ACCEPTANCE — COUNCIL PHASE D

I accept Council Phase D security/failure qualification for the evidence
published through PR #35 and merged as:

e0a6fdb107a52886504aea883628d42324dca5da

This decision is bound to the published candidate, its final review receipts,
the threat model, the limitation ledger, and the reported successful
post-merge run 43146449328.

I accept the following residuals for Phase D exit only:

- T6: universal dispatch-seam enforcement remains an activation-time wiring
  requirement. This acceptance does not authorize a production path that
  bypasses required admission or credential controls.

- T7: stream-json is not qualified. Acceptance covers only the implemented
  protocol and its verified behavior.

- T10: monetary enforcement remains unresolved. Attempt fencing is not a
  currency ceiling. This acceptance authorizes no live spending.

- T11: Linux production process control remains unqualified and requires
  separate evidence against the pinned target runtime.

- T12: a repository-wide no-live-call scanner has not been built. The evidence
  establishes the tested fake-transport boundaries, not a repo-wide guarantee.

I acknowledge these evidence limits:

- Historical-binary compatibility was reasoned from source, not established
  by executing the historical binary.
- The duplicate-admission lock test has a sequential-schedule limitation and
  does not establish exhaustive concurrent-schedule coverage.

These residuals remain open and visible. They are not reclassified as
verified controls.

Disposition:
Phase D accepted with the named residuals and evidence limits.

This is not installation, activation, deployment, live attachment, Phase E
qualification, provider authentication, a live canary, or spending approval.
It does not authorize Switchyard, delegation-gate, or Bitwarden changes.

---

## Historical evidence limits that still stand

- The fence compatibility claim for an old runtime is reasoned from current replay source,
  not executed against a historical binary.
- The duplicate-admission lock test can pass under a sequential schedule; interleaving
  dependent.
- The full suite was run before the final documentation edits; the documentation edits do
  not change code or tests.
