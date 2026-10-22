---
name: noesis-prompt-library
description: "Use when authoring or auditing prompt-library goal packets."
version: 1.0.0
author: noesis-forge
license: MIT
metadata:
  hermes:
    tags: [noesis, prompt-library, prompts, audit, goal-packets]
    related_skills: [hermes-agent]
---

# Noesis Prompt Library

## When to Use

- Writing or updating a goal/task prompt packet in `~/projects/noesis-prompt-library`.
- Running (or delegating) a full audit of the prompt packets, then applying fixes.
- Integrating a new platform (Paperclip, Buzz, Goose, …) into the fleet's prompt set.

## Repo layout

The fleet's copy-ready goal-prompt set at `~/projects/noesis-prompt-library`
(GitHub: `HashGrid-Networks/noesis-prompt-library`). Companion repos:
`enuno/noesis-agent-stack` (definitions, contracts, orchestration) and
`enuno/noesis-ansible` (IaC deployment). Verify remotes with
`git remote -v` before citing URLs in prompts — never guess org names.

## House style — every prompt packet

- Copy-ready goal packet: required-inputs table, concept map (Noesis ↔
  platform), bounded workflow, phase gates, hard boundaries, acceptance
  checks. Follow the house style of `noesis-agent-stack/DEPLOYMENT-PROMPT.md`.
- No prompt grants execution authority by itself: every prompt halts at
  planning without a byte-exact-verified operator approval manifest.
- Platform-integration prompts (Paperclip, Buzz, Goose, …): verify platform
  mechanics from the upstream repo/docs at authoring time — do not embed
  stale or guessed flags, paths, or config keys.

## Canonical conventions (verified; do not rediscover)

- **Target repo for all Ansible deliverables:** `~/projects/noesis-ansible/`
  (inventory dir is `inventory/`, not `inventories/`). The historical
  `~/projects/enuno/home-lab/ansible` path is dead — if a prompt points
  there, repoint it and note the migration.
- **Phase order single source of truth:** the "Phase order for execution"
  table in `0.Master-Prompt/Repo-Layout.md` (identity → security/tools →
  communications → runtime → macOS → operations → orchestration). Any file
  disagreeing with it is stale.
- **Agent naming scheme:** display `Noesis ClawDev`/`Noesis HermesDev`;
  kebab registry IDs `noesis-clawdev`/`noesis-hermesdev`; Hermes profile
  slug `noesis-hermesdev`.
- **Operator identity and chat IDs never hardcoded:** Telegram operator
  handle/user-ID and group name/peer-ID live in vault vars
  (`inventory/*/group_vars/secrets.yml`). Telegram group peer IDs differ
  between Bot API and TDLIB for the same supergroup — prompts must require
  a live verification step (method + date recorded) before playbooks run
  against the real group.
- **Scaffolding tasks** (repo/monorepo generation) carry abort-on-conflict
  guards: if a target file already exists with content, stop and list
  conflicts instead of overwriting the live repo; generation is additive.
- **Unverifiable components are labeled greenfield/internal** (e.g. ANS,
  Clawvisor, Agent Registry dashboard) — never present them as existing
  third-party software.

## Audit workflow

1. Split sections across parallel read-only `delegate_task` audits (rubric:
   `references/audit-rubric.md`). Instruct auditors: **do not modify files**.
2. **Spot-verify every material claim against disk before patching** —
   subagent findings are self-reports. Check the quoted line exists, the
   stale path truly is absent (`ls`), the target repo truly exists.
3. Apply fixes surgically:
   - Repoint stale paths; strip orphan citation markers (`[web:N]`,
     `[page:N]`) with no reference list.
   - Superseded/archived variants get a status header
     (`> **SUPERSEDED by …**` / `> **ARCHIVED — historical evidence only**`)
     and are preserved, not rewritten.
   - Keep JSON examples concrete and valid; put indirection (ports, vars) in
     notes, not inside the JSON block.
4. Write `AUDIT-REPORT.md` at repo root: fixes applied, open items not
   fixable offline, new prompts added.
5. Update `README.md` section index if sections changed.
6. **Local commits only — never push.** Publication belongs to the
   operator/orchestrator's separately authorized checkpoint process.
