# Review packet identity

A review packet is evidence. The reviewer is asked to certify the artifact
against the identity tuple the packet declares, so the packet's numbers are
load-bearing: a mismatch does not cost a finding, it costs the whole review.

## Why a packet blocks a review before anything is reviewed

The reviewer reproduces the identity first. If the packet's own fields
disagree with each other, or with the artifacts, there is no single tuple to
certify against, and the correct outcome is BLOCKED at the prerequisite
stage: no suite run, no boundary examined, no finding. The artifact can be
perfect and the review still produce nothing.

## The three ways the numbers go wrong

1. **A support file is omitted from the count.** `test_*.py` files are easy
   to count; `conftest.py` beside them is not, because it does not match the
   `test_` prefix. Say "9 test files" when the directory holds 10.
2. **A character count is labelled as a byte count.** `len(text)` and
   `len(text.encode())` differ whenever the text carries a multi-byte
   character, and Markdown artifacts carry em-dashes (3 bytes in UTF-8) and
   other punctuation by the hundred. Report both numbers, each labelled.
3. **A digest is quoted from an earlier round.** The combined digest and the
   per-file digests are separate values; quoting one where the other belongs
   produces a tuple that cannot reproduce.

## Generate the block; never type it

`scripts/packet_identity.py` does this.

```
python3 scripts/packet_identity.py render \
  --manifest <per-file-digests.json> --root <candidate-root> \
  --artifact design=<design-artifact.md>
```

`render` prints the identity block: file count with its breakdown, the
combined digest, the per-file list and digests, and for each declared
artifact BOTH its byte count and its character count, each labelled. Paste
that block into the packet. Never hand-write a count or a size.

`verify` checks a finished packet against the artifacts:

```
python3 scripts/packet_identity.py verify \
  --manifest <per-file-digests.json> --root <candidate-root> \
  --packet <review-packet.md> --artifact design=<design-artifact.md>
```

It reports every disagreement with the offending line, so a packet that
mentions a stale count in a note about a previous round is caught and
rephrased rather than silently shipped. Exit 0 means the packet agrees with
the artifacts.

The `--artifact label=path` label must be a token that appears on the line
carrying the size claim, so the checker can attribute the number to the file
it describes.

## Two dispatch gates, both before any provider call

The candidate gate and the packet gate protect different things.

  candidate gate   recomputes the frozen digest and refuses when the bytes
                   moved. Protects the artifact from the delay.
  packet gate      recomputes what the packet says about those bytes and
                   refuses when the description is wrong. Protects the
                   review from the packet.

Both run in the launcher before the reviewer starts. Prove both refusal
paths with a stub launcher that echoes its argv and exits: the refusal must
be observed to happen with no provider call and no session row. Keep the
stub's output on a separate log so it cannot be counted as the session's.

## A packet block is a packet defect; the next dispatch is a separate question

When a reviewer blocks at the identity gate, classify it before routing.

  stopped at the identity gate   nothing was reviewed; the cause is the
                                 packet. Fix the packet, keep the candidate
                                 bytes UNCHANGED, and write any subsequent
                                 verdict to a DIFFERENT path so the BLOCKED
                                 verdict survives unmodified.
  carries findings or test results  the review happened. It routes to the
                                 implementer.

Record which of the two it was, the attempt's measured token and tool-call
usage against the ceiling, and the fact that the candidate digest did not
move between the attempts. A re-dispatch is not a repair cycle: no source
changes and no new issue group.

### The classification does not grant the re-dispatch

A DELIVERED verdict consumed the review session whatever it stopped at --
the reviewer ran, the provider billed, the lane was used. Classification
tells you what to FIX; it does not tell you that you may dispatch again.
Whether another session is permitted comes from the envelope's authorization
language:

  envelope names one review and forbids automatic replacement
  or continuation sessions      return ONE request naming the re-dispatch
                                 you want (lane, ceilings, unchanged
                                 candidate digest). Do not dispatch on your
                                 own judgement.
  envelope authorizes a bounded attempt or re-dispatch budget  dispatch
                                 within it, and record which clause you
                                 are reading.

A dispatch that never reached the model -- zero tokens, zero tool calls, no
session row -- consumed nothing, and the authorization is still outstanding;
that case is genuinely re-dispatchable.

Precedent from an earlier envelope is never authorization for this one. If
you dispatch anyway, record it as an authorization deviation with the
reasoning that was overridden, rather than folding it into the chronology as
though it had been authorized.

## Counting helpers

`str.endswith("test_*.py")` does not glob -- it compares a literal suffix,
so the pattern never matches and the count silently comes back wrong. Use
`fnmatch` (or `Path.glob`) for pattern counts, and assert the count against
the directory listing before putting it in a packet.
