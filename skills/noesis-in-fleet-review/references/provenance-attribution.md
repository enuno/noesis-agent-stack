# Provenance archaeology and installation-assurance resolution

When a candidate contains an edit no session recorded (author, session,
and authorization unknown), the qualification record must not leave a
permanent undefined hold — identify the required evidence, review,
reconstruction, or explicit operator decision that resolves it. Both
reviewers may judge the unknown authorship non-blocking for exact-byte
offline qualification while blocking attribution/installation assurance;
the orchestrator then owns closing the attribution question.

## Read-only archaeology procedure

Search for attribution evidence before asking the operator — but treat
the result honestly:

1. **Agent session stores (negative evidence).** Hermes session tables
   (`~/.hermes/state.db`) may hold only a small gateway-side cache
   (timestamps as epoch floats, not ISO strings — query with numeric
   ranges, e.g. `where last_activity_at between <epoch> and <epoch>`),
   and CLI transcripts may live elsewhere or be pruned. Claude Code logs
   (`~/.claude/projects/**/*.jsonl`) grep by worktree path. A clean
   negative result supports "no agent session recorded it" — it does
   not prove a human made it.
2. **Interactive shell history.** `~/.zsh_history` in extended-history
   format (`: <epoch>:<elapsed>;<command>`). Scan the edit window with
   Python, not awk — awk aborts on multibyte history lines (`towc:
   multibyte conversion failure`); convert the window with `date -j -f`
   first because naive epoch math drifts. Vim edits of OTHER files
   minutes around the edit mtime are circumstantial support for an
   interactive workstation session — never attribution.
3. **Filesystem mtimes.** `find ~/.hermes -newermt ...` around the
   window; nothing touched means no hermes-side session was even
   writing state then.

Report the archaeology as evidence with its limits: what was searched,
what was found, and explicitly "circumstantial — no authorship
asserted." Never invent an author to close the gap.

## Resolution menu (pick one; none requires code changes)

- **P1 — operator attestation (preferred, zero cost).** The operator
  states in one line whether they made the edit. Resolves attribution
  completely.
- **P2 — documented risk acceptance.** Explicit operator decision
  accepting content-verified, unattributed bytes for the destination,
  recorded as a risk decision. Mirrors the reviewers' bounded-impact
  judgment; legitimate when the destination policy does not hard-require
  authorship.
- **P3 — re-author and re-qualify.** Re-implement the change as a
  recorded, reviewed change on top of the qualified base. New digest,
  full fresh qualification. Only when a destination policy hard-requires
  authorship.

Note which resolution applies to WHICH decision: P1–P3 gate
installation/release assurance only. Exact-byte offline qualification
stands on content verification alone; provenance limits stay recorded
on the preserved asset.
