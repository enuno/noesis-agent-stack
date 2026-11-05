# Verifying reviewer evidence against the candidate

How to prove that a repair cycle actually closed what an independent reviewer
found, and how to tell the three failure classes apart. Read this after a
reviewer returns REQUEST_CHANGES and before you write the repair contract,
and again after the repair returns.

## Why the reviewer's file, not the implementer's copy

A reviewer's negative test is the specification of the defect. It is the only
artifact that states, in executable form, what "refused" means: which refusal
code, which exception, which returned value.

An implementer who writes its own version of that test writes a test that
asserts whatever its own implementation happens to do. It then passes, the
report says "reviewer's test: FAILED → PASSED", and the candidate still fails
the reviewer's actual assertion. The rewrite hides the gap instead of closing
it, and it does so in the one row a reader is most likely to trust.

So: stage the reviewer's file as a canonical artifact, copy it into the
candidate suite byte-for-byte, and replay that copy.

### Staging

1. Keep the reviewer's file where it was produced until it is staged. A
   scratch file that evaporates between rounds is a spec that cannot be
   reproduced.
2. Copy it to a stable, hash-bound location in the mission artifacts, for
   example `contracts/<DOMAIN>-ADVERSARIAL-SUITE.py`, and record its
   byte length and SHA-256.
3. Add the in-suite destination path to the freeze tool's closed path set in
   the SAME work unit as the repair contract that permits it. A freeze tool
   that does not know the path will refuse to emit reviewer contracts, and
   widening the set after the fact reads as scope laundering.
4. In the repair contract, name the canonical path and its SHA-256, and
   require a byte-for-byte copy into the suite with no edits: no assertion
   change, no import change, no whitespace change. Require the copy's own
   SHA-256 to be reported and equal.

### Replaying

Run the reviewer's file against the candidate, not a paraphrase of it:

- Run the whole file together, and each test individually. A test that
  passes alone but fails in the file is an ordering or shared-state
  artifact, not a pass — resolve it (find the polluting test, isolate the
  fixture) rather than dismissing it.
- Run with the candidate worktree as the working directory, and print the
  imported package's `__file__` to confirm the suite resolved the
  worktree's module rather than an operational checkout or an installed
  package. A suite count is only worktree-bound once the import origin is
  proven.
- Run with the interpreter the project pins and with any ambient
  `PYTHONPATH` cleared.
- Compare the per-test result against the implementer's own report row. Any
  divergence is a reporting-accuracy defect in the receipt and must be
  recorded as one, separately from whether the behaviour is correct.

## When the provider refuses the reviewer session

A third refusal class exists besides entitlement blocks and model-support
errors: the provider's SAFETY FILTER can refuse a request mid-session. It
typically lands on the turn that would have written the verdict, AFTER the
reviewer has done its whole analysis. The result record carries an error
like a content-policy block, and no verdict file exists.

Do not read that as "the reviewer did nothing" and do not read it as a
verdict. Segment the session stream by `session_id` and count the tool calls
that DID complete — the analysis is evidence, and it is often complete.

Preserve before you do anything else:

  - the raw session stream, byte-identical, with its digest
  - the reviewer's own scratch artifacts — the scripts it wrote to recompute
    the identity, inspect the surface, compare cases, and probe behaviour —
    each with its digest
  - the absence of a verdict file, recorded as such

Recover with a CONCLUSION dispatch on the SAME lane — same provider, same
model, same reviewer profile. A refusal that produced no verdict consumed no
verdict, so it does not consume the authorised review either.

The conclusion packet is not a re-review. It must:

  - hand the reviewer ITS OWN observed results, so it need not re-run the
    analysis that already succeeded
  - forbid re-reading the preserved suites and forbid authoring new probe
    or test code — that accumulated content is what the filter objected to
  - require a preserved case to be referenced by short identifier or by the
    suite file's sha256, never by quoting the fixture literals from inside
    it
  - require neutral, concise wording: describe a behaviour by what it does,
    not by repeating the values that provoke the classifier
  - name the verdict path, which stays keyed to the candidate identity
  - instruct that if the filter recurs, the reviewer writes a BLOCKED verdict
    whose sole reason is the refusal class — a recorded disposition is a
    complete outcome, and no further tool calls follow a refusal

Give the reviewer the raw findings it had already established, including any
behaviour it had probed but not yet written up. Those are the ones a filter
interruption loses, and they are the ones a candidate is most likely to
carry an undiscovered defect on.

A refusal that produces no verdict is not a verdict and not a partial
verdict: record it as a failed dispatch with the analysis preserved. If a
second refusal lands on the same lane, stop the round and return one
consolidated authorization request — a different provider lane is a
substitution and needs its own authority, and repeating the same content
against the same classifier is not a fix.

## The three failure classes

Read the actual assertion failure before writing the repair contract. A
failing negative test is one of three things, and they need different repairs:

1. **Missing refusal.** The decision is still ALLOWED, or the forged input
   still produces the effect. This is a behavioural hole. The repair changes
   what the code does.
2. **Refusal present, vocabulary differs.** The decision is refused, but
   under a different refusal code than the reviewer's expected set. The
   behaviour is fail-closed; the contract is the code name. Align the code
   to the reviewer's set unless the candidate's own vocabulary is strictly
   more precise and the reviewer accepts it — and say which you did.
