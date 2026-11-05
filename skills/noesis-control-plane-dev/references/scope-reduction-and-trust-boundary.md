# Scope reduction and the trust boundary

Use this when an adversarial review loop keeps finding new instances of one
shape and another repair cycle would be another instance of the same pattern.
Not for a single specific defect that needs one targeted fix.

## The shape test

A finding is a RE-SURFACE when it is the same defect class in a new place: a
caller-supplied or observed value that reaches a decision without being bound
to an authoritative source. It is a GENUINE NEW CLASS when it exercises a
capability, an interface, or a code path earlier rounds never touched.

Two or three rounds of the same shape is a signal to change the design, not
to run another cycle. The tell: the class sweep you did last round marked
areas as bound, and the next round found instances in exactly those areas. A
class sweep re-derived but NOT re-derived FROM THE SCHEMA keeps producing
instances, because a hand-maintained field list is always incomplete.

## The reduction procedure

1. PRESERVE the failed candidate before touching anything.
   - snapshot the full tree of every changed path
   - snapshot per-file digests, a production-source manifest and a test
     manifest separately
   - snapshot the ledger
   - preserve every reviewer artifact byte-identical, with its digest
   - classify every replayed failure: behaviour-reaching versus stale
     precondition
   - record the status as REQUEST_CHANGES / NOT PUBLISHABLE, and do not
     rewrite prior findings or prior "bound" claims as though they held

2. DECIDE the retained surface, then DEFINE its trust boundary, then patch.
   Writing the binding table before the patch is what makes the reduction
   checkable: a patch that contradicts a row is a defect, not a preference.

3. DELETE, do not defend, the authority surfaces you are removing. A removed
   symbol must be absent from the module namespace AND the package
   namespace. "Callable but undocumented" is not a reduction.

4. Re-derive the route and record identity comparison from the TYPED SCHEMA,
   and add an exhaustiveness test that fails when a schema field is added
   and the comparison is not updated. A hand-maintained partial comparison
   is the defect generator.

5. Carry the reviewer's cases forward by disposition, and produce the
   retention map.

6. Freeze, build the focused review packet, and dispatch exactly the number
   of review sessions the envelope covers.

## The binding table

One row per value that can influence a decision. Starter file:
`templates/trust-boundary-binding-table.md`.

Columns: value | authoritative source | who may supply or alter it |
validation rule | persisted binding | consumer | negative test.

Two rules govern every row:

  RULE A — observed evidence is never relabelled. A readiness fact, a
  capability observation, a provider-family map and a policy route are
  different kinds of thing. An observation naming provider P is never
  re-expressed as provider Q to fit a requested identity. Mismatch is a
  refusal, and the persisted evidence carries the OBSERVED names.

  RULE B — the decision record is an immutable snapshot, not a grant. It
  records what was decided, from which sources, under which identity. Any
  consumer must apply current authority and fencing checks itself. Say this
  in the record's own docstring.

Rules that decide which rows belong, and how they are validated:

  - A caller may REQUEST a value; it can never GRANT one. Validate the whole
    requested set, not the one field the primary assertion used. If any
    member of a set fails, refuse the whole set and persist nothing.
  - Declared, installed, exposed and authorized are four separate facts with
    four separate sources. A directory existing is not installation; a
    non-empty toolset list is not per-capability evidence; membership is not
    authorization.
  - A source bound by digest must have its digest computed from the BYTES
    THE DECISION USED. Re-reading a file at decision time after binding it
    at construction is a time-of-check/time-of-use split: the recorded
    identity then describes different bytes than the decision.
  - An injected or overridden object may be a test seam, never a source of
    authority. Prove it equivalent to the repository-derived value field for
    field, or refuse it.
  - Optional-field semantics are part of the identity: an absent optional is
    not equal to a present default. Unknown security-relevant fields are
    rejected, not ignored.
  - A caller-supplied identity value is never authority: resolve it from the
    authoritative source and refuse a supplied value that disagrees.

## Reviewer-case dispositions

Every case from every preserved reviewer suite gets exactly one disposition.

  RETAINED — the behaviour still exists. Carry the function forward
  byte-for-byte, then MEASURE and report the byte-fidelity: diff the carried
  body against the preserved artifact and count exact matches. Differences are
  acceptable only when the scope reduction forced them (a symbol the module
  no longer re-exports, a public method that became internal, a section
  banner). Report the count; do not assert it. A case that was renamed rather
  than dropped must be listed with both names and the reason.

  REMOVED-INTERFACE — the interface the case exercised is gone. Replace it
  with a case that proves the ABSENCE: the name is not importable from the
  module or the package, the event constant is gone, and no retained reader
  treats a hand-appended ledger event of that kind as authority. State which
  original case each replacement covers.

  STALE-PRECONDITION — the case fails at its own setup assertion: the fixture
  was expected to be empty, to lack a key, to hold a different value. It never
  reaches the behaviour under test, so it is neither a defect nor a pass.
  Retain it separately with a NOTE, and do not count it in either direction.

