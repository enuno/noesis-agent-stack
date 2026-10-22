t_file_content># Bounded offline compatibility check against the installed baseline

Use this reference when the operator authorizes a "bounded offline
compatibility check" against the installed (not the dev) baseline. This
is the verification step that follows `references/drift-port-proposal.md`
and answers the question the operator asks before approving a
port: **does the proposed composition actually build, import, and
test against the installed Hermes HEAD**, with a clean reproduction of
the proposed destination state and a documented dependency disposition?

The check is read-only. It writes only inside a scratch directory and a
git worktree that does not touch the operator's installed or dev
checkouts. It does not enable plugins, restart services, issue live
provider calls, or commit.

## 1. The authorization pattern

The operator's authorization is typically a 1-3-1 decision packet that
identifies:

- The items the operator wants verified (numbered 1-N), each as a
  specific command, expected result, and where to record the result.
- A blanket prohibition on destination writes, dependency installation,
  plugin enablement, service restart, source adaptation, and live
  execution.
- A requirement to distinguish "environmental failure", "inherited
  limitation", and "port incompatibility" in any finding.
- A requirement to preserve failing evidence rather than repair, weaken
  tests, or replace qualified bytes.
- A requirement to record the recorded Sentinel/Skeptic verdict
  verbatim and to preserve any memory/recorded-verdict discrepancy as
  a provenance note, not as an independent reviewer verdict.

Honor every prohibition. Do not implement remediation inline; return the
smallest repair scope as a separate authorization request.

## 2. Build the isolated composition in three layers

Do not run the verification against the dev source or against the
reconstruction directory; the operator's question is about the
proposed composition *as it would land in the installed checkout*. The
three-layer model matches that question.

### 2a. Hermes layer (isolated git worktree)

```bash
mkdir -p "$ISOLATE"
git -C "$INSTALLED_HERMES" worktree add --detach \
    "$ISOLATE/hermes-worktree" "$INSTALLED_HERMES_BASELINE"
```

The worktree starts at the bound installed baseline HEAD with no
operator dirty state carried in. A fresh `git worktree add --detach`
does not inherit the operator's pre-existing `M hermes_cli/config.py`
or any other uncommitted change from the installed checkout; those
remain at the operator's checkout and are excluded by design.

### 2b. Noesis layer (isolated git worktree + overlay writes)

```bash
git -C "$INSTALLED_NOESIS" worktree add --detach \
    "$ISOLATE/staging/noesis-overlay" "$NOESIS_BASELINE"
```

Then apply each Noesis overlay write:

- The dirty `models.py` (entry 1) is the operator's on-disk byte from
  `$INSTALLED_NOESIS/orchestration/orchestrator/app/models.py`. Copy
  it into the worktree at the same relative path. Verify the SHA-256
  matches the packet's `overlay-manifest.sha256`.
- Each `NO_OP` (entries 2, 3) is the packet's qualified source byte
  from the reconstruction. Copy and verify SHA-256.

The other 10 `app/*.py` files in the Noesis worktree remain at the
clean baseline HEAD. Do not copy the rest of the dirty worktree
(`specialist_routing.py`, `agency/*`, `platform/*`, `profiles/live/*`).
These are excluded.

### 2c. A6 layer (copy from reconstruction)

The A6 overlay is untracked at the operator's Noesis destination. Copy
the 11 A6 files from the packet's reconstruction at exact manifest
bytes. Stage them under the namespace prefix the manifest uses
(`a6:workspace/a6-integration/...`) so path resolution matches the
manifest's per-entry `dest_path` resolution.

### 2d. Restore-baseline backup

Before writing any REPLACE in the Hermes worktree, copy each
destination file to `$ISOLATE/restore-baseline/<rel>` so rollback can
restore the pre-write byte. The pre-write byte is the on-disk byte at
the bound installed baseline; it should match `git show
<BOUND_HEAD>:<rel>` but capture the actual on-disk byte as
authoritative.

## 3. Composition identity digest

After all writes, recompute the integrated overlay digest using the
packet's declared recipe (raw concatenation, no separators, in
`candidate-identity.json::integrated_overlay_order`) over the three
layers. The result must equal the packet's claimed successor digest
(e.g. `e8c33bb…` for A6). If it does not, the source of truth is
broken; halt.

The three-layer approach also gives you a defensive verification: if
the on-disk byte at the operator's installed checkout happens to
equal the qualified source for a file marked `REPLACE` (because the
upstream changed it), the write is still a write — the proposal's
restoration table is built from the on-disk byte, and rollback
restores the on-disk byte.

