# Council ADR Phase D threat model

Status: new requirements, authored 2026-11-09. These are not pre-existing mandates of docs/decision-council-integration-2026-11-05.md. That ADR defines Phase D only as "Security/failure testing" with exit "Threat-model mitigations verified; limitation ledger updated."

Terminology, corrected without rewriting historical evidence:

- ADR Phase D is this document: security and failure testing.
- ADR Phase E is runtime qualification plus a separately authorized bounded live canary. Open question 6 is unanswered by the ADR. A proposal lives in docs/council-phase-e-canary-proposal.md and is not authorized.
- Historical workflow comments that say "Phase D repair slice" mean earlier verdict-shape tests. They are not this threat model. Those comments were not rewritten.
- Mission packets that called live-canary authorization "Gate D" used the wrong name. That label is retired. The packets themselves were not edited, so old evidence still shows the old words.

Host of the verification below: Darwin arm64. Offline synthetic transports only. No provider call.

## Trust boundaries

1. Parent process environment to HermesCliAdapter._env. Attestation still uses a parent copy with an ambient-inference denylist (launcher.py _env).
2. Parent process environment to the seat child. The inference spawn no longer uses that copy. app/seat_credentials.py builds an allowlist.
3. Isolated seat home ($HERMES_HOME for the child) versus the persistent profile home. Identity files (SOUL.md, honcho.json) are copied by _bind_spawn_identity. Credential files, if declared, go only under .seat-credentials and are removed when the spawn call returns.
4. CouncilSeatDispatch's injected launcher versus HermesCliAdapter.launch. Dispatch still accepts any callable. HermesCouncilSeatLauncher is an explicit seam, not a forced one.
5. Untrusted seat payload versus control-plane argv. Payload is serialized into the prompt argument. It does not select --provider or -m.

## Threats

### T1 parent-env leak into the seat child

Asset: undeclared secrets in the parent environment. Boundary: 2.
Scenario: os.environ.copy() puts SYNTHETIC_UNRELATED_SECRET into the child even though the seat contract did not name it. The pre-repair helper unsafe_parent_copy still demonstrates that leak. Production spawn uses build_spawn_env.
Existing control before this change: denylist _AMBIENT_INFERENCE_ENV only.
Mitigation: baseline names plus contract.allowed_env values only.
Verification: tests/test_seat_credentials.py::test_spawn_env_does_not_inherit_undeclared_secret and test_launch_propagates_only_declared_synthetic_credential.
Pass: unrelated secret absent from the inference env. Fail: any parent key outside the baseline and the contract appears.
Residual: none for the inference child. Profile-show env is T5, now verified.

### T2 missing required credential starts a child

Asset: fail-closed admission. Boundary: 2.
Scenario: a declared required name is absent, and the child starts, then fails inside Hermes with "No usable credentials" after a process exists.
Mitigation: validate_seat_credential_contract before write_isolated_fallback_session and before process_runner.
Verification: test_launch_refuses_missing_credential_before_any_process. Error contains the variable name and not the synthetic value.
Pass: process_runner call list is empty. Fail: any cmd is recorded.
Residual: scope none has no required names, so existing offline launches still spawn. That is not a claim that credentials exist. A live canary must not use scope none.

### T3 credential file survives the spawn or is world-readable

