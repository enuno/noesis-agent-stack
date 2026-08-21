# Claude Code Bridge Protocol

Defines the file-bridge protocol between **Noesis Praxis** (Hermes supervisor,
writing side) and **Claude Code** (on-demand development worker, reading side).
The bridge is a shared directory of durable files — no network service required.
The Hermes-side writer is the `evey-bridge` plugin (`claude_bridge_*` tools); the
Claude Code-side reader is the `noesis-bridge-check` hook + `noesis-loop` /
`noesis-status` skills, deployed by `noesis-ansible`.

## Scope

- `contracts/bridge/task.schema.json` — inbox task files
- `contracts/bridge/channel-message.schema.json` — channel.jsonl lines
- `contracts/bridge/result.schema.json` — outbox result files
- `agents/claude-code-worker/config/bridge.yaml` — deployed layout reference

## Transport

One directory (default `~/.hermes/claude-bridge`, parameterized as
`claude_code_bridge_dir` in `noesis-ansible`). Writes are atomic append/file
creates; reads use cursors to avoid reprocessing:

| Item | Writer | Reader | Cursor |
|------|--------|--------|--------|
| `channel.jsonl` | both | both | `.last_read` (Hermes), `.mother_last_read` (Claude Code) |
| `inbox/{id}.yaml` | Noesis Praxis | Claude Code | file presence (consumed once) |
| `outbox/{id}.result.yaml` | Claude Code | Noesis Praxis | moved to `active/` on read |

## Identities

- Supervisor writes `from: noesis-praxis` (current deployed plugin emits `evey`
  for backward compatibility; readers accept `noesis-praxis`, `evey`, `hermes`).
- Worker writes `from: claude-code` (readers accept `claude-code`, `mother`).

## Lifecycle

1. Noesis Praxis calls `claude_bridge_task` → writes `inbox/{task_id}.yaml`.
2. Claude Code's `UserPromptSubmit` hook reads `inbox/` + new channel lines and
   injects them as context.
3. The worker executes the task within its declared scope, writes
   `outbox/{task_id}.result.yaml`, and posts a summary to the channel.
4. Noesis Praxis calls `claude_bridge_check` → reads outbox results (moves them
   to `active/`) and new worker channel messages.
5. Channel grows → compressed to `archive/` (gz) beyond 200 lines, keeps last 50;
   archives pruned after 7 days.

## Security notes

- Bridge files may contain repo paths and task context — treat as
  confidentiality-sensitive but not secret-bearing.
- No credentials or tokens cross the bridge. Task-scoped grants stay in Hermes.
- The bridge directory is user-owned, mode 0700-equivalent where the OS allows.
- Claude Code sessions are ephemeral; no standing authority beyond the task.

## Validation

- Task files validate against `task.schema.json` before dispatch.
- Channel lines validate against `channel-message.schema.json`.
- Result files validate against `result.schema.json` before acceptance.
- The `noesis-ansible` role validates layout on deploy (`validate.yml`).
