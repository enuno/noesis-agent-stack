# Bounded implementer contract template

Copy this template per bounded implementation dispatch, replace every
`<PLACEHOLDER>`, and pass the finished file via `--query-file`
(never `-q`). The contract is the session's entire world: the child
knows nothing about prior rounds. Structure and exact-marker discipline
matter more than prose polish.

---

# <Workstream> — Slice <N> implementer contract — <profile>

You are the bounded implementer for <scope name>. You know nothing about
prior rounds; this contract is complete. Follow it exactly.

## Authorization and identity

- Operator authorization: <verbatim authorization text or reference>
- Base commit (verified, clean): <FULL_BASE_SHA>
- Your worktree (cwd): <ABSOLUTE_WORKTREE_PATH>
- Branch: <BRANCH_NAME> (already checked out)
- Lane: provider <PROVIDER_ID>, model <MODEL_ID>. No provider fallback,
  ever. <any other hard bounds: no network / no installs / etc.>

## Mission

Implement exactly <N> new files, nothing else touched:

1. <REPO_RELATIVE_PATH_1>
2. <REPO_RELATIVE_PATH_2>
3. <REPO_RELATIVE_TEST_PATH_1>
4. <REPO_RELATIVE_TEST_PATH_2>

<One paragraph: what these adapt/build and which existing module is the
source of truth. Tell the child to READ that module first.>

## Interfaces you code against

<Quote the exact protocol/class/function signatures from the existing
module with their file and approximate line numbers. Include the data
shape of the inputs (fixture field names) and outputs (result/verdict
fields, enums). The child verifies against the file, not your quote.>

## Required behavior

<Numbered, testable requirements. Each must be precise enough to fail a
wrong implementation: admission/refusal rules with exact triggers,
flag/checkpoint semantics (what must NOT happen after an abort/revoke),
honest field mapping (unknown stays None, never invented zeros),
error types the child defines. One requirement per rule; no adjectives
without a measurable.>

## Explicit non-goals (do NOT implement)

<Bulleted list of adjacent capabilities the child will be tempted to add
(engine internals, schema changes, control-plane edits, enforcement
paths). Naming them here prevents scope creep that reviewers must then
reject.>

## TDD and test requirements

Strict TDD: failing tests first, watch them fail, then implement.
Baseline suite (must stay green): <X> passed / <Y> skipped / <Z> xfailed.
Run:

    PYTHONPATH= <APPROVED_VENV>/bin/python -m pytest <TEST_PATH> -q

Test coverage required (at minimum):
- <per refusal rule: one test that triggers it and asserts the refusal>
- <happy path with scripted/injected doubles only — no live anything>
- <mid-run abort/revoke: assert the negative — the forbidden call count
  stays zero after the trigger>
- <bridge/artifact shape: digest binding, advisory markers, tamper
  rejection>
- Update the CI count note in the workflow yml with a dated line ONLY if
the collected count changes; if unchanged, do not touch the yml.

## Prohibitions

No commits, no pushes, no branch changes, no git history operations, no
installs, no network access, no writes outside the named files, no
writes outside the worktree, no reading or printing of secrets or
credentials, no ledger writes.

## Deliverables (before exit)

1. The named files implemented; full suite run at the end — paste the
   final summary line.
2. Receipt file at absolute path:
   <ABSOLUTE_RECEIPT_PATH>
   Line 1 exactly: IMPLEMENTATION_COMPLETE (or BLOCKED with reason).
   Last line exactly: not_self_approved: true
   Body must state: base commit full SHA; the implemented file paths;
   final pytest summary line; the test names proving each required
   behavior; the lane (provider/model); and confirmation — supported by
   `git status --porcelain` output quoted verbatim — that no file
   outside the closed set was modified.
3. Final chat message: under 15 lines — what was built, test totals,
   receipt path, anything not completed.

If you are blocked (missing interface, failing baseline, tooling failure
you cannot fix within scope), write the receipt with line 1 BLOCKED and
the exact blocker; do not improvise around it.

---

## Dispatcher checklist (delete this section before `--query-file`)

- [ ] Every identity value generated from the artifacts (SHA, path,
      counts) — none typed by hand.
- [ ] Closed file set matches what the freeze/digest will cover; receipt
      path is OUTSIDE the candidate worktree so it is not candidate bytes.
- [ ] Route amendment written and fenced-audited if this launch uses the
      operator-authorized degraded direct route.
- [ ] Ledger task proposed/approved/enqueued/claimed/started by driver
      BEFORE launch; idempotency key reused on any re-run.
- [ ] Fence-aware bracket/angle audit of the finished contract returned
      zero hits outside code fences (SKILL.md pitfalls).
- [ ] Contract contains no secrets, no absolute paths that must stay
      private, no stale counts from an earlier round.
