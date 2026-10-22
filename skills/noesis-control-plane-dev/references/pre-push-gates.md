# Pre-push gates for an external Hermes publication

Use when authorized to push a local development branch as a new branch
on a remote `enuno/hermes-agent` (or equivalent operator-owned fork). This
file holds the **executable recipe** and the **classifier** for what each
result means. The corresponding always-on rules live in the parent
SKILL.md under "Pre-push scope-divergence check"; this file is the
depth reference when actually running the gate.

A clean final tree and a clean secret-pattern grep are necessary but not
sufficient. The real test is the **history shape**, not the working
tree. A push can publish tens of thousands of upstream commits that the
operator never authorized for that destination.

## The four-number scope check (run before any push)

```bash
LOCAL=path/to/dev-repo
REMOTE=<remote-name>           # e.g. operator-github
DEST_BRANCH=<exact-ref>        # e.g. refs/heads/a6-checkpoint/2026-10-11-v3.1

cd "$LOCAL"

# 0. Verify repository root, branch, and remotes (do not assume names)
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD                                  # local source commit
git remote -v

# 1. Confirm the destination ref does not already exist on the remote
git fetch "$REMOTE"                                  # fetch refs
git ls-remote --heads "$REMOTE" "$DEST_BRANCH"
# exit 0 with no rows = safe to create
# any row returned = HALT, report its commit, do not overwrite

# 2. Get the destination main tip (do not assume the default branch is main)
git ls-remote --heads "$REMOTE" | head
DEST_MAIN_TIP=$(git rev-parse "$REMOTE/main")

# 3. Compute the merge base and the ahead/behind counts
LOCAL_TIP=$(git rev-parse HEAD)
git merge-base "$LOCAL_TIP" "$DEST_MAIN_TIP"          # fork point
git log --oneline "$DEST_MAIN_TIP..$LOCAL_TIP" | wc -l   # ahead
git log --oneline "$LOCAL_TIP..$DEST_MAIN_TIP" | wc -l   # behind

# 4. Inspect push-triggered automation at the destination
curl -fsSL "https://api.github.com/repos/<owner>/<repo>/contents/.github/workflows?ref=main" \
  | python3 -c "import sys, json; [print(f['name']) for f in json.load(sys.stdin)]"
# for each workflow file, fetch and check the `on:` block for a `push:
# branches:` clause that includes the destination branch. None of the main
# workflows should match.
```

## Interpreting the four numbers

- **Local tip ≠ `operator-github/main` and merge-base = 0 (unrelated
  histories):** the local branch carries the destination's full upstream
  history or a parallel fork. Pushing under the approved branch name
  publishes the upstream commits' authors, dates, and content under the
  operator's identity. Halt. Propose option: branch from `remote/main`,
  replay the operator-approved delta as one or two new commits, push that
  branch.

- **Local tip = `operator-github/main`:** the branch is a clean checkout
  of main; the push is a no-op for content. Likely wrong unless the
  operator wanted an empty new branch.

- **Ahead > 0 and behind > 0 with non-trivial ahead (say, > 100):** the
  branch contains the destination's upstream history plus a small local
  delta. A typical "preservation artifact" case. Decide whether the
  ahead portion is acceptable for the destination, and if not, port the
  delta as a new commit on `remote/main`.

- **Ahead > 0, behind = 0:** the branch is a clean delta on top of
  destination main. The standard case the authorization covers.

- **Ahead = 0, behind > 0:** destination is ahead of local. Stale
  branch; do not push a branch the destination does not need.

For a "development preservation artifact" authorization (the most common
case), `ahead > 1000` is the threshold at which the local branch is
**not a checkpoint delta** and the prior "preservation" intent does not
transfer. Anything below that threshold may be acceptable but still
deserve the four-number report.

## Secret-pattern scan — the fast path

Per-blob `git show <tip>:<path>` scans are too slow at repository scale
(15K+ paths, 226 MB tarball). Use the in-memory tar:

```python
import subprocess, re, tarfile, io
from collections import defaultdict

TIP = "<local-tip>"
REPO = "<repo-path>"
OUT = "/tmp/scan.out"

PATTERNS = {
    "BEGIN_PRIVATE_KEY": rb"-----BEGIN (RSA |OPENSSH |EC |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----",
    "AWS_ACCESS_KEY":     rb"AKIA[0-9A-Z]{16}",
    "AWS_SECRET_ASSIGN":  rb"(?i)aws(.{0,20})?(secret|sk)[_-]?(access)?[_-]?key",
    "GITHUB_PAT":         rb"ghp_[A-Za-z0-9]{36,}",
    "OPENAI_KEY":         rb"sk-[A-Za-z0-9]{20,}",
    "XAI_KEY":            rb"xai-[A-Za-z0-9_-]{20,}",
    "VENICE_INFERENCE_KEY": rb"VENICE_INFERENCE_KEY[A-Za-z0-9_=]{6,}",
    "BITWARDEN":          rb"(?i)bitwarden",
    "BWS_":               rb"BWS_[A-Za-z0-9_]+",
    "ANTHROPIC_KEY":      rb"sk-ant-[A-Za-z0-9_-]{20,}",
    "GOOGLE_API_KEY":     rb"AIza[0-9A-Za-z_-]{35}",
    "PASSWORD_ASSIGN":    rb"(?i)(password|passwd|pass)\s*=\s*[\"'][^\"']{6,}[\"']",
    "TOKEN_ASSIGN":       rb"(?i)(auth[_-]?token|access[_-]?token|api[_-]?token|bearer[_-]?token|secret[_-]?token)\s*=\s*[\"'][A-Za-z0-9_\-\.=]{20,}[\"']",
}

