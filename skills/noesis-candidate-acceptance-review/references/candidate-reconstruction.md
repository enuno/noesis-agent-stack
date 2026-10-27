# Candidate Reconstruction and Hash Reproduction

How to verify a candidate that is no longer in the worktree, and how to map a
claimed diff hash back to the recipe that produced it.

## Why this exists

A candidate deliverable is normally an **uncommitted** working tree: modified
tracked files plus untracked new files. When the work moves on (remediation
landed, commit made, branch pushed), that exact byte state is no longer
reachable from the worktree — but the bytes usually survive in the git object
DB as unreachable blobs. Reporting "the candidate cannot be verified" when the
bytes are one command away is a false negative, and it turns a solvable review
into a BLOCK on a technicality.

## Step 1 — Detect that the candidate moved

```bash
WT=/path/to/worktree
git -C "$WT" status --short          # report says: M ... ?? ...
git -C "$WT" log --oneline -3
git -C "$WT" rev-parse HEAD
git -C "$WT" reflog --date=iso | head -20
git -C "$WT" branch -r --contains HEAD
```

A clean tree at a commit that the report described as uncommitted means the
candidate was superseded. Record that as a top-line finding: the artifact under
review is not the artifact on disk.

## Step 2 — Find the candidate bytes by content hash

The report's per-file SHA-256 table is the lookup key. Git's own object IDs are
SHA-1 (or SHA-256) over a *header plus* the content, so they do NOT equal the
file's plain SHA-256 — you must hash the content yourself and compare.

```bash
cd "$WT"
git cat-file --batch-all-objects --batch-check='%(objectname) %(objecttype) %(objectsize)' \
  | awk '$2=="blob"{print $1}' > /tmp/blobs.txt

while read -r obj; do
  h=$(git cat-file blob "$obj" | shasum -a 256 | cut -d' ' -f1)
  echo "$h $obj"
done < /tmp/blobs.txt > /tmp/blob-sha256-index.txt
```

Now look up each claimed hash in that index. A blob that matches a claimed
per-file hash IS that file's exact content.

## Step 3 — Materialize the candidate tree in scratch

```bash
SCRATCH=/tmp/recon
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH/tree"

# base state
git -C "$WT" archive "$BASE" | tar -x -C "$SCRATCH/tree"

# overlay candidate content (tracked-modified files and new files alike)
git -C "$WT" cat-file blob "$BLOB_SHA" > "$SCRATCH/tree/$PATH"
```

Files unchanged from base need no overlay — `git archive` already carried them.

Verify the reconstruction by recomputing the report's per-file SHA-256 table
against `$SCRATCH/tree`. Every entry must match before you trust the tree.

## Step 4 — Reproduce the diff hashes without touching the repo

The repo's real index must not be disturbed. Redirect it:

```bash
export GIT_INDEX_FILE="$SCRATCH/idx"; rm -f "$SCRATCH/idx"
git -C "$WT" read-tree "$BASE"          # index := base tree
export GIT_WORK_TREE="$SCRATCH/tree"

# Variant A — tracked-only (new files absent from index => not in the diff)
git -C "$WT" diff --no-color > "$SCRATCH/tracked.diff"

# Variant B — new files included via intent-to-add
git -C "$WT" add -N -- <new file paths>
git -C "$WT" diff --no-color > "$SCRATCH/tracked-with-new.diff"

# Variant C — fully staged
git -C "$WT" add -A
git -C "$WT" diff --no-color --cached "$BASE" > "$SCRATCH/staged.diff"
```

Always `rm -f "$GIT_INDEX_FILE"` first — a stale index file makes `read-tree`
fail or silently reuse the wrong base.

## The recipe matrix

| Recipe | Command | Typical use |
|---|---|---|
| tracked-only | `git diff --no-color` with index=base, worktree=scratch | "tracked_diff_sha256" |
| tracked + new-as-additions | same, after `git add -N` on new files | hashes that include new files |
| fully staged | `git diff --no-color --cached <base>` after `git add -A` | full content diff |
| tree-to-tree | `git diff --no-color <base> <commit>` | a committed candidate |
| combined | tracked diff + `--- new files ---` + concatenated new-file bodies | "combined_sha256" |

## The combined-patch recipe

Several implementers build a "combined" hash by concatenating a tracked diff
with the raw bodies of the new files:

```bash
{
  git -C "$WT" diff --no-color
  echo "--- new files ---"
  for f in <new file paths in the report's order>; do
    echo "+++ $f (untracked) +++"
    cat "$SCRATCH/tree/$f"
  done
} > "$SCRATCH/combined.diff"
shasum -a 256 "$SCRATCH/combined.diff"
```

Two details make or break reproduction: the **file order** in the loop must
match the report's order, and the loop must read from the reconstructed tree
(not the live worktree) so the content is the candidate's bytes.

## Interpreting a mismatch

- One recipe matches and the others do not → the candidate is intact; you had
  the wrong recipe. Not a finding.
- No recipe matches → real divergence. Then check, in order: the base commit
  (is it the one the report named?), the per-file table (does the reconstructed
  tree match it?), and whether the report's own two hashes are mutually
  consistent (recompute the tracked hash from the same tree that produced the
  combined hash).
- The reviewers' verdict hashes match a recipe but the implementer's reported
  hashes match none → the implementer's self-reported hashes are wrong or
  stale, while chain of custody to the reviewed artifact is intact. Report
  both facts separately.

## Chain of custody

```bash
# what the reviewers bound their verdicts to
rg -o '"candidate_revision": "[a-f0-9]{64}"' ledger.jsonl | sort | uniq -c

# what is actually on the remote
git -C "$WT" ls-remote --heads origin

# whether the commit message's own quoted hash recomputes
git -C "$WT" log -1 --format='%B' <commit>
```

Also compare review timestamps against the commit timestamp. Reviews that
precede the commit are the expected order; a commit that precedes the reviews
it cites is a process finding worth surfacing on its own.

## Never

- Do not `checkout` the base commit in the live worktree to compare behavior —
  it changes the tree under review.
- Do not `git add` into the repo's real index.
- Do not `git gc` / prune before searching the object DB; unreachable blobs are
  exactly what you are looking for.
- Do not delete scratch reconstructions until the verdict is written — the
  next question will be "re-run that probe".
