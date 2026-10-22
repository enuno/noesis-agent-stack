# SQLite Ledger Hardening — Rules and Recipes

Rules for turning a bare `sqlite3` file-backed ledger into one with explicit
provisioning/reopen semantics, guarded settlement, and honest filesystem claims.
All stdlib-only; no new dependencies.

## Silent-create is the root hazard

`sqlite3.connect(path)` creates an empty database when `path` is absent. Every
"open existing" code path that reaches connect on a missing/deleted file silently
re-provisions a fresh empty store — resetting budgets, totals, or any accumulated
state to zero without an error.

Defenses, in layers:

1. **Existence pre-check at open** — refuse to open a file that does not exist
   (`os.path.isfile`), with a distinct error from "corrupt" (`ledger_missing` vs
   `ledger_unreadable`).
2. **Provision-vs-open classmethods** — `create()` refuses to overwrite (probe with
   `sqlite3.connect("file:<abs>?mode=rw", uri=True)`; success means the file exists),
   requires the parent directory to already exist, and writes an identity row.
   `open()` never creates.
3. **Identity row re-verified INSIDE every write transaction** — a meta table with
   `format` tag, `schema_version`, and a provisioning nonce (`ledger_id`). Reading
   it inside each `BEGIN IMMEDIATE` transaction catches the delete-and-recreate
   case: sqlite silently makes a new empty file at connect time, the meta read
   then fails with "no such table", and the operation denies instead of writing
   into a blank ledger.

## Where corrupt-file errors actually surface

Not at `connect` — sqlite opens files lazily. The first error surfaces at the first
statement, which is often `PRAGMA journal_mode=WAL` inside your `_connect` helper,
BEFORE any application query runs. So the exception classifier must wrap the
connect-and-pragma phase as well as the query phase, or "file is not a database"
leaks as a raw sqlite message instead of your `ledger_unreadable` denial reason.
Message-map at both layers:

- "no such table: <meta>" → mismatch (real sqlite file, not this ledger)
- "file is not a database" → unreadable/corrupt
- lock/busy timeout → explicit denial, never an exception through the admission path

## Autocommit means per-statement commits

With `isolation_level=None`, every statement outside an explicit transaction commits
immediately. Two consequences:

- Multi-statement schema init leaves a PARTIAL schema if it fails halfway. Wrap
  `CREATE TABLE` batches in `BEGIN IMMEDIATE … COMMIT` with rollback on error.
- A single `UPDATE` "settlement" was previously atomic-by-accident but had no
  read-check; making it transactional (`BEGIN IMMEDIATE`, read current row, decide,
  write, commit) is what enables conflict detection.

## Guarded settlement contract

Settlement should never refund (consumption happens at reservation; settle must not
touch budget tables) and must define three outcomes explicitly:

- unsettled row (`success IS NULL`) → write outcome, commit.
- identical re-settlement → idempotent no-op, commit nothing.
- different outcome or unknown attempt key → raise a typed conflict error AFTER
  rollback; the durable final outcome is never overwritten.

Failure observability: record failures on a bounded in-process deque and re-raise so
the caller's catch-and-log path names them. Do NOT promise a durable marker of the
failure inside a database that may be the thing that failed.

## Admission replay semantics: unsettled vs settled

Re-presenting an attempt key has two different meanings and the store must
distinctly:

- **Unsettled reservation** (`success IS NULL`) → idempotent admit, no additional
  consumption. This is the crash-after-reservation redelivery path: the reservation
  already consumed its unit, so replaying the same identity must neither re-spend
  nor refund.
- **Settled reservation** (`success NOT NULL`) → deny with `attempt_already_settled`
  BEFORE any consumption. Re-presenting a completed attempt is a duplicate-transport
  attempt, not a redelivery. Without this denial, one admission identity can drive a
  second physical request through any caller that re-issues a settled identity —
  pushing physical invocations beyond the configured allowance. Regression shape:
  count invocations at the real request boundary (instrumented transport), not at
  the authority, and prove both the duplicate-delivery case (two deliveries, one
  transport, one unit) and the reuse case (denied pre-transport, count never grows).

## Error-class taxonomy: OperationalError is broader than locks

