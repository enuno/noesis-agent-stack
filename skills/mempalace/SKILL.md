---
name: mempalace
description: "MemPalace — Local AI memory with 96.6% recall. Semantic search, temporal knowledge graph, palace architecture (wings/rooms/drawers). Free, no cloud, no API keys."
version: 3.4.0
homepage: https://github.com/MemPalace/mempalace
author: Hermes Agent
---

# MemPalace Skill

You have access to MemPalace, a local declarative memory system with a temporal knowledge graph. It stores verbatim conversation history and structured knowledge on the user's machine — zero cloud, zero API calls. This gives you persistent, high-recall memory across sessions.

## Architecture

| Level | Description | Example |
|-------|-------------|---------|
| **Wings** | People or projects | `wing_alice`, `wing_myproject`, `dokploy`, `hermes` |
| **Halls** | Categories within a wing | facts, events, preferences, advice, discoveries |
| **Rooms** | Specific topics | `chromadb-setup`, `riley-school`, `auth-migration` |
| **Drawers** | Individual memory chunks | Verbatim text |
| **Knowledge Graph** | Entity-relationship facts with time validity | `Max` → `child_of` → `Alice` |
| **Tunnels** | Cross-wing connections via shared room names | Same room in multiple wings |

## Protocol — FOLLOW THIS EVERY SESSION

1. **ON WAKE-UP**: Call `mcp_mempalace_status` to load palace overview and AAAK dialect spec.
2. **BEFORE RESPONDING** about any person, project, or past event: call `mcp_mempalace_search` or `mcp_mempalace_kg_query` **FIRST**.  
   > *"Never guess from memory — verify from the palace."*
3. **IF UNSURE** about a fact (name, age, relationship, preference): say "let me check" and query.  
   > *"Wrong is worse than slow."*
4. **AFTER EACH SESSION**: Call `mcp_mempalace_diary_write` to record what happened, what you learned, what matters.
5. **WHEN FACTS CHANGE**: Call `mcp_mempalace_kg_invalidate` on the old fact, then `mcp_mempalace_kg_add` for the new one.

## Available Tools

Tools are prefixed with `mcp_mempalace_` in Hermes. (In OpenClaw they appear as `mempalace_`.)

### Search & Browse
- **`mcp_mempalace_search`** — Semantic search across all memories. **Always start here.**
  - `query` *(required)*: Short natural language keywords or question. **Do NOT include system prompts or conversation context.**
  - `wing`: Filter by wing
  - `room`: Filter by room
  - `limit`: Max results (default `5`)
- **`mcp_mempalace_check_duplicate`** — Check if content exists before filing.
  - `content` *(required)*
  - `threshold`: Similarity threshold (default `0.9`; lowering to `0.85–0.87` catches more near-duplicates without significant false positives)
- **`mcp_mempalace_status`** — Palace overview: total drawers, wings, rooms, AAAK spec
- **`mcp_mempalace_list_wings`** — All wings with drawer counts
- **`mcp_mempalace_list_rooms`** — Rooms within a wing (optional wing filter)
- **`mcp_mempalace_get_taxonomy`** — Full wing/room/count tree
- **`mcp_mempalace_get_aaak_spec`** — Get AAAK compression dialect specification

### Knowledge Graph (Temporal Facts)
- **`mcp_mempalace_kg_query`** — Query entity relationships with time filtering.
  - `entity` *(required)*: e.g., `"Max"`, `"MyProject"`
  - `as_of`: Date filter (`YYYY-MM-DD`) — what was true at that time
  - `direction`: `"outgoing"`, `"incoming"`, or `"both"` (default `"both"`)
- **`mcp_mempalace_kg_add`** — Add a fact: subject → predicate → object
  - `subject`, `predicate`, `object` *(required)*
  - `valid_from`: When this became true
  - `source_closet`: Source reference
- **`mcp_mempalace_kg_invalidate`** — Mark a fact as no longer true
  - `subject`, `predicate`, `object` *(required)*
  - `ended`: When it stopped being true (default: today)
- **`mcp_mempalace_kg_timeline`** — Chronological story of an entity
  - `entity`: Optional filter (omits for all events)
- **`mcp_mempalace_kg_stats`** — Graph overview: entities, triples, relationship types

### Palace Graph (Cross-Domain Connections)
- **`mcp_mempalace_traverse`** — Walk from a room to find connected ideas across wings
  - `start_room` *(required)*
  - `max_hops`: Connection depth (default `2`)
- **`mcp_mempalace_find_tunnels`** — Find rooms that bridge two wings
  - `wing_a`, `wing_b` *(required)*
- **`mcp_mempalace_graph_stats`** — Graph connectivity overview

### Write
- **`mcp_mempalace_add_drawer`** — Store verbatim content into a wing/room
  - `wing`, `room`, `content` *(required)*
  - `source_file`: Optional source reference
  - *Checks for duplicates automatically*
- **`mcp_mempalace_delete_drawer`** — Remove a drawer by ID
  - `drawer_id` *(required)*
- **`mcp_mempalace_diary_write`** — Write a session diary entry
  - `agent_name` *(required)*: Your name/identifier
  - `entry` *(required)*: What happened, what you learned, what matters
  - `topic`: Category tag (default `"general"`)
- **`mcp_mempalace_diary_read`** — Read recent diary entries
  - `agent_name` *(required)*
  - `last_n`: Number of entries (default `10`)

## Auto-Save Integration

Sessions are automatically mined every 15 minutes via cron job `mempalace-auto-save`.

**Hermes Palace Heartbeat** (active structured saves):
- `~/.hermes/hooks/hermes_palace_heartbeat.sh` — check if checkpoint save is due
- `~/.hermes/hooks/hermes_palace_heartbeat.sh --precompact` — emergency save check
- `~/.hermes/hooks/hermes_palace_heartbeat.sh --ack` — acknowledge save completed
- Protocol defined in `~/.hermes/HEARTBEAT.md`

Legacy hooks (for Claude Code / Codex CLI):
- `~/.hermes/hooks/mempal_save_hook.sh` — trigger manual save checkpoint
- `~/.hermes/hooks/mempal_precompact_hook.sh` — emergency pre-compaction save

**Cron job danger — never mine a full directory from a scheduler:**
If a cron job runs `mempalace mine <directory> --mode convos` on a recurring interval,
each invocation scans the **entire** directory. When the directory grows large enough
that mining takes longer than the interval, overlapping instances pile up, consume
all CPU/RAM, and bloat the palace with duplicate drawers. **Always use event-driven
hooks (mine a single staged file) rather than polling cron jobs (mine a directory).**
If you must use cron, add a single-instance guard (`flock` or PID file check) and
a `--limit` flag to prevent unbounded runs.

