# Audit Rubric — prompt-library audits

Reusable rubric for auditing (or delegating audits of) the prompt packets.

## Dispatch shape

- 2+ parallel read-only `delegate_task` children, split by section ranges
  (e.g. sections 0–2 vs 3–6). Each child reads every file in its range
  fully.
- Hard instruction: **audit only — do NOT modify any files.**
- Allow read-only cross-checks against the live environment
  (directory-existence probes via `search_files (target='files')` or
  terminal `ls`, `git remote -v`) but no writes outside the library.

## Per-file issue format (require this exactly)

`- [SEVERITY|category] quote-or-line-ref — why it matters — FIX: concrete recommended change`

- SEVERITY: HIGH / MED / LOW.
- category: correctness | completeness | safety | clarity | consistency.

## Rubric dimensions

1. **Correctness** — stale repo names/URLs/paths, commands that don't match
   the known deployment flow (`scripts/apply-noesis-profiles.sh`,
   `noesis-ansible/playbooks/master-stack.yml` + `inventory/local/hosts.ini`),
   invented flags/paths, contradictions between files (goal vs task, v1 vs
   v2, README vs prompt).
2. **Completeness** — missing required inputs (approval manifest,
   revisions/digests, inventory, rollback criteria), missing failure/halt
   behavior, missing acceptance/verification steps.
3. **Safety** — approval gates, no-secrets handling, destructive-command
   guards, no "deploy from this prompt alone" anti-patterns, exposure
   guardrails (Tailscale binding, public endpoints).
4. **Clarity** — placeholders clearly marked, single responsible role,
   machine-readable outputs where promised, no conversational artifacts
   ("I can turn this into a second prompt…") inside executable prompts.
5. **Consistency** — terminology (NoesisPraxis, ACP/A2A/MCP naming),
   versioning (v1/v2 duplicates, supersession markers), README coverage of
   all sections.

## Required report sections

- Per-file audit (purpose 1 line + numbered issues in the exact format).
- `## TOP-10 PRIORITIZED ISSUES` — numbered, cross-file.
- `## RECOMMENDED EDITS` — bullet list: `file: exact change`.
- `## UNVERIFIABLE` — facts the auditor could not verify (flag, never
  silently correct — e.g. Telegram peer IDs, component upstreams).
