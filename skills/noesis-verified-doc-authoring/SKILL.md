---
name: noesis-verified-doc-authoring
description: Use when authoring Noesis docs or review bundles.
version: 1.0.0
author: noesis-scribe
license: proprietary
platforms: [macos, linux]
metadata:
  hermes:
    tags: [noesis, documentation, review, evidence, provenance, verification, scribe]
    category: noesis
    related_skills: [noesis-memory-routing, llm-wiki]
---

# Noesis verified documentation & review-bundle authoring

The Scribe's recurring class of work: writing README/docs, preparing external
review bundles, and assembling freeze/evidence packets for the Noesis stack.
These are NOT ordinary prose — they are provenance-carrying artifacts the
operator reads forensically. Every stated path, URL, count, role, and digest
must be true, and every limitation must be carried forward explicitly.

## When to Use

- Writing or updating a Noesis README, docs page, or profile-family overview.
- Preparing an external manual / independent review bundle from frozen
  evidence (Track A/B packets, RED/GREEN logs, review prompts, ledgers).
- Assembling freeze-integrity reconciliation or evidence handoff packets.
- Checking that a doc's paths, URLs, counts, or digests are true before
  publishing them.

## Always-on rules

- **Verify before you write.** A doc citing `profiles/noesis-roster.yaml`, a URL,
an agent count, a test total, or a wave membership must be checked against the
live source (git tree, `search_files (target='files')`, `git remote -v`, the
roster/curation YAML, a run of the tests) — never reconstructed from
prior-context memory. This user reads docs to audit the system; an invented
path or URL is the fastest way to lose their trust.
- **Verify placeholders twice.** URLs, directory names, and hashes are the exact
tokens that get fabricated from memory. After drafting, re-check each one
directly (git remote -v, search_files, sha256sum). Never paste a URL from
memory — read it from the repo's own remote config.
- **Do not invent structure.** If a top-level directory, sub-path, or
  generated-profile location is uncertain, run `search_files (target='files')`
  and state what actually exists instead of guessing what probably does. When
  in doubt, leave the claim out.
- **Distinguish committed vs generated.** Profiles created at apply time (e.g.
  `agency/` Tier A specs) may not be committed under `agents/` — say they are
  generated, not that they live at a path that is empty.
- **Never silently overwrite prior versions.** Preserve prior digests/claims;
  reclassify (e.g. "historical working-tree snapshot, not HEAD object digest")
  rather than deleting or contradicting without correcting the record.
- **Run `git diff --check`** after editing repo docs; leave unrelated
  pre-existing working-tree changes (e.g. logo assets) untouched and note them.

## Review-bundle packaging (external manual / independent review)

When asked to prepare a self-contained, non-sensitive review bundle:

1. **Ground every hash.** Recompute each snapshot digest and per-file SHA-256
   from the on-disk artifacts and report `computed == recorded` (or the diff).
2. **Inspect the material on disk first** — the bundle is a curation of
   existing evidence (review prompts, reconstructed packets, RED/GREEN logs,
   ledgers), not original research. Locate and read the real artifacts before
   writing.
3. **Embed the review prompts verbatim** so the reviewer does not need to hunt
   for them.
4. **Carry every limitation forward explicitly**: provenance (`reconstructed_by`,
   missing child handoff, executor exit code), preparation-free-vs-wrapper RED
   evidence, unresolved regression classification, worker-writable-ledger
   caveats. A limitation omitted from the bundle is a limitation that gets
   over-claimed as readiness.
5. **Separate resolved from unresolved** freeze-integrity reconciliation
   findings; do not blur them.
6. **No verdict = approval.** State plainly that no reviewer verdict
   constitutes installation, activation, canary, live-goal, commit, push,
   merge, or deployment approval.
7. **Do not launch a reviewer process** or issue provider calls; the bundle is
   an input for a manually-run external review. Stop after preparing it and
   wait.

## Snapshot-digest verification

When recomputing an ordered-manifest digest: the algorithm is
`sha256 of newline-joined "<sha256-or-MISSING>  <path>" over the ordered
manifest`. Try the trailing-newline and separator variants before declaring a
mismatch — a first-pass recompute that misses the trailing newline will
falsely report failure. See `references/snapshot-digest-verification.md`.

## Cross-track independence

Do not infer one track's approval/rejection from another track's reviews (e.g.
Track B review outcome says nothing about Track A). Treat each candidate
identity as independently reviewed.

## Dispatching a bounded task to a peer profile (review/commit/push)

When the operator asks you to hand a doc change to a peer profile (e.g.
noesis-steward) to review, commit, and push:

1. **Write a bounded dispatch prompt** following the repo's
   `workspace/orchestrator/dispatch-*.prompt.md` convention: task, exact
   repo/branch/remote, the precise files to stage (and the explicit exclusion
   of any already-committed or unrelated working-tree changes), review
   requirements, commit message, push target, and hard boundaries (no
   force-push, no history rewrite, no merge to main, stop-and-report on
   remote rejection).
2. **Dispatch via the repo's explicit specialist path** — `hermes -p <profile>
   chat -q "$PROMPT"` — NOT parent-inheriting `delegate_task`. This matches
   how the fleet actually routes specialist work and keeps the dispatch
   auditable in `workspace/orchestrator/dispatch-logs/`.
3. **Run it in the background with `notify=true`** and a bounded turn/budget
   (`--max-turns`, `--run-budget`), then report status and wait for the
   completion notification. Do not poll.
4. **Verify the dispatch actually started** (process alive, log file being
   written, profile applied its secrets) before reporting it as dispatched.
5. **You do not commit/push yourself** when the operator named a peer to do
   it — the peer's authorized action is the commit/push; your job is the
   faithful handoff.
6. **Verify the peer's self-report after the background process completes.**
   A child's "committed and pushed" claim is not verified fact. After the
   completion notification, independently confirm: the commit exists
   (`git cat-file -t <sha>`), the remote-tracking ref equals local HEAD
   (`git rev-parse origin/<branch>` == `git rev-parse HEAD` — this proves the
   push actually reached origin, not just local), the commit contains exactly
   the intended files (`git show --name-only --format="" <sha>`), and the
   working tree is clean. Report the verified commit SHA and push result, not
   the peer's summary. A concurrent process may have committed on top of the
   peer's push afterward — distinguish the peer's commit from later local-only
   commits and say which is on origin.

## Concurrent git mutation pitfall

A separate process (e.g. an `a6` loop) may be committing to the same repo
while you work. Re-verify git state **right before** you dispatch or commit:
`git rev-parse --abbrev-ref HEAD`, `git status --short`, and `git ls-files`
on any asset you reference (a logo you point the README at may have just been
committed, or the branch may have changed under you). Do not assume the branch
or tracked-status you saw earlier still holds; a dispatch prompt that names a
stale branch or stages files that were already committed will fail or mis-scope.
