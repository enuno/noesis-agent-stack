# Proposal — MemPalace SQLite Integrity Verification

**Status: PROPOSAL ONLY. NOT EXECUTED.** No integrity check, repair, VACUUM,
rebuild, export/import, or threshold change was performed. This document is a
plan awaiting explicit per-change approval.

Date drafted: 2026-10-22 · Author: noesis-praxis · Scope: read-only so far

## 1. Why this exists

`mempalace_status` reports:

```
sqlite_integrity:
  checked: false
  ok: null
  sqlite_path: ~/.mempalace/palace/chroma.sqlite3
  reason: startup integrity check skipped — 3785 MB is over the 512 MB limit
          (MEMPALACE_STARTUP_INTEGRITY_MAX_MB); no quick_check has run
```

**Unverified is not corrupted.** The backend is serving reads and writes
normally (588,782 drawers, `stale: false`, chromadb 1.5.9 serving). A skipped
startup check means nobody has asked the question, not that the answer is bad.
This proposal exists to ask it safely.

## 2. Actual layout (verified 2026-10-22)

- Deployment: **single shared palace**, backend `chroma`, embedding device `cpu`.
- Palace root: `~/.mempalace/palace` (~4.8 GB observed).
- SQLite file: `~/.mempalace/palace/chroma.sqlite3`, **3,785 MB**.
- SQLite library version: **3.46.1**.
- Store contents: 588,782 drawers across 10 wings and 18 rooms.
  Largest: `hermes` 586,286. `wing_noesis_praxis` 4.
- mempalace server **3.12.0**; chromadb **1.5.9** (not stale).

The 512 MB `MEMPALACE_STARTUP_INTEGRITY_MAX_MB` limit is a *startup
convenience* guard, not a corruption threshold. **Do not raise it** as a way of
"fixing" this — that would only make every startup scan a 3.8 GB read.

## 3. Supported verification procedure

Preferred, in order:

1. **`PRAGMA quick_check`** — the documented fast structural pass. This is what
   the startup check would have run. Non-destructive, read-mostly.
2. **`mempalace repair-status`** — read-only status of the last repair run.
   Run first; it is free and may already answer the question.
3. **`mempalace repair`** — only under §7 conditions, and only as a *check*
   first. It is the documented command named in the skipped-check reason.

Not used: `PRAGMA integrity_check` (full) as a first move — it is far slower
than `quick_check` on a 3.8 GB file with no added signal for a first pass.

The MemPalace recall skill documents the corrupt-index recovery path
(`repair --mode from-sqlite --archive-existing --yes`) for the case where the
HNSW index and `chroma.sqlite3` have diverged. **That is a repair, not a check,
and is explicitly out of scope here.**

## 4. Backup method consistent with this deployment

A consistent copy of a live SQLite file is a *backup API* copy, not `cp`:

- **Preferred:** SQLite online backup to a sibling path, which is consistent
  while the server keeps serving. Requires brief exclusive locking.
- **Fallback:** stop the MemPalace service, copy, restart. Cleaner but causes
  downtime for every agent using the shared palace.
- **Rejected:** `cp`/`rsync` of a live `chroma.sqlite3` — can capture a torn
  page set and produce a backup that fails to open.
- **Also rejected:** `VACUUM INTO` as the first action — it rewrites the file
  and needs free space roughly equal to the database.

Back up `chroma.sqlite3` **and** the sibling Chroma directories together; a
restored SQLite with a mismatched index is the failure mode the `--from-sqlite`
mode exists to handle.

## 5. Resource impact and headroom

Required before starting:

- **Free disk ≥ 2× the SQLite size** (~7.6 GB) for backup + working space.
  Verify actual free space first; do not assume.
- Backup destination on the **same filesystem** is fine for this pass, but note
  it gives no protection against host loss.
- **Expected lock window:** minutes, not hours, for a backup of this size.
  `quick_check` on 3.8 GB is I/O-bound and will contend with serving traffic.
- **CPU:** sqlite check is single-threaded; the `cpu` embedding device means the
  palace is not GPU-bound, so contention is modest.
- Blast radius: the palace is **shared by all four profiles**. A lock or
  restart affects every agent, not just Praxis.

## 6. Maintenance window and validation criteria

- Run in a window where no agent is doing a bulk ingest or recall sweep.
- Sequence: `repair-status` → backup → `quick_check` → record result.
- **Validation criteria for success:** `ok: true`, `error_count: 0`, and
  `mempalace_status` still reports the same drawer count (588,782) with
  `stale: false`. A drop in drawer count is a failure, not a cleanup.
- Validate the backup independently: open it read-only and count rows before
  declaring the backup good. An unverified backup is not a backup.

## 7. Conditions that would justify repair or recovery

Do **not** repair because the check was skipped. Repair only if:

- `quick_check` reports errors, **or**
- the backend reports an HNSW segment-writer error / ChromaDB compaction
  failure / persistent "Not connected" after a write, **or**
- drawer counts diverge from expectations in a way that is not explicable.

If any of those hold, follow the documented recovery
(`repair --mode from-sqlite --archive-existing --yes`), which preserves
MCP-added drawers and diary entries. Do not re-mine — that drops them (#1843).
Do not attempt an in-process repair from the agent.

## 8. Rollback and restore verification

- `quick_check` itself is non-mutating; rollback is "stop".
- Backup restore: stop service → move the bad file aside (do **not** delete) →
  restore → `repair --mode from-sqlite` if the index needs rebuilding → restart
  → verify drawer count and `stale: false`.
- Keep the pre-check backup until the post-check status has been stable for one
  full session across all four profiles.

## 9. Approval required before executing

Not yet requested. Execution needs explicit approval covering: the check
itself, the backup path and destination, the maintenance window, and
acknowledgement that the palace is shared across all four profiles. The
`MEMPALACE_STARTUP_INTEGRITY_MAX_MB` threshold stays as it is.
