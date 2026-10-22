# Clean candidate reconstruction

Use this recipe when a reviewed candidate was tested in a dirty worktree, contains untracked files, or may import changed files omitted from its manifest. The goal is to prove that the declared identity—not ambient checkout state—is sufficient to import and pass its qualification suite.

## 1. Freeze history before investigating

- Preserve prior manifests, patches, reports, logs, and reviewer outputs byte-for-byte. Create a successor evidence directory; never rewrite an older identity into a supposedly complete one.
- Record each repository baseline with its full commit ID and verify the object exists.
- Record current HEAD and dirty/untracked inventory separately. HEAD identifies the baseline lineage; it does not identify a dirty reviewed candidate.

## 2. Discover the minimal dependency closure

Start from the actual runtime entrypoints, plugin/adapter entrypoints, schemas, tests, and fixtures in the declared path. Trace both static imports and runtime loads such as registry discovery, configuration/schema reads, importlib calls, relative file opens, generated assets, and subprocess entrypoints.

Classify every relevant file:

| Class | Meaning | Action |
|---|---|---|
| Baseline | Required bytes already supplied unchanged by the recorded baseline | Cite the baseline; do not duplicate them in the addition bundle |
| Candidate addition | Dirty or untracked exact bytes required to import, test, or execute the path | Freeze full path, baseline state/hash, current SHA-256, importer/consumer, and rationale |
| Environment prerequisite | Interpreter/package/tool required but not repository candidate content | Record exact requirement; do not install without authorization |
| Excluded | Dirty bytes unrelated to the declared path | Name and exclude; do not copy them for convenience |

Inspect beyond the first missing symbol. A direct import can expose further changed imports, registry data, schema files, or test fixtures. Conversely, do not include every dirty file merely because it appears in `git status`.

For each imported dirty file, separate **path dependency** from **dirty-delta dependency**. Substitute the baseline version in the isolated reconstruction and run the smallest import/behavior probe that exercises the consumer. If baseline bytes pass, classify the dirty delta as excluded even though the module path is imported. If a required symbol or behavior is absent from baseline, freeze the complete existing file and put every hunk in review scope; do not extract only the needed class or function during evidence collection.

A changed file may contain both required and unrelated edits. Dependency-freezing authorizes recording its existing bytes, not silently approving all semantics. Put the complete file into the successor review scope and call out unrelated hunks for reviewer attention; if those bytes cannot be accepted as a unit, stop for a bounded clean-base repair proposal rather than editing during evidence collection.

## 3. Build the reconstruction without contaminating it

Use new task-local directories outside both source checkouts. Extract each baseline from Git objects, for example:

```bash
git -C "$SOURCE" archive "$BASELINE" | tar -x -C "$CLEAN_ROOT"
```

Do not reset, stash, clean, or mutate the source checkout. Do not copy the entire dirty tree. Apply only the reconstructing patch and explicit untracked additions. Run `git apply --check` against the extracted baseline before applying tracked changes; then copy each explicit addition by manifest path.

Produce an ordered manifest containing full relative path, origin class, baseline hash/state, final SHA-256, and reason. Define the aggregate identity algorithm exactly, including ordering, separators, and whether it hashes file bytes or textual digest lines. Hash the patch, addition bundle, manifest, and reconstruction instructions as separate artifacts.

When reconstructing a successor from an older digest recipe, reproduce the old digest over its original ordered path set for continuity, but do not call it the complete successor identity if qualification-relevant files now sit outside that set. Freeze a separate expanded identity that includes every changed runtime, CLI, schema, fixture, and test file needed to evaluate the successor. Publish both identities with distinct labels and recipes: the legacy-scope digest proves byte continuity; the expanded digest binds the reviewable successor. Never silently widen the old recipe or imply that a matching legacy digest qualifies bytes it never covered.

Reject absolute symlinks, editable-install pointers, `.pth` files, and source paths that point back to the dirty checkout. Do not package caches, SQLite run state, bytecode, coverage output, or test-generated files unless the product contract explicitly requires them.

