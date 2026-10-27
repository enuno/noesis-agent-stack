# Operator packet review and approval manifests

Depth for the operator-executed launch-packet pattern (see SKILL.md →
"Operator-executed launch packets"). Use when preparing the final
approval request for an operator-run pilot, or when acting as the
independent reviewer of such a packet.

## Approval manifest structure

The manifest is the artifact the operator approves. It must contain, with
no ellipses anywhere in commands:

1. **Release identity** — the complete release directory; the approved
triplet (packet + companion + runner) as full sha256 values; the
preserved-history list so substitution is detectable.
2. **Exact command to be approved** — a single absolute-path command.
3. **Targets and live paths** — every file the run may write, with the
apply-then-restore semantics stated; bounded reads listed separately.
4. **Sanitized config diff** — the authorized delta only, described by
key and value shape, never whole-config content.
5. **Launch argv and environment** — the exact argv; non-secret env
settings; flags explicitly excluded with the verified reason.
6. **Provider/model route and credential SOURCE NAMES only** — provider
ids and model names; where keys resolve from (stored profile config);
never values; the child gets zero tools and no credentials.
7. **Expected external calls and cost exposure** — how many inference
streams, to which providers; no-USD-ceiling authorizations stated
explicitly; expected spend small but unpriced.
8. **Enforced vs procedural bounds** — separate the two lists honestly.
Config-authoritative caps (delegation.max_iterations), leaf/toolset
derivation, MCP inheritance, deny-by-default approval are enforced;
single-dispatch count, --max-turns semantics, and supervised observation
are procedural.
9. **Attempt directory** — location, mode 0700, contents inventory,
which files are secret-bearing (preimages) and never exported.
10. **Manual recovery command** — exact, absolute, and stated to refuse
rather than overwrite on drift.
11. **Exit-code contract** — every code, its meaning, configuration
state after it, and whether a provider was called. Codes observed in
practice: 0 success; 2 refused pre-mutation; 4 apply-incomplete and/or
restore failure (nothing-applied variant worded separately from genuine
restore failure); 5 launched parent still running (do not restore while
it lives); 6 apply+restore clean but launch exited nonzero.
12. **Dependency and race disclosure** — every PATH-resolved binary the
runner uses, unpinned; the residual race stated as documented, not
eliminated; the in-design mitigations (source hash into attempt dir,
preimage-match guards, help-text flag re-verification).

## Independent review round

The reviewer's discipline, whether you are preparing for one or acting as
one:

- **Verify hashes before reading content.** `shasum -a 256` the triplet
  against the manifest values first; a mismatch ends the review.
- **Trust the delivered files, not the packet's claims.** Every
  assertion in the packet gets re-derived from the code with file:line
  references. Packet text that says "guarded" means nothing until the
  guard is read.
- **Spot-check drill evidence by re-running, not by reading summaries.**
  Build your own fixture trees (exact preimage shapes + a canary-secret
  line outside every affected window), stub the CLI, run through the
  script's env-override hooks. The most common drill anomalies are
  harness errors — wrong fixture shape, stale fixture state — and the
  script's correct refusal is not a script defect. Reset fixtures to
  pristine between drills.
- **Hunt the specific defect classes that survive self-review:**
  fail-open sequencing (any check that runs after mutation), exit codes
  that mask failure, launch-not-gated-on-apply-success, parsed-but-ignored
  CLI flags, restore postconditions that ignore untouched targets,
  symlink/TOCTOU boundaries, and secret material reaching terminal
  output or public receipts.
- **Report PASS / FAIL / UNVERIFIED per claim with evidence; recommend
  READY or NOT-READY but never approve.** Approval is the operator's act.

## Finding-to-revision discipline

- A hash-identified artifact is never patched. Findings produce a
  successor file (new name, new hash), the superseded file stays
  byte-identical, and the new packet documents the findings, the fixes,
  and re-drill results. Revision filenames carry the revision number
  (`...-pilot-005.md`).
- After fixes, a second-round delta review diffs old vs new to confirm
  only intended changes landed, then traces the whole artifact for
  regressions the fix introduced — renamed-file consistency across copy
  targets, refuse-lists, receipt text, recovery commands, and embedded
  hash references are the classic casualties of a mechanical rename.
- A reviewer caught a YOLO precondition placed post-mutation, a restore
  that exited 0 over a silent MISMATCH on an untouched profile, and a
  manifest hash embedded before it was computed. These classes generalize:
  check placement, postcondition coverage, and hash-the-artifact-then-
  reference-it ordering.

## Reviewer fixtures (reference recipe)

- Orchestrator fixture config: top-level `delegation:` block of exactly
  `delegation:` + `  max_iterations: 250`, plus a canary comment line
  outside the block.
- Architect fixture config: top-level `model:` block with two-space
  scalar indent (`default: claude-sonnet-5`, `provider: anthropic`) and
  a TOP-LEVEL `fallback_providers:` three-entry list — nesting the list
  inside `model:` is the classic fixture error; the guard will refuse
  correctly and the refusal reads as a script bug to the unprepared.
- Stub `hermes`: answers `chat --help` with the five required flags,
  exits 3 at launch. `PATH`-prepend it; never touch the real binary.
- Give fixtures mixed original modes (e.g. 0644 and 0600) so mode
  restoration is actually exercised.
