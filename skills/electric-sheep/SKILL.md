---
name: electric-sheep
version: 2
description: Async self-improvement loop. Reviews recent work in MemPalace, finds skill gaps, discovers or authors new Hermes skills, and writes a diary entry. Runs unattended via hermes cron or post-task hooks.
agents: [hermes, claude, claude-code, mcp-compatible]
dependencies:
  - mempalace
---

# Skill: Electric Sheep

A scheduled, unattended self-improvement loop for Hermes agents.
Inspired by biological sleep-phase memory consolidation, it reviews recent
performance, mines lessons into MemPalace, detects capability gaps, and either
finds existing skills or authors new ones.

Stateless at invocation — all persistent state lives in MemPalace.
Safe to call from hermes cron, a post-task hook, or any MCP trigger.

**Critical safety rule:** Never mine the raw `~/.hermes/sessions/` directory
directly. It contains mixed file types (`request_dump_*.json`, cron transcripts,
etc.) that cause segfaults, extreme slowness, and palace bloat. Always stage
clean files first. See Phase 2 below.

---

## When to Use This Skill

- hermes cron fires (nightly or every N hours)
- Post-task hook fires after a session ends
- Error-rate threshold exceeded
- Explicit trigger from another skill (e.g. self-reflection-self-improvement)

Keywords: "run dreaming cycle", "consolidate memory", "self-improve",
"find missing skills", "write skill", "reflect on recent tasks",
"palace sweep", "electric sheep", "hermes reflect"

---

## Prerequisites

**MemPalace**
- Palace initialised and MCP server functional
- Verify with `mcp_mempalace_status` before each run

**Skill Factory**
- Access to local skill registry (`HERMES_SKILL_DIR` env var, default `~/.hermes/skills/`)
- Read/write files for SKILL.md authoring

**Optional**
- GitHub token (`GH_TOKEN`) if PR creation desired
- Internet for remote registry search

**Environment**
```
MEMPALACE_DIR=~/.mempalace
HERMES_SKILL_DIR=~/.hermes/skills
DREAM_MAX_NEW_SKILLS=3
DREAM_PR_ON_COMPLETE=false
DREAM_LOOKBACK_HOURS=24
```

---

## Workflow

### 1. Wake-Up

Load recent context into working memory:
- `mcp_mempalace_status` — verify palace health and get AAAK dialect spec
- `mcp_mempalace_diary_read(agent_name="electric-sheep", last_n=5)` — load prior diary
- Set `dream_session_id = uuid4()` and record start time

If `mcp_mempalace_status` fails:
- Try killing stale MCP servers: `pkill -f "mempalace.mcp_server"`
- Retry after 10s. If still failing, abort and reschedule.

### 2. Mine & Consolidate

**NEVER run `mempalace mine ~/.hermes/sessions/` directly.** The raw sessions
directory contains `request_dump_*.json` files and cron transcripts that cause:
- Segfaults (SIGSEGV, exit code -11) from mixed file types
- Extreme slowness (10–30+ hours instead of 20–60 minutes)
- Palace bloat (single request dumps can generate 500–900 drawers each)

**Safe staging workflow:**
```bash
# Stage only clean conversation files
mkdir -p /tmp/electric-sheep-staging

# Copy only actual session files (adjust pattern to your session naming)
cp ~/.hermes/sessions/session_*.json /tmp/electric-sheep-staging/ 2>/dev/null || true
cp ~/.hermes/sessions/*.jsonl /tmp/electric-sheep-staging/ 2>/dev/null || true

# Exclude known problematic patterns
rm -f /tmp/electric-sheep-staging/request_dump_*
rm -f /tmp/electric-sheep-staging/session_cron_*

# Count staged files
echo "Staged $(ls /tmp/electric-sheep-staging/*.{json,jsonl} 2>/dev/null | wc -l) files"
```

Then mine the staging directory in the background (not via MCP):
```bash
mempalace mine /tmp/electric-sheep-staging/ --mode convos
```

Monitor via `ps` and `ls -lt ~/.mempalace/palace/chroma.sqlite3` rather than
stdout (output is buffered until completion). Typical runtime: 20–60 min for
~2,000 clean session files.

**If mining segfaults or hangs:**
1. Kill all miners: `pkill -f "mempalace mine"`
2. Run `mempalace repair` (25–30 min for ~22K drawers)
3. Re-stage and retry

**Recall pass** — use `mcp_mempalace_search` (NOT CLI `mempalace search`, which
can silently return empty results while MCP search works):
- Failures: `mcp_mempalace_search(query="task failed error could not", limit=10)`
- Gaps: `mcp_mempalace_search(query="don't know how missing skill no capability", limit=10)`
- Wins: `mcp_mempalace_search(query="succeeded completed successfully", limit=10)`
- Perf: `mcp_mempalace_search(query="slow timeout took too long", limit=10)`

Cap at 50 drawers total across all queries.