## 4. Prove import and execution provenance

Run from the reconstruction using an existing authorized interpreter with dependency installation disabled. Clear inherited source-path overrides where safe and set only reconstruction-local roots needed by the project.

For each critical module, import it and record its resolved origin (`module.__file__` plus `Path(...).resolve()`). Assert the path is inside the reconstruction root. Check adapters, plugins, request-path modules, and their authority/store dependencies—not only the top-level entrypoint. Launch the interpreter with reconstruction-local `cwd`/import roots and cleared inherited path variables; do not monkeypatch `pathlib`, `sys.path` semantics, or absolute-path constructors to redirect imports. Such shims can make dirty-checkout references appear reconstructed and therefore invalidate provenance. If an unchanged test or fixture hardcodes the original checkout and cannot run without redirection, record that as a reconstruction/test-fixture defect and request a bounded repair rather than manufacturing a passing provenance check.

Make test-root configuration an explicit candidate interface when a fixture spans repositories: accept narrowly named environment roots, resolve them with ordinary `pathlib.Path`, and keep any developer default separate from the qualifying run. During clean qualification, set every required root explicitly to the reconstruction and assert the resolved paths; never allow a fallback to the dirty checkout to make the run pass. Treat this fixture-only correction as a new candidate identity, preserve the shim-dependent attempt as failed chronology, and rerun reconstruction plus review rather than editing evidence in place. If a developer fallback still names a source checkout, record it as a residual limitation and state that clean provenance is proven only with the reconstruction-root variables set; do not claim clean-tree import with variables omitted unless that mode was separately exercised.

Classify every non-green scope from evidence rather than the implementer's label. Record the exact failing test/import and exit, then ask in order: (1) does the frozen candidate alter the failing path; (2) is the scope required for the claimed qualification boundary; (3) does the same failure reproduce from the clean baseline under the same environment; and (4) is a missing package/tool an environment prerequisite rather than repository content? A failure may be nonblocking only when that classification is supported; preserve it in chronology even when the required candidate scopes pass, and require each independent reviewer to issue its own disposition.

Before tests:

1. hash every candidate file;
2. run import/schema checks;
3. run focused behavior tests through the production handler boundary;
4. run the full candidate suite;
5. run regressions for newly frozen dependency files;
6. record actual process exits without masking them through a pipeline;
7. hash every candidate file again and compare.

Fake transport proves boundary behavior only when the real controller/admission/quarantine path remains in the call chain. No live provider call is implied or permitted by a clean reconstruction test.

If a test fails because a repository file is absent, return to dependency classification and include its unchanged existing bytes only when the path is actually necessary and in scope. If passing requires changing bytes, stop: that is a code defect and needs a bounded repair authorization, followed by a new identity, reconstruction, and review. If the interpreter lacks a prerequisite, request that exact environment setup; do not modify candidate code to compensate.

## 5. Review the reconstructed identity

Freeze the complete successor identity before review. Give fresh independent reviewers:

- full baseline IDs;
- ordered manifest and aggregate algorithm;
- reconstructing patch/addition bundle hashes;
- reconstruction commands;
- module-origin evidence;
- pre/post hashes and test logs;
- explicit dependency additions and exclusions;
- preserved prior worktree evidence, labeled as historical.

Require each reviewer to recompute identity, verify clean provenance, inspect all newly included dependency bytes, rerun relevant tests, and distinguish what prior dirty-worktree evidence did from what the clean reconstruction now proves. A conditional verdict is unresolved until its conditions are satisfied and the reviewer issues the required final disposition.

## 6. Route the next gate precisely

- Reconstructable plus every required review passes: request the exact installation/port proposal for the pinned identity; do not install, activate, commit, merge, or deploy.
- Dependency exposes a code defect: request/authorize only the bounded repair, then reconstruct and re-review the changed identity.
- Environment prerequisite missing: request the specific environment setup, not permission to alter the candidate.
- Integrity or scope cannot be closed: report the exact missing file/byte set, provenance conflict, or review condition and the smallest operator action.
