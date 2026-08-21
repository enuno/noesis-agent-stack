# Decision: Claude Code Bridge as an On-Demand Development Lane

**Status:** Accepted · **Date:** 2026-08-21 · **Owner:** Noesis Praxis
**Scope:** `noesis-agent-stack` (contract) + `noesis-ansible` (deployment)

---

## Context

The stack needs a way to delegate bounded development tasks — code changes,
patches, reviews, new files — to **Claude Code** (subscription frontier models)
under Noesis Praxis supervision. `noesis-clawdev` (OpenClaw) remains the
persistent development worker; the operator also wants the option of an
on-demand Claude Code lane that runs as operator-visible interactive sessions.

The `evey-bridge-plugin` (Claude Code ↔ hermes-agent bridge) already exists:
a file bridge (`channel.jsonl`, `inbox/`, `outbox/`) plus a Hermes-side plugin
(`evey-bridge` providing `claude_bridge_task` / `claude_bridge_message` /
`claude_bridge_check`). The plugin's hardcoded `/mnt/v/evey` path and Evey
naming do not fit the Noesis stack.

## Decision

1. **Introduce `claude-code-worker` as an ephemeral worker lane**, not a third
   persistent agent. The charter's two-persistent-agent invariant is preserved:
   every Claude Code bridge session is one bounded task with explicit scope and
   a structured result.
2. **Canonicalize the file-bridge protocol in `noesis-agent-stack`**:
   - `agents/claude-code-worker/` — AGENT.md (auto-loaded by Claude Code),
     RUNBOOK.md, config/bridge.yaml.
   - `contracts/bridge/` — task, channel-message, and result JSON schemas +
     protocol.md.
   - Extend `contracts/handoffs/broker-job.schema.json` and
     `contracts/broker-api/job.schema.json` with the `claude-code-worker`
     target, bounded dev capabilities (`git_read`, `git_write`, `file_read`,
     `file_write`, `bash_exec`, `run_tests`), and a `bridge` callback type.
3. **Deploy via `noesis-ansible`** with a new `claude_code_bridge` role:
   - Bridge directories under `~/.hermes/claude-bridge/` (matches the Hermes
     plugin's `$HERMES_HOME/claude-bridge` default), parameterized as
     `claude_code_bridge_dir`.
   - Claude Code hook (`noesis-bridge-check.py`) registered on
     `UserPromptSubmit` + `Stop`; `noesis-loop` / `noesis-status` skills.
   - Hermes-side `evey-bridge` plugin synced (unchanged origin strings for
     backward compatibility; readers accept `noesis-praxis`, `evey`, `hermes`).
   - Wired into `master-stack.yml` behind `noesispraxis_enable_claude_code_bridge`.
4. **Legacy SQLite MCP bridge is out of scope** for the Noesis deployment: the
   live Hermes plugin is file-based. The Claude Code hook in the Noesis role
   reads only the file bridge.

## Consequences

- **Positive:** Noesis Praxis can dispatch dev tasks to Claude Code today via
  the existing `claude_bridge_*` tools; the deployed hook surfaces tasks in
  Claude Code sessions; results flow back to `outbox/`.
- **Positive:** Policy stays canonical (two persistent agents); the bridge lane
  is documented as ephemeral in `shared/POLICY.global.md`.
- **Trade-off:** `created_by: evey` and `from: evey` remain in the deployed
  Hermes plugin for compatibility; canonical Noesis identity
  (`noesis-praxis`) is documented as the target for a future plugin revision.
- **Watch item:** the external `42-evey-hermes-plugins-sync.sh` script could
  overwrite the deployed `evey-bridge` plugin; the Ansible role is the
  source-of-truth sync for the Noesis flavor.

## Files

- `agents/claude-code-worker/{AGENT.md,RUNBOOK.md,README.md,config/bridge.yaml}`
- `contracts/bridge/{protocol.md,task.schema.json,channel-message.schema.json,result.schema.json}`
- `contracts/handoffs/broker-job.schema.json` (extended)
- `contracts/broker-api/job.schema.json` (extended)
- `shared/POLICY.global.md` (§1 bridge lane)
- `noesis-ansible`: `roles/claude_code_bridge/`, `playbooks/claude-code-bridge.yml`,
  `group_vars/all.yml` toggle, `playbooks/master-stack.yml` phase

## Verification

- `ansible-playbook --syntax-check playbooks/claude-code-bridge.yml`
- `ansible-playbook --check playbooks/claude-code-bridge.yml`
- Live deploy: bridge dirs, hook registered in `~/.claude/settings.json`,
  skills present, Hermes plugin present.
- JSON schema files lint clean (`python3 -m json.tool`).
- `git diff --check` clean in both repos.