### Auto-Save Hook Execution Workflow (Hermes Sessions)

When running `mempalace mine` on `/home/elvis/.hermes/sessions/` as a cron job, follow this checklist to avoid segfaults, stale processes, and incomplete runs.

#### 1. Check for existing mining processes
Before starting, verify no other `mempalace mine` process is already running:
```bash
ps aux | grep -i mempalace | grep -v grep
```

If a process is found:
- Check its elapsed time and CPU: `ps -p <pid> -o pid,cmd,pcpu,etime`
- **If running for >30 min with 300%+ CPU and low progress**, it is likely stuck on mixed file types (see pitfall below)
- **If running for >10 min with 0% CPU and threads in `futex_do_wait`** (`ps -L -p <pid> -o tid,stat,wchan`), the HNSW index is corrupted and the process is deadlocked. Kill it and run `mempalace repair` before restarting.
- **If it is a new process (<10 min) mining from a staging directory (`/tmp/mempalace_staging/` or similar), another session is likely performing recovery.** Do NOT interfere — let it finish.
- SIGTERM the stale process: `kill -15 <pid>`
- Verify palace health with a quick `collection.add()` test (see HNSW corruption section) before launching a new miner

#### 2. Sanitize the directory (in-place staging)
Hermes `sessions/` directories accumulate `request_dump_*.json` artifacts that cause segfaults or extreme slowness. Temporarily move them out:
```bash
mkdir -p /tmp/request_dumps_hold
mv /home/elvis/.hermes/sessions/request_dump_*.json /tmp/request_dumps_hold/
```

#### 3. Start mining in the background
Run the mining job as a background process so it survives foreground timeouts:
```bash
mempalace mine /home/elvis/.hermes/sessions/ --mode convos
```

#### 4. Launch a restore watcher
Cron jobs cannot block for hours. Start a background watcher to restore request dumps when mining finishes:
```bash
(while kill -0 <mining_pid> 2>/dev/null; do sleep 30; done; mv /tmp/request_dumps_hold/request_dump_*.json /home/elvis/.hermes/sessions/ 2>/dev/null; rmdir /tmp/request_dumps_hold 2>/dev/null; echo "Restored $(date)") &
```

#### 5. Verify mid-run progress via direct ChromaDB query
`mempalace status` is sampled and lags. Use direct ChromaDB queries to track real progress while the background job runs:
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import chromadb
client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
collection = client.get_or_create_collection('mempalace_drawers')
results = collection.get(where={'wing': 'sessions'})
sources = set(m.get('source_file', '') for m in results['metadatas'])
print(f'Total unique sources filed: {len(sources)}')
"
```

Calculate rate and ETA:
- Note sources filed at two time points
- `sources_per_minute = (sources2 - sources1) / minutes_elapsed`
- `ETA_minutes = remaining_sources / sources_per_minute`
- Typical clean-directory rate: 6–10 sources/minute for a large palace

#### 6. Final verification
After mining completes:
- Confirm `chroma.sqlite3` timestamp updated: `ls -l /home/elvis/.mempalace/palace/chroma.sqlite3`
- Run a direct ChromaDB count to verify total drawers (see Pitfalls section below for exact query)
- Confirm request dumps were restored by the watcher: `ls /home/elvis/.hermes/sessions/request_dump_*.json | wc -l`

## Setup

If MemPalace needs installation or re-initialization:

```bash
pip install mempalace
mempalace init ~/my-convos
mempalace mine ~/my-convos
```

### Hermes MCP Config

MemPalace is already configured as an MCP server in Hermes. If you need to re-add it:

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "python3",
      "args": ["-m", "mempalace.mcp_server"]
    }
  }
}
```

## Quick Reference

**Search for context:**
```python
# Semantic search — keep query short, no system prompt context
mcp_mempalace_search(query="Redis decision against")

# Knowledge graph query
mcp_mempalace_kg_query(entity="ProjectX")

# Specific wing/room
mcp_mempalace_search(query="API design", wing="myproject", room="backend")

# Traverse cross-wing connections
mcp_mempalace_traverse(start_room="auth-migration", max_hops=2)
```

**Add to memory:**
```python
# Check for duplicates first (optional but recommended)
mcp_mempalace_check_duplicate(
    content="Decided to use PostgreSQL over MySQL because...",
    threshold=0.87
)

# File verbatim content
mcp_mempalace_add_drawer(
    wing="myproject",
    room="decisions",
    content="Decided to use PostgreSQL over MySQL because..."
)

# Add KG fact
mcp_mempalace_kg_add(
    subject="User",
    predicate="prefers",
    object="dark themes"
)

# Diary entry in AAAK format
mcp_mempalace_diary_write(
    agent_name="Hermes",
    entry="SESSION:2026-04-20|built.mempalace.hooks+configured.cron|milestone:memory.active|★★★"
)
```

## CLI Fallback

If MCP tools aren't available yet, use the CLI:
- `mempalace search "query"` — search
  - Options: `--wing WING`, `--room ROOM`, `--results N`
- `mempalace status` — overview
- `mempalace mine <dir>` — ingest files
  - Options: `--mode convos` for conversation mining
- `mempalace repair` — rebuild vector index from stored data (fixes HNSW segfaults after corruption)
- `mempalace wake-up` — get L0+L1 context

## Tips

- Search is semantic (meaning-based), not keyword. "What did we discuss about database performance?" works better than "database".
- The knowledge graph stores typed relationships with time windows. Use it for facts about people and projects — it knows WHEN things were true.
- Diary entries accumulate across sessions. Write one at the end of each conversation to build continuity.
- Use `mcp_mempalace_check_duplicate` before storing new content to avoid duplicates. Try `threshold=0.85–0.87` for near-duplicate detection.
- The AAAK dialect (from `mcp_mempalace_status`) is a compressed notation for efficient storage. Read it naturally — expand codes mentally, treat *markers* as emotional context.
- When filing, choose the narrowest wing+room that fits. Metadata filtering at query time is only as good as your organization at write time.

## Pitfalls & Verification

