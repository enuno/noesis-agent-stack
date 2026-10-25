# Native Delegation Enforcement — verified mechanics

Facts below were verified by reading the installed Hermes core and the
`advanced-delegation` plugin source. Paths refer to the installed checkout
(`~/.hermes/hermes-agent/`). Verify against the installed revision before
relying on a specific line number; the mechanism is the durable part.

## Child toolset derivation (the load-bearing fact)

A delegate child's toolsets come from `tools/delegate_tool_toolsets.py::_
resolve_child_toolsets`:

- With no per-task `toolsets` parameter, the child inherits the PARENT'S
  in-memory `enabled_toolsets` — not a fresh config read, not the child
  profile's own config.
- `DELEGATE_BLOCKED_TOOLS` (`delegate_task`, `clarify`, `memory`,
  `send_message`, `cronjob_manage`) plus the `delegation` and `kanban`
  toolsets are stripped for non-orchestrator roles. Role is depth-derived:
  with the default `delegation.max_spawn_depth: 1` every first-level child
  is a leaf, so nested delegation is always stripped.
- The child `AIAgent` receives the resolved lists as explicit constructor
  arguments; they are authoritative (`model_tools.get_tool_definitions`),
  so the child profile's own `agent.enabled_toolsets` does NOT narrow (or
  widen) a delegate child.
- The per-task `toolsets` narrowing parameter exists in core but is not
  guaranteed to be exposed on a given session's `delegate_task` tool
  surface — check the live schema before relying on it.
- `delegation.inherit_mcp_toolsets` (default TRUE) re-appends the parent's
  MCP toolsets to a narrowed child; set it `false` when MCP/network tools
  must be absent.

Consequence: a running supervisor session cannot narrow its own future
children by editing config — its in-memory toolset is fixed. A FRESH parent
launched with `-t/--toolsets` is the supported way to get a restricted
child surface.

## The restricted-parent, zero-tool-child recipe

1. Launch the parent oneshot with `-t delegation` (supported flag; the
   toolset named `delegation` carries exactly `delegate_task`).
   `-t/--toolsets` also applies the MCP server filter
   (`set_mcp_server_filter`), so no MCP servers spawn.
2. Parent tool surface = {delegate_task}. Plugin tools cannot re-enter:
   plugins register their tools under their own toolset names, and the
   registry merge only adds tools registered INTO an enabled toolset name.
3. Dispatch one task. The child inherits ["delegation"], the leaf strip
   removes it, and the child is built with an empty toolset — zero tools.
4. The zero-tool child answers from its prompt; its final message returns
   via the inline synchronous join (oneshot declares a stateless channel,
   so `delegate_task` joins inline instead of going background).
5. The restriction is schema-level: absent tools never enter the function
   schema and cannot be dispatched. This is not a prompt convention.

## Iteration and approval controls

- `delegation.max_iterations` is the per-child iteration cap and is
  CONFIG-AUTHORITATIVE: `delegate_task` explicitly ignores a caller-supplied
  max_iterations. The child's exhaustion is recorded as
  `exit_reason == "max_iterations"`.
- `--max-turns` on the CLI bounds the PARENT session only; it is not a
  child control.
- Child command approval is deny-by-default: the subagent worker installs a
  non-interactive deny callback unless `delegation.subagent_auto_approve:
  true` (opt-in YOLO with audit warnings). A `/yolo` session bypass exists
  per session — never combine it with governance profiles.
- There is NO native hard wall-clock limit. Bounded-turn and supervision
  statements must be labeled as such; never call a supervised session
  time-bounded or unattended.

## CLI flag consumption (parser acceptance is not behavior)

A flag can parse successfully yet be silently ignored. `main.py` defines
`_CHAT_PASSTHROUGH` — the exact tuple of CLI args `cmd_chat` forwards into
the chat runtime. `--usage-file`, for example, is defined at top level
(`-z` oneshot path, honored via `_run_and_exit_oneshot`) but is NOT in
`_CHAT_PASSTHROUGH`, so `hermes chat ... --oneshot --usage-file X` accepts
and discards it. Before baking any flag into an operator launch command,
verify it is both (a) present in `hermes <subcmd> --help` on the installed
binary and (b) actually consumed on that code path (grep the passthrough
tuple / call site). Decide from evidence which flags survive; never leave a
"delete this flag and relaunch" instruction for the operator to improvise.

## Delegation state location

Per-profile state lives at `~/.hermes/profiles/<profile>/state.db` (it
carries the `async_delegations` table), NOT `~/.hermes/state.db`. Correlate
post-flight cleanup by the pilot's own identifiers (delegation/subagent/
session ids from the stream-json log) against that table — never a
whole-table count. The synchronous inline join (oneshot stateless channel)
may write no row at all; absence of a row is a stated property of the sync
path, not cleanup proof by itself. Process evidence (pgrep/no matching
parent) is primary for termination.

## advanced-delegation profile_routes

Configuration lives in the ACTIVE profile's config.yaml:

```yaml
delegation:
  backend: profile_routes
  inherit_mcp_toolsets: false
  max_iterations: 12
  backends:
    profile_routes:
      profiles:
        - name: noesis-architect
          description: one line the parent model sees
      default: noesis-architect   # routes profile-less tasks
```

- When the backend is active, `delegate_task` gains a `profile` enum
  parameter listing exactly the allowlist. A task without `profile` runs
  as `default` when set, else the parent's own route.
- The routed child binds the named profile's home: its own model,
  credentials, skills, SOUL.md, secret scope, and terminal-env policy
  (`delegated_profile_scope`). The child route's provider readiness is the
  NAMED PROFILE's route — never assume one specialist's provider is
  another's, and check authenticated-pool presence (values never read).
- The plugin supplies no hooks, middleware, or enforcement of its own; the
  route is a binding, not a gate. No expected_epoch or approved-pair
  semantics exist natively — record route decisions as procedural
  observations, never as enforced facts.

## Pilot governance checklist

- Durable pilot brief: pilot id, exact named profile, task, selected
  provider/model, effective tools, limits, expected result, stop/rollback
  conditions.
- Config changes: pilot-scoped only, 0600 backups, non-secret diff
  recorded, exact old settings preserved for restoration.
- Supervisor stands down: the operator (or an eligible executor) launches
  the restricted parent; never mutate the running supervisor's tool
  surface, never leave duplicate supervisors on one pilot.
- Evidence: native SQLite delegation id correlated with the pilot id as the
  single execution-state authority; do not hand-append invented events to
  `tasks.jsonl`; use a distinctly labeled pilot evidence artifact.
- Post-pilot: independent eligible review before any allowlist expansion;
  restore configs from backup; do not reset SQLite or erase sessions.
