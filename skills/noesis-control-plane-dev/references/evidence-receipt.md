# Successor-package receipt verification

Use this procedure when an implementation worker returns a new candidate and the operator authorizes receipt inspection but not more implementation or test execution.

## Procedure

1. **Freeze the claimed identity.** Record the baseline, candidate digest, manifest hash, diff hash, ordered file list, and the exact documented digest recipe. Never substitute a familiar recipe: raw-file concatenation and newline-joined per-file digests produce different identities.
2. **Recompute without executing the candidate.** Hash every live file and compare it with the manifest, then reproduce the candidate digest byte-for-byte. Hash the manifest, diff, completion records, and test logs separately. When the producer did not declare an expected evidence hash, label the value receipt-derived and freeze it in the receipt rather than claiming a producer match.
3. **Validate the diff structurally.** Parse all `diff --git` paths and compare them as a set with the manifest; section order need not match manifest order. Verify `git apply --check` against a clean baseline and `git apply --reverse --check` against the candidate tree. Do not mutate either tree.
4. **Separate snapshot preservation from the current tree.** Rehash frozen historical evidence and identify which prior candidate files remain byte-identical, which changed, and which are new. Say explicitly that preserved historical artifacts can coexist with a modified successor working tree.
5. **Recover real test status.** A log ending in `N passed` is content evidence, not process-status evidence. Prefer a preserved tool/session row that binds the exact command, summary, and integer exit status. If only the log exists, report the exit status as unknown. Do not rerun tests when receipt authority is read-only.
6. **Verify cleanup read-only.** Check the worker's descendants, test temporary directory, redirected logs, and candidate-specific database/WAL/SHM artifacts. Distinguish an idle live worker wrapper from a leftover test process.
7. **Attribute protected-tree changes.** Inventory every worker write/patch target from preserved tool calls, then inspect protected repositories. A globally dirty installed checkout is not automatically a candidate violation: report the dirty file, compare its timestamp/provenance with the worker window, and state separately whether the candidate wrote it. Never turn timestamp evidence alone into a global-clean claim.
8. **Audit claim namespaces and scope.** Ensure closure tables name the review findings they purport to close rather than similarly numbered orchestration gates. Verify physical transport with an invocation counter at the transport boundary; repeated `authorize` calls prove reservation semantics only. Distinguish default restart identity adoption from opt-in caller-bound identity retention.
9. **Separate provider claims.** Inspect worker-session inference records independently of test evidence. State provider-backed authoring when it occurred. Claim zero test network/provider calls only with a network-denial mechanism, transport interception, or equivalent observed evidence—not merely because tests use fakes in their names or assertions.
10. **Gate review on clarification.** If a required supplement is missing, deliver an exact documentation-only request bound to the candidate, diff, manifest, and baseline. Require `UNRESOLVED` where existing evidence does not answer an item. Do not start a provider turn, code change, test run, or reviewer dispatch merely to improve the packet. Once the supplement arrives, hash it and prepare fresh independent reviews; never carry old verdicts to the successor.

## Bounded correction turns

Use this sequence when the operator authorizes one model turn to correct an existing evidence artifact without changing the candidate:

1. Read the approval manifest and authoritative artifacts directly; never fill a truncated hash, symbol, or status from conversation context.
2. Snapshot the target bytes before dispatch. If no local snapshot was created, recover the original complete content from the persisted write/patch tool-call payload that produced it; verify its hash equals the known pre-correction hash.
3. Send one self-contained prompt to the already-live worker session. Name the sole writable path, exact replacements, preserved unresolved findings, forbidden actions, expected unchanged candidate digest, and the stop condition.
4. Wait for that same turn to return idle. Do not send a follow-up turn to fix formatting or ask for a summary; the one-turn budget includes all reasoning and tool retries inside the turn but authorizes no new user message afterward.
5. Reconstruct the exact before/after unified diff from the verified byte snapshots (for example, Python `difflib.unified_diff`), rather than copying a worker's abbreviated prose diff.
6. Independently hash the corrected artifact and recompute the candidate using its documented recipe. Inspect the turn's persisted tool calls: enumerate every state-changing call and target, and distinguish test-name strings in reads/patches from actual test execution. A successful patch result proves that edit landed; a failed patch attempt is not a write.
7. Report exactly the requested diff, new hash, and unchanged-candidate confirmation, then stop. Do not convert documentation completion into technical closure, acceptance, integration, installation, or deployment approval.

## Receipt verdict vocabulary