Produce a RETENTION MAP as a deliverable: every case in every candidate test
file, with its disposition and where it now lives. A reduced packet that
silently drops coverage is worse than the packet it replaced.

## Metamorphic tests

Beyond one negative per finding, add:

  - alter one bound identity, policy or source field at a time; admission
    must fail wherever that field affects authority
  - add one unauthorized member to an otherwise valid request; admission must
    fail AND the member must not be persisted
  - remove authoritative membership from a source; admission must fail
  - replay a claim against changed authoritative inputs; it must not be
    silently treated as current authorisation
  - an unknown field on an otherwise valid record; it must be rejected

Inspect what was WRITTEN, not only what was returned. A refusal that still
persists a record is not a refusal.

## The focused review packet

The packet is not the mission history. Include:

  - the exact candidate identity with a recompute recipe, the changed-path
    list, and per-file digests
  - the complete remaining production-source diff, as a FILE referenced by
    path and digest, not pasted into the prompt
  - the trust-boundary table, referenced by path and digest
  - the findings-to-regressions mapping
  - the retained and removed interface contracts
  - the observed test results with commands and exit statuses

Keep the complete evidence available on demand at named paths. Do not resend
the historical transcript or the unchanged repository as default context: a
reviewer who must read the whole mission will not read the diff. Starter file:
`templates/focused-review-packet.md`.

Point the reviewer at the PRESERVED reviewer suites and require it to run
them and classify each case. Your own classification is a claim to be
verified, not a settled fact.

## Storage trust assumptions

State them explicitly rather than implying cryptographic protection. An
append-only JSONL ledger is protected by convention and file permissions; a
process with the same UID can append a well-formed line. Therefore every
record is an untrusted claim: closed schema rejecting unknown and missing
fields, re-verification of the recorded bindings against current sources, and
a digest over the claim bytes used ONLY to detect corruption.

An UNKEYED digest stored beside the claim is NOT authenticity proof. The
writer of the record also holds the key material, because the key is the
record itself: a writer who alters a security-relevant field simply
recomputes the digest, and the record validates. A self-digest check answers
"were these bytes altered in transit", never "did an authorised writer
produce these bytes". Anything that labels a self-digest-checked record as
validated, authoritative, or safe to return to a consumer is a defect even
when no live consumer exists yet — the next reader inherits the false
label. Either remove the read path (see the removal-beats-defence rule above)
or require current source verification plus a fresh derivation and exact
field comparison before anything is returned as validated, and keep the
self-digest under a name that says corruption detection.

If cryptographic authentication is out of scope for the slice, say so as a
known limitation rather than implying the record is tamper-proof.

## Fail-open shapes that survive a schema check

  - **A loop over an empty collection is a pass, not a check.** A verifier
    that iterates a caller-supplied mapping and compares each entry performs
    ZERO comparisons when the mapping is empty, and returns success. Require
    the expected binding to be PRESENT and non-empty BEFORE entering the
    comparison loop, then validate that complete binding against the current
    sources. Give the empty/missing case its own typed refusal, distinct
    from the staleness mismatch code, so the two are not confused.
  - **A missing entry coerced to an empty mapping is a grant.** Converting an
    absent source entry into `{}` and then merging it with another source
    lets one authoritative source disappear silently. Absence is a typed
    refusal, never a default that another source fills in.
  - **A supplied set is validated member by member, not at its first
    member.** A check that only inspects the one field the primary assertion
    used leaves every other member of a caller-supplied set unvalidated AND
    lets it be persisted into the durable record.
  - **A frozen dataclass holding a mutable inner container is not
    immutable.** `frozen=True` stops attribute REBINDING on the outer
    object and does nothing to the dict it contains, so a captured snapshot
    whose sources map is a plain dict can have an entry replaced after the
    decision was taken. Nested structures need actual immutability (or a
    validated-ownership rule that forbids post-capture mutation) and the
    proof is a mutation, not a dataclass decorator.
  - **Two independent sources of truth for the same value.** When the
    serializer is handed both the decision and a separately supplied
    parsed snapshot, the record's provenance can describe bytes the decision
    never examined. Provenance and decision must be ONE value that travels
    together; a serializer that re-reads provenance from a second argument
    has to validate that argument against the decision's own binding, or
    refuse.
  - **A path built by interpolating an unvalidated identifier.** A
    profile-derived source path is a filesystem path: an identifier that is
    only checked for non-emptiness can carry traversal segments and resolve
    outside the supplied root, and a symlink inside the root redirects the
    read outside it. Validate the identifier as one safe path segment,
    resolve the root and every target, and refuse any target not contained
    under the resolved root -- with a symlink policy, not a containment
    check alone.
  - **Identities checked one field at a time are never joined.** Validating
    a runtime, an enabled flag and a profile name separately lets a
    definition whose own id belongs to a different identity satisfy every
    check. Selected profile, captured profile, preflight profile and the
    agent's own id must satisfy ONE declared relationship, and a mismatch
    must be refused naming the specific field.
  - **Free text persisted without a type and a disclosure rule.** A field
    accepted as "any non-empty string" is an uncontrolled channel into the
    durable record: a secret-shaped value passes validation and is written
    verbatim. Persisted fields need supported types, bounded formats, length
    limits, and an explicit rule for what may be written at all -- and where
    free text is not necessary, persist a controlled identifier or a digest
    instead of the text.

