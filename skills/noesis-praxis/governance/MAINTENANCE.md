# Maintenance Policy — noesis-praxis Skill Tree

This file is the durable maintenance policy for `skills/noesis-praxis/`. It is
referenced from this tree's `README.md` and from the noesis-praxis Hermes
profile's `MEMORY.md` cheatsheet (`~/.hermes/MEMORY.md` on the operator's
host).

Note: as of this writing, `noesis-agent-stack` has no repository-root
`AGENTS.md` file to cross-reference from (verified by direct search, not
assumed) — only the two references above actually exist. If a repo-root
AGENTS.md is added later, it should link here too.

## Canonical source

- `noesis-agent-stack` (this repository), under `skills/noesis-praxis/skills/`,
  contains the **authoritative reviewed** Praxis skill content.
- Any copy of these skills loaded into a running Hermes profile's
  `~/.hermes/skills/` (or a named profile's skill directory) is a **deployed
  copy / read-only view** of this repository's content at a specific commit.
  It is not a second source of truth.
- Upstream repositories (the original GitHub sources a skill was retrieved
  from) are **inputs** to review, never an automatically trusted replacement
  for what is committed here. A skill is only as current as its last reviewed
  sync from upstream — upstream moving on does not change this repo's content
  by itself.

## Mandatory synchronization and commit

Every authorized skill **update, patch, adaptation, rename, addition,
removal, or dependency/reference change** must be reflected here, specifically:

1. Every changed file for that skill is updated in
   `skills/noesis-praxis/skills/<name>/` — not only `SKILL.md`. Scripts,
   references, templates, and assets all move together.
2. `provenance/manifest.yaml`, `provenance/checksums.sha256`, this tree's
   `tests/`, and `governance/deployment-map.yaml` are updated to match.
3. A **scoped local Git commit** is created containing exactly the reviewed
   change (explicit path staging — never `git add .` / `git add -A`).
4. The commit is **not pushed** without separate, explicit authorization.
5. The update is **not** declared complete until:
   - the commit exists and its SHA is recorded, AND
   - the deployed runtime copy (if any) is verified to match the committed
     content (same checksums), AND
   - static validation (see `tests/`) passes for the changed skill(s).

If any of the above cannot be completed, the work is reported as
**"modified but uncommitted"** or **"runtime drift unresolved"** — never as a
completed maintenance-policy-compliant update.

## Normal workflow

1. Inspect current repository and runtime state; identify drift (do the
   deployed copy's checksums match this repo's `provenance/checksums.sha256`
   for that skill right now, before touching anything?).
2. If syncing from upstream, resolve the exact upstream revision (commit SHA)
   to pull from. Do not pull from a moving branch tip without capturing the
   SHA you actually read.
3. Make and review the change inside this repository's managed tree — never
   edit the deployed runtime copy first (see "Runtime-first exception" below
   for the narrow case where that already happened).
4. Validate: run the static checks in `tests/`, re-review for the same
   security criteria used in the original review (`governance/REVIEW.md`),
   and re-resolve any references this skill depends on.
5. Review the full diff, stage explicit paths, and create a scoped Git
   commit with a clear message (e.g. `fix(praxis-skills): patch tailscale
   diagnostic guidance`). Do not push.
6. Deploy the committed content to the active Praxis skill location (a
   filesystem copy into `~/.hermes/skills/<category>/<name>/` or the relevant
   named profile's skill directory — never a live symlink/tap into this
   repo's working tree, so the runtime never edits the canonical repo).
7. Verify runtime discovery (the skill shows up in `skills_list` /
   `hermes skills list`) and content equivalence (checksums match).
8. Record the deployed commit SHA and the actual verification outcome in
   `governance/deployment-map.yaml` — not inside the commit itself (a
   commit's own SHA cannot be known before it exists, so the deployment
   record always lives in a file written or updated *after* the commit, in a
   separate location such as this deployment map, not amended into that
   commit).

## Runtime-first exception

Runtime-first edits are avoided by default. If an explicitly authorized
emergency, or a pre-existing runtime edit, is discovered:

1. Stage a copy of the runtime version **outside** this canonical tree for
   review (e.g. under `provenance/patches/<skill>-runtime-<date>/`), never
   directly over the canonical copy.
2. Compare it against the canonical (committed) version. Do not blindly
   overwrite either side.
3. Copy the approved parts of the runtime change into this repository's
   managed tree.
4. Revalidate (tests + review), update `provenance/manifest.yaml` and
   `provenance/checksums.sha256`, and create a scoped commit.
5. Redeploy the committed version over the runtime copy and verify
   equivalence.
6. Until steps 3–5 are complete, the change is reported as
   **temporary/unreconciled**, never as complete.

## Blocked commits

If Git identity, signing, hooks, merge conflicts, repository availability, or
permissions block creating the commit:

- Do not bypass the blocker (no `--no-verify`, no identity override, no
  force-anything).
- Preserve the reviewed work safely (leave it staged/committed-locally-if-
  possible, or clearly labeled as pending in the working tree).
- Report **"modified but uncommitted"** or **"runtime drift unresolved"**
  explicitly, with the specific blocker named.
- Do not claim compliance with this maintenance policy for that change.
- Do not treat a blocked-commit change as a "normal update" that can proceed
  to deployment — deployment of uncommitted canonical content is exactly the
  runtime-first case above, and must be flagged as such, not silently skipped.

## Scope — what this policy does NOT authorize

- No autonomous periodic/scheduled updates. Every sync described above
  happens because of an explicit, in-session authorization to do that work,
  not on a timer.
- No secret handling, infrastructure mutation, public exposure, or spending.
- No remote Git writes (push, PR, merge) under this policy — that always
  requires separate, explicit authorization.
- **Reading a skill (to review or package it) never authorizes executing its
  procedures.** A skill describing a legitimate operational capability (e.g.
  "how to install k3s") stays a reviewed document until a human separately
  authorizes running that procedure against a real target.
