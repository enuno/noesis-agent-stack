# Hermes Palace Heartbeat

Replicates Claude Code's `Stop` and `PreCompact` hook behavior for Hermes Agent.
Ensures MemPalace is actively used — not just passively mined by cron.

## Principle

> The AI does the actual filing — it knows the conversation context, so it classifies
> memories into the right wings/rooms/halls. The heartbeat just tells it **WHEN** to save.

## Trigger Conditions

| Trigger | When It Fires | Action Required |
|---------|--------------|-----------------|
| **Checkpoint Save** | Every 15 user exchanges | Pause. Save key topics, decisions, quotes, code. Classify into wings/rooms/halls. Write diary entry. Acknowledge heartbeat. Continue. |
| **PreCompact Save** | Before context compaction, session end, or very long operation | Emergency save. Save **everything** — all topics, unresolved items, decisions, code. Be thorough. Write comprehensive diary entry. Acknowledge heartbeat. |
| **Cron Mining** | Every 15 minutes (background) | Already handled by `mempalace-auto-save` cron job. Passive session ingestion. |

## How to Check

```bash
# Check if a checkpoint save is due
~/.hermes/hooks/hermes_palace_heartbeat.sh

# Force a precompact/emergency save check
~/.hermes/hooks/hermes_palace_heartbeat.sh --precompact

# After performing a save, acknowledge it
~/.hermes/hooks/hermes_palace_heartbeat.sh --ack
```

## Current State

```json
{
  "last_save_count": 0,
  "last_save_time": null,
  "session_file": null,
  "save_interval": 15
}
```

> This state is maintained in `~/.mempalace/hook_state/hermes_heartbeat.json`.

## Save Protocol (What to Do When Triggered)

### 1. Checkpoint Save (Every 15 exchanges)

Scan the recent conversation for:
- **Decisions made** → `hall_facts` in relevant wing/room
- **Code written or modified** → verbatim drawer in `wing_code` or project wing
- **Key quotes or requirements** → verbatim drawer
- **Unresolved questions or follow-ups** → note them so they survive compaction
- **User preferences revealed** → `hall_preferences` or KG fact

Then:
- `mcp_mempalace_add_drawer` for verbatim content (check duplicate first)
- `mcp_mempalace_kg_add` for new stable facts
- `mcp_mempalace_diary_write` for session continuity (AAAK format)
- Run `~/.hermes/hooks/hermes_palace_heartbeat.sh --ack`

### 2. PreCompact Save (Emergency)

Same as checkpoint but **more thorough**:
- Save *everything* that might be lost
- Include context that seems ephemeral but might matter later
- Write a longer diary entry capturing the full arc of the session
- Do NOT skip this — compaction destroys detail

### 3. Navigation After Saving

Use the palace structure actively:
- `mcp_mempalace_traverse(start_room="<topic>")` — follow threads across wings
- `mcp_mempalace_find_tunnels(wing_a="<project>", wing_b="<project>")` — discover cross-project connections
- Shared room names are bridges between wings

## Palace Structure Reminder

```
WING (project/person)
  ├── hall_facts        → decisions, locked-in choices
  ├── hall_events       → sessions, milestones, debugging
  ├── hall_discoveries  → breakthroughs, new insights
  ├── hall_preferences  → habits, likes, opinions
  └── hall_advice       → recommendations, solutions
       └── Room (topic: auth-migration, ci-pipeline, etc.)
            └── Drawer (verbatim text chunk)

TUNNEL → when the same room exists in multiple wings, the graph connects them
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_SAVE_INTERVAL` | `15` | User exchanges between checkpoint saves |
| `HERMES_SESSIONS_DIR` | `~/.hermes/sessions` | Where session JSONL files live |
| `MEMPALACE_STATE_DIR` | `~/.mempalace/hook_state` | Hook state storage |
| `MEMPAL_PYTHON` | auto-resolved | Python interpreter override |

## Hook Log

Check `~/.mempalace/hook_state/hook.log` for heartbeat history.

## Integration with SOUL.md

This heartbeat is Layer 1 behavior. `SOUL.md` mandates that Hermes:
1. Query the palace before asserting memory-dependent claims
2. Run checkpoint saves every 15 exchanges
3. Run precompact saves before context loss
4. Use wings/rooms/halls for structured organization
5. Write diary entries in AAAK format
6. Never guess what can be queried