## 4. Verify imports resolve to the isolated roots

Imports must resolve to the three layers, not to the operator's
editable installations or to the reconstruction. The verification
script's `ALLOWED_PREFIXES` is the union of the three layer roots;
`DIRTY` is the list of paths whose appearance in a resolved origin
fails the check.

```python
import sys
WT = Path(os.environ["A6_HERMES_ROOT"]).resolve()
STAGE_NOESIS = Path(os.environ["A6_NOESIS_ORCH"]).resolve()
STAGE_A6 = Path(os.environ["A6_A6_ROOT"]).resolve()
ALLOWED = [str(WT), str(STAGE_NOESIS), str(STAGE_A6)]
DIRTY = ["/Users/elvis/projects/hermes-agent-track-b-runtime-enforcement",
         "/Users/elvis/projects/noesis-agent-stack",
         "/Users/elvis/.hermes/hermes-agent",
         "/Users/elvis/.hermes/profiles/noesis-forge/cache/scratch/a6-path-repair-reconstruction"]

# build sys.path so app.* and agent.* resolve to the layers, NOT to the
# operator's editable checkout
sys.path.insert(0, str(STAGE_NOESIS / "orchestration" / "orchestrator"))
sys.path.insert(0, str(STAGE_A6))
sys.path.insert(0, str(WT))
for p in list(sys.path):
    if any(p.startswith(d) for d in DIRTY):
        sys.path.remove(p)
```

Expected outcomes (when the env is right):

- 9-10 modules OK to allowed prefixes; 0 dirty.
- Three failure shapes are environmental, not candidate defects:
  - `No module named 'ruamel'` — pass when running with the Hermes
    test venv (has `ruamel.yaml`).
  - `No module named 'yaml'` — pass when running with the Noesis venv
    (has the ruamel compat `yaml` module).
  - `app.specialist_routing` — EXCLUDED from the proposal by design;
    do not include in the failure list.

`app.control_plane` is a particularly common edge case: the proposed
composite imports it; some venvs have `yaml` and some have `ruamel`
but not `yaml`. Run the import check with each candidate venv
separately and report which failures are venv-specific vs universal.

## 5. Harness scripts may need a `paths.py` shim

A reconstruction's harness scripts (e.g. Sentinel's
`harness/import_schema_check.py`) typically have `import paths` at the
top, which references a `harness/paths.py` shim in the same directory.
If you write your own harness to do an isolated check, do NOT depend
on the reconstruction's harness; the reconstruction's `allowed_prefixes`
is hardcoded to its own layout. Use the venv + sys.path approach above
and write a small in-place isolated-import-check.py.

If you do call the reconstruction's harness, copy the `paths.py` shim
to the same directory as the harness script. Without it, the harness
fails at collection with `ModuleNotFoundError: No module named 'paths'`
even though the import logic itself is sound.

## 6. Run the bounded check items

Order matters. Items 2-4 cascade from item 1's resolution; item 6 is
the most important single result. Item 7 is the byte identity check
the operator cares about most.

1. Imports resolve to the isolated layers. (See §4.)
2. D1-D4 focused test battery.
3. E1 production-path test (the most exacting quarantine/restart
   check).
4. Full A6 suite (or equivalent qualified-acceptance suite).
5. (Optional) Any cross-cutting integration test in the A6
   reconstruction.
6. Hermes runtime-enforcement battery: every `tests/agent/test_runtime_enforcement*.py`
   test in the operator's worktree at the new HEAD, with the Hermes
   test venv. 60-pass is the typical A6 number; record actual exit
   status.
7. Identity verification byte: import the qualified interface
   module, print `INTERFACE_VERSION` and the resolved module path,
   hash the file, and assert the hash matches the manifest's
   qualified source SHA-256 prefix.

Capture commands, environment, and exit statuses in
`$ISOLATE/logs/<item>-<name>.log`. Save the JSON output of any
import-check helper to `$ISOLATE/logs/<item>-<name>.json`.

## 7. Per-function review of the flagged files

When the manifest binds REPLACE operations to files that changed in
the upstream sync (typically one file: the one whose blob differs
between the previously bound HEAD and the new HEAD), classify the
diff hunks before declaring the port safe.

