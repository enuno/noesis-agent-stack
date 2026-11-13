# Council Phase E readiness matrix

Status: PREPARED — NOT AUTHORIZED FOR EXECUTION. Prepared offline under the
post-Phase-D closeout mission; nothing here is installed, activated, or
launched. Phase D acceptance (d9217027f7829a7bc8c56bfbdee9ae1d832683ec) is
not modified by this document.

Current code revision for every row: main at d9217027 plus the offline
readiness branch `feat/phase-e-readiness` (T6/T10 code, tests
test_phase_e_readiness.py). Full suite on that branch: 937 passed,
2 skipped, 2 xfailed.

| Item | Current state | Acceptance criterion | Owner / repo | Offline evidence | Target-runtime evidence still needed | Authorization required | Rollback / stop behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T6 production dispatch seam | `CouncilSeatDispatch.production(...)` builds `HermesCouncilSeatLauncher` over the runtime adapter; `require_governed_launcher=True` rejects injected callables on the production path only; offline tests keep the injected-callable contract with the default False. Fencing and budget enforcement are non-optional on the production factory. | Production path cannot bypass admission (cost-ceiling estimate, allowed routes, fencing token), credential contract, approved provider/model, attempt fencing, or pre-inference budget refusal. | Orchestrator runtime (this repo), activation owner. | 6 new offline tests: governed seam construction, injected-callable refusal, fencing-token refusal, budget refusal before inference, within-ceiling accounting, offline-contract preservation. Fake adapter only. | One activation-time wiring exercise on the pinned host proving the factory is the only production caller. | Explicit operator authorization to activate the production path (Phase E). | `abort()` / `execution_revoked` honored before every launcher call; admission failures raise before any seat work; no automatic retry after ambiguous execution (attempt fencing settles uncertain, not re-fenceable). |
| T10 spend control | Output-token layer: per-request `max_output_tokens` (pre-spawn refusal when the transport cannot enforce it) plus cumulative session gate `enforce_budget` in the dispatch adapter (projected observed + requested vs `cost_ceiling.estimated_tokens`, refusal before inference). Estimate layer: `cost_ceiling.estimated_tokens` admission. Accounting layer: observer `observe_budget` per completed round. | Hard monetary ceiling enforced before spend, with reservation semantics, concurrency treatment, refusal when enforcement is unavailable, and exhaustion stop. | Orchestrator runtime (token layers, implemented); provider/account layer (not implemented — see spend-control design doc decision request). | Offline tests for the cumulative gate; pre-spawn output-cap refusal tests (PR #33). | Live provider/account enforcement evidence: billing API, account-level spend cap, or accepted manual stop. | T10 monetary decision (design doc §Decision request) — no live spending authorized by any current artifact. | BudgetExhausted before inference; session `stop_conditions` include `budget_exhausted`; manual abort path documented in the canary proposal. An estimate, attempt lock, or post-hoc usage report is NOT a hard prevention mechanism. |
| T11 Linux process control | macOS-only offline harness observations exist (PR #33-era). No Linux PID-1, zombie, or production-kill evidence exists in this repository. | Descendant identification, timeout/cancel/termination/reaping, zombie/orphan observation, and emergency stop qualified against the pinned immutable runtime on the pinned Linux target. | Phase E harness owner (this repo docs; noesis-ansible NOT modified under this mission). | Qualification package only (`docs/council-phase-e-linux-qualification.md`): cases, fixtures, pass/fail criteria, sanitization. No Linux execution performed. | Execution on the pinned Linux target — separately authorized; not done here. | Explicit operator authorization naming target host and pinned runtime. | Emergency stop via recorded pid/pgid only (`cancel_managed`); never kill-by-name; recovery steps in the package. |
| Phase E canary | Proposal (`docs/council-phase-e-canary-proposal.md`) and bounded contract draft (`docs/council-phase-e-canary-contract.md`) exist. Contract has unresolved safety-critical fields marked UNRESOLVED; it is not executable. | Operator signs the contract naming profile, provider/model pair, credential source, monetary ceiling and its enforcement mechanism. | Operator decision; orchestrator runtime prepares evidence. | Offline contract draft with prerequisites, stop conditions, cleanup, redaction requirements. | The canary execution itself — one launch, one seat, pong reply. | Explicit operator authorization per canary contract §Authorization; monetary decision (T10) resolved or manual-stop accepted in writing. | Abort list in the proposal: credential_unavailable, fallback_unenforced, timeout, nonzero exit, unexpected stdout, second launch attempt. No retry after timeout. |
| T7 stream-json | Not qualified. Canonical argv verified; stub stdout without a usage object is refused, not converted to invented tokens. | Stream-json readiness established against a pinned protocol implementation, if ever selected. | ADR runtime integration owner. | Refusal-path tests only. | Interop evidence against a real stream-json emitter. | Separate design decision; NOT imported into the first canary. | N/A — not part of the canary contract. |
| T12 repo-wide no-live-call | Not built. Tested paths use recording fakes; `process_runner=None` real-spawn paths are refused for output-cap cases in tests. | A repo-wide boundary (e.g. conftest network/subprocess guard) covering every test module. | Test harness owner. | Fake-transport boundaries in credential/council/readiness tests. | None beyond implementation. | Routine — fold into a future test-harness slice. | N/A. |

Inherited evidence limits (acknowledged by the operator at Phase D exit, not
re-litigated here): historical-binary compatibility reasoned from source;
duplicate-admission lock test sequential-schedule dependent.

## Stage separation (explicit)

- Preparation (this matrix, the T6/T10 code, the three design docs): offline, done.
- Installation/apply: NOT authorized, not started.
- Activation (production dispatch wiring live): NOT authorized.
- Non-provider runtime qualification (Linux package execution): NOT authorized.
- Bounded provider canary: NOT authorized.
- Wider rollout: NOT authorized.