`sqlite3.OperationalError` covers more than lock/busy — a `disk I/O error` (e.g.
after sidecar tampering) also arrives as OperationalError. A blanket
`except OperationalError → ledger_busy` handler therefore MISLABELS unavailability
as contention. Classify by message: contains "locked" or "busy" → contention
denial; any other OperationalError → unavailability denial. (Corrupt-file messages
like "file is not a database" raise DatabaseError and map per the section above.)

## Ledger identity: adopted by default, pinned only on request

State the semantics precisely when asked — this is a common reviewer probe:

- Provisioning always writes a `ledger_id` (caller-chosen or generated nonce) into
  the identity row.
- Default reopen (no caller input) ADOPTS the stored identity: it is read into
  memory once at open and re-asserted inside every transaction for the life of
  that store object. No caller state is required, but nothing pins the file
  against a same-format replacement across processes.
- Opt-in binding: the caller records the expected value at provisioning time
  (either by choosing it at `create`, or by reading it back from the provisioned
  store's `ledger_id` property) and supplies it as the expected identity at every
  later `open`. Mismatch → `ledger_id_mismatch` denial.

## Contention testing without stress suites

Purpose-built lock tests, not parallel full-file runs:

- Hold a write lock from a RAW second connection: `sqlite3.connect(path,
  isolation_level=None)` then `execute("BEGIN IMMEDIATE")` and do not commit.
- The contender opens the store with a SHORT `busy_timeout` (e.g. 150 ms via a
  configurable `busy_timeout_ms`, not the default 30 s) and must receive an explicit
  `(False, "ledger_busy", 0)`-style denial — assert reason and that nothing was
  written.
- Commit the holder; assert the contender then succeeds and budget math is exact.
- Keep thread count ≤2 and iteration counts small; a 2×25 two-thread race against a
  budget of 10 is enough to prove no overspend.

## Honest filesystem claims

- WAL requires the parent directory to be writable by the owning uid (for `-wal`/`-shm`
  sidecars). A read-only directory fails at `PRAGMA journal_mode` — classify it as
  unavailability, and note it is the extent of "unauthorized access" detection.
- WAL locking serializes writers; it is NOT tamper prevention. State the
  same-authority-writer limitation verbatim: a process with the same uid and write
  access can replace or edit the ledger, and swap-detection only reaches as far as
  the identity row (format/version/bound `ledger_id`). Pin the residual gap as a
  named limitation test rather than leaving it implicit.
- Chmod-based permission tests must skip when `os.geteuid() == 0` and when
  `os.access(dir, W_OK)` is still true after `chmod 0o500` (ACL/rootless quirks).

## Enumerate deletion sub-scenarios separately

Main-DB deletion and WAL/SHM sidecar deletion are DIFFERENT scenarios with
different recovery behavior — a reviewer may require them tested separately.
If only one has a test, say so verbatim ("main-DB deletion tested; sidecar
deletion untested; actual outcomes UNRESOLVED") rather than letting one test
stand for both. Never claim data-loss or recovery behavior for a scenario no
test exercised.

### Recorded actual outcomes (observed: macOS, Python 3.14 bundled sqlite)

Setup for both: provision and checkpoint a ledger, then open a long-lived raw
`sqlite3.connect` that executes `PRAGMA journal_mode=WAL` and stays open — this
keeps `-wal`/`-shm` present and blocks checkpoint-on-close, so a second
connection's committed frames exist only in `-wal`. Delete one sidecar, then
observe through NEW connections:

- **`-shm` deletion: no data loss.** The next connection recreates `-shm` from
  `-wal`; committed frames survive; reservation replay of an existing unsettled
  key stays idempotent (no double consumption). Opening is unaffected.
- **`-wal` deletion: new connections fail CLOSED.** Opening the store can still
  succeed (meta read), but subsequent reads raise `disk I/O error` (stale `-shm`
  referencing the vanished `-wal`) — surface as your unavailability type; a
  reservation attempt must deny with the unavailability reason, never a fresh
  admission. No allowance reset and no silent re-admission of lost identities is
  observable through new connections. The in-flight connection that held `-wal`
  open keeps its own consistent view via its file descriptor — that window is
  trusted-owner territory, not a boundary the ledger resists.

Do not assert a hypothesized outcome (e.g. "partial reset to consumed=N-1") in
these tests — run once, record what actually happens, then pin the observed
behavior as the assertion. Platform sqlite versions can change the failure mode;
the record belongs in the evidence packet, not in an over-strong claim.
