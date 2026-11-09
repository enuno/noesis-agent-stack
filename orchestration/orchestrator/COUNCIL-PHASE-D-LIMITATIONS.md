# Council Phase D limitation ledger

New ledger for ADR Phase D (security and failure testing). This is not an update of orchestration/orchestrator/DELEGATION-PROTECTIONS.md, which remains the delegation-handoff ledger and was not rewritten.

Measured on Darwin arm64, offline, against the candidate that adds app/seat_credentials.py and the launcher spawn-env change. No live provider call. No Linux /proc run. No production credential store was read.

## Verified in this candidate

| Control | Evidence | Limit of the evidence |
|---|---|---|
| Inference spawn does not copy undeclared parent secrets | test_spawn_env_does_not_inherit_undeclared_secret; test_launch_propagates_only_declared_synthetic_credential | Synthetic values only. Not a scan of a live parent environment. |
| Missing required contract value does not start a process | test_launch_refuses_missing_credential_before_any_process | Applies when a SeatCredentialContract with required_env is passed. scope none still spawns. |
| Seat credential files are mode 0600, not shared, and removed after the spawn call returns | test_two_seats_do_not_share_credential_files; cleanup assertion in the propagation test | Unlink, not secure delete. A crash before the finally can leave the file in the launch workspace. |
| Identity bind does not gain a parent credential-store copy | inspection of _bind_spawn_identity; write_seat_credential_files accepts basenames only | Does not prove a future caller will not put secrets in SOUL.md. |
| Payload does not select --provider | council seam tests | Prompt text can still contain those words. |
| sk- shaped stdout is redacted | test_redact_strips_synthetic_secret_from_child_stdout | Other secret shapes are not covered by redact(). |

## Not verified

| Item | Why it remains open |
|---|---|
| Profile-show parent-env inheritance | _env() still copies the parent environment for attestation. Not changed. |
| Every CouncilSeatDispatch caller uses the credential seam | Dispatch still accepts any injected callable. |
| stream-json seat launch and readiness | Canonical argv is still -z. No stream parser was added. |
| Monetary enforcement | Attempt-budget lock is not a currency ceiling. |
| Production process control | No change. macOS harness observations are not Linux PID-1 qualification. |
| Live provider authentication | Offline synthetic values are not credentials a provider will accept. |
| Real resolver hydration (keyring, Bitwarden, profile .env) | Intentionally not copied. A live canary must supply values through the contract at execution time. This candidate does not do that. |

Phase D exit is not met for the unverified rows. No operator risk acceptance is claimed for them.