### `mempalace status` / `mcp_mempalace_list_wings` omit wings outside the top sample
Both the CLI `status` command and MCP `mcp_mempalace_status` / `mcp_mempalace_list_wings` use a sampling/aggregation approach that, in large palaces, surfaces only the largest wings (commonly just `dokploy` and `misjustice-alliance`). They will:
- Report a truncated or capped drawer count (e.g., exactly **10,000** via CLI, regardless of true size)
- Completely omit smaller wings such as `sessions`, `hermes`, `ryno-prd`, etc.
- **Fix:** Do not rely on `status` or `list_wings` to verify a mining run. Instead:
  1. Use `mempalace search "<session_id>"` (CLI) or `mcp_mempalace_search(query="...", wing="sessions")` (MCP) to confirm content is retrievable.
  2. If you know the wing name, use `mcp_mempalace_list_rooms(wing="<wing>")` — it returns accurate room-level drawer counts even when the wing is hidden from `status` / `list_wings`.
  3. If both CLI and MCP search are inconclusive, query the ChromaDB collection directly via the pipx venv Python (more reliable than raw SQL since schema varies by version):
     ```bash
     /home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
     import chromadb
     client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
     collection = client.get_or_create_collection('mempalace_drawers')
     total = collection.count()
     print(f'Total drawers: {total}')
     # Query a specific wing (exact syntax depends on installed ChromaDB version)
     try:
         results = collection.get(where={'wing': 'sessions'})
     except Exception:
         results = collection.get(where={'wing': {'$eq': 'sessions'}})
     print(f'Drawers in wing: {len(results[\"ids\"])}')
     # List all wings (sample if huge; cap at 50K to avoid OOM)
     sample_limit = min(total, 50000)
     all_data = collection.get(limit=sample_limit)
     wings = {}
     for meta in all_data['metadatas']:
         w = meta.get('wing', 'unknown')
         wings[w] = wings.get(w, 0) + 1
     for w, c in sorted(wings.items(), key=lambda x: -x[1]):
         print(f'  {w}: {c}')
     "
     ```
     *Note:* ChromaDB telemetry warnings in stderr are harmless. If `where={'wing': 'sessions'}` fails with an operator error, fall back to `where={'wing': {'$eq': 'sessions'}}` (or vice versa) depending on the local ChromaDB version.

### CLI search can silently return nothing
The CLI `mempalace search` has been observed returning empty results for queries that successfully match via MCP search. If verification fails on the CLI, always double-check with MCP `mcp_mempalace_search`.

### Metadata `source_file` stores absolute paths
When querying ChromaDB directly by `source_file`, the metadata stores the **full absolute path** (e.g., `/home/elvis/.hermes/sessions/session_20260421_080032.json`), not just the filename. Querying with only the basename will return zero matches.

### Post-mining verification can lag
Immediately after a successful `mempalace mine` run, the following can appear stale for a short period (seconds to minutes depending on palace size):
- **Room drawer counts** from `mcp_mempalace_list_rooms` — may not yet reflect newly filed drawers.
- **Search results** — `mcp_mempalace_search` and CLI `mempalace search` may not surface the freshest content until ChromaDB flushes its index.
- **Wing lists** — `mempalace status` and `mcp_mempalace_list_wings` are sampled/aggregated and will not show updated totals in real time.

**Reliable post-mining verification:**
1. Confirm `chroma.sqlite3` was modified at the mining timestamp (`ls -l /home/elvis/.mempalace/palace/chroma.sqlite3`).
2. Search for a unique phrase or filename from the mined content rather than counting drawers.
3. If uncertain, wait 30–60 seconds and re-run search; do not rely on room counts as the sole confirmation.
4. **Direct ChromaDB verification — sort by `filed_at`:** If you query the collection directly, do not rely solely on `Counter.most_common()` on `source_file`; a new file with ~62 drawers can be buried below older files that have identical counts. Instead, sort by the `filed_at` metadata to surface the most recently filed drawers:
   ```python
   results = collection.get(where={'wing': 'sessions'})
   indexed = sorted(enumerate(results['metadatas']),
                    key=lambda x: x[1].get('filed_at', ''),
                    reverse=True)
   # indexed[0] will be the most recently filed drawer
   ```
   This is the fastest way to confirm that a specific mining run actually wrote drawers to the palace.
5. **ChromaDB v0.6.0+ API change:** `client.list_collections()` now returns a list of **strings** (collection names), not collection objects. Use `client.get_collection(name)` to access a collection. Code written for older versions will raise `NotImplementedError`.
6. **Telemetry warnings are harmless:** `Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given` is a known non-fatal ChromaDB issue. Ignore it.

### Stale MCP server processes cause empty search results
The MCP server (`mempalace.mcp_server`) is a **long-running process** that caches the ChromaDB collection in memory. When a new mining run adds drawers to the palace, existing MCP server processes may hold a **stale cached index** that does not include the new data.

**Symptoms:**
- CLI `mempalace search "cooling" --wing terrahash-stack` returns results
- MCP `mcp_mempalace_search(query="cooling", wing="terrahash-stack")` returns empty `[]`
- `mcp_mempalace_list_rooms(wing="terrahash-stack")` shows room counts, but search with the same wing filter returns nothing
- Multiple `mempalace.mcp_server` processes visible in `ps aux` (started hours or days apart)

**Root cause:**
- The CLI spawns a fresh Python process on every invocation, loading the latest ChromaDB index
- The MCP server caches `_collection_cache` globally and never refreshes it
- After large `mempalace mine` runs, the cached collection is out of sync with the on-disk palace

**Fix:**
```bash
# Kill all stale MCP server processes
pkill -f "mempalace.mcp_server"
```
Hermes will auto-restart a fresh MCP server on the next tool call. The new process will load the current palace state.

**Workaround if MCP is still failing after restart:**
Use the CLI as a fallback:
```bash
mempalace search "query" --wing mywing --room myroom --results 10
```

### HNSW corruption during `mempalace mine` — segfaults OR deadlocks
If `mempalace mine` fails to write after a previous run crashed mid-write, the HNSW vector index is likely corrupted. Corruption manifests in **two distinct ways**:

#### Path A: Segfault (exit code 139)
- CLI `mempalace mine` crashes with `core dumped` in `chromadb/segment/impl/vector/local_hnsw.py`
- New Python processes using `chromadb.PersistentClient` also segfault
- **Collection counts can fluctuate wildly between queries** (e.g., 1,060 drawers one moment, 0 the next)

#### Path B: Deadlock/hang (no crash, 0% CPU, threads in `futex_do_wait`)
- `mempalace mine` starts but never progresses — no DB modifications, no new drawers filed
- All threads show `futex_do_wait` in `ps -L` output
- CPU drops to 0% after initial file enumeration
- Direct `collection.add()` calls hang indefinitely (not just slow — they never return)
- Existing MCP server processes may continue working fine (they loaded the index before corruption)

