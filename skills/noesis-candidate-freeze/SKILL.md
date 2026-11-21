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
   freezing the new one — and build the successor IN that reconstruction,
   not in the frozen worktree. A reviewed candidate's worktree is evidence:
   never layer new edits onto it. Create a fresh worktree at the SAME base
   commit, `git apply` the prior round's frozen patch, and keep THAT as the
   successor workspace. Prove lineage before touching anything: recompute
   the path-prefixed NUL-separated sorted digest recipe over the recombined
   tree and require it to reproduce the prior round's frozen combined digest
   exactly — only then make Repair-N edits on top. Record the lineage in the
   new manifest (`base + overlay digest <prior> + <new> delta`) so a reviewer
   can re-derive ancestry. Reconstruct via
   `git worktree add <dir> -b <new-branch> <base-sha> && git -C <dir> apply <frozen-diff>`
   (or `git archive HEAD | tar -x -C <scratch> && git -C <scratch> apply
   <frozen-diff>` where a worktree is unsuitable), then sha256-compare every
   path in the frozen status manifest except the contracted changed files
   against the live worktree, and every frozen untracked-manifest entry
   (except legitimately changed ones) against live hashes. Silence means the
   worker touched only what the contract allowed.
6. Compute the reviewer-side pins (profile manifests for each reviewer profile)
   and confirm source-base HEADs are unchanged.
7. Only then write reviewer contracts and the operator packet naming the digest,
   and fill the packet's artifact hash table. Fill every count, size, and digest
   in that table from MEASUREMENT, never by hand -- a wrong number in the
   packet's identity block blocks the review at the identity gate before it
   examines anything. See the `noesis-in-fleet-review` skill's
   `references/review-packet-identity.md`.

## Pitfalls

- An empty `git diff HEAD` is not an empty candidate. When porcelain
  `-uall` lists in-scope untracked files, the identity is the base commit
  plus the combined digest of those files. Do not bind a review to the
  empty-diff hash alone.
- A contract base token whose length is not 40 or 64 hex characters is a
  typo, not a stop, once `git rev-parse HEAD` has been measured. Pin that
  measured HEAD. Stop only if HEAD differs from the pin.
- `--verify` hashes the stored evidence files only — it is a self-consistency
  check and silently passes even when the live tree has drifted. A verify MATCH
  proves nothing about the current tree; only the full live comparison does.
  Never report a candidate as unchanged on `--verify` alone.
- Capture ordering: if the digest comes out wrong, suspect a file written into
  the tree between capture and manifest (receipts are the usual culprit).
  Re-capture from a clean tree and recompute; do not patch the manifest by hand.
- Agent patch appends commonly leave a double newline at EOF (`git diff --check`:
  "new blank line at EOF"), and diff-hygiene CI fails the whole event-tree job on
  that one byte. After ANY edit to a candidate file, strip to exactly one trailing
  newline and run `git diff --check` over the entire candidate — not only the file
  just edited — before validating or freezing.
- Committed-message equivalence: `git commit -F <file>` appends a trailing newline
  when the file lacks one, so the committed message bytes differ from the message
  file by that byte. Hash the committed blob (`git log -1 --format=%B`) or compare
  stripped text; never declare a message mismatch or match from a raw byte compare
  of the file alone.
- The combined-digest recipe "sorted path, NUL, file hexdigest, NUL" concatenates
  the ASCII hex string, not the raw 32-byte digest. A raw-bytes join will not match.
- Do not stack a separate experiment onto a repair candidate merely because it
  shares a base. If that experiment refuses the real subprocess when a proof is
  missing, stacking it disables launches the repair still intends. Leave it off
  the candidate and say why.
- `git diff --check` does not run the event-tree secret scanner. That job scans
  the full text of every file changed versus the PR base with `agency/secretscan.py`,
  not the diff hunks. `scan_file` takes a path; `scan_text` takes the file text. Passing both to `scan_file` raises TypeError and is not a clean scan. The scanner flags a credential keyword used as an assignment target
  (`secret =`, `API_KEY=`), not only a long literal after `=` or `:`. Do not
  name the variable or keyword argument with a credential word. Build a probed
  key by concatenation (`"API" + "_KEY"`) and store the marker in a neutrally
  named variable. Splitting a constant does not clear the hit if the assignment
  still holds the long literal. Report the path and keyword only. Do not print
  the matched value.
- Pytest rewrites `assert actual == SECRET` and prints the value on failure. Compare
  through a helper that raises `AssertionError` with a fixed label, so the secret is
  not an operand of an assert.
- A pull_request job checks out GitHub's merge commit, not the branch tip. Report
  that checkout SHA separately from the head. A later tree match after pinned merges
  is not execution of the tip. Socket success is not the event-tree scan. An
  `action_required` run with zero jobs is neither a pass nor a fail, and a green job
  on a descendant does not rewrite an ancestor's failed job.
- A file-tool child verdict is not a Sentinel or Skeptic receipt. Record the
  delegation id and model, and say so. A review thread marked resolved is GitHub
  metadata, not proof the current head still satisfies the comment — re-read the
  comment against the current file before treating it as closed.
- Digest discipline: a superseded digest is recorded in the chronology and then
  never used again — reviewer contracts, packets, and verdicts name exactly one
  digest, and a verdict bound to digest A never transfers to digest B (prior-round
  verdicts are terminal for their own candidate).
