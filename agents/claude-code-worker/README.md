# Noesis Claude Code Worker — Profile

**Runtime:** Claude Code (local CLI, subscription) · **Agent:** claude-code-worker · **Parent:** noesis-praxis
**Transport:** Claude Code bridge (file bridge under `~/.hermes/claude-bridge/`)
**Version:** 1.0.0 · **Updated:** 2026-08-21

## What this profile is

`claude-code-worker` is the canonical definition of a **Claude Code session acting as
an on-demand development worker** in the Noesis stack. Noesis Praxis (Hermes)
delegates bounded development tasks — code changes, patches, reviews, new files,
bounded research — to Claude Code by writing a task into the bridge `inbox/`.
A Claude Code session ("Mother" role, loaded with `noesis-loop` / `noesis-status`
skills and the bridge hook) picks up the task, executes it within the scope defined
in the task file, writes the result to the bridge `outbox/`, and Hermes collects it
via `claude_bridge_check`.

## Charter alignment

The stack charter defines **exactly two persistent agents**: `noesis-praxis` (Hermes)
and `noesis-clawdev` (OpenClaw). This profile does **not** create a third persistent
agent. Every Claude Code bridge session is **ephemeral**: one bounded task, explicit
success criteria, task/trace IDs, expiry, risk tier, and a structured result. No
Claude Code session may self-authorize beyond the task it was dispatched for.

## Relationship to noesis-clawdev

`noesis-clawdev` is the persistent OpenClaw development worker. `claude-code-worker`
is the **on-demand Claude Code lane** for subscription-frontier development work —
useful when the operator wants Claude Code (Opus-class models) handling a specific
repo task with human-visible interactive sessions, without spinning up a container
worker. Routing between the two lanes is a Noesis Praxis decision based on task fit,
availability, and operator preference.

## Files

- `AGENT.md` — full agent contract: persona, responsibilities, non-authorities, task contract, structured result. Auto-loaded by Claude Code in the working directory.
- `RUNBOOK.md` — operational runbook (startup, job lifecycle, failure classification, escalation)
- `config/bridge.yaml` — bridge path/protocol reference matching the deployed role

## Deployment

Deployment is owned by `noesis-ansible`:

```bash
ansible-playbook -i inventory/local/hosts.ini playbooks/claude-code-bridge.yml
```

See `roles/claude_code_bridge/` in `noesis-ansible` for the installer (bridge
directories, Claude Code hook, `noesis-loop`/`noesis-status` skills, Hermes-side
`evey-bridge` plugin sync).
