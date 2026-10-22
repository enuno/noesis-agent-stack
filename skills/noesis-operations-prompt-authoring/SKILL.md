---
name: noesis-operations-prompt-authoring
version: 1.0.0
author: Hermes Agent
license: Proprietary
description: "Use when authoring Noesis lifecycle prompts."
metadata:
  hermes:
    tags: [noesis, ansible, infrastructure, prompts, runbooks, documentation]
    related_skills: [omh-verification-gate, noesis-control-plane-dev]
---

# Noesis operations prompt authoring

Use this skill to build copy/paste-ready prompts or runbooks for Noesis Agent Stack deployment and lifecycle operations from the actual `noesis-agent-stack`, `noesis-ansible`, and prompt-library repositories. The deliverable is documentation/prompt content; do not deploy infrastructure merely to validate it.

## When to Use

Use when a prompt library, operator runbook, or infrastructure-agent handoff must be authored or refreshed from current Noesis repositories and Ansible automation.

Do not use for live deployment execution, control-plane implementation, or generic prose editing without repository-backed operational claims.

## Procedure

1. Establish the three canonical repositories and intended remotes before reading their content. Inspect branch, upstream, HEAD, ahead/behind status, and working-tree status; fetch `--all --tags --prune`. State explicitly that fetching updates refs but does not update the checked-out branch. Fast-forward only clean, non-divergent branches with an upstream. If a dirty or divergent repository blocks safe synchronization, preserve it, record the exact branch/full HEAD/upstream and dirty paths, label it unsynchronized, and stop affected execution unless the operator explicitly authorizes that named snapshot. Never describe a dirty worktree as reproducible from its HEAD alone. When current upstream content must be inspected without disturbing the canonical worktree, use a detached review worktree outside the canonical path at a recorded ref; do not copy local secrets or untracked configuration into it. Never reset, clean, stash, switch branches unexpectedly, or overwrite local work.

2. Read applicable repository instructions and the current architecture/automation entry points. For Noesis, inspect the core README and deployment/operations docs, the Ansible README and `ansible.cfg`, selected inventories, `group_vars`/`host_vars`, playbooks, role defaults, tasks, handlers, and validation/backup/rollback tasks. Read the prompt library README and representative existing prompts to match its organization. Trace each named playbook and variable to a real file before writing it into a prompt.

3. Build a capability matrix from source, not names or README promises. For every lifecycle operation, record the verified playbook, roles/tasks invoked, inventory/environment inputs, feature toggles, secret mechanism, target scope, validation path, disruptive effects, and rollback limits. Distinguish supported behavior, partial behavior, and unsupported gaps. Treat backup artifacts as usable only after verifying their contents; a directory, marker, or zero exit status is not a pre-change backup gate. If copy tasks use `ignore_errors`, require per-artifact inspection and report partial-backup risk. If restore/rollback ignores errors, require independent post-operation verification. Treat separately gated packages as separate workflows: an offline plan or apply authorization does not imply backup, restore, rollback, activation, or canary authorization.

4. Organize prompts by lifecycle class rather than by incident or date. At minimum cover only the workflows the automation supports: bootstrap/deploy, inventory/configuration, maintenance/update, targeted component, health verification, troubleshooting/recovery, and backup/restore/rollback where mechanisms exist. Make each prompt self-contained: objective/outcome, repository URLs and canonical paths, mandatory repository preparation, required placeholders, documentation inspection, existing-playbook workflow, preflight, approval gate, verification, failure handling, rollback limits, and completion report.

5. Embed operational safeguards in every apply-capable prompt. Require explicit inventory, environment, host/group scope, and missing-value requests; prohibit guessing. Preserve local work and infrastructure state. Use the established secret-management path without literal secrets in prompts, logs, diffs, or reports. Prefer idempotent Ansible roles and handlers over ad hoc shell/service edits. Require syntax checks and `--check --diff` where meaningful, while explicitly stating that check mode is partial simulation. Require approval before production, network, secret, security, service, data, macOS, destructive, or disruptive changes.

6. Validate the prompt library statically. Confirm every named playbook, role, inventory, variable, and command exists in the inspected repositories. Check every operational prompt for the repository-freshness block and required sections. Run `git diff --check`, a focused secret-pattern scan, and any repository documentation/lint checks available. Do not include deployment, live health mutation, commit, or push commands as validation actions.

7. Validate Ansible examples without secrets or live changes. Prefer a clean detached review worktree at the selected upstream ref when the canonical source tree is dirty, and record the exact source commit. Run `ansible-inventory --graph` for the referenced inventories. Run `ansible-playbook --syntax-check` for referenced playbooks. If the repository's default `ansible.cfg` points to a vault-password file that is unavailable, do not create or guess credentials or bypass decryption; use an isolated scratch config outside the repository only when it preserves the review worktree's role/library paths, and report exactly which repository configuration and credential/decryption behavior was not exercised. Keep syntax validation, inventory parsing, check-mode execution, and live operational verification as separate evidence classes. Never claim the prompts are production-safe solely because syntax checks pass.

8. Finish with an evidence-based report. List added/modified files, prompt catalog and modes, repository branch/HEAD identities, synchronization caveats, commands and observed results, unsupported capabilities, and follow-up changes needed in the automation repository. State explicitly that no infrastructure, deployment, commit, or push was performed when that is true.

## Always-on rules

- Treat repository content as authoritative over older prompts, memory, and README-only claims.
- Preserve unsynchronized snapshots as evidence; do not call them current, and do not proceed with affected execution without explicit authorization for the exact snapshot.
- Distinguish fetched remote refs from a branch update; approval binds to the inspected source identity, so source or execution-plan drift after approval requires renewed approval.
- Never invent playbook names, roles, variables, integrations, health endpoints, rollback behavior, or secret flows.
- Keep documentation-only work separate from live execution and repository publication.
- Separate planned commands, check-mode evidence, syntax evidence, live execution evidence, and post-deployment verification; one does not prove the others.
- Report ignored Ansible errors and partial checks as limitations, not success; never let an incomplete backup satisfy a recovery gate.
- Keep unsupported workflows visible as follow-up recommendations instead of filling gaps with ad hoc commands.
- Never expose secrets or ask the operator to paste them into a prompt or chat.

## References

- `references/ansible-lifecycle-prompt-checklist.md` — compact capability-matrix and validation checklist for Ansible-backed lifecycle prompt sets.

## Verification standard

A prompt set is ready only when its referenced paths resolve, its lifecycle claims match inspected tasks, each operational prompt is self-contained and approval-aware, the documentation diff is clean, secret scanning is clean, and every validation limitation is reported.