- Every review round gets NEW artifact filenames (a round suffix such as
  `-repair2-`); the prior round's packet, manifest, patch, receipts, and
  transcripts stay byte-identical forever. Never edit a historical packet to
  make its old claims read as correct — issue a successor packet that names
  the corrected framing and the prior artifact's inaccuracy explicitly.
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
- A closed-set porcelain equality test is not a harness non-interference
  check. It fails a developer checkout that already has unrelated dirt,
  and it fails CI once the closed-set files are committed and status is
  empty. If the claim is "the harness wrote nothing during the run,"
  snapshot Git-visible paths at the start of the tested interval and fail
  only on a new path or a content change to a path already dirty. Keep
  the limits: ignored files, transient create-then-delete, and writes
  outside that Git root are not proved absent by either snapshot.
- **Update exact-count CI assertions only for OBSERVED count changes, and
  check the focused-suite selections first.** A suite-wide count change does
  not imply every asserted count changes: read the focused jobs' file lists to
  see whether they even select the suites you touched (e.g. a council-suite
  delta leaves focused dispatch/routing counts unchanged). Update only the
  counts you measured, with a dated note naming what was added — never lower
  an expectation to hide a failure, and never raise one in anticipation.
- **Extend the freeze's closed path set BEFORE re-freezing when a repair
  contract permits a NEW file.** A repair cycle allowed to add a regression
  test file otherwise makes that file read as out-of-scope drift: the freeze
  refuses to emit reviewer contracts, and widening the set after the fact
  reads as scope laundering. Add the permitted path to the freeze tool's
  closed set at the same time you write the repair contract, then re-freeze
  and record the new identity. A superseded digest is never rewritten in
  place — the prior identity and its verdicts stay on disk, still bound to
  the bytes they actually reviewed.
- Verify each repair regression's teeth by mutation before freezing: copy the
  whole tree, revert only the fix, and confirm the regression fails for the
  intended reason. A test that passes a policy flag to the constructor does
  not pin a factory that is supposed to set that flag — drop the flag from the
  factory method and require a red test that builds through the factory. A TypeError from a later comparison (`None < 0` after the
  type check was removed) is not that reason — the test must fail because the
  bad case was accepted or the refusal escaped, not because the mutated code
  crashed. In a Repair-N cycle the revert baseline is the prior round's
  reconstructed tree (step 5 reproduces it), not the original merge base — a
  test that also passes on the prior round pins nothing new. Parametrized cases
  that share a process-global attempt budget must use a distinct key per case;
  otherwise a later case is refused before the assertion under test. See
  `noesis-control-plane-dev` for the exact recipe and the
  fixture-resolution pitfall.
- **A repair that adds a REQUIRED field to an existing contract has chosen a
  breaking change — resolve it deliberately, not by default.** First check
  whether any producer, fixture, or consumer actually needs the field absent:
  if not, the smallest coherent fix is usually to make the field OPTIONAL with
  explicitly documented absent-semantics (a conditional branch that treats
  absent-or-default as the legacy shape), not a version bump — a filename
  change or a prose note is NOT versioning. Whichever option is chosen, pin the
  boundary with tests for all of: the previously valid artifact, the new
  shape, malformed values, rejection of invalid completed shapes, and
  non-broadened minimums. Report the chosen option, the actual compatibility
  boundary, and the rationale in the successor packet.
- **Key every review artifact path to the candidate identity, not to a fixed
  name.** The freeze tool is the generator: if it emits `VERDICT-1.md`, the
  reviewer writes there — correctly, because the contract names that path —
  and the next round's verdict overwrites the previous round's file,
  destroying the evidence that justified the repair cycle that followed. Derive
  the verdict path AND the review-contract filename from the candidate digest,
  and make the launcher select the newest matching contract rather than a
  hard-coded name. When a fixed path has already caused an overwrite, the
  earlier verdict's text may be unrecoverable if the shared session log does
  not carry tool inputs: preserve what survives in the mission ledger, state
  the loss plainly, and do not reconstruct the reviewer's words.
- **Verify the WHOLE frozen tree before AND after the review — not just the
  candidate-path digest.** The candidate digest covers the closed path set; it
  does not cover a file written elsewhere in the tree, and a file written
  under an ignored path never appears in `git status` at all. Capture a
  per-file sha256 inventory of EVERY file in the worktree (excluding `.git`)
  before the launch, and after the reviewer exits re-hash the whole tree:
  nothing added, nothing removed, nothing changed, and no
  `__pycache__`/`.pyc`/generated artifact. The reviewer does all executable
  work — tests, compilation, mutation probes, generated output — in a
  disposable copy OUTSIDE the tree with bytecode writing disabled, so the
  frozen tree cannot gain a generated file even by accident. Compare the
  post-review `git status --porcelain -uall` byte-for-byte against the frozen
  status manifest as well: a status comparison alone misses an ignored path,
  and a digest comparison alone misses a file outside the closed set. Use
  `--untracked-files=all` for that comparison — plain porcelain collapses an
  untracked directory into one entry and hides a new file inside it. Any
  difference is an integrity deviation, not a rounding error: report it
  against the candidate, do not absorb it.
