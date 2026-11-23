# Reconciling a Dirty Checkout with a Moved origin/main

Use when the operational checkout has uncommitted changes, local `main` has
fallen far behind `origin/main`, and a pull refuses because local files would
be overwritten. The reconcile is: preserve, fast-forward, sync forward, commit.
Push only on explicit operator approval.

## 1. Assess (read-only, no mutations)

- `git status`, `git log --oneline -5`, `git fetch origin`,
  `git log --oneline HEAD..origin/main | wc -l`.
- If `git log origin/main..main` is empty and status says "behind N, can be
  fast-forwarded", there is NO commit divergence — the entire conflict is
  uncommitted state. Everything below assumes this shape; if local main has
  unique commits, stop and treat it as a real merge problem instead.
- Two sets block a fast-forward pull. Find both:
  - tracked files changed locally AND upstream:
    `comm -12 <(git diff --name-only | sort) <(git diff --name-only HEAD..origin/main | sort)`
  - untracked files that upstream now tracks:
    `comm -12 <(git ls-files --others --exclude-standard | sort) <(git ls-tree -r --name-only origin/main | sort)`

## 2. Audit what is actually unique (before destroying anything)

Diff-derived candidate lists mislead; verify uniqueness per block by content.

- Markdown list items appear as `+-` lines when you grep a diff for `^\+`, so
  a naive `git diff origin/main | grep '^\+'` both overcounts (common content
  at different positions) and undercounts (alignment artifacts in heavily
  edited regions).
- For each candidate block, run `git grep -l "<distinct phrase>" origin/main
  -- <path>` against the upstream branch, then grep the worktree copy and
  every profile source dir. Only content absent from BOTH the upstream branch
  and all profile sources is truly unique.
- Most "local edits" in a skills checkout turn out to be a stale sync state
  the upstream branch already superseded (compare manifest `generated_at`,
  skill `version:` frontmatter, and upstream merge commits that already
  carried a fleet sync). Only genuinely newer profile-side content needs
  carrying forward — via the profile working copy, never the repo tree.

## 3. Preserve rollback points

- Save the full change set with `git diff HEAD > <backup>.patch` (plain
  `git diff` alone can omit content depending on index state — `diff HEAD`
  captures staged + unstaged together).
- For any specific block you care about, ALSO extract it directly from the
  live file (`sed -n '<line>p' <file>`) and grep the snapshot to confirm the
  capture contains it. The live file is ground truth; a derived snapshot you
  have not verified is not.
- `git stash push -m "pre-reconcile: <what and why>"` the tracked changes.
- Move the colliding untracked files to a backup dir OUTSIDE the repo,
  preserving directory structure.

## 4. Fast-forward, then sync forward

- `git pull --ff-only origin main`. If it still refuses, re-run the Step 1
  collision checks — something was missed.
- Immediately run `scripts/sync-noesis-skills.py --sync` and confirm
  `--check` exits 0. The sync overwrites repo skills from the profile
  working copies and regenerates the manifest; anything repo-side-only from
  Step 2 is destroyed here, which is why the verified backup matters.
- Preflight `python3 agency/validate-specs.py` — the pre-commit hook runs it
  on every commit regardless of staged paths, so surface failures as a clean
  pre-read, not a rejected commit.

## 5. Commit and push

- One commit: `skills/noesis-*/` changes together with
  `skills/noesis-skills.manifest.json`. Never a separate cleanup commit;
  never `--no-verify`.
- Push only on explicit operator approval. Preflight
  `git ls-remote origin main` to confirm the remote has not moved; after the
  push, read back `git ls-remote origin main` and compare to the local tip
  before declaring done. Do not rely on the push command's own success
  output as the verification.

## What to report

- Local vs remote position before and after (old tip -> new tip).
- What was stashed and where the backup dir lives (rollback path).
- Any truly unique content found and its disposition (carried into the
  profile source, saved as a patch, or discarded by operator decision).
- Whether the push happened; if held, that it is held.