## Reading the envelope

Before declaring a budget spent, read the envelope's exact scope clause.
"per newly discovered issue group" grants each group its own allowance and is
not a total. When the clause is ambiguous, return one consolidated
authorization gap naming the readings and your recommendation, rather than
choosing the reading that stops the work. If you already told the operator a
bound was exhausted and it is not, correct that plainly before continuing.

Also read the completion criteria to see whether a SECOND independent
reviewer is covered. If the envelope says "each with an independent reviewer",
one per cycle is what it covers; if a second reviewer is required but not
authorized, return one exact review-authorization request after the first
PASS rather than dispatching it.

Record the remaining envelope limits BEFORE dispatching: the number of
sessions, the exact provider/model routes already authorized, and the
standing no-purchase/no-limit-change limits. When the envelope states no
numeric token or currency ceiling, record the limit as a session count
rather than inventing a number.

Report CONSUMPTION against those limits in the completion output, not just
the limits themselves: sessions authorised versus sessions used, provider
substitutions made, limit resets made, issue groups opened, and whether any
held operation was performed. An operator reading a completion report needs
to see what the envelope still has left, and a count that only appears in the
ledger is not visible at the point of decision.

### Do not let a clean provider fact stand in for envelope compliance

These are separate axes and a report must not let one cover for the other.
"No limit was reset, raised or purchased" and "no provider was substituted"
describe the PROVIDER's quota and route. They say nothing about whether the
envelope's OWN limits held. An envelope can leave the provider quota
untouched and still be breached: more sessions dispatched than authorized,
a token ceiling exceeded, a ceiling that was monitored rather than enforced.

So state each deviation on its own axis, with its own measurement:

  sessions dispatched vs authorized   every session, including one whose
                                      review produced no substantive finding
  ceilings                            the ceiling, the value observed at
                                      termination, the final recorded value,
                                      and the gap -- a monitored ceiling
                                      that was exceeded is breached, and the
                                      overshoot is reported
  provider quota                      reset / raised / purchased / substituted,
                                      as a separate line
  authorization deviations            any action taken outside what the
                                      envelope authorized, recorded with the
                                      reasoning that was overridden, not
                                      folded into the chronology as though it
                                      had been permitted

A sequence of attempts belongs in the report as a sequence, with each
attempt's outcome and usage on its own row: an attempt that was never
delivered, an attempt that delivered a verdict, and any subsequent attempt.
Collapsing them into "the review ran N times" hides both the attempt that
consumed nothing and the attempt that was not authorized.

And keep token usage separate from financial cost throughout: report the
token totals against the ceiling, report the cost fields only as the
records state them, and say plainly when no per-session cost figure is
derivable rather than estimating one from a token count.

### Record a passing suite as what it is

A green test suite is a measurement of the suite, not a qualification of an
invariant the suite does not measure. When a review returns a negative
disposition, record the acceptance set EXACTLY as delivered -- each item
PASS, FAIL or PARTIAL, including the partials -- and do not summarise the
set as "mostly passing" or let a total count stand in for the items. A
PARTIAL is its own answer: name what was left unproven.

A preserved failed candidate is evidence. So is a preserved negative verdict.
Keep both, plus the probe scripts that established each finding, and record
which of your own probes initially disagreed with a reviewer and how that
was resolved. A probe that appears not to reproduce can be wrong in the
direction that matters, and the corrected classification is part of the
record.
