---
name: noesis-candidate-freeze
description: Freeze and verify a candidate digest for formal review.
---

# Noesis candidate freeze and verification

Formal review (Sentinel/Skeptic) binds to an immutable candidate digest computed
over a captured evidence directory. Worktrees live under
`~/projects/.worktrees/<candidate-name>/{noesis-agent-stack,noesis-ansible}`.
The freeze tooling lives in the repo's evidence `tooling/` directory
(`freeze_candidate.py --write <dir>`, `--verify <digest>`); digest recipes and
profile-manifest hashing live with the review tooling referenced by the
reviewer contracts. Run Python tooling with `PYTHONPATH=` cleared and
`/usr/local/bin/python3.12` unless the repo venv is required.

## When to Use

Capturing or re-capturing review evidence for a candidate worktree, computing
or verifying a candidate digest, correcting a bad capture, or writing reviewer
contracts / operator packets that name a digest.

## Procedure

1. Move every non-evidence file (implementer receipts, result summaries) OUT of
   the worktree before capture — anything written into the tree after capture
   but before manifest finalization pollutes the untracked-file count.
2. Capture the evidence directory with the established per-repo convention —
   the digest binds to the capture flags, so keep them byte-compatible across
   rounds: `git status --porcelain=v1 --untracked-files=all` for the stack
   worktree, plain `git status --porcelain=v1` for the ansible worktree.
   Do NOT use `--untracked-files=all` on the ansible worktree: it expands
   mutable agent-state directories (`.claude/`, `.no-amnesia/`, `.omc/`,
   `.serena/`) into individual manifest entries, making the digest brittle to
   unrelated tooling state. The untracked hash manifest lists FILES only —
   skip directory entries; when a collapsed directory contains exactly one
   candidate file (the ansible worktree's `tests/hermes_profiles/test_offline.py`
   under `tests/hermes_profiles/`), add that file explicitly.
3. Compute the digest with the recipe's script (never by hand), then
   `--verify <digest>` — necessary but NOT sufficient (see pitfall below).
4. Full live comparison against the worktree BEFORE binding the digest to any
   contract or packet: git HEADs of both repos, git status manifests, and the
   sha256 of every untracked file compared one by one against the capture.
5. Scope-check a remediation round against the FROZEN PRIOR candidate before
   freezing the new one. Reconstruct the prior candidate in scratch:
   `git archive HEAD | tar -x -C <scratch> && git -C <scratch> apply <frozen-diff>`,
   then sha256-compare every path in the frozen status manifest except the
   contracted changed files against the live worktree, and every frozen
   untracked-manifest entry (except legitimately changed ones) against live
   hashes. Silence means the worker touched only what the contract allowed.
6. Compute the reviewer-side pins (profile manifests for each reviewer profile)
   and confirm source-base HEADs are unchanged.
7. Only then write reviewer contracts and the operator packet naming the digest,
   and fill the packet's artifact hash table.

## Pitfalls

- `--verify` hashes the stored evidence files only — it is a self-consistency
  check and silently passes even when the live tree has drifted. A verify MATCH
  proves nothing about the current tree; only the full live comparison does.
  Never report a candidate as unchanged on `--verify` alone.
- Capture ordering: if the digest comes out wrong, suspect a file written into
  the tree between capture and manifest (receipts are the usual culprit).
  Re-capture from a clean tree and recompute; do not patch the manifest by hand.
- Digest discipline: a superseded digest is recorded in the chronology and then
  never used again — reviewer contracts, packets, and verdicts name exactly one
  digest, and a verdict bound to digest A never transfers to digest B (prior-round
  verdicts are terminal for their own candidate).
- Declare, don't conceal: if the live tree diverged from earlier evidence (e.g.
  an edit made outside the recorded workflow), state the divergence and its
  provenance in the fresh-stability receipt rather than absorbing it silently.
- Test environment: repo pytest runs need `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and
  `PYTHONDONTWRITEBYTECODE=1` (plugin autoload deadlocks with OSError Errno 11
  on this machine); use the repo venv python for stack tests and
  `/usr/local/bin/python3.12` for ansible-side tests. Stack suites that
  exercise `scripts/apply-noesis-profiles.sh` additionally need
  `PATH="/opt/homebrew/bin:$PATH"` — the script uses bash-4 `mapfile` and
  macOS `/bin/bash` is 3.2, so without homebrew bash first the
  materialization fixture tests fail environmentally (the failure looks like
  a candidate defect). The schema suite lives at
  `orchestration/orchestrator/tests/test_schema_conformance.py`, not
  `tests/`.
- Scratch helper scripts may hardcode a profile path and silently ignore argv —
  a manifest-hash helper printed the SENTINEL hash when handed the SKEPTIC
  directory. Before pinning any profile identity from a helper's output, grep
  the helper for a hardcoded root or missing argv handling, or recompute the
  manifest manually (sha256 over `name\0<file-bytes>\0` for SOUL.md,
  config.yaml, honcho.json in that order) and compare.
- A contract command that was never run costs the worker a cycle on an
  environmental failure that reads as a candidate defect. Verify every test
  command in an orchestrator-authored remediation contract by executing it
  once (with the exact env prefix) before dispatch.