3. **Refusal present, API shape differs.** The function refuses, but it
   raises where the spec expects a returned denial (or the reverse). The
   behaviour is fail-closed; the contract is the surface. Convert the
   refusal into the shape the spec expects, and keep the refusal code and
   reason recoverable in the returned value.

Collapsing classes 2 and 3 into class 1 sends the executor to repair
behaviour that is already correct, burns a bounded cycle, and can make the
implementation worse by removing a working refusal to satisfy a naming
mismatch.

## Proving the repair has teeth

A regression that passes on the repaired bytes proves nothing until it fails
on the pre-repair bytes.

- Clone the ENTIRE worktree into scratch, not just the package directory. A
  partial clone leaves fixture paths unresolvable and yields a
  `FileNotFoundError` that looks like a successful mutation check.
- Locate the block to mutate by indentation, not by a hand-written regex. An
  imprecise replacement can leave a dangling call and produce a `NameError`
  instead of the intended assertion failure — and can patch a docstring line
  that merely mentions the symbol, producing a false "teeth confirmed".
- Assert the mutation actually changed the intended line before trusting the
  result.
- The regression must fail for the INTENDED reason: the route admitted, the
  value invented, the gate bypassed. A fixture or import error is not teeth.
- Record the before and after output as the teeth evidence.

### A negative-property proof needs its own teeth

A test that asserts a property CANNOT happen ("the decision core never
reopens a source", "no stage performs I/O") proves far less than it appears
to, and the usual proof is a RUNTIME DENIAL: patch the I/O entry points with
functions that raise, then assert the operation still succeeds.

That proof has a silent hole: it only covers the symbols it patched. A
read through `io.FileIO` bypasses `builtins.open`, `io.open` and `os.open`
entirely, so a stage that reopens a source through the C-level primitive
runs unmolested and the denial test passes. A STATIC scan has the mirror
defect: it proves the absence of a call only in the modules it walks, and
one module is rarely the whole stage.

Before you accept a negative-property proof:

- enumerate the entry points the audited code could use, not the ones that
  are conventional, and patch every one of them — or make the audited code
  read through a primitive the denial set covers;
- scan EVERY module in the audited stage, not just its entry point;
- INJECT the violation into a disposable copy of the candidate and confirm
  the proof FAILS to detect it. A proof that still passes with the
  violation present is not a proof.

Keep the injection in a copy, never in the candidate tree, and verify the
candidate's per-file digests before and after. The injection is a mutation
probe: confine it, run it, and report the result either way. When the
proof survives the injection, report THAT as the finding — the property may
be true in the current code while the evidence does not establish it — and
put it to the reviewer as an open question rather than silently repairing
it inside a bounded cycle.

## Reproducing a finding without manufacturing a false negative

Your own reproduction is evidence about the CANDIDATE, so it can be wrong in
the direction that matters: a probe that appears not to reproduce a real
finding is a false negative that would send you to "the reviewer is wrong"
and close a live defect. Two probe-design traps cause this, and both look
like a clean non-reproduction.

**A fixture that binds the bytes will refuse your mutation for a different
reason than the one under test.** When a fixture pins a digest of every
source, mutating one source makes the pipeline refuse on the DIGEST BINDING
before it ever reaches the validation you are probing. The refusal is real,
but it is not the finding. Rebind the fixture's dependent digests to the
mutated bytes first, so the ONLY thing broken is the invariant under test.
Record that you rebound, and say which invariant the probe isolates.

**Comparing two snapshots of an UNCHANGED tree cannot show a mismatch.**
Pairing a decision from snapshot A with provenance from snapshot B, where
both were captured from the same bytes, proves nothing — the digests are
identical by construction, so the pair can never disagree. To show a
cross-pairing or mutation defect, make the two sides ACTUALLY DIFFER: mutate
the captured map in place between the decision and the serialization, and
assert that the emitted record carries the mutated value under one identity
while still claiming the original under another.

The check for either trap: the probe must FAIL against a deliberately
violating candidate. A probe that passes against both a violating and a
clean candidate is not measuring the property. Run the same injection
technique used for a negative-property proof — copy the tree, introduce the
violation, confirm the probe reports it — and state the result either way.
When your reproduction disagrees with the reviewer, do not resolve the
disagreement in the reviewer's favour or yours by default: reproduce both
ways, report which probe isolates which invariant, and keep the reviewer's
finding live until a probe that has teeth contradicts it.

## Converging a repeated finding shape

When consecutive review rounds surface the same SHAPE of defect — typically a
caller-supplied or weakly-observed value steering a decision that must be
bound to an authoritative source — fixing one instance invites the next one.

Require a class sweep as a deliverable: the implementer enumerates every
caller-supplied value that can influence a decision (classification sets,
capability indexes, epochs, runtime profiles, revisions, policy objects,
registries, adapters), and for each one states whether it is now bound to an
authoritative source, refused, consumed without authority, or deliberately
authoritative. A table with one row per value is the artifact.

Treat the next same-shape finding as an incomplete cycle rather than a newly
discovered issue group, so a single defect's instances cannot be counted as
separate groups to keep spending the bound.

## Reading the cycle bound

A budget phrased as "N cycles per newly discovered issue group" grants N
cycles per group, not N cycles for the whole workstream. Classify each
round's findings as a new group or a re-surface of an open one, and track
consumption per group.

If you have already told the operator a budget was exhausted and then read
the bound and find it says otherwise, correct it plainly: quote the wording,
state the reading you are now applying, and say whether to continue. Do not
silently reinterpret the bound in either direction, and do not open another
group's budget without saying so.