- **RECEIPT VERIFIED**: identity, artifact integrity, provenance, test-status source, cleanup, and required clarification are complete.
- **RECEIPT VERIFIED WITH CLARIFICATION BLOCKERS**: integrity checks pass, but review cannot start until exact documentation gaps are answered.
- **BLOCKED**: identity or provenance cannot be tied to the claimed package.

Receipt verification is not specification approval, quality/security approval, installation readiness, or deployment readiness.

## Post-receipt reconciliation and impact audit (read-only)

Use this when receipt verification finds execution/reporting violations and the operator authorizes bounded reconciliation: read existing records, write exactly two audit artifacts (supplement + audit receipt), change nothing else. This procedure does not authorize tests, provider calls, cleanup, or any state change.

1. **Authorization binding.** Tie the source/test mutation to the exact approval manifest (approval id, idempotency key, sha256) and distinguish documentation-only correction approvals from technical-remediation approvals. Verify the changed-path set against the approval's permitted paths. Classify deviations as boundary violations under a valid approval, not unauthorized mutation — and name which forbidden-work item was breached.
2. **Preparation forensics.** Find the pm sync receipts under `$HERMES_HOME/logs/update_receipts/pm_*.json`; each binds started/finished, `outcome`, `steps`, and `venv_rebuild`. `venv_rebuild.ok: false` with reason `already in sync` and empty `steps` proves a verify-only sync regardless of any setup banner text. Cross-check the install tree: venv `pyvenv.cfg` mtime, a find over `venv/lib` restricted to the turn window, uv cache dir mtimes (`archive-v0`, `interpreter-v4`, `builds-v0`), and install input stamps. Report four separated claims: installed/downloaded components, reused cache, environment regeneration, and stamp re-recording — never one compound "no changes".
3. **Profile provenance.** Enumerate the env handling of every invocation (e.g. `env -u HERMES_HOME` stripping). Grep BOTH the new logs and the frozen prior-candidate logs for the profile-fallback warning line; identical lines mean the caveat is shared by both candidates. Verify default-profile state DB and runtime-dir mtimes fall outside the worker window before claiming no wrong-profile writes, and attribute in-window writes to daemon vs worker by path (receipts/logs dirs vs gateway-owned files).
4. **Attempt chronology from the session DB.** Open the worker's Hermes session DB read-only (sqlite3). `sessions.id` IS the session key string — query `messages` directly by it; no join. `tool_calls` is JSON text whose `function.arguments` may be a dict; timestamps are epoch floats. Dedupe compaction-replayed message rows (same id, original older timestamps interleaved with new rows) before building the timeline. Bind command start/end from message timestamps and internal attempt/retry durations from the log body; preserve the full first-attempt failure output by log line range.
5. **Claims correction.** State corrected values (baseline commit, per-surface effect claims) in the new supplement only — never edit hash-recorded packet files. Replace compound booleans such as `dependencies_or_provider_changes: false` with separate evidence-based statements per surface.
6. **Impact inventory.** Table each surface (installed runtimes, caches, default-profile files, secrets, protected repos) with mtime/provenance evidence and an explicit daemon-vs-turn attribution; propose recovery steps but execute none.
7. **Artifact discipline.** Hash-verify both artifacts after their final edit — every cited hash inside them must have been recomputed from source during the write, never recalled. Append one ledger record carrying both artifact hashes, the freeze designation (candidate digest frozen as reported review scope while blocked), and the exact list of what now requires new authorization. Capture critical values via direct file reads or Python/SQLite rather than terminal stdout (the wrapper may return only one line), and keep checklist `blocked_reason` text under 200 characters.

## Guarded-suite isolation

Some Hermes test suites carry a file-I/O guard that refuses realpath I/O under
the real-home root. When the approval forbids touching the installed runtime,
placing `HERMES_HOME` inside the production tree — even as a fresh empty
subdirectory — triggers that guard and fails tests that would otherwise pass.

Bind `HERMES_HOME` to a fresh empty temp directory outside every guard root
(e.g. under the system temp dir) and bind `HERMES_TEST_SANDBOX_HOME` per the
suite's own test-owned-session-home mechanism. Confirm the canonical-resolved
home is outside the guard roots before running; report the effective guard
roots, zero fallback/guard/flaky markers, and the exact path used as evidence.

When a verification run fails for this environmental cause, retain the failed
run's artifacts unaltered and record the diagnosis. A corrected follow-up run
supersedes the failed scope only — it does not rewrite the failed run's
history. Aggregate split-run evidence explicitly (scope, exit, duration, log
hash per run) rather than presenting the corrected run as a single
verification pass.
