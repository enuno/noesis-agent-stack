# Review handoff snapshot identity — command recipe

Use when freezing an operator-mediated review packet (Sentinel/Skeptic
hand-carry) or any "exact artifact identity" a reviewer must recompute.

```bash
REPO=~/projects/noesis-agent-stack   # adjust per task
BASE=<full-revision-of-scope-base>   # e.g. 52c5b6ec... (40 chars)
TIP=<full-revision-of-tip>           # e.g. 366f9eb6... (40 chars)
cd "$REPO"

git rev-parse "$BASE" "$TIP"         # (a) full revisions, never abbreviate

# (b) per-file sha256 at the tip, plus each frozen code dependency
for f in <reviewed-file-1> <reviewed-file-2> ... <frozen-dependency>; do
  printf "%s  " "$f"; git cat-file blob "$TIP:$f" | sha256sum | awk '{print $1}'
done

# (c) combined snapshot digest: NUL-separated name prefix + raw bytes,
#     reviewed files AND their code dependencies, in a fixed documented order
{ for f in <same-ordered-file-list>; do printf "%s\0" "$f"; git cat-file blob "$TIP:$f"; done; } \
  | sha256sum | awk '{print $1}'

# (d) later-change inspection: no commit after the tip may touch the code
git log --oneline "$TIP"..HEAD --name-only --format="COMMIT %h %s"

# (e) working tree must be clean for every reviewed path
git status --porcelain <reviewed paths...>
```

Record all five in the packet. The reviewer re-derives them independently;
the orchestrator re-verifies the snapshot digest after the verdict returns.
Declare in the packet whether later commits are docs-only or code-affecting —
a docs-only tail does not invalidate the snapshot, a code tail does.
