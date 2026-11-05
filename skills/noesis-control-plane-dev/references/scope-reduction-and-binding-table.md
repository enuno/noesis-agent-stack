# Scope reduction and the binding table

Depth for the always-on rules in SKILL.md: "Scope reduction and the trust
boundary before patching", the "A persisted record is a claim" rule, and the
reviewer lane-switch discipline.

## 1. When to reduce scope instead of cycling

A governed integration candidate that keeps a bounded review/repair loop
usually converges. When it does not, the signal is a SHAPE, not a count:
successive independent reviews keep finding new instances of the same defect
class — a caller-supplied or observed value that is not bound to, or is
rewritten against, an authoritative source.

Reduce scope when all of these hold:

- the same defect shape recurs across two or more review rounds;
- the adversarial test surface is GROWING (more reviewer-authored cases, more
  parameterised substitutions) rather than shrinking;
- the failing instances sit in a surface the operator did not actually ask
  for — typically the lifecycle/dispatch half of an adapter whose stated
  purpose was admission;
- the operator's own contract contains a clause the candidate has been
  straining to satisfy (for example: reuse the existing task, attempt,
  preflight, audit, readiness and isolated-home mechanisms rather than parallel
  replacements).

Do NOT reduce scope because one review was harsh, because a reviewer wanted
optional improvements, or because a session ran long. Reduce scope because the
candidate is failing a contract it should never have tried to own.

Present the pattern with its evidence — rounds, instances per round, the
adversarial test surface size — and let the operator choose between reducing
scope, redesigning the binding model, and stopping. Do not silently redefine a
stated bound to keep cycling: when a bound's scope word decides whether the
next cycle is authorised ("two cycles per newly discovered issue group" is not
"two cycles total"), quote the source text back and correct any earlier
misreading explicitly before acting on either reading.

## 2. The binding table row shape

Produce this table BEFORE the first source edit, one row per value that can
influence a decision. Each row carries seven fields.

| field | what it must say |
| --- | --- |
| value | the exact input, named as the code names it |
| authoritative source | the file, loader or ledger the value must come from |
| who may supply or alter it | nobody, the operator, the runtime adapter, or a caller who may only REQUEST it |
| validation rule | the check that must pass, including the failure code |
| persisted binding | what is written, and which digest or identity proves it |
| consumer | which surface reads it, and whether it re-verifies |
| negative test | the case that fails when the rule is removed |

Two rules belong in the table for any observed evidence.

RULE A — observed evidence is NEVER relabelled. A readiness fact, a capability
observation, a family map and a policy route are different kinds of thing. A
fact naming provider P is never re-expressed as provider Q to fit a requested
identity. A mismatch is a refusal, with its own code. Never reconstruct,
normalise or re-express observed evidence with the expected identity.

RULE B — the persisted decision record is an IMMUTABLE DECISION SNAPSHOT, not
a grant. It records what was decided, from which sources, under which
identity. A consumer must apply current authority and fencing checks itself.
Nothing in a source-only candidate may be read as authorising execution,
dispatch, reconciliation or acceptance.

A row that is not ENFORCED is a finding, even if a test asserts it. A table
written after the code rationalises whatever the code happens to do, so write
it first and let the reviewer judge the code against it.

## 3. Multi-source declaration set semantics

When a declaration is named by more than one authoritative source, the
contract must state whether the effective set is the union, the intersection,
or a conditional form — and must distinguish three states that a
`value or ()` idiom silently collapses.

| roster capability field | effective DECLARED set | outcome |
| --- | --- | --- |
| ABSENT (key not present) | A | declared |
| present, explicit valid set | A ∩ R | roster constrains the agent |
| present, explicitly empty | the empty set | nothing declared |
| present but MALFORMED (null, wrong type, unparseable) | — | typed refusal |
| roster membership missing entirely | — | typed refusal |

A is the set the agent definition explicitly declares. R is the roster
entry's explicit capability set when it carries one. Rules that hold in every
case:

- the agent declaration is ALWAYS required; a roster-only capability is never
  sufficient;
- the roster may CONSTRAIN the agent declaration but may never ADD a
  capability the agent does not declare;
- null is not absence, and malformed is not absence — both are typed
  refusals;
- never infer a capability from a profile name, a description, a domain
  string, or unrelated skills text;
- DECLARED is one state only. Installed, available, enabled, exposed and
  authorised stay separate, and a declaration alone grants no execution
  authority.

Check the ACTUAL repository schema before writing the rule: the authoritative
roster may carry no capability field at all, in which case the field-absent
branch is the live one and the intersection branch is exercised only by
fixtures that add an explicit set.

## 4. The reduced-boundary checklist

Keep only the surface the operator actually asked for. For an admission-only
slice, that means: capability admission from the authoritative roster and
agent definitions; explicit declared / installed / exposed / authorised
distinctions; identity and source / policy / revision bindings; reuse of the
existing route selection and admission interfaces; and a durable record
through the existing canonical storage.

Remove from the candidate: new dispatch ownership; result reconciliation and
dispatch-event consumption; submit/reap lifecycle; attempt-home
orchestration; fallback execution or planning; any parallel lifecycle,
reservation or acceptance authority.

Removal must be REAL, not cosmetic:

- delete the symbol from the class, the module and the package export list;
- do not leave it callable-but-undocumented, and do not re-export it under a
  new name or behind a new callback that carries the same responsibility;
- do NOT remove or replace the existing orchestrator's own implementations —
  the reduced candidate stops owning that surface, it does not delete it;
