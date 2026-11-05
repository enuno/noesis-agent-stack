# <Candidate name> — Review Packet

Reviewer: <profile> (independent; you did not implement this)
Supervisor: <supervisor> (must not review its own dispatch)
Lane: <provider> / <model> (record the provider and model you actually used)

This is a FOCUSED packet. It is not the mission history. Complete evidence is
available on demand at the paths named below; read only what you need.

## 1. Exact candidate identity — recompute before you judge

  base commit              <sha>
  branch                   <branch>
  worktree                 <path>
  tracked diff SHA-256     <hex>
  combined content digest  <hex>
  changed paths            <n>

Per-file digests: <path to per-file digest file>

Combined digest recipe: <the exact byte recipe, so the reviewer can reproduce
it rather than trust it>

Recompute both digests yourself, BEFORE and AFTER your tests. If they differ
from the values above, or differ before and after, write BLOCKED and stop.

The changed path set is exactly these <n>:

  <one path per line>

## 2. What this candidate is

<one paragraph: the question it answers, and explicitly what it does NOT do>

### The reduced public surface — exactly this

  <symbols>

### Deleted from the public surface — verify each is GONE

  <symbols and the reason each was removed>

Check BOTH the module namespace and the package namespace.

### The trust boundary is already defined — read it

  <path to the binding table>

Judge the candidate against that table. A row that is not actually enforced
is a finding.

### The complete remaining production-source diff

  <path to the diff file> — <bytes>, sha256 <hex>

Read it from that path; do not ask for it to be pasted back to you.

## 3. Findings and regression mapping

| finding | disposition | regression |
| --- | --- | --- |
| <F-id> <one line> | <how it was addressed> | <test names> |

### The reviewer's own preserved cases — RUN THESE

<path>  sha256 <hex>
<path>  sha256 <hex>

To run a preserved suite against the candidate, copy it into the tests
directory under a distinct filename, run it, and REMOVE the copy afterwards.
Do not leave it in the worktree and do not modify it. Report every case that
fails.

Your classification of the cases is below. VERIFY it rather than accepting
it.

  RETAINED: <names>
  REMOVED-INTERFACE: <names>
  STALE-PRECONDITION: <names>

The measured byte-fidelity count for the retained cases was <n> of <m>. The
differences were <reasons>. Verify that claim yourself.

## 4. Interface contracts and test results

### The structural guarantee you should check first

<the structural property, and how to check it>

### The retained public surface, exercised

<what the decision carries>

### The durable record

<what is written, through which existing path, and the storage trust assumption>

### Test results, observed by the supervisor

  <suite>            <counts>, exit <status>, <duration>
  <focused packet>   <counts>
  git diff --check   exit <status>
  workflow counts    <where the exact counts live>

Run it yourself:

  <command>

## 5. What to review, and what not to

REVIEW, at minimum:

  1. <...>
  2. <...>

DO NOT:

  - Do not edit, stage, commit, push or create a pull request. Do not repair
    anything you find; report it.
  - Do not modify the operational checkout.
  - Do not perform a live provider request, readiness probe, or dispatch.
  - Do not require the scope to grow. The absence of <surfaces> is the
    intended design, not a gap.
  - Do not spend more than one review session.

## 6. Verdict

Write your verdict to exactly:

  <path keyed to the candidate digest>

That path is keyed to the candidate identity you are reviewing. Do not write
to any other verdict path. A previous review's verdict file must never be
overwritten.

<the required header fields, the verdict token set, the required sections>
