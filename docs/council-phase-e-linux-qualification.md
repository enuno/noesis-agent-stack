# Council Phase E Linux process-control qualification package (T11)

Status: COPY-READY PACKAGE — NOT EXECUTED. Nothing in this document has run
on a Linux host. macOS observations from the offline harness do NOT qualify
Linux and must not be cited as Linux evidence.

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
4. Termination of a child that ignores SIGTERM: escalate to SIGKILL after
   a bounded grace of 5 seconds, and record both signals with timestamps.
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
