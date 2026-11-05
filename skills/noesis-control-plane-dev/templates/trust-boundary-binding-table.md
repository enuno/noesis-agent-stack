# Trust boundary — binding table

Status: AUTHORITATIVE DESIGN INPUT. Define before patching.
Candidate: <name>   base commit: <sha>   branch: <branch>

## Retained public surface

| symbol | role |
| --- | --- |
| `<symbol>` | <role> |

## Removed public surface — deleted, not left callable

| removed | reason |
| --- | --- |
| `<symbol>` | <why it is no longer this candidate's responsibility> |

## RULE A — observed evidence is never relabelled.
An observation naming provider P is never re-expressed as provider Q to fit a
requested identity. Mismatch is a refusal, and the persisted evidence carries
the OBSERVED names.

## RULE B — the decision record is an immutable snapshot, not a grant.
It records what was decided, from which sources, under which identity. Any
consumer must apply current authority and fencing checks itself.

## Binding rows

### B1 — <value name>

| field | value |
| --- | --- |
| **Value** | |
| **Authoritative source** | |
| **Who may supply or alter it** | |
| **Validation rule** | |
| **Persisted binding** | |
| **Consumer** | |
| **Negative test** | |

(repeat one row per value that can influence a decision)

## What is NOT in this candidate

- <explicitly excluded surfaces, so their absence reads as design>

## Storage and access trust assumptions

<state plainly whether the durable store is cryptographically authenticated or
only protected by convention and file permissions, and what the candidate does
with records it cannot trust>
