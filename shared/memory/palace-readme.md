# MemPalace — Agent Read/Write Guide

MemPalace is the platform's persistent semantic memory. It provides cross-session continuity and high-recall retrieval across all agent operations with zero cloud dependency.

## Structure

| Level | Description |
|-------|-------------|
| **Wings** | People or projects (e.g., `wing_platform`, `wing_research`) |
| **Halls** | Broad domains within a wing |
| **Rooms** | Specific topics within a hall |
| **Drawers** | Individual memory chunks (verbatim text, findings, transcripts) |
| **Tunnels** | Cross-wing connections via shared room names |
| **Knowledge Graph** | Entity-relationship facts with time validity |
| **Diary** | Per-agent session summaries and learnings |

## How Agents Read

1. **Query on wake-up:** Before making decisions, agents query the palace for prior decisions, operator preferences, and project state.
2. **KG lookup:** Use `mcp_mempalace_kg_query` to traverse entity relationships (e.g., "What projects depend on PostgreSQL?").
3. **Semantic search:** Use `mcp_mempalace_search` with natural-language hints to find relevant drawers.
4. **Diary read:** Review recent diary entries from self and related agents to establish context.

## How Agents Write

1. **Checkpoint saves:** Every 15 minutes during long sessions, write incremental progress to the appropriate room.
2. **Pre-compact saves:** Emergency save before compaction or resource-constrained operations.
3. **End-of-session diary write:** Record what happened, what was learned, and what matters.
4. **KG updates:** When facts change, invalidate old triples and add new ones with timestamps.
5. **Broker receipt hook:** The broker automatically writes job receipts and normalized events to the `broker/jobs` room.

## Write Isolation

- **Research** writes to `research-vault` wing.
- **Subconscious** writes to `subconscious-room` wing.
- **Broker hook** writes to `broker` wing.
- **Hermes** reads cross-wing but writes only to `hermes` wing and shared handoffs.
- Downstream agents (coder, qa) read relevant wings but write only to their own.

## Deduplication

Before writing, prefer `mcp_mempalace_check_duplicate` to avoid drawer bloat. The broker hook and agents should stage large mining operations rather than streaming every intermediate thought to the palace.

## Integration with Broker Artifacts

Jobs may reference palace artifacts by drawer ID using the `artifact_type: palace_drawer_ref` in `artifact.schema.json`. This lets workers pass memory references instead of duplicating large verbatim content.