- **Annotation-only hunks** (`dict[str, Any]` ↔ `Dict[str, Any]`,
  `tuple[...]` ↔ `Tuple[...]`, `Optional[...]` modernization,
  `int(round(...))` casts, `# noqa: F401` linter hints,
  `return None` additions, docstring expansions): no runtime effect.
- **Additive hunks** (new dict entry, new enum value, new function
  call): compatible.
- **Parameter removals** (a kwarg deleted from a call site): safe at
  the signature level only if the callee's signature still has the
  parameter as a kwarg with a default. Verify the callee's signature
  with `git show <HEAD>:<callee_path>` or read the worktree file.
  Document any downstream effect (e.g. a telemetry field that now
  records `None` instead of the classifier's reason).
- **Body changes** (different control flow, different helper, different
  exception handling): semantic change. These are the only hunks
  that need a separate operator call.

A heuristic for annotation vs non-annotation:

```python
ANNOTATION_PATTERNS = {
    'dict[str, Any]', 'Dict[str, Any]', 'list[', 'List[', 'tuple[',
    'Tuple[', 'Optional[', 'int(round(', 'callable', '# noqa',
    '"""', "'''", 'return None', 'from ', 'import ', '#'
}
```

Treat anything not in this set as non-annotation. Classify each hunk
in the diff separately. Report the counts of each class.

## 8. Re-compute the composition identity after the tests

Tests are read-only against the worktree, but `__pycache__` is
generated and the pytest cache may be created. The composition
identity digest (computed over the overlay bytes) is unchanged by
running tests, but the worktree's `git status --porcelain` will show
untracked `.pyc` files. The pre-write overlay bytes are the same
post-test; record both pre-test and post-test digests as identical,
and `git diff <worktree>` on overlay files should be empty (only
`__pycache__` differs).

## 9. Distinguish findings before reporting

Every failure must be classified as one of:

- **Environment failure** (missing venv dependency, missing
  interpreter, wrong venv used). Fix: run with the correct venv.
  Document the missing package; do not install it.
- **Inherited limitation** (Sentinel-classified non-green scope;
  documented in the packet; not a candidate defect). Preserve the
  classification verbatim.
- **Port incompatibility** (the proposed composition does not
  satisfy the manifest's contract on the installed baseline). Return
  the smallest repair scope requiring separate approval; do not
  implement it.
- **Reproducibility defect** (the A6 candidate itself depends on a
  dirty file; the port preserves the on-disk byte but the
  reproducibility story is preserved from the packet's existing
  non-green scope). Inherited; not a port concern.

The operator's instruction is explicit: "Do not classify the port as
safe merely because a patch applies or file replacement is
mechanically possible." Material semantic changes in a REPLACE file
warrant a per-file call.

## 10. Memory-context vs recorded-review discrepancy

Memory at session start may describe a verdict that does not match
the recorded review artifact (e.g. memory says "BLOCKED" but the
recorded Sentinel verdict is "PASS, no blocking findings"). When
this happens, report both verbatim:

- The memory claim, as a provenance note ("system memory at session
  start described the candidate as ...").
- The recorded verdict, from the actual review artifact (read with
  `skill_view` or `read_file`, never from memory).
- The discrepancy, as a "preserved provenance note, not an
  independent reviewer verdict."

Do not reinterpret a scoped BLOCKED as PASS or APPROVED. Do not
reinterpret a recorded PASS as BLOCKED. Report the recorded verdict
verbatim and let the operator reconcile.

## 11. Final package

A single directory containing:

- `final-installation-decision-package.md` — the human-readable
  report (binding verification, construction, items 1-7 results,
  per-function review, non-green scopes, recommendation, next
  required decision).
- `final-installation-decision-pkg.json` — the same content as
  machine-readable JSON.
- `SUMMARY.md` — one-page summary.
- `composition-digest.txt` — the `e8c33bb…` match line.
- `hermes-worktree/` — the isolated git worktree.
- `staging/noesis-overlay/` — the isolated Noesis git worktree.
- `staging/a6-overlay/workspace/a6-integration/` — the A6 staging.
- `restore-baseline/` — the 6 backup files for rollback.
- `logs/` — captured command output.
- `harness/isolated-import-check.py` — the isolated import-verification script.

Verify the operator's installed checkout and dev checkout are
unchanged at the end (`git rev-parse HEAD`, `git status --porcelain`).
The worktree list should show the operator's main checkout plus the
detached worktree, both at the bound baseline HEAD.

## Common failure modes to avoid

- **Annotating a diff as annotation-only when it is a body change.** `str = None` and `str | None = None` are equivalent at runtime, but a try/except wrapping a different function call is not annotation. Walk each non-annotation hunk explicitly and classify it.
- **Treating an inherited Sentinel non-green scope as a port failure.** Non-green scopes documented in the packet are not port blockers; they are inherited and are out of scope of the port. Preserve their classification; do not repair them inline.
- **Recomputing the composition digest with the wrong path resolution.** The packet's `candidate-identity.json::integrated_overlay_order` defines the order and namespace. The `a6:` namespace is `a6:workspace/a6-integration/...`, and the staging must mirror that path prefix. A wrong path resolution (`STAGE_A6/noesis_admission_adapter.py` instead of `STAGE_A6/workspace/a6-integration/noesis_admission_adapter.py`) will produce a SHA-256 mismatch with the manifest and look like a source-of-truth defect.
- **Running the verification against the dev source.** The operator's question is "does it work against the installed HEAD". Dev source tests pass; they do not answer the operator's question.
- **Counting failed imports in venvs that lack `ruamel.yaml` as port defects.** The `ruamel.yaml` import in `agent.turn_api_error` and `agent.agent_init` is an environmental prerequisite, not a candidate defect. Run with the Hermes test venv, which has `ruamel.yaml` available.
- **Re-using the operator's `M hermes_cli/config.py` in the worktree.** A fresh `git worktree add --detach` does not carry pre-existing local modifications; the worktree's `hermes_cli/config.py` is the clean baseline. The pre-existing modification is preserved at the operator's checkout and is excluded from the worktree.
- **Bypassing the harness `paths.py` shim.** The reconstruction's harness imports `paths`; without the shim, every harness call fails at collection.
- **Assuming the memory-context verdict is the recorded verdict.** Always read the recorded review artifact, not memory.
- **Restoring the operator's installed checkout to fix a verification failure.** The check is read-only. If a verification fails, classify it, preserve the failing evidence, and return the smallest repair scope for separate authorization.

## Reading a guard before you fight it (universal pattern)

When a check hits a guard that rejects your staging path (e.g.
`tests/home_io_guard.py` rejecting paths under `/Users/elvis/.hermes/`),
read the guard's source BEFORE you attempt any workaround. The pattern
that wastes the most time: guess that the guard checks `os.path.realpath`
of the staging path, try symlinks, find that `realpath` resolves through,
discover the guard checks BOTH the lexical path AND a second-pass
`os.path.realpath(absolute)` against captured roots, and only then
realize that the right answer was to read the guard. Three pre-emptive
reads avoid three workaround rounds.

Concrete recipe:

1. Find the guard module: `search_files(pattern="home_io_guard", target="files", path=".")`.
2. Read its imports and its root-capture function (often
   `tests/conftest.py:1408` or the guard's own module-level code).
3. Identify the captured roots as a list of `Path` objects resolved at
   import time. Note whether roots are captured at import time or
   refreshed per call (import-time means a moved worktree after
   conftest load still has the old roots).
4. Identify the I/O functions the guard intercepts: `os.stat`,
   `os.path.isfile`, `Path.is_file()`, `Path.exists()`, `Path.read_bytes()`,
   `open(...)`. Each guard has a different interception surface; a
   guard that intercepts `Path.is_file()` will let `os.stat` through
   and vice versa.
5. Identify the predicate: `_within(absolute, root)`, `_within(resolved, root)`,
   or both. The double-check (lexical + realpath) defeats both
   symlink tricks AND path-mutation tricks. Workarounds must satisfy
   both predicates simultaneously.
6. Identify the workarounds the guard explicitly disallows (whitelist
   edits, environment variable bypass, profile-id spoofing). Never
   attempt them; they are category violations.
7. Identify the workarounds the guard allows: moving the staging
   outside every captured root, using a separate interpreter
   invocation that doesn't import conftest, mocking the guard at the
   test entry point with explicit operator authorization.
8. Implement the smallest allowed workaround. Copy, do not symlink
   (symlinks defeat the realpath check). Re-verify the candidate
   digest at the new location — same source bytes → same digest; if
   it changes, you have a different candidate.

If the guard is in the operator's installed checkout and the
operator's authorization says "do not edit, disable, or bypass
`home_io_guard.py`," that constraint closes option 6 (whitelist edit)
and option 8 (mock) when they would mutate the guard. The only
remaining workaround is moving the staging outside the captured
roots — and that is the right answer because it preserves the
guard's protection of the operator's real Hermes state.
