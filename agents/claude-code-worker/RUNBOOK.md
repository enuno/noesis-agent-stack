# Noesis Claude Code Worker — Operational Runbook

**Runtime:** Claude Code · **Agent:** claude-code-worker · **Parent:** noesis-praxis
**Version:** 1.0.0 · **Updated:** 2026-08-21

---

## 1. Startup / deployment

Deployment is owned by `noesis-ansible` (playbook: `claude-code-bridge.yml`,
role: `claude_code_bridge`). The role:

1. Creates the bridge directories (`~/.hermes/claude-bridge/` by default:
   `inbox/`, `outbox/`, `active/`, `archive/`, `channel.jsonl`, `.last_read`).
2. Installs the Claude Code bridge hook into `~/.claude/hooks/` and registers it
   for `UserPromptSubmit` and `Stop` events in `~/.claude/settings.json`.
3. Installs the `noesis-loop` and `noesis-status` skills into `~/.claude/skills/`.
4. Syncs the Hermes-side `evey-bridge` plugin into `~/.hermes/plugins/` (provides
   `claude_bridge_task` / `claude_bridge_message` / `claude_bridge_check`).

```bash
ansible-playbook -i inventory/local/hosts.ini playbooks/claude-code-bridge.yml
```

Start an interactive worker session from the target repo:

```bash
cd ~/projects/<repo>
claude
```

The hook polls the bridge on every prompt; `noesis-loop` drives the task cycle.

## 2. Health check

```bash
# Bridge layout present?
ls ~/.hermes/claude-bridge/{inbox,outbox,active,archive} ~/.hermes/claude-bridge/channel.jsonl

# Hook installed + registered?
ls -la ~/.claude/hooks/noesis-bridge-check.py
grep -c "noesis-bridge-check" ~/.claude/settings.json

# Skills installed?
ls ~/.claude/skills/noesis-loop ~/.claude/skills/noesis-status

# Hermes plugin present?
ls ~/.hermes/plugins/evey-bridge/__init__.py
```

Healthy = directories exist, hook registered, skills present, plugin present,
no unprocessed inbox backlog (unless intended).

## 3. Receiving a task

1. The hook injects pending inbox tasks / channel messages on `UserPromptSubmit`.
2. The worker validates: `type`, `description` presence, scope, priority.
3. The worker acknowledges via channel.jsonl (`from: claude-code`) and starts.

If validation fails → return `status: failed`,
`failure_classification: validation` and do NOT execute.

## 4. Execution

- Operate inside the task scope and the named repo paths.
- Stay within the task's declared type and constraints.
- Emit milestone messages to the channel for long tasks.
- On an external-side-effect boundary without a grant → stop, classify, return.

## 5. Completion

Write `outbox/{task_id}.result.yaml` (see `AGENT.md` structured result contract):

```yaml
task_id: <task_id>
status: completed
summary: ...
artifacts: [...]
test_results: {passed: N, failed: N, skipped: N}
```

Hermes collects it via `claude_bridge_check`.

## 6. Failure classification

| Class | Meaning | Supervisor action |
|-------|---------|-------------------|
| `timeout` | Exceeded assigned deadline | Retry with revised budget or investigate |
| `credential` | Missing/invalid scoped credential | Re-issue task or check Bitwarden secret |
| `tool_error` | Tool failure within scope | Retry idempotent op; else escalate |
| `policy_block` | Grant/scope/guardrail violation | Do NOT retry; review policy |
| `validation` | Task payload or result failed schema checks | Re-dispatch with corrected task |
| `other` | Unclassified | Manual triage by Noesis Praxis |

## 7. Channel etiquette

- Messages from Noesis Praxis arrive as `from: noesis-praxis` (legacy: `evey`).
- Reply as `from: claude-code` with ISO-8601 timestamps.
- Keep messages concise; move detail into outbox result files.

## 8. Escalation

Escalate to Noesis Praxis on: repeated failures, policy blocks, budget breach,
suspected secret exposure, or any R2/R3 boundary encountered without a grant.
Never silently continue past a boundary.
