# Council Phase E canary proposal

PROPOSED — NOT AUTHORIZED FOR EXECUTION.

This answers ADR open question 6 with conservative defaults. It does not grant the separate operator authorization the ADR requires. Do not run it.

## Why these defaults

The implemented offline system can refuse a missing explicit credential, can pin provider and model, and cannot enforce a currency ceiling. The smallest canary is therefore one seat, one harmless reply, a token cap, and a manual abort. Two-seat duo mode would double spend without adding a security proof this candidate lacks.

## Proposed run

- Profiles: noesis-skeptic only. One seat. noesis-architect is not included.
- Task: reply with the single word pong. No tools. No file writes. No repository commands.
- Lane: the operator's already approved pair for that profile. Fallback policy deny. Isolated empty fallback chain, as HermesCliAdapter.launch already requires.
- Credential source: SeatCredentialContract scope api-key-env, one required env name chosen by the operator at execution time. Values supplied in process memory for that call. Not a copy of the parent environment. Not a copy of auth.json or .env into the isolated home.
- Request limit: one launch.
- Token limit: max_output_tokens 64. If the seam cannot observe usage, abort. Do not invent zeros.
- Concurrency: 1.
- Wall clock: timeout_s 60 and remaining_lease_s 60. No retry after timeout.
- Monetary ceiling: 1 USD proposed. Actual enforcement in this repository is absent. currency_value on the council session fixture is null. Until a hard stop exists, the operator must be able to abort the provider session manually and must accept that this codebase will not stop spend by itself.
- Expected artifacts: LaunchResult blocker or captured stdout digest, credential-scope category (not the value), process id if a child started, cleanup_state. No secret values in the report.
- Abort: credential_unavailable, fallback_unenforced, timeout, nonzero exit, stdout that is not the single word pong, any second launch attempt.
- Recovery: remove_seat_credential_files on the spawn finally path; cancel_managed only for the recorded pid/pgid of that child. Do not kill by process name.
- Billing reconciliation: compare the provider invoice for that hour to the single request. This repository cannot do that comparison.
- Platform: a Darwin result would not be Linux process-control evidence. Do not claim it is.

## Still missing before execution

1. Explicit operator authorization naming this proposal, the profile, the provider/model pair, and the 1 USD ceiling.
2. A monetary stop, or a written acceptance that the stop is manual and outside this repository.
3. A credential value supplied at execution time through the contract, without logging it.
4. Confirmation that scope none will not be used.
5. stream-json seat readiness is not a prerequisite for this one-shot -z proposal, and this proposal does not establish it.

Executing this file is not authorized.
