# Snapshot-digest and per-file verification

Reusable method for verifying ordered-manifest snapshot digests in Noesis
freeze/evidence packets (Track A/B reconstructed and revised packets).

## Ordered-manifest digest algorithm

The recorded algorithm is:

> SHA-256 of the UTF-8 bytes of newline-joined `<sha256-or-MISSING>  <path>`
> over the ordered manifest, **plus one trailing newline**.

## Correct recompute (Python)

```python
import hashlib, json

def digest_of(packet_path):
    p = json.load(open(packet_path))
    lines = [f"{m['sha256']}  {m['path']}" for m in p["ordered_manifest"]]
    blob = "\n".join(lines) + "\n"          # trailing newline is REQUIRED
    return hashlib.sha256(blob.encode()).hexdigest()
```

## Why the trailing newline matters

The digest is `sha256("...".join(lines) + "\n")`. A first-pass recompute that
joins without the trailing newline produces a DIFFERENT hash and falsely
reports a mismatch. Always try the variants before declaring a discrepancy:

- `"\n".join(lines)`
- `"\n".join(lines) + "\n"`  (this is the canonical form)
- space-joined, path-only, and hash-only variants

If `+"\n"` matches the recorded digest, the packet is internally consistent.

## Per-file manifest verification

Verify each entry in `ordered_manifest` against the on-disk file:

```python
import hashlib, os, json
p = json.load(open(packet_path))
for m in p["ordered_manifest"]:
    path = m["path"]
    try:
        actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print("OK " if actual == m["sha256"] else "DIFF ", path)
    except FileNotFoundError:
        print("MISS", path)
```

When a packet lists absolute paths that point into a different checkout than
the repo you are reading (Track B dev checkout vs noesis-agent-stack), resolve
relative paths against the correct dev directory before hashing.

## Reporting

Report each artifact as `recorded = recomputed` and state MATCH/DIFF/MISS so
provenance is auditable. Do not write a digest into a bundle that you have not
recomputed.