Asset: synthetic credential bytes on disk. Boundary: 3.
Scenario: a seat.token file mode is broader than 0600, or a second seat home can read it, or the file remains after launch returns.
Mitigation: write under isolated_root/.seat-credentials with mode 0600, single path segment only, unlink in a finally around _run.
Verification: test_two_seats_do_not_share_credential_files and the cleanup assertion in test_launch_propagates_only_declared_synthetic_credential.
Pass: mode 0600, other home lacks the file, file gone after launch returns.
Residual: a crash between write and the finally can leave the file in the workspace. The workspace is the launch workspace, not the persistent profile. Cleanup is now anchored to the creation directory file descriptor (merged PR #33), so a rename or substitution of the path after creation does not redirect unlink. No shred beyond unlink.

### T4 identity bytes treated as credentials, or credentials copied from the parent store

Asset: SOUL.md / honcho.json versus secrets. Boundary: 3.
Scenario: _bind_spawn_identity copies the whole profile, including a parent .env or auth.json, into the isolated home.
Existing control: _bind_spawn_identity copies only SOUL.md and honcho.json.
Mitigation: credential files come only from contract.files. No parent-store copy was added.
Verification: code inspection of _bind_spawn_identity; write_seat_credential_files refuses a non-basename.
Pass: no code path copies auth.json or .env. Fail: a new copy of those names.
Residual: if a future caller puts secret bytes into SOUL.md, this control does not detect that.

### T5 attestation child inherits the parent environment

Asset: secrets in os.environ. Boundary: 1.
Scenario: hermes profile show is started with _env(), which copies the parent environment.
Mitigation: _env() is now a baseline-name allowlist (BASELINE_ENV_NAMES plus HERMES_HOME), with newline and NUL value rejection. It no longer copies the parent environment.
Verification: tests/test_seat_credentials.py::test_profile_show_env_is_allowlisted_no_parent_secret_inheritance. Full suite 931 passed, 2 skipped, 2 xfailed on the final bytes.
Pass: an unrelated parent secret and a synthetic AWS key are absent from the profile-show env; PATH and HERMES_HOME are present. Existing profile-show tests still pass.
Residual: none known for the attestation child. A future caller that needs another variable for profile resolution must add it to BASELINE_ENV_NAMES explicitly.

### T6 dispatch can bypass the credential seam

Asset: the admission guarantee. Boundary: 4.
Scenario: CouncilSeatDispatch is constructed with a scripted launcher that ignores SeatCredentialContract.
Mitigation: HermesCouncilSeatLauncher is available and tested. Dispatch was not changed to require it, because the injected callable is the existing offline contract.
Verification: test_council_seam_refuses_before_inference_and_ignores_payload_flags.
Pass for the seam class. Fail if that class calls process_runner when the required value is missing.
Residual: bypass remains possible. Not a passed control for every dispatch caller.

### T7 stream-json seat launch is treated as implemented

Asset: seat readiness evidence. Boundary: canonical argv.
Scenario: a test sees a stub stdout and reports stream-json readiness.
Mitigation: canonical argv remains hermes -p PROFILE --provider P -m M -z PROMPT. The seam rejects stdout that has no usage object instead of inventing tokens.
Verification: test_launch_propagates_only_declared_synthetic_credential asserts stream-json and --format are absent. test_council_seam_does_not_invent_usage.
Pass: those assertions. This does not pass stream-json qualification.
Residual: stream-json parsing, per-seat readiness, and malformed stream recovery are not implemented.

### T8 untrusted payload selects the provider

Asset: approved provider/model. Boundary: 5.
Scenario: payload contains "--provider": "evil-provider" and the child argv changes.
Mitigation: provider and model are constructor arguments. Payload is JSON in the final prompt slot.
Verification: test_council_seam_refuses_before_inference_and_ignores_payload_flags on the refusal path, and test_council_seam_does_not_invent_usage checks the approved provider flag on the spawn path.
Pass: argv provider is the approved value.
Residual: the prompt itself can still contain the words "--provider". That is data, not an argv flag, for this command shape.

### T9 secret appears in captured stdout

Asset: synthetic secret values. Boundary: LaunchResult.captured_stdout.
Existing control: redact() replaces declared contract secrets first (longest first), then strips sk- tokens, AKIA keys, Bearer tokens, and private-key blocks.
Verification: test_redact_strips_synthetic_secret_from_child_stdout and the declared-secret redaction tests in tests/test_seat_credentials.py (merged PR #33).
Pass: captured stdout and stderr do not contain synthetic sk- or declared contract values, including a tail after the token in a composite string.
Residual: a secret that matches neither the declared contract nor _SECRET is not stripped by redact(). The council seam additionally replaces contract values in credential-unavailable errors. Other blocker errors do not echo child stderr through that seam; they pass the blocker code only.

### T10 monetary ceiling is not enforced

Asset: spend. Boundary: budget.
Existing control: credential_attempt_exhausted closes a same-attempt retry after a launch. cost_ceiling in the council session is a token estimate. currency_value is null in the duo fixture.
Mitigation: none added. A unit test of that attempt lock would not be monetary enforcement.
Residual: live spend is not stopped by this candidate.

### T11 process cleanup is not production process control

Asset: descendant processes. Boundary: cancel_managed and the offline harness.
Existing control: the merged harness classifies tested macOS observations. It does not qualify Linux PID-1 zombies or production kill.
Mitigation: none added. This slice does not signal unrelated processes.
Residual: unchanged from the merged harness limitations.

### T12 offline test reaches a provider

Asset: the no-live-call boundary.
Scenario: a test invokes hermes or a network client.
Mitigation: process_runner is a synthetic in-process callable. Tests do not set a real hermes_bin execution.
Verification: inference_count and calls are asserted on the recording transport. No network assertion harness was added.
Pass for these tests: the recording transport is the only runner.
Residual: a future test that forgets process_runner would execute the real binary. Not scanned repo-wide in this slice.

## Phase D exit reading

Threat-model mitigations verified, for the controls this document marks verified: T1, T2, T3 with creation-directory-anchored cleanup, T4, T5, T8, T9 including declared contract secrets.
Not verified, and therefore not accepted without explicit operator risk acceptance: T6 as a universal dispatch gate (the injected callable remains the offline test contract; no production caller constructs CouncilSeatDispatch today, and no shipped production path bypasses the seam), T7 as a stream-json interoperability claim (the implemented protocol is verified; a future protocol is not), T10 monetary enforcement (attempt locks and token estimates are not currency enforcement), T11 Linux process control (requires pinned Linux runtime, Phase E), T12 as a repo-wide no-live-call guarantee (fakes are used in the credential and council paths; no repo-wide scanner was added).
Durable attempt fencing across restart is verified offline (merged PR #33): schema-fence events, closed/uncertain attempts not re-fenceable, malformed records fail closed. Historical-binary compatibility is reasoned from current replay source, not executed against an old runtime binary; that evidence limit stands.
Phase D passes for the verified controls above. The remaining items are residuals with named ownership, not silent relabeling. Whether the operator accepts the T6/T7/T10/T11/T12 residuals as Phase D residuals rather than blockers is the operator's explicit decision; no reviewer can make it.
