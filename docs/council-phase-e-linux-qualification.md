# Council Phase E Linux process-control qualification package (T11)

Status: EXECUTED 2026-11-12 on noesis-lab under operator authorization
"bounded Linux runtime qualification" (host confirmed by operator). The
execution was bounded: disposable Docker container, non-provider cases,
no live inference. Results and findings are recorded below; this package
remains the copy-ready procedure for any requalification. macOS
observations do not qualify Linux and were never cited as Linux evidence.

## Target/platform requirements

- UNRESOLVED (operator): target host identity, OS distribution and version,
  init system (expected systemd; confirm PID-1), and whether the host is
  dedicated/isolated (required: yes — no operational workloads co-located).
- Pinned runtime: `hermes` CLI at a full revision SHA recorded before
  execution (verify `hermes --version` output and
  `git -C <install> rev-parse HEAD` against the pinned SHA). UNRESOLVED
  until the operator names the pinned revision.
- Compatible agent-stack revision: the revision under test, recorded in the
  qualification receipt (precedent fields: `DEPLOYMENT-RUNBOOK.md` §8).

## Isolated test setup

- Disposable user account or container with no access to operational
  profiles, ledgers, or credentials. Network egress denied except the
  pinned provider endpoint when (and only when) a provider case is
  authorized — the base package needs no network.
- Fixtures: synthetic SeatCredentialContract values only; fake adapter and
  recording transports from the repo test suite; no Bitwarden, no live
  stores.
- Baseline: full suite on the pinned revision (expected 937 passed,
  2 skipped, 2 xfailed at package time — re-derive from observed results).

## Cases

1. Ownership and descendant identification: spawn a local child that itself
   spawns a grandchild; verify the harness records pid and pgid for the
   direct child and can enumerate descendants (psutil or /proc walk).
2. Timeout: child sleeps past `timeout_s`; verify the timeout path settles
   the attempt `uncertain` and the recorded child is gone.
3. Cancellation: `cancel_managed` with the recorded pid/pgid; verify the
   process group is terminated. Never kill by name.
4. Termination of a child that ignores SIGTERM: the runtime escalates to
   SIGKILL after a bounded grace of **0.2 seconds** (constant in
   `launcher.py::_signal_process_group`, `time.monotonic()` deadline —
   not platform-specific, not configurable). An earlier revision of this
   package stated 5 seconds; that value was wrong (F-2, see below). The
   2026-11-12 execution measured 0.204 s, consistent with the constant.
   Record both signals with timestamps.
5. Reaping/zombie: child exits but is not waited; observe zombie state and
   verify the harness does not leak un-reaped children over 25 repeated
   launches.
6. Orphan: parent dies before child; verify the child is re-parented
   (expected: subreaper/PID-1) and the harness's recorded handle is stale-
   detected, not trusted.
7. Emergency stop: abort mid-session; verify no further launcher calls
   (existing offline contract) plus on-Linux process cleanup of any started
   child.
8. Re-run after each case; the ledger/store must show fenced/uncertain
   attempts not re-fenceable after reconstruction (existing offline tests
   cover replay; this confirms them on the pinned runtime).

## Evidence collection and sanitization

- Record: case id, command shape (no secrets), exit/timeout/abort outcome,
  pid/pgid lifecycle observations, zombie/orphan verdict, attempt fence
  state before and after reconstruction.
- Sanitize: no credential values, no environment dumps; synthetic values
  only; scan every artifact with the repo secret scanner before retention.
- Receipt fields per `DEPLOYMENT-RUNBOOK.md` §8: target environment,
  readiness class, repo + installed revisions, digests, changed paths,
  commands + outcomes, limitations, remaining gates, rollback reference.

## Pass/fail criteria

- Pass: every case above completes with the expected process state, the
  attempt ledger is consistent after reconstruction, and zero secret-shaped
  strings appear in artifacts.
