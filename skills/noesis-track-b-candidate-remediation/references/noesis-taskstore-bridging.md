# Noesis TaskStore Bridging — Durable Facts for the Hermes Bridge

Facts about `orchestration/orchestrator/app/store.py` (Noesis checkout) that shape any
adapter bridging the Noesis TaskStore to the Hermes `DurableAttemptAuthority`.
Verified during the A6 prototype; re-check against the checkout if behavior is ever
in doubt.

## Replay folds breaker AND quarantine events

`TaskStore.replay` surfaces circuit-breaker events into `breaker_events` and folds
`quarantine` control events into a durable `quarantined_tasks` set. A malformed
quarantine record (missing/null/empty/non-string `task_id`) sets `replay_error`
and aborts the fold — fail closed: admission denies (`taskstore_replay_error`)
and dispatch denies (`RoutingBlocked launch_blocked`) whenever `replay_error` is
set. Any OTHER record type is read for forward compatibility and then dropped.

Consequences for adapter/gate work:

- `store.is_quarantined(task_id)` is the authoritative check; quarantine survives
  restart via replay. There is deliberately no automatic unquarantine and no
  release API in the store — release is manual/operator-only.
- The dispatch gate (`Orchestrator._assert_spawn_gates`) raises
  `RoutingBlocked("quarantined", ...)` immediately after its fail-closed
  replay/breaker block, so quarantine wins over every later gate (epoch, lease,
  approval) and over any healthy folded task state.
- The adapter checks quarantine BEFORE task-state and budget evaluation and denies
  `task_quarantined`. The gate is fail-closed: a store WITHOUT `is_quarantined`
  denies `task_store_quarantine_capability_missing`, and a check that raises
  denies `task_store_quarantine_check_failed: ...` — update every hand-rolled
  store double (including subprocess worker snippets) to carry the capability or
  the whole suite goes red. The adapter must still never write TaskStore state —
  quarantine RECORDING stays control-plane-owned; the adapter only denies.
- Behavior tests for quarantine need a REAL TaskStore + Orchestrator (replay
  folding and the dispatch gate are store/control-plane behavior); fake stores
  only cover the adapter-side check.

## Quarantine write path (control-plane-owned)

- The production handler `Orchestrator._quarantine_reservation` records quarantine
  as a `quarantine` CONTROL event via `store.append_control_event({task_id,
  reason})` — never as a task-state `store.put`; the durable write must succeed
  (a failed write raises, fail closed).
- `append_control_event` applies the in-memory `quarantined_tasks` effect BEFORE
  the durable write, so a failed write still leaves the current process denying
  the task while the raised exception surfaces. Quarantine payloads without a
  non-empty string `task_id` raise `ValueError` at write time (a malformed record
  would otherwise fail EVERY future replay closed via D3 replay_error).
- Quarantine events are never appended to `breaker_events`; a quarantine denial
  must be provable as code `quarantined`, not the breaker/`launch_blocked` branch.

## attempt_key composition

The Hermes ledger's `attempt_key` already folds `(ledger_id, task_id,
admitted_attempt_id)`. Distinct unsettled `attempt_key`s per task therefore equal
distinct `admitted_attempt_id`s per task — a per-task concurrent-attempt (N1) limit
reduces to counting unsettled rows `WHERE task_id = ? AND attempt_key != ?` (exclude
the caller's own replayed key). Same-key redeliveries never reach the count: they
are the idempotent-replay path.

## Budget discipline at the bridge

The Noesis `Task.request_limit` is the AUTHORITATIVE physical-attempt budget; the
TaskStore may be read for validation (task exists, not cancelled, budget present)
but the adapter must not treat TaskStore fields as its own consumption ledger.
Consumption state lives in the adapter-owned sqlite ledger (same hardening rules as
references/sqlite-ledger-hardening.md). Keep the TaskStore strictly read-only inside
the adapter — control-plane writes (quarantine, cancellation) stay control-plane-owned.

## Test interpreter discovery (cross-repo suites)

Plain `python3 -m pytest` fails with "No module named pytest" — the system python
and the Hermes tools python both lack pytest, and bounded turns forbid installs.
Two pre-existing venvs cover the two repos:

- Hermes suites: the checkout's synced test venv:
  `eval "$(cd <hermes-repo> && python3 -m pm.environments --format sh)"` then
  `"$__HERMES_TEST_PYTHON" -m pytest <suite> -v --tb=short`.
  Do not discover it by filesystem scan: the venv interpreter is a symlink (missed
  by `find -type f`), and some `.hermes` tool-cache dir names contain glob-hostile
  characters that break shell quoting.
- Cross-repo suites (imports from BOTH repos, e.g. `app.control_plane`): the
  Noesis checkout's own project venv (`<noesis-repo>/.venv/bin/python`) — it has
  pytest and every Noesis app dependency (PyYAML etc.). The Hermes test venv
  CANNOT import `app.control_plane` (no PyYAML), so a suite touching the Noesis
  control plane must run entirely under the Noesis venv (the Hermes enforcement
  module is stdlib-only and imports fine there).

Probe before choosing: run `<candidate-python> -c "import <heaviest module>"`
under each candidate interpreter with the real repo roots on `sys.path` before
committing to one — a missing third-party import otherwise surfaces at collection
time and burns a fix/verify cycle.

## Driving the production spawn path in behavior tests

`Orchestrator.route_and_launch(dry_run=False)` is the real production entrypoint
(classify → select → propose → spawn gates → launch); the only legitimate double
is the process-spawn boundary (`orch.runtime_adapter = <object with launch(**kwargs)>`),
the repo's own test pattern. A raising adapter drives the real
`_quarantine_reservation` production handler. Harness facts that cost cycles when
guessed:

- The task classifier maps many ordinary intents to `task_class="review"`, and
  review-classified work rejects every non-reviewer profile — probe
  `TaskClassifier().classify(intent, capability).task_class` before writing the
  test intent, or selection dies with `no_eligible_specialist`.
- Inject a one-record `CapabilityIndex` (`SpecialistRecord(..., policy_eligible=True,
  launchable=True, eligibility_reasons=())`) for deterministic selection — the
  default index scans the host's installed profiles. Policy admission
  (`validate_assignment`) still reads the REAL registry, so the stub record's
  `profile_id` must be a real roster profile with the required capability declared.
- `TaskStore.all_tasks()` returns a dict, not a list.

## workspace/ is gitignored

Under noesis-agent-stack, `workspace/` is gitignored: handoff packets and prototypes
written there exist on disk but never appear in `git status`. Do not conclude "no
changes" from a clean `git status` when evidence lives under `workspace/`.
