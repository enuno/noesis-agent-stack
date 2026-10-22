# Local Skill Sync Policy — `noesis-*` skills

**Status:** active · **Enforced:** `shared/GUARDRAILS.global.yaml` §`skills_sync` ·
**Enforcer:** `scripts/hooks/pre-commit` Gate 3 · **Sync tool:**
`scripts/sync-noesis-skills.py`

## The rule

The Hermes profile skill directories are the **working copy** for `noesis-*`
skills. `noesis-agent-stack/skills/` is the **durable, reviewable, versioned**
copy.

> **When a local `noesis-*` skill is created, edited, or patched, the same change
> must re-run `--sync` and commit `skills/noesis-*/` plus
> `skills/noesis-skills.manifest.json` in the same commit.** An uncommitted local
> skill edit is a policy violation, not a pending chore.

There is no "sync later" window and no separate cleanup commit.

## Why

A skill edited only in `~/.hermes/profiles/<p>/skills/` exists on one machine, in
one profile, with no review, no history, and no rollback. The repo copy is what
makes a skill change auditable and propagatable to the rest of the fleet.

## Commands

```bash
scripts/sync-noesis-skills.py --status   # table: fleet digest vs repo digest
scripts/sync-noesis-skills.py --check    # drift detection, writes nothing (CI + pre-commit)
scripts/sync-noesis-skills.py --sync     # copy drifted skills into skills/, refresh manifest
```

Exit codes: `0` in sync · `2` drift · `3` divergent duplicates / needs operator ·
`4` nothing discovered (misconfigured environment) · `5` post-copy digest mismatch.

## What sync does

1. Scans `~/.hermes/profiles/*/skills` and `~/.hermes/skills` for directories
   named `noesis-*` that contain a `SKILL.md`.
2. Picks one authoritative copy per skill name. On a tie the
   `noesis-orchestrator` copy wins, then the `default` profile copy.
3. Computes a recursive SHA-256 over every content file (path + bytes, sorted),
   so a change in a `references/` file is detected, not just `SKILL.md`.
4. Copies into `skills/<name>/` and **re-verifies the digest after the copy**.
   A mismatch aborts the run — a partial or corrupt copy never lands.
5. Writes `skills/noesis-skills.manifest.json` recording, per skill: repo path,
   source profile, source absolute path, file count, digest, sync timestamp, and
   any duplicate copies.

`HERMES_HOME` is deliberately **not** trusted as the scan root: inside a fleet
profile session it points at the profile dir (`~/.hermes/profiles/<p>`), which has
no `profiles/` child. The script resolves the real Hermes root itself. Getting
this wrong silently syncs one profile's skills and calls it the fleet.

## Excluded from the durable copy

`_skill_library_update.json`, `.DS_Store`, `__pycache__/` — local bookkeeping that
leaks private paths (it records the author's home-directory source path) and adds
nothing to the reviewable skill content.

## Divergent duplicates

`noesis-memory-routing` currently exists in two places with identical content. If
copies ever **disagree**, sync refuses (exit 3) and names the conflict. Silently
picking one would hide a real divergence between profiles; the operator decides.

## Enforcement

`scripts/hooks/pre-commit` Gate 3 runs `--check` whenever a commit stages
`skills/noesis-*/` or the manifest. Drift blocks the commit with the repair
command. Commits that touch no tracked skill skip the gate entirely.

Install with `scripts/install-hooks.sh` (idempotent; preserves a foreign hook as
`.git/hooks/pre-commit.local`).

## Scope limits

- Covers `noesis-*` skills only. Third-party and agency skills are out of scope.
- Sync is mechanical copy, not review. Per the standing rule that implementation
  and independent review never share a session, a reviewer other than the author
  still signs off on the skill change itself.
- Sync never edits a live profile skill. The fleet copy is authored, the repo
  copy is derived.