tar_bytes = subprocess.run(["git","-C",REPO,"archive","--format=tar",TIP],
                           capture_output=True, check=True).stdout
hits = defaultdict(list)
files_scanned = 0
with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
    for m in tf:
        if not m.isfile():
            continue
        files_scanned += 1
        f = tf.extractfile(m)
        if f is None:
            continue
        blob = f.read()
        if b"\x00" in blob[:4096]:
            continue
        for name, pat in PATTERNS.items():
            for hit in re.finditer(pat, blob):
                line = blob[:hit.end()].count(b"\n") + 1
                snippet = hit.group(0).decode("utf-8", errors="replace")[:120]
                hits[(name, m.name)].append((line, snippet))
```

`git archive` returns one tarball; reading 17K files from it in Python is
~10 seconds end-to-end. The same scan via per-blob `git show` subprocess
calls does not finish inside a 300-second Python kernel.

## Classifying the matches — none of the patterns is a secret by itself

A pattern match is not a finding. Common false-positive classes:

- `«redacted:sk-…»`, `«redacted:AKIA…»`, `«redacted:ghp_…»`, `«redacted:AIza…»`
  — explicit redaction placeholders in test fixtures. Treat as
  unambiguous safe.
- `Bitwarden` / `bitwarden` — vault backend name. The operator's
  architecture uses Bitwarden; the matches are code that calls into the
  vault, not credentials.
- `BWS_*` — Bitwarden Secrets CLI environment-variable *names*
  (BWS_ACCESS_TOKEN, BWS_SERVER_URL, BWS_RUN_TIMEOUT), not values.
- `AWS_SECRET_ACCESS_KEY`, `aws_secret_key`, `aws_access_key_id` — AWS
  env-var names used by Bedrock and Iron Proxy adapters. Not values.
- `password="..."` in tests — fixture passwords (`hunter2`,
  `mypassword`, `boundaryPasswordABC123456789`). The fixture pattern is
  recognizable: a string literal assigned to a variable named `password`
  inside a test function or `setUp`. In production code, the same
  pattern is a real leak.
- `BEGIN RSA/OPENSSH PRIVATE KEY` — test fixtures that write
  `"[REDACTED PRIVATE KEY]"` or the literal PEM header to a temp file.
- `xai-access-token-account-a/b`, `xai-tmp-imgen-already-404`,
  `xai-dashboard-dedupe-test` — test fixture tokens, mock URLs, session
  IDs. Not real keys.
- `model-slug` strings like `xai-grok--responses-api--prompt-caching` —
  model identifiers, not keys.

For any pattern that does not match a known false-positive class, sample
3–10 matches and inspect the surrounding 3 lines. If the surrounding
context is `os.environ[...]` or `KEY = os.getenv("KEY", "")` it is
almost always an env-var read, not a real key. If it is a literal value
in production code, **stop and request operator decision** before pushing.

## Differential scan when the destination already carries secret-like material

A full-tip scan on a branch off a repo that already contains secret-like
matches (config files with literal tokens, signed URLs, fixture PEM headers)
will alarm on material this branch did not add. The correct go/no-go signal is
the **delta against the merge base**, not the tip total. Run the fast-path
scan twice — once at `origin/main` (or the merge base) and once at the feature
tip — and compare the per-category hit-path sets:

- **new** (`tip − base`): these are introduced by the branch and must be zero,
  or each new hit must classify as an explicit placeholder. This is the only
  number that blocks the push.
- **existing** (`tip ∩ base`): pre-existing material. Report it separately (by
  path + category, never the matched value) so it stays visible as a known
  exposure, but it is not a reason to block this branch.
- **removed** (`base − tip`): the branch deleted a previously-flagged path —
  a good sign, worth noting.

Fold the two passes into one script that returns `new` / `existing` / `removed`
per category and a summed `new` count; assert `new == 0` before authorizing.
Do not substitute a clean `git diff --check` or a staged-file scan for the
archive-level delta — those miss untracked files and whole-tree history shape.

## The push command itself (do not run until confirmed)

```bash
cd "$LOCAL"
git push "$REMOTE" "${LOCAL_TIP}:${DEST_BRANCH}"
# non-force, no --mirror, no --all, no other branch, no tag, no main update
```

The push is irreversible on a public repository. Honor the tool-level
confirmation requirement: present the resolved command, the destination
URL, the exact source commit, the exact outgoing diff stats, the
secret-scan verdict, and the destination-branch-existence check, and
wait for explicit operator confirmation in the same session. The
confirmation prompt is mandatory even if the prior authorization letter
named the branch — the operator's "push" is what makes the destination
visible.

## Post-push verification

```bash
git ls-remote --heads "$REMOTE" "$DEST_BRANCH"   # should match $LOCAL_TIP
git fetch "$REMOTE" "$DEST_BRANCH"
git rev-parse "FETCH_HEAD"                       # must equal $LOCAL_TIP
```

If the FETCH_HEAD tip does not equal the source commit, **stop and report**
— the push either did not land or landed on a different ref.

## What this gate does NOT cover

- Source-tree content quality (covered by the test suite + Sentinel review).
- Runtime/destination compatibility (covered by the bounded compatibility
  check + separate install authorization).
- Public exposure of branch names (this is the operator's expected
  artifact, not a leak).
- Workflow automation (covered above by the trigger inspection).
