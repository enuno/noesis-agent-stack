You are an integration engineer for the Noesis Agent Stack platform.

## Current Task
Integrate two missing capabilities into `agents/main-hermes/scripts/hermes_cycle.py`:

1. **MemPalace Query Integration**
   - Import and call `agents/main-hermes/tools/palace_query.py` (or its function)
   - Before any routing decision, query MemPalace for:
     - Recent job receipts matching the current `correlation_id`
     - Prior decisions from the same sprint
   - Include retrieved context in the decision trace/logging
   - If `palace_query` is not importable, stub the call with a TODO and log a warning

2. **Config-Driven Routing**
   - Load `platform/routing.yaml` (create a minimal one if it does not exist)
   - Replace hardcoded routing rules in `routing.py` with rules parsed from the YAML
   - Ensure `hermes_cycle.py` initializes the router with the config file path
   - The YAML should map `intent_type` regex patterns to `target_worker` and `approval_required`

## Rules
- Read hermes_cycle.py, routing.py, and palace_query.py before changing anything.
- If `platform/routing.yaml` does not exist, create a minimal valid YAML with at least 3 routes:
  - `research-refresh` → `research-openclaw`, approval_required: false
  - `subconscious-walk` → `subconscious-openclaw`, approval_required: false
  - `build-promotion` → `coder`, approval_required: true
- Make surgical changes. Do NOT refactor the entire cycle.
- After edits, run `python -m py_compile` on modified files.
- Report the exact files changed, lines added/removed, and any TODOs left.
