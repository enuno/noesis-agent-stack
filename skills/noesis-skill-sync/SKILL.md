---
name: noesis-skill-sync
description: "Use when editing any noesis-* skill: sync + commit it."
version: 1.0.0
metadata:
  noesis:
    owner_profile: noesis-orchestrator
    policy_ref: noesis-agent-stack:shared/GUARDRAILS.global.yaml#skills_sync
    doc_ref: noesis-agent-stack:docs/skills-sync-policy.md
    enforcement: noesis-agent-stack:scripts/hooks/pre-commit#gate-3
---

# Noesis Skill Sync

Local Hermes profile skill dirs are the **working copy** for `noesis-*` skills.
`noesis-agent-stack/skills/` is the **durable, reviewable, versioned** copy.

**Any local `noesis-*` skill edit obliges a sync + commit in the same work unit.**
An uncommitted local skill edit is a policy violation, not a pending chore.

## When to use

- Creating, editing, or patching a `noesis-*` skill in any profile's skills dir.
- **A `skill_manage` call that writes a `noesis-*` skill.** `skill_manage` edits
  the FLEET copy, so it starts this obligation immediately - in the same turn,
  not in some later cleanup. A lesson captured in one turn and synced in a
  later turn is drift, and the pre-commit gate will block the next commit.
- Seeing drift in `scripts/sync-noesis-skills.py --status` or `--check`.
- Reviewing or committing anything that touches `noesis-agent-stack/skills/`.

## Procedure

1. Make the skill edit in its owning profile dir
   (`~/.hermes/profiles/<profile>/skills/...`). Edit the fleet copy, never the repo copy.
2. Sync:
   ```bash
   cd ~/projects/noesis-agent-stack
   python3 scripts/sync-noesis-skills.py --sync
   ```
3. Read the output. It prints one line per skill with its source profile and
   digest, and verifies the digest again *after* copying — a mismatch aborts.
4. Verify before declaring done:
   ```bash
   python3 scripts/sync-noesis-skills.py --check   # must exit 0
   ```
5. Commit `skills/noesis-*/` and `skills/noesis-skills.manifest.json` **together**
   with the skill change, in the same commit. Never a separate cleanup commit.

## Rules

- Never hand-edit `noesis-agent-stack/skills/` to resolve drift. That directory is
  derived. Drift means sync forward; the next `--sync` overwrites the repo copy.
- Never `--no-verify` the pre-commit hook. Gate 3 blocking a commit on drift is
  the policy working, not an obstacle to route around.
- Sync is mechanical copy, **not review**. A skill change still needs an
  independent reviewer; your own sync is never your own approval.
- If two profiles hold copies of the same `noesis-*` skill with **different**
  content, sync exits 3 and names the conflict. Stop and escalate to the operator.
  Never pick a winner silently.
- Identical duplicates are fine and recorded in the manifest under `duplicate_copies`.

## Pitfalls

- **The pre-commit gate checks the OPERATIONAL checkout, not your worktree.**
  The hook resolves its repository root from the shared `.git/hooks` path, so
  `skills-sync --check` always runs against the operator's primary checkout
  regardless of which worktree you commit from. A commit in a linked worktree
  therefore fails with `pre-commit: FAIL - noesis skill drift` even when that
  worktree's `skills/` is perfectly in sync. The remedy is to sync the
  OPERATIONAL checkout too - but back up the operator's uncommitted `skills/`
  tree first and verify the sync is lossless, because `--sync` deletes and
  recreates each destination directory and would discard untracked files there.
  Never bypass this with `--no-verify`.

- **`HERMES_HOME` is not the scan root.** Inside a fleet profile session it points
  at the profile dir (`~/.hermes/profiles/<p>`), which has no `profiles/` child.
  The script resolves the real root itself; if you write your own scan, resolve it
  the same way or you will silently sync one profile's skills (6 of 11) and call
  it the fleet.
- **Digest must be recursive.** Hashing only `SKILL.md` misses edits to
  `references/*.md`, which is where most of these skills' content actually lives.
- **The manifest digest is a TREE digest, not a file digest.** Each entry
  carries `source_digest_sha256` and `repo_digest_sha256`, computed over
  path+bytes for every file in the skill directory. To check whether ONE file
  matches, hash that file directly; to check whether the whole skill matches,
  compare the manifest's tree digests. A per-file digest you compute will
  never equal the manifest's digest, and treating that mismatch as drift sends
  you chasing a problem you do not have.
- **`_skill_library_update.json` is excluded** from the durable copy — it records
  the author's home-directory source path and leaks private paths into git.
- A skill added on another machine, or from another profile, still syncs from
  here: the scan covers `~/.hermes/profiles/*/skills` and `~/.hermes/skills`.

- **Drift in a fleet copy is often NOT yours — attribute it before you claim
  it or fix it.** Hermes' background curator rewrites profile skill copies on
  its own schedule, so a `noesis-*` fleet copy can differ from the repo copy
  without you having edited anything. Attribution evidence lives in two
  places: the curator ledger at
  `~/.hermes/profiles/<p>/skills/.curator_ledger.jsonl` (timestamped actions)
  and the pre-edit blobs under `~/.hermes/profiles/<p>/.curator_backups/blobs/`
  (a blob whose hash equals the repo copy's hash proves the fleet copy ALREADY
  differed before the curator's edit — i.e. the drift pre-dates the curator
  run and pre-dates your session). Compare hashes and mtimes before
  attributing drift to yourself, and before reporting a drift you did not
  cause as your own uncommitted skill edit.

- **When an envelope forbids touching the operational checkout or
  committing, REPORT drift — do not remediate it.** `--sync` writes into the
  operational checkout's `skills/` and clears Gate 3 only via a commit, so a
  bounded envelope that preserves the checkout and excludes commits cannot
  clear drift. Record the drifted skill names, the attribution evidence, and
  the exact remediation command (`scripts/sync-noesis-skills.py --sync`, then
  commit `skills/noesis-*/` with `skills/noesis-skills.manifest.json`), and
  hand it to the operator as an outstanding obligation alongside that
  envelope's own next-decision request. Do not let an unrelated envelope
  silently expand into a repo mutation.

## Commands

| Command | Purpose | Exit codes |
|---|---|---|
| `--status` | table of fleet vs repo digest per skill | 0 |
| `--check` | drift detection, writes nothing (CI + pre-commit) | 0 ok, 2 drift, 3 divergent, 4 nothing found |
| `--sync` | copy drifted skills into `skills/`, refresh manifest | 0 ok, 3 divergent, 4 nothing found, 5 digest mismatch |

## Verification checklist

- [ ] `--check` exits 0 after the sync
- [ ] `skills/noesis-skills.manifest.json` staged in the same commit as the skill
- [ ] no `_skill_library_update.json` or `.DS_Store` under `skills/`
- [ ] independent reviewer signed off on the skill change itself