Update knowledge graph for entities appearing 3+ times:
```python
mcp_mempalace_kg_add(
    subject="<entity>",
    predicate="recurring_issue",
    object="<issue_type>",
    source_closet=f"electric-sheep/{dream_session_id}"
)
```

### 3. Find Gaps

Build `gaps[]` from search results:
- `high` — same gap ≥5 times
- `medium` — 2–4 times
- `low` — 1 time

Sort by severity, then frequency. Take top `DREAM_MAX_NEW_SKILLS`.

### 4. Discover or Author

For each gap:

1. Search palace for prior solutions:
   ```python
   mcp_mempalace_search(query="<gap keywords>", limit=5)
   ```
2. Search local skill registry:
   ```bash
   grep -ri "<gap keywords>" ~/.hermes/skills/ --include="SKILL.md" -l
   ```
3. Search remote registry (GitHub) if online:
   ```bash
   gh search repos "hermes skill <topic>" --limit 5
   ```
4. Decide:
   - Match found → note in report, do not duplicate
   - No match → flag for authoring
   - Uncertain → flag `needs_review` for human triage

### 5. Author Skills

For each flagged gap (max `DREAM_MAX_NEW_SKILLS`):

Draft a SKILL.md:
```
---
name: <kebab-case>
version: 1
description: <one line>
agents: [hermes, claude]
---

# Skill: <Name>

## When to Use This Skill
## Prerequisites
## Workflow
## Output Format
## Rules & Constraints
## Examples
```

Ground every section in palace evidence. Cite drawer IDs in a comment:
`<!-- evidence: drawer_<id1>, drawer_<id2> -->`.

Validate:
- [ ] `name` is unique in `HERMES_SKILL_DIR`
- [ ] `Workflow` has ≥3 concrete steps
- [ ] `Rules & Constraints` has ≥1 hard rule
- [ ] `Examples` has ≥1 input → output pair
- [ ] No `[TBD]` or `TODO` placeholders

Write to: `HERMES_SKILL_DIR/<name>/SKILL.md`
Store raw text in palace:
```python
mcp_mempalace_add_drawer(
    wing="electric-sheep",
    room="authored-skills",
    content="<skill markdown>",
    source_file=f"{HERMES_SKILL_DIR}/<name>/SKILL.md"
)
```

### 6. Write Diary

Use AAAK format per MemPalace protocol:
```
SESSION:<session_id>|TIMESTAMP:<ISO8601>|LOOKBACK:<h>h
WINS:<n>|FAILURES:<n>|GAPS:<n>|DISCOVERED:<n>|AUTHORED:<n>|REVIEW:<n>
WIN:<summary>
FAIL:<summary>
GAP:[<severity>]<description>
SKILL:<name>→<path>
NEEDS_REVIEW:<description>|reason:<why>
PERF:<slowness_pattern>
NEXT_DREAM:<ISO8601>|★★★
```

Store via MCP:
```python
mcp_mempalace_diary_write(
    agent_name="electric-sheep",
    entry=f"SESSION:{dream_session_id}|TIMESTAMP:{datetime.now().isoformat()}|LOOKBACK:{lookback_h}h|WINS:{n_wins}|FAILURES:{n_failures}|GAPS:{n_gaps}|AUTHORED:{n_authored}|★★★",
    topic="self-improvement"
)
```

### 7. Commit (Optional)

If `DREAM_PR_ON_COMPLETE=true` and skills were authored:

1. `git checkout -b dream/<date>-<short_id>`
2. `git add HERMES_SKILL_DIR`
3. `git commit -m "chore(skills): dream cycle <short_id> — add <n> skills"`
4. `gh pr create --title "Electric Sheep: <date>" --body "<diary>" --label "electric-sheep,auto-generated"`

If no `GH_TOKEN`, write patch to `HERMES_SKILL_DIR/.pending/<id>.patch`.

Clean up staging directory:
```bash
rm -rf /tmp/electric-sheep-staging
```

---

## Output

1. Palace diary entry (always)
2. Knowledge graph nodes (always)
3. SKILL.md file(s) (if authored)
4. GitHub PR (if enabled and skills authored)
5. Stdout summary:
   ```
   [electric-sheep] Session <id> complete.
     Drawers swept:      <n>
     Gaps identified:    <n>
     Skills discovered:  <n>
     Skills authored:    <n>
     Needs review:       <n>
     Diary written:      YES
     PR opened:          <YES|NO|SKIPPED>
   ```

---

## Rules

- NEVER overwrite existing SKILL.md files. Version instead (`-v2`).
- NEVER author without palace evidence. Cite drawer IDs in a comment:
  `<!-- evidence: drawer_<id1>, drawer_<id2> -->`.
- NEVER open an empty PR.
- NEVER skip Phase 2–3 before authoring. Evidence first.
- NEVER mine `~/.hermes/sessions/` directly — always stage clean files first.
- Cap new skills per cycle. Unbounded authoring degrades quality.
- Complete within 10 minutes. Cancel mining after 5 minutes if stuck.
- Log all command exit codes. Skip phases on error, do not abort.
- `needs_review` items are for human eyes only.