- Fail: any case leaves an unreaped child after bounded cleanup, kills by
  name/pattern, records a secret, or treats an ambiguous execution as safe
  to retry.

## Recovery and rollback

- No repository or runtime mutation is part of this package; rollback is
  disposal of the disposable account/container and deletion of its
  artifacts after the receipt is written.
- If a case wedges a process, record pid/pgid and escalate to the operator;
  do not broaden kill scope.

## Cross-repository note

noesis-ansible remains absent (runbook gap G-1) and was NOT modified under
this mission. If the operator wants this package wrapped as idempotent
roles, that is a separate cross-repository scope decision.

## Qualification record (executed 2026-11-12)

Environment: noesis-lab (Ubuntu 26.04.1 host), disposable Docker container
`noesis-t11-qual`, image digest
sha256:065aa8626841f16057b78b027b464cd59c4fac36c204c72dcbf48d66f5fa8a96,
kernel 7.0.0-43-generic x86_64, container PID 1 = non-reaping init,
Python 3.11.18, hermes v0.23.1 @ 3b421578588243f920886e6fe79a6faa87ea026e
(operator-approved pin; repository CI pins v0.22.5 — see the canary
contract's runtime compatibility table), agent-stack @
338ac8399d92a8b5e42d453ccaaef81ad22a22e7. Harness artifact sha256
1ec97ece5b54bc5f5bace53250548d7e1c15371cd8bb7fc0c3576a9e82901dcf.

Results:
- Hermetic baseline full suite: 937 passed, 2 skipped, 2 xfailed
  (CI fixture recipe: seeded HOME from `profiles/live/`, 33 files).
  An initial non-hermetic run (empty default HOME) failed 16
  CLI/plugin-host tests; that run is preserved as historical evidence of
  the fixture requirement, not a runtime defect. The hermetic rerun is the
  valid baseline.
- Cases 1-7: all PASS (ownership/descendants; timeout settle; pgid
  cancellation; SIGKILL escalation at 0.204 s observed; 0 zombie leaks
  over 25 launches; orphan re-parented to PID 1 with stale-handle
  detection; emergency-stop group cleanup with harness still usable).
- Case 8 (attempt fencing / replay on the pinned runtime): 9 passed.
- Secret scan over the harness artifact: 0 findings.
- Cleanup: container removed and host temporary files deleted after
  evidence capture.

### Finding F-1 — unconfirmed group-signal result (disposition: documented)

On Linux, `_signal_process_group` can return False when the SIGTERM-killed
child persists as a zombie during the 0.2 s grace window even though the
group is already dead. Caller inspection found no defect: every consumer
treats False conservatively (`cleanup_state="uncertain"`,
`workspace_reusable=False`, attempt settled `uncertain`, credential budget
closed, relaunch refused). The conservative handling was already pinned by
`test_uncertain_timeout_keeps_partial_artifacts_and_blocks_relaunch`. No
caller interprets unconfirmed as "still running" or as permission to
duplicate execution. Repair: the return contract is now documented at the
function (docstring only; no behavior change).

### Finding F-2 — grace value 5 s vs 0.2 s (disposition: document corrected)

An earlier revision of this package stated a 5-second SIGKILL grace. The
pinned implementation has always used a 0.2 s constant
(`time.monotonic()` deadline). 5 s was an error introduced while drafting
this package, not a requirement and not an implementation override. The
document is corrected to the implementation value; no runtime behavior was
changed and the qualification evidence is not invalidated (the 0.204 s
measurement matches the constant). 0.2 s fails closed and is acceptable
for the bounded canary scope; a larger grace is a design question, not a
defect.

### What this qualification does NOT establish

Disposable-container results must not be read as bare-metal, systemd host,
production PID-1, provider, or gateway qualification. Orphan/zombie
verdicts were observed under a non-reaping container init; a systemd host
may re-parent to a subreaper. Provider-adjacent behavior remains
unqualified until the separately authorized canary.