**Quick diagnostic test (30 seconds):**
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import chromadb, time
client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
collection = client.get_or_create_collection('mempalace_drawers')
start = time.time()
collection.add(ids=['test_hnsw'], documents=['test'], metadatas=[{'wing': 'test'}])
print(f'OK — add() completed in {time.time()-start:.2f}s')
collection.delete(ids=['test_hnsw'])
" 2>&1 | grep -v telemetry
```
If this hangs for >10s, the HNSW index is corrupted and needs repair.

**Do NOT:**
- Upgrade or downgrade `chromadb` or `chroma-hnswlib` — this does not fix index corruption and may break `mempalace` compatibility
- Delete the HNSW segment directory manually — you will lose the vector index

**Fix:**
```bash
mempalace repair
```
This rebuilds the palace vector index from stored data, backs up the old index to `/home/elvis/.mempalace/palace.backup`, and resolves both segfaults and deadlocks.

**Repair timeline expectations:**
| Palace size | Drawers | Duration | CPU | RAM |
|-------------|---------|----------|-----|-----|
| ~350 MB | ~22K | **25–30 min** | 325% | ~850 MB |
| 20+ GB | 100K+ | Can exceed 1 hour | 300%+ | 2+ GB |

During repair, monitor progress via `chroma.sqlite3` growth and `find ~/.mempalace/palace -mmin -10` for new HNSW segment files. The process is CPU-intensive with multiple threads in `R` state — 0% CPU for >5 min indicates a problem, not completion.

After repair, verify writes work before restarting the miner:
```bash
# Quick post-repair verification (should complete in <1s)
mempalace search "test" --wing sessions --results 1
```
Then run `mempalace mine` again.

### `mempalace repair` fails with `shutil.copytree` error (SQLite journal race condition)
`mempalace repair` begins by copying the existing palace to `palace.backup`. If a SQLite transaction is active when repair starts, a `.chroma.sqlite3-journal` file may exist briefly and then disappear mid-copy. This causes `shutil.copytree` to raise:
```
shutil.Error: [('/home/elvis/.mempalace/palace/chroma.sqlite3-journal', '/home/elvis/.mempalace/palace.backup/chroma.sqlite3-journal', "[Errno 2] No such file or directory...")]
```

**Fix:** Wait for any active SQLite transactions to settle (no other `mempalace` processes running), then retry `mempalace repair`. If the journal file persists, shut down any MCP server processes that may hold the database open:
```bash
pkill -f "mempalace.mcp_server"
sleep 2
mempalace repair
```

## MCP Server Down — Direct Palace Access Fallback

When `mcp_mempalace_*` tools fail with `ClosedResourceError` or the gateway reports `MCP server 'mempalace' is unreachable after N consecutive failures`, you can still read and write palace data directly while the transport is broken.

### Diagnose before bypassing

1. **Kill stale MCP processes** — cached servers may be out of sync or deadlocked:
   ```bash
   pkill -f "mempalace.mcp_server"
   ```
   Wait 10s and retry the MCP call. If it still fails, the server is likely crashing on spawn or the gateway transport is broken.

2. **Verify the palace files are intact:**
   ```bash
   python3 -c "
   import sqlite3
   for db in ['/home/elvis/.mempalace/palace/knowledge_graph.sqlite3',
              '/home/elvis/.mempalace/palace/chroma.sqlite3']:
       conn = sqlite3.connect(db)
       print(f'{db}: {conn.execute(\"PRAGMA integrity_check\").fetchone()[0]}')
       conn.close()
   "
   ```

### Read fallback — direct ChromaDB query

If MCP search is down but you need to find drawers:
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import chromadb
client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
collection = client.get_collection('mempalace_drawers')
res = collection.query(query_texts=['your search phrase'], n_results=5)
for doc in res['documents'][0]:
    print(doc[:500])
"
```

### Read fallback — direct KG query

If `mcp_mempalace_kg_query` is unavailable, query `knowledge_graph.sqlite3` directly:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/elvis/.mempalace/palace/knowledge_graph.sqlite3')
c = conn.cursor()
c.execute('SELECT subject, predicate, object, valid_from FROM triples WHERE subject = ?', ('entity_name',))
for r in c.fetchall():
    print(r)
conn.close()
"
```

### Write fallback — direct KG triple insertion

When `mcp_mempalace_kg_add` fails and you must backfill knowledge graph relationships (e.g., a post-mortem was filed but its triples were not added):

```python
import sqlite3
import uuid
from datetime import datetime

conn = sqlite3.connect('/home/elvis/.mempalace/palace/knowledge_graph.sqlite3')
c = conn.cursor()

def ensure_entity(name, etype='unknown'):
    c.execute('SELECT id FROM entities WHERE name = ?', (name,))
    row = c.fetchone()
    if row:
        return row[0]
    eid = str(uuid.uuid4())
    c.execute('INSERT INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)',
              (eid, name, etype, '{}'))
    return eid