**Edge cases:**
- Empty palace → skip to diary, note "insufficient history", reschedule in 1h.
- All gaps covered → diary "no new skills needed", exit.
- Validation fails → write to `.drafts/<name>.md` with `STATUS: DRAFT`, flag review.
- Offline → skip remote search, continue locally.
- Mining segfault → kill miners, run `mempalace repair`, re-stage, retry.
- Mining deadlock (0% CPU, threads in futex_do_wait) → kill miners, run `mempalace repair`.
- HNSW corruption → `mempalace repair` (25–30 min). Do NOT upgrade/downgrade chromadb.
- Stale MCP server → `pkill -f "mempalace.mcp_server"`, wait 10s, retry.

---

## Examples

### Hermes cron (nightly)

Create a scheduled job:
```bash
hermes cron create "0 3 * * *" \
  "Run the electric-sheep skill. Review the last 24h of palace history, identify gaps, and author any missing skills. Stage session files safely before mining." \
  --name "electric-sheep" \
  --skill electric-sheep
```

Output:
```
[electric-sheep] Session a3f1b2c9 complete.
  Drawers swept:      142
  Gaps identified:    4
  Skills discovered:  2  (git-bisect-debug, ansible-lint)
  Skills authored:    1  (terraform-drift-detect)
  Needs review:       1  (ambiguous gap: "better logging")
  Diary written:      YES
  PR opened:          SKIPPED (DREAM_PR_ON_COMPLETE=false)
```

### Post-task hook (lightweight dry-run)

Create a gateway hook that fires after each agent session:

```bash
mkdir -p ~/.hermes/hooks/electric-sheep-trigger
cat > ~/.hermes/hooks/electric-sheep-trigger/HOOK.yaml << 'EOF'
name: electric-sheep-trigger
description: Trigger electric-sheep dry-run after each agent session
events:
  - agent:end
EOF

cat > ~/.hermes/hooks/electric-sheep-trigger/handler.py << 'EOF'
import subprocess
from pathlib import Path

async def handle(event_type: str, context: dict):
    # Trigger a lightweight electric-sheep dry-run after each session.
    # Full authoring is heavy; run that on cron instead.
    subprocess.run(
        [
            "hermes", "chat",
            "-q", "Run the electric-sheep skill as a dry-run: search palace for gaps from the last 1h, but do NOT write files.",
            "-s", "electric-sheep",
            "--quiet",
        ],
        cwd=Path.home(),
        capture_output=True,
    )
EOF
```

Output (diary excerpt, AAAK format):
```
SESSION:b7d2e441|TIMESTAMP:2026-05-06T04:12:00Z|LOOKBACK:1h
WINS:2|FAILURES:1|GAPS:1|AUTHORED:0
WIN:Deployed Ansible playbook to staging
WIN:Resolved DNS propagation with dig trace
FAIL:Terraform plan failed: provider version mismatch
GAP:[high]No skill for Terraform provider version drift
NEXT_DREAM:2026-05-07T03:00:00Z|★★★
```

### Clean cycle

Output:
```
[electric-sheep] Session c9a0f3d2 complete.
  Drawers swept:      18
  Gaps identified:    0
  Skills discovered:  0
  Skills authored:    0
  Needs review:       0
  Diary written:      YES
  PR opened:          SKIPPED (no new skills)
```

### Recovery from mining segfault

```bash
# Step 1: Kill all miners
pkill -f "mempalace mine"

# Step 2: Repair the palace
mempalace repair

# Step 3: Stage clean files only
mkdir -p /tmp/electric-sheep-staging
cp ~/.hermes/sessions/session_*.json /tmp/electric-sheep-staging/
rm -f /tmp/electric-sheep-staging/request_dump_*

# Step 4: Re-mine
mempalace mine /tmp/electric-sheep-staging/ --mode convos

# Step 5: Clean up
rm -rf /tmp/electric-sheep-staging
```

---

## Deployment

**Hermes cron (recommended):**
```bash
hermes cron create "0 3 * * *" \
  "Run the electric-sheep self-improvement cycle. Stage clean session files, mine them safely, search for gaps, and author missing skills." \
  --name "electric-sheep" \
  --skill electric-sheep
```

**Systemd (legacy fallback):**
```ini
# electric-sheep.service
[Unit]
Description=Electric Sheep — Hermes self-improvement loop

[Service]
Type=oneshot
ExecStart=/home/elvis/.local/bin/hermes cron tick
```

---

## Success Criteria

- [ ] Palace health verified via `mcp_mempalace_status` before starting
- [ ] Clean files staged before mining (no raw `~/.hermes/sessions/` mine)
- [ ] Diary entry written via `mcp_mempalace_diary_write` in AAAK format
- [ ] Each authored skill exists at `HERMES_SKILL_DIR/<name>/SKILL.md` and passes validation
- [ ] Stdout summary emitted
- [ ] No unhandled exceptions (errors logged to diary)
- [ ] If PR opened: URL logged to diary
- [ ] Staging directory cleaned up after mining
