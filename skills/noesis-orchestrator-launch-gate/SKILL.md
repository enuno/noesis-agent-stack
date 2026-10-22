---
name: noesis-orchestrator-launch-gate
title: "Noesis Orchestrator Launch-Gate Repair"
description: "Bounded remediation of the launch boundary: persist authoritative contract_revision/baseline, derive verification_pending from LaunchResult, enforce fail-closed per-launch authorization, child-side profile attestation, and bounded same-provider credential attempts. Before any claim: compile, targeted regressions, full suite."
version: "1.0.0"
last_updated: "2026-10-09"
---

# Noesis Orchestrator Launch-Gate Repair

## Overview

Repair the launch boundary in `orchestration/orchestrator/app/launcher.py`, `control_plane.py`, `models.py`, and `store.py` when the launch path lacks:

1. Authoritative contract_revision/baseline persisted on `TaskContract.Delegation` and passed into launch (F1).
2. verification_pending derived from LaunchResult, not hard-coded (F2).
3. Mandatory fail-closed authorization at the real inference boundary before child spawn, and a child-side in-process attestation of the launched isolated profile + effective fallback chain (F3 + F4).
4. Bounded same-provider credential attempts via a durable counter/block state, distinct from provider fallback and wall-clock timeout (F5).

Never: edit Hermes core source, monkey-patch, change provider/policy, or make persistent config changes to installed Hermes. Keep every edit inside the five allowed files and targeted regressions.

## When to Use

- Re-running this repair after the frozen digest changed and F1–F5 are still unimplemented.
- Adding regression tests that exercise the real `HermesCliAdapter.launch` path through the orchestrator entrypoint.
- Before claiming any F1–F5 outcome or emitting a new completion digest.

## Pre-checks (fail-closed)

- Confirm the checkout HEAD matches a known-good revision; do not act on an unverified tree.
- Confirm the allowed-file scope: `control_plane.py`, `launcher.py`, `models.py`, `store.py`, and `tests/test_*.py` only.
- Confirm `_authorize_launch_request` and `_credential_attempt_consumed` are actually called on the real launch path, not only in synthetic tests.
- Confirm no child/provider starts occur when authorization is absent or denied.

## Procedure

### 1. Authoritative contract_revision / baseline (F1)

1. Add `contract_revision` and `baseline` to `Delegation` in `models.py` and serialize them in `to_dict()` in `store.py`. Do not make them optional caller assertions.
2. In `control_plane.route_and_launch` (non-dry-run), derive the authoritative values **before** reservation and persist them through `store.reserve_launch` and the launch reservation.
3. Pass the persisted values into `launcher.launch` as `contract_revision` / `baseline`, and carry `task_id`, `attempt_id`, `contract_revision`, `assignment_epoch`, and `baseline` into every `LaunchResult` branch.
4. End-to-end regression: drive a real non-dry-run launch through `route_and_launch` and inspect the persisted `launch_reservation`/`Delegation` fields equal the derived values.
5. Replay regression: a successful exit with no collected artifact must show `verification_pending=False` with `candidate_digest=None`; a collected artifact shows `True` with a non-empty `candidate_digest`.

### 2. verification_pending consistency (F2)

1. Remove any hard-coded `verification_pending=True` in `control_plane.py` and any hard-coded `True` in `launcher.py`.
2. Persist `launch.verification_pending` (derived as `verified_digest is not None`) together with `candidate_digest`, `artifacts`, `collection_error`, `stdout_digest`, and attempt identity.
3. Verify by behavioral replay, not file inspection.

### 3. Mandatory fail-closed inference authorization at the real boundary (F3)

1. Add a single authorized authorizer `_authorize_launch_request` that refuses when authorization is absent/denied **before** the child starts, using the persisted approved pair + effective fallback state + durable attempt counter/block state.
2. Call it at the real `launcher.py:launch()` boundary immediately before `_run` starts the child.
3. If installed Hermes does not expose the necessary mechanism inside authorized Noesis integration code, emit a BLOCKER with the exact missing path + citation, and a separately scoped core/integration proposal. Do not monkey-patch or silently edit core.
4. Verify zero child starts on a denied authorization with the real adapter path.

### 4. Child-side profile/config attestation (F4)

1. Re-open `$HERMES_HOME/profiles/<id>` and read back the effective profile identity and the effective fallback chain **before** the first inference request, after the isolated home is written and re-read.
2. Require the re-attested loaded profile to equal `profile_id`; require the re-read fallback chain to be `[]`.
3. Verify by child-side readback regression that detects identity/chain mismatch, not just file-level parser inspection.

### 5. Bounded same-provider credential attempts (F5)

1. Add a durable child-level attempt budget: a counter + block state keyed by provider|model|task_id, with an explicit block once exhausted.
2. Do not conflate this with the provider fallback chain or with wall-clock timeout.
3. Verify with an offline multi-credential double: after a simulated pool/billing failure, a second credential request for the same attempt must be zero.
4. Cite the exact installed-Hermes mechanism used (e.g., `cron/scheduler.py` and `run_agent.py` fallback-pool references) in the completion packet.

## Files (allowed changes only)

- `orchestration/orchestrator/app/launcher.py`
- `orchestration/orchestrator/app/control_plane.py`
- `orchestration/orchestrator/app/models.py`
- `orchestration/orchestrator/app/store.py`
- `orchestration/orchestrator/tests/test_*.py`

## Exclusions

- Hermes core source edits outside the allowed scope; no monkey patches; no file-only proof; no timeout-as-bound; no unenforced success flag.
- No provider promotion; no deployment; no commit/push; no persistent config change; no credential changes.

## Regressions (run in order)

1. Compile: `uv run --no-sync python -m compileall -q orchestration/orchestrator/app`
2. Targeted F1/F2 replay test(s) through `route_and_launch` + replay.
3. F3 authorization denied → zero child starts.
4. F4 child-side readback passes and mismatch fails closed.
5. F5 dual-credential double → zero second credential request.
6. Full suite: `uv run --no-sync pytest orchestration/orchestrator/tests -q`
7. `git diff --check`

## Output Packet

Return the exact completion-packet location with:

- Implementation and enforcement mechanism changes.
- Changed files and complete diff (scoped to allowed files).
- Per-file hashes (sha256) of edited files.
- RED/GREEN and suite results.
- Compatibility/migration considerations.
- Remaining blockers and live-verification requirements.
- Provenance and child-process cleanup.
- `not_self_approved: true`.

## Verification Checklist

- [ ] `contract_revision` and `baseline` persisted on `Delegation` and passed into launch.
- [ ] `verification_pending` derived from `LaunchResult.verification_pending`; replay shows no-candidate = False, collected = True.
- [ ] `_authorize_launch_request` called before child spawn; blocked when absent/denied.
- [ ] Child-side re-attestation runs before first inference; identity/chain mismatch fails closed.
- [ ] Durable same-provider credential attempt counter/block state survives a billing failure without a second credential request.
- [ ] compileall, targeted regressions, and full suite all exit 0.
- [ ] `not_self_approved: true` in the packet.