def add_triple(subject, predicate, obj, valid_from=None, source_closet=None):
    valid_from = valid_from or datetime.now().strftime('%Y-%m-%d')
    tid = 't_' + subject + '_' + predicate + '_' + obj + '_' + str(uuid.uuid4())[:12]
    c.execute('''INSERT INTO triples
        (id, subject, predicate, object, valid_from, valid_to, confidence, source_closet, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (tid, subject, predicate, obj, valid_from, None, 1.0, source_closet, datetime.now().isoformat()))

# Example usage
ensure_entity('mempalace', 'system')
ensure_entity('palace_bloat_86GB', 'issue')
add_triple('mempalace', 'suffered_issue', 'palace_bloat_86GB',
           source_closet='infrastructure/mempalace_bloat_postmortem')
conn.commit()
conn.close()
```

**Safety rules for direct writes:**
- Backup `knowledge_graph.sqlite3` before bulk inserts (`cp ... /tmp/kg_backup.sqlite3`).
- Always `ensure_entity()` before inserting a triple — the `entities` table must contain the subject/object names or the KG will have orphaned references.
- Use deterministic or prefixed `id` values for triples (e.g., `t_<subject>_<predicate>_<object>_<uuid4>`) so accidental re-runs don't create exact duplicates.
- Set `source_closet` to the wing/room path so the triples are traceable later.

### When to use fallback vs. fix the server

- **Use fallback** for one-off urgent reads/writes when the user needs immediate results and restarting the gateway/session is not practical.
- **Fix the server** (kill stale processes, restart gateway, run `mempalace repair`) when ongoing palace operations are needed. Direct SQLite writes bypass validation layers and should not become your default workflow.

### `mempalace repair` timeout on large palaces
On very large palaces (20+ GB), `mempalace repair` can exceed foreground timeout limits. If repair is killed or times out mid-rebuild, the palace may be left with **0 drawers** because the new index was incomplete.

**Symptoms:**
- `mempalace status` shows `0 drawers`
- Direct ChromaDB query confirms `collection.count() == 0`
- `/home/elvis/.mempalace/palace.backup` exists

**Fix:**
Restore from the backup that repair created before modifying data:
```bash
mv /home/elvis/.mempalace/palace /home/elvis/.mempalace/palace.empty_repair
mv /home/elvis/.mempalace/palace.backup /home/elvis/.mempalace/palace
```

Verify restoration:
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import chromadb
client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
print(client.get_or_create_collection('mempalace_drawers').count())
"
```

The restored backup may still contain the original HNSW corruption (if any), but the data drawers are intact. Test with a tiny `mempalace mine` on one file before restarting the full run.

### Fresh palace swap strategy (when repair itself is broken)
If `mempalace repair` crashes or leaves the palace in an unusable state, and the backup is also corrupted, create a **fresh palace** and swap it in. Reading from a corrupted palace usually works fine; writing to it segfaults. Use this asymmetry to recover data.

**Diagnostic pattern:**
```bash
# Reading works even when writing segfaults
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import chromadb
c = chromadb.PersistentClient('/home/elvis/.mempalace/palace')
col = c.get_collection('mempalace_drawers')
print('Readable count:', col.count())  # Usually succeeds
"
```

**Recovery workflow:**
1. Create a fresh palace and migrate recoverable drawers (reading from old, writing to new):
   ```bash
   mkdir -p /home/elvis/.mempalace/palace_fresh
   /home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
   import chromadb, shutil, os
   old = chromadb.PersistentClient('/home/elvis/.mempalace/palace')
   new = chromadb.PersistentClient('/home/elvis/.mempalace/palace_fresh')
   old_col = old.get_collection('mempalace_drawers')
   new_col = new.create_collection('mempalace_drawers')
   total = old_col.count()
   batch_size = 500
   for offset in range(0, total, batch_size):
       batch = old_col.get(limit=batch_size, offset=offset, include=['documents', 'metadatas'])
       if batch['ids']:
           new_col.add(ids=batch['ids'], documents=batch['documents'], metadatas=batch['metadatas'])
           print(f'Migrated {min(offset + batch_size, total)}/{total}')
   "
   ```
2. Mine new content into the fresh palace:
   ```bash
   mempalace --palace /home/elvis/.mempalace/palace_fresh mine /tmp/clean_sessions --mode convos
   ```
3. Swap directories:
   ```bash
   mv /home/elvis/.mempalace/palace /home/elvis/.mempalace/palace.corrupted.$(date +%s)
   mv /home/elvis/.mempalace/palace_fresh /home/elvis/.mempalace/palace
   ```

**Note:** Migration is CPU- and I/O-intensive. For 1,000+ drawers, run the Python migration in the background and monitor `chroma.sqlite3` growth rather than blocking on completion.

**If the backup itself is corrupted (malformed sqlite):**
Repair creates the backup by copying the palace mid-operation. If repair is interrupted while writing the backup, the backup's `chroma.sqlite3` can also be malformed (`sqlite3.DatabaseError: database disk image is malformed`). In this case:

1. Preserve the old palace for possible future data recovery:
   ```bash
   mv /home/elvis/.mempalace/palace /home/elvis/.mempalace/palace.prerewrite
   mv /home/elvis/.mempalace/palace.backup /home/elvis/.mempalace/palace.corrupt_backup
   ```
2. Initialize a fresh palace:
   ```bash
   mempalace init /home/elvis/.mempalace/fresh_palace
   ```
   Or let the next `mempalace mine` auto-create a new palace.
3. Mine from a **staging directory** containing only clean conversation files (see "Mixed file types" pitfall below for staging commands).

### Mixed file types causing `mempalace mine --mode convos` segfaults or extreme slowness
A `mempalace mine <dir> --mode convos` run can **segfault (exit code -11 / SIGSEGV)** or run ** orders of magnitude slower than expected** when the target directory contains a small number of actual conversation files (`.jsonl`) mixed with a large number of unrelated files (e.g., `.json` request dumps, logs, or artifacts) that `mempalace` attempts to parse as conversations.

**Symptoms — segfault path:**
- `mempalace mine /home/elvis/.hermes/sessions/ --mode convos` segfaults after listing thousands of files
- The crash occurs during file enumeration/parse, not during `collection.add()` (unlike HNSW corruption)
- `mempalace repair` completes but finds 0 drawers, and previously filed data may become inaccessible

**Symptoms — extreme slowness path:**
- Process stays alive (no segfault), CPU remains at 300%+, and `chroma.sqlite3` continues growing
- Progress counter appears **frozen on a single file** for 10–30+ minutes
- Throughput drops to ~1–3 files per minute instead of the expected 50–100+
- A run expected to take 20–60 minutes can stretch to **10–30+ hours**
- `mempalace status` may cap at exactly **10,000** drawers even though embeddings are still being written (verify via direct ChromaDB query)

**Root cause:**
- `--mode convos` does not filter by extension; it attempts to ingest every file in the directory
- Hermes sessions directories often contain 4,000+ `request_dump_*.json` files alongside ~1,800 actual `session_*.json` conversation sessions
- Each `request_dump_*.json` file generates ~800+ embedding chunks (one per message), while a typical session generates only ~3–10
- Parsing and embedding this volume of non-conversation JSON either triggers a native segfault or saturates the embedding pipeline

**Fix — isolate target files before mining:**
```bash
# Create a clean temp directory with only conversation sessions
mkdir -p /tmp/hermes_jsonl
cp /home/elvis/.hermes/sessions/*.jsonl /tmp/hermes_jsonl/
mempalace mine /tmp/hermes_jsonl/ --mode convos
rm -rf /tmp/hermes_jsonl
```

If `.jsonl` files are unavailable and you must mine `.json` session files, filter explicitly:
```bash
mkdir -p /tmp/hermes_sessions
cp /home/elvis/.hermes/sessions/session_*.json /tmp/hermes_sessions/
mempalace mine /tmp/hermes_sessions/ --mode convos
rm -rf /tmp/hermes_sessions
```

**Alternative — in-place staging to preserve wing name and skip duplicates**
If you have already mined some content from the original directory and want to avoid creating a new wing (which would duplicate already-filed drawers due to different `source_file` paths), temporarily move the artifacts out of the directory, mine the clean directory, then restore them:

```bash
mkdir -p /tmp/request_dumps_hold
mv /home/elvis/.hermes/sessions/request_dump_*.json /tmp/request_dumps_hold/
mempalace mine /home/elvis/.hermes/sessions/ --mode convos
mv /tmp/request_dumps_hold/request_dump_*.json /home/elvis/.hermes/sessions/
rmdir /tmp/request_dumps_hold
```

This preserves the original wing name (e.g., `sessions`) and `source_file` paths, so already-filed files are correctly skipped as duplicates.

**Prevention for auto-save hooks:**
Configure cron hooks to copy only `.jsonl` files (or `session_*.json` files) to a staging directory before calling `mempalace mine`. Do not point `mempalace mine` directly at the raw Hermes `sessions/` directory.

### Large mining runs exceed foreground timeouts
`mempalace mine` on directories with thousands of files (e.g., 4,000+ Hermes session files) can take **30–60+ minutes** to complete under ideal conditions (clean, homogeneous files). On **mixed directories** containing request dumps or other non-conversation artifacts, the same job can take **10–30+ hours**. The process is CPU-intensive (300%+ utilization) and alternates between compute-bound (`Rsl`) and disk-I/O-bound (`Dsl`) states as ChromaDB vectorizes and writes chunks.

**Symptoms:**
- Foreground execution in Hermes Agent times out after 5 minutes (`exit_code 124`)
- The process was actively writing (`chroma.sqlite3` growing and timestamp updating) before the timeout killed it
- Re-running immediately starts from the beginning and will time out again
- Progress counter appears stuck on a single file for extended periods (this is normal when processing large request dumps or mixed content — verify via `chroma.sqlite3` growth, not the file counter)

**Fix:**
Run the mining job in the background so it is not subject to foreground timeout limits:
```bash
# Background — agent polls until completion
mempalace mine /home/elvis/.hermes/sessions/ --mode convos
```
Then monitor via `ps` or process polling until the job finishes. Do not start overlapping mining jobs; wait for the previous one to complete.

**AI-Agent execution note:** If an AI agent (e.g., a Hermes cron hook) is executing this workflow, avoid tight `poll`/`wait` loops — they exhaust the tool-call budget without producing progress and can leave the job orphaned when the iteration limit is hit. Instead:
1. Start the miner in background with `notify_on_complete` if your runtime supports it.
2. Verify progress by checking `chroma.sqlite3` modification time or running `ps` on the child PID **no more than once every 5–10 minutes**.
3. Do not rely on stdout or process `output_preview` for progress — `mempalace mine` buffers all output until completion.
4. If the agent must deliver a final report while the miner is still running, report that the job is in progress and include the child PID for manual verification.

### Quick Diagnostic: Miner Appears Stuck on One File
When the progress counter freezes on a single file for >10 minutes, use this checklist to decide whether the process is still making progress or should be killed.

| Check | Command | Interpretation |
|-------|---------|----------------|
| **File size** | `ls -la <file>` | If <1 MB with normal JSON, the file itself is not the bottleneck. |
| **JSON sanity** | `python3 -c "import json; d=json.load(open('<file>')); print(len(d.get('messages',[])))"` | Confirms the parser isn't choking on malformed data. |
| **Process state** | `ps -p <pid> -o pid,cmd,pcpu,etime,stat` | `R` + high CPU = compute-bound. `D` = disk-I/O-bound. `S` + 0% CPU = idle/stuck. |
| **Context switches** | `cat /proc/<pid>/status \| grep ctxt_switches` | Increasing numbers = threads are still scheduling. Flat for >2 min = deadlocked. |
| **Database growth** | `ls -la ~/.mempalace/palace/chroma.sqlite3` | Growing size + recent mtime = embeddings are still being written. Flat = no progress. |
| **Thread states** | `ps -L -p <pid> -o tid,stat,wchan` | All `futex_do_wait` = HNSW deadlock (kill + run `mempalace repair`). Mixed `R`/`D` = working. |
| **Open files** | `lsof -p <pid> \| grep chroma` | `chroma.sqlite3` open with write access = actively writing. No DB files open = process may have crashed or finished. |

**Decision matrix:**
- **chroma.sqlite3 growing** → Wait. Do not kill. Progress is real but stdout is buffered.
- **CPU high + ctxt increasing + DB flat for >5 min** → Likely livelock on mixed file types (see pitfall below). Kill and stage clean files.
- **0% CPU + all threads in futex_wait** → HNSW deadlock. Kill, run `mempalace repair`, then restart.
- **File is tiny + JSON valid + 20+ min frozen** → Bug/livelock. Kill and exclude the file from the batch.

### Monitoring a background mining job
When started via Hermes Agent's `terminal` or `process` tools, a bash wrapper spawns the actual `mempalace` child process. The wrapper PID may appear sleeping with 0% CPU even though mining is proceeding normally.

- **Find the real child PID:**
  ```bash
  pstree -p <wrapper_pid>
  # or
  ps --forest -o pid,ppid,cmd -g $(ps -o pgid= -p <wrapper_pid>)
  ```
- **Check the child directly:**
  ```bash
  ps -p <child_pid> -o pid,cmd,pcpu,pmem,etime,vsz,rss
  ```
- **Track unique source files processed.** Total drawer count can be misleading because different files generate different numbers of chunks. To estimate completion, count unique `source_file` entries in the target wing:
  ```python
  results = collection.get(where={'wing': 'sessions'})
  filed_sources = set(m.get('source_file', '') for m in results['metadatas'])
  print(f'Unique files filed: {len(filed_sources)}')
  ```
- **Empty output is normal.** `mempalace mine` buffers stdout until completion. Verify progress by watching `chroma.sqlite3` timestamps or checking child process CPU/RSS growth.
- **Do NOT kill the process just because `output_preview` is empty.** In Hermes Agent and similar environments, the absence of visible output does not mean the process is hung. Killing a working miner discards partial progress.
- **If the process exits with `-9` (SIGKILL), the system killed it — not mempalace.** This indicates the execution environment (cron timeout, agent iteration limit, OOM killer) terminated the process. The miner itself did not crash. Partial progress up to that point may have been written.
- **`lsof` confirms the process is active:** `lsof -p <pid>` shows open files. If `chroma.sqlite3` appears in the output with a growing size (`ls -lt ~/.mempalace/palace/chroma.sqlite3`), the miner is writing embeddings even though stdout is silent.
- **Expected resource profile** (reference: ~2.5 GB / 4,000+ Hermes session files, *clean* directory):
  - Duration: **20–60+ minutes**
  - CPU: **150–300%+**
  - Memory: **400–600 MB RSS**
  - Threads: **10–15** (ChromaDB HNSW + embedding workers)
  - State alternates between compute-bound (`R`) and disk-I/O-bound (`D`)
- **Mixed directory profile** (same file count but includes request dumps):
  - Duration: **10–30+ hours**
  - Progress counter may freeze on individual files for 10–30 minutes
  - Database grows steadily even when file counter does not advance

If the child PID disappears but the wrapper remains, the job finished (check exit code via `wait`). If the child is gone and `chroma.sqlite3` was not updated, investigate segfaults or disk-space issues.

### Conversation-mining wing/room naming
`mempalace mine <dir> --mode convos` auto-creates:
- **wing** = directory name (e.g., `sessions` for `~/sessions`)
- **room** = topic detection result (`technical`, `architecture`, `planning`, `decisions`, `problems`, or `general`)
To verify a convo-mining run, search with `wing="<dirname>"` rather than expecting the wing to appear in `status`.

## Palace Bloat Diagnosis & Emergency Pruning

Use this workflow when the user says the palace is "huge," "needs pruning," disk is full, or MCP is failing after rapid growth.

### Step 0 — Kill rogue background miners first
Before measuring or cleaning anything, verify that **no background `mempalace mine` process is actively re-bloating the palace** while you work. Rogue miners from previous failed sessions, cron jobs, or backgrounded hooks will continuously ingest junk and undo your cleanup.

```bash
pgrep -af "mempalace mine" | grep -v grep
```

**Kill every miner you did not intentionally start:**
```bash
pkill -f "mempalace mine"
```

**Also kill stale `mempalace repair` processes** — they compete for the same ChromaDB locks and can interfere with cleanup:
```bash
pkill -f "mempalace repair"
```

**Check for respawned miners under the gateway cgroup.** If the Hermes gateway is running as a systemd service, a rogue miner may reappear as a child process of the gateway after you kill the first one:
```bash
systemctl --user status hermes-gateway
# or
pgrep -af "mempalace mine" | grep -v grep
```
Kill any respawned miner immediately.

Wait 5 seconds and verify nothing remains:
```bash
pgrep -af "mempalace" | grep -E "mine|repair" | grep -v grep
```

If any rogue process respawns immediately, disable the auto-save hook temporarily (`chmod -x ~/.hermes/hooks/mempalace_save_hook.sh`) until cleanup is complete.

---

### Step 0b — Find and disable the spawner (cron jobs & hooks)
If miners respawn after killing them, they are being triggered by a **recurring scheduler**, not a one-off background job. Trace the spawner before continuing cleanup.

**1. Check Hermes cron jobs:**
```bash
cronjob list
# or
hermes cron list
```
Look for any job whose prompt or script contains `mempalace mine` or mines the sessions directory. Note the `job_id`.

**2. Check system cron / systemd timers:**
```bash
crontab -l
systemctl list-timers --all
ls /etc/cron.d/
```

**3. Check save hooks:**
```bash
grep -r "mempalace mine" ~/.hermes/hooks/
cat ~/.hermes/hooks/mempal_save_hook.sh
cat ~/.hermes/hooks/mempalace_save_hook.sh
```
Distinguish between:
- **Hook miners** — mine a single staged transcript file (fast, harmless)
- **Cron miners** — mine the entire sessions directory (slow, overlapping, dangerous)

**4. Remove the cron job:**
```bash
cronjob remove <job_id>
```

**5. Verify no more miners spawn:**
Wait for the original interval (e.g., 15 minutes) and re-check:
```bash
pgrep -af "mempalace mine" | grep -v grep
```
If nothing appears, the spawner is dead.

**Root cause pattern:** A cron job running `mempalace mine /home/elvis/.hermes/sessions/ --mode convos` every 15 minutes will spawn overlapping instances when each run takes >15 minutes. Each instance scans the entire directory, re-ingests already-stored transcripts (no dedup at the directory level), and piles up until CPU/memory are exhausted. **Never run a full-directory mine from a cron job without file locking or a single-instance guard.**

---

### Step 1 — Measure disk bloat sources
```bash
du -sh ~/.mempalace/*/
```
**Typical offenders:**
- `palace.backup/` — left by `mempalace repair` (often 10–20+ GB)
- `palace-backup-<timestamp>-N/` — multiple dated backups from repair or manual snapshots
- `palace.empty_repair/` — from a failed or timed-out repair
- `palace.pre_merge.*` — old pre-merge snapshots
- `palace/` itself — oversized `chroma.sqlite3` or bloated HNSW segments

**Action:** Delete all backup/restore directories immediately. They are safe to remove.
```bash
rm -rf ~/.mempalace/palace.backup ~/.mempalace/palace.empty_repair ~/.mempalace/palace.pre_merge.*
```

### Step 2 — Identify orphaned HNSW segments
ChromaDB keeps vector index segments as UUID-named directories inside `palace/`. After repairs or crashes, old segments are left behind.

Find the active segment:
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import sqlite3
conn = sqlite3.connect('/home/elvis/.mempalace/palace/chroma.sqlite3')
c = conn.cursor()
c.execute(\"SELECT id FROM segments WHERE scope = 'VECTOR'\")
print('ACTIVE:', c.fetchone()[0])
conn.close()
"
```

Delete every UUID directory **except** the active one:
```bash
active="<ACTIVE_UUID>"
for d in ~/.mempalace/palace/*-*-*-*-*; do
  [ "$(basename "$d")" = "$active" ] || rm -rf "$d"
done
```

### Step 3 — Identify garbage drawers
Query source files to find what inflated the palace:
```python
import chromadb
from collections import Counter
client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
coll = client.get_or_create_collection('mempalace_drawers')
results = coll.get(limit=coll.count())
sources = Counter(m.get('source_file', '') for m in results['metadatas'])
for src, cnt in sources.most_common(20):
    print(f'{cnt:4d}x  {src}')
```

**Common garbage patterns:**
- `request_dump_*.json` — API payload artifacts, **500–900 chunks each** (explode into hundreds of drawers due to large JSON payloads)
- `session_cron_*.json` — automated cron transcripts, low-value for memory
- Test/mining experiment wings (e.g., `hermes_batch_test`)

If you see only a handful of `request_dump_*.json` source files dominating the top-20 with counts in the hundreds, those are the primary bloat source. A typical interactive session generates 3–10 drawers; a single `request_dump_*.json` can generate 800+.

### Step 4 — Delete garbage drawers safely
Use small-batch ID deletion. Do **not** use `where` filters with `$contains` — this ChromaDB version rejects them.

```python
for attempt in range(5):
    total = coll.count()
    results = coll.get(limit=max(total, 2000))
    bad_ids = [rid for rid, meta in zip(results['ids'], results['metadatas'])
               if 'session_cron_' in meta.get('source_file', '')
               or 'request_dump' in meta.get('source_file', '')]
    if not bad_ids:
        break
    for i in range(0, len(bad_ids), 500):
        coll.delete(ids=bad_ids[i:i+500])
```

If this segfaults (exit 139), the HNSW index is corrupted — run `mempalace repair` and try again.

### Step 5 — Vacuum the SQLite DB
```bash
sqlite3 ~/.mempalace/palace/chroma.sqlite3 "VACUUM;"
```

If the `sqlite3` CLI is not available, use Python:
```bash
/home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
import sqlite3
conn = sqlite3.connect('/home/elvis/.mempalace/palace/chroma.sqlite3')
conn.execute('VACUUM')
conn.close()
"
```

### Step 6 — Controlled rebuild (nuclear option)
If incremental cleanup keeps segfaulting or the count/limit semantics are inconsistent:

1. **Back up `knowledge_graph.sqlite3` before touching anything:**
   ```bash
   cp ~/.mempalace/palace/knowledge_graph.sqlite3 /tmp/kg_backup.sqlite3
   ```

2. **Move the old palace out of the way:**
   ```bash
   mv ~/.mempalace/palace ~/.mempalace/palace.old
   ```

3. **Stage only clean interactive files.** Exclude cron transcripts, request dumps, and any `session_cron_*` files explicitly:
   ```bash
   mkdir -p /tmp/mempalace_staging
   for f in ~/.hermes/sessions/session_2026*.json ~/.hermes/sessions/session_sess_*.json; do
       basename=$(basename "$f")
       case "$basename" in
           session_cron_*) continue ;;
           request_dump_*) continue ;;
       esac
       cp "$f" /tmp/mempalace_staging/
   done
   echo "Staged $(ls /tmp/mempalace_staging/*.json | wc -l) files"
   ```

4. **Mine the staging directory in the background:**
   ```bash
   mempalace mine /tmp/mempalace_staging/ --mode convos
   ```
   Then monitor via `ps` or process polling until completion. Do not start overlapping mining jobs.

   **Watch for `InvalidCollectionException`:** If the miner crashes with `Collection <uuid> does not exist`, the collection was recreated mid-run (e.g., by a concurrent `repair` or by `rm -rf palace/*`). Clear the partial state and restart:
   ```bash
   rm -rf ~/.mempalace/palace/*
   mempalace mine /tmp/mempalace_staging/ --mode convos
   ```

5. **Restore the knowledge graph backup:**
   ```bash
   cp /tmp/kg_backup.sqlite3 ~/.mempalace/palace/knowledge_graph.sqlite3
   ```

6. **Verify the rebuild:**
   ```bash
   /home/elvis/.local/share/pipx/venvs/mempalace/bin/python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/home/elvis/.mempalace/palace')
   coll = client.get_collection('mempalace_drawers')
   print(f'Clean drawers: {coll.count()}')
   "
   ```

7. **Delete old palace and staging directory:**
   ```bash
   rm -rf ~/.mempalace/palace.old /tmp/mempalace_staging /tmp/kg_backup.sqlite3
   ```

### Step 7 — Fix the auto-save hook
The most common root cause of uncontrolled growth is `~/.hermes/hooks/mempalace_save_hook.sh` (or the legacy `mempal_save_hook.sh`) mining the **entire** sessions directory instead of just the transcript being saved.

Patch the mining block to **stage the single transcript file**:
```bash
STAGE_DIR=""
MINE_DIR=""
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    STAGE_DIR=$(mktemp -d /tmp/mempalace_hook_stage.XXXXXX)
    cp "$TRANSCRIPT_PATH" "$STAGE_DIR/"
    MINE_DIR="$STAGE_DIR"
fi
if [ -n "$MINE_DIR" ]; then
    mempalace mine "$MINE_DIR" --mode convos >> "$STATE_DIR/hook.log" 2>&1 &
    if [ -n "$STAGE_DIR" ]; then
        (sleep 30; rm -rf "$STAGE_DIR") &
    fi
fi
```

This prevents request dumps, cron sessions, and unrelated files from being ingested every time the hook fires.

---

## Post-Rebuild MCP Reconnection

After a controlled rebuild (or any `mempalace repair` that changes the palace state), the **Hermes agent's internal MCP client may enter a persistent backoff loop** if it experienced `ClosedResourceError` or segfault-related disconnects during the cleanup. Symptoms:

- `mcp_mempalace_status` returns: `MCP server 'mempalace' is unreachable after N consecutive failures. Auto-retry available in ~Xs.`
- `hermes mcp test mempalace` works fine (spawns a fresh test connection)
- Direct Python queries to ChromaDB work fine
- Only the current agent session cannot call MCP tools

**This is a session-level transport issue, not a palace issue.** The agent's cached MCP connection to the old/crashed server is dead and the backoff timer keeps extending.

**Fix:** Restart the Hermes agent session (or the gateway if running through it). The clean palace and MCP server are ready; the agent just needs a fresh connection.

## Best Practices

1. **Query before assuming** — Palace has facts your context window lost
2. **Use verbatim quotes** — When filing, preserve exact wording
3. **Organize thoughtfully** — Put content in logical wings/rooms
4. **Write regularly** — Diary entries maintain session continuity
5. **Update KG as things change** — Invalidate old facts, add new ones
6. **Let the palace breathe** — Trust search over cramming context

## Remember

> "Never guess what you can query."

The palace is your long-term memory. Use it actively.

---

## Extended MemPalace Workflows

### Broker Filesystem Bridge
When a FastAPI broker or other non-agent service needs to write job receipts to MemPalace but cannot call MCP tools directly, use the on-disk bridge pattern.
See `references/broker-filesystem-bridge.md` for the full recipe.

### Postmortem Filing
File structured post-mortems in MemPalace with full knowledge graph integration. Link root causes, timeline facts, and remediation triples.
- Formerly: `memoria-palace-postmortem`

### Explicit Search Workflows
Project research via targeted MemPalace search: multi-step query refinement, wing/room filtering, and cross-wing tunnel following.
- Formerly: `mempalace-search`

### Directory Cataloging
Systematically catalog a directory tree of documentation, code, or notes into the palace with automatic wing/room taxonomy.
- Formerly: `catalog-directory-to-palace`

---

[MemPalace](https://github.com/MemPalace/mempalace) is MIT licensed. Created by Milla Jovovich, Ben Sigman, Igor Lins e Silva, and contributors.