- a compatibility requirement that makes deletion unsafe is satisfied by an
  explicit refusal with a typed code, and must be recorded as such.

## 5. Verifying absence of a removed interface

Absence is a claim that must be measured, not assumed. Check all three
namespaces — the module, the package (`from app import X`) and the class
(`hasattr(Adapter, "X")`) — and add a CURRENT contract test that asserts the
interface stays absent, so a later change cannot quietly reintroduce it.

When a removed helper was also used by the candidate's own tests, rewrite
those tests honestly: a test that inspected persistence must read the DURABLE
LEDGER FILE directly, not a helper that designates appended claims as
authoritative, and a test whose subject WAS the removed path becomes a test
asserting the interface is absent and that the underlying store still
replays. Never restore removed code so an old test collects.

## 6. Reviewer-case classification and fidelity verification

Classify every case from every preserved reviewer suite as exactly one of:

- RETAINED BEHAVIOUR — the interface survived; the case must be copied
  byte-for-byte into the candidate suite.
- REMOVED INTERFACE — the exercised interface is gone; the case is replaced by
  a proof of absence plus a proof that no retained surface grants the
  authority the removed surface used to grant.
- STALE PRECONDITION — the case fails at its OWN setup assertion, before
  reaching the behaviour under test; keep it separately and do NOT count it as
  a security regression in either direction.

Verify fidelity YOURSELF rather than trusting the implementer's report: diff
each retained case's source against the preserved suite and count the ones
that are byte-identical. When a scope reduction FORCES a delta — an import
alias because a symbol is no longer re-exported, a renamed target because the
public method became internal, a banner comment — verify that only the
assertions are unchanged, and DISCLOSE the delta in the review packet as a
claim the reviewer must check, not as a settled fact.

## 7. Count-change accounting

An exact-count assertion is a contract. When a scope reduction or a fix
legitimately changes the test population:

- write the new exact count from the FINAL measured run, in every site that
  asserts it, including the prose comments;
- explain the delta in the completion evidence (tests added, tests rewritten,
  tests removed) so a reviewer can check the arithmetic;
- never weaken an exact assertion, add a skip or an xfail, or delete a test to
  land a number;
- the floors and the exact failed / errors / xpassed / skipped / xfailed
  values do not move.

## 8. Digest identity clarification

Two digests are routinely quoted for one candidate and they mean different
things. State which is which, in the record, every time:

- the TRACKED DIFF SHA-256 is the digest of the patch over `git diff HEAD`. It
  identifies the PATCH.
- the COMBINED CONTENT DIGEST is taken over the changed files' CONTENTS —
  path, NUL, lowercase hex content digest, NUL, in alphabetical path order.
  It identifies the FILES.

Recompute both from the live tree before any edit and after the final edit.
Any byte change creates a new identity and invalidates pending verdicts.

## 9. Content-filtered review lanes

A provider safety filter can refuse a review on the turn that would have
written the verdict, after the reviewer has done the whole analysis. The
analysis survives; the write does not. Treat it as `dispatch_not_delivered`
with the analysis preserved — not a partial verdict, not a candidate defect.

Do not blindly re-send the same packet: the trigger is usually the
accumulated context (preserved adversarial fixture files, a freshly authored
probe), so an identical re-send can be refused identically. The recovery
pattern, the conclusion-packet structure and the session-id segmentation rule
are in `noesis-in-fleet-review`.

## 10. Decision-bound provenance, containment, and joined identity

Seven invariants an admission slice must hold. Each one was found by an
independent reviewer against a candidate whose OWN SUITE PASSED, so none of
them is visible from a green test run. A binding table row (section 2) is
what forces them; a table that omits one of them is the defect.

**Provenance travels with the decision.** The decision carries the exact
bytes it evaluated, and the serializer reads them from there. A serializer
that takes a SECOND parsed object and re-reads provenance from it can emit a
record whose provenance does not correspond to the decision, and the two
disagree silently. Re-derive provenance from the decision, or refuse when the
pair does not match.

**Frozen is not immutable.** `@dataclass(frozen=True)` freezes attribute
assignment, not the contents of a dict or list field. A snapshot whose
sources live in a mutable mapping can be rewritten in place between the
decision and the serialization. Snapshot containers must be deeply immutable,
and the negative test must mutate the CONTAINER, not reassign an attribute.

**A caller-supplied id is not a path.** When an id is interpolated into a
filesystem path, validate it as ONE safe path segment and containment-check
every resolved target against the resolved root. A traversal segment and a
symlink both redirect the read outside the root while the manifest still
looks closed.

**One identity, compared once.** Bind the selected profile, the captured
profile, the agent's own id, and the preflight's profile to ONE identity and
compare them against each other. Checking each source against a different
reference lets a mismatch through.

**Persisted free text needs a format, not a non-empty check.** "Is a
non-empty string" admits a credential-shaped value straight into a durable
record. Give every persisted text field a bounded, non-secret format and
reject secret-shaped values before the decision, or persist a controlled
identifier or digest instead of the raw text.

**Every unreadable input is a typed refusal.** A missing file and an
unreadable file are the same class of outcome. Catch the read error at the
per-source boundary and raise the typed refusal naming the source id, not
the raw OS error.

**An acceptance matrix is a matrix.** "Each required field" means every
required field, including the nested ones. Enumerate the matrix from the
schema rather than from the fields a fixture happens to set, and mark
optional fields explicitly instead of skipping them under a generic test.
"Current behaviour is probably correct" is not evidence.
