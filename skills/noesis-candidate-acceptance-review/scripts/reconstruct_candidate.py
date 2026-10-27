#!/usr/bin/env python3
"""Reconstruct a superseded candidate from the git object DB and print every
diff-hash recipe variant, so a claimed hash can be matched to the recipe that
produced it.

Read-only with respect to the repository: the real index is never touched
(GIT_INDEX_FILE is redirected into a scratch dir) and no commits are made.

Usage:
    reconstruct_candidate.py --repo <worktree> --base <sha> --scratch <dir>
                             [--blob <sha256>:<path> ...]
                             [--tracked <path> ...] [--new <path> ...]
                             [--claimed <sha256> ...]

    --blob <sha256>:<path>   candidate file content, identified by the SHA-256
                             of its bytes; looked up in the object DB.
    --tracked <path>         path that is a tracked modification vs base.
    --new <path>             path that is a new (untracked) file in the candidate.
    --claimed <sha256>       a claimed hash to check against every variant.

Without --blob the script just materialises the base tree and reports the
hashes of the tracked/new path sets you name, which is enough to check a
tracked-only or combined hash that the caller assembles by hand.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str, env: dict | None = None) -> str:
    """Run a git command in `repo` and return stdout as text."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_blob_index(repo: Path) -> dict[str, str]:
    """Map SHA-256 of blob content -> git object id.

    Git object ids are a hash over a header plus the content, so they never
    equal the plain SHA-256 of the file bytes. Hash the content directly.
    """
    index: dict[str, str] = {}
    listing = git(
        repo,
        "cat-file",
        "--batch-all-objects",
        "--batch-check=%(objectname) %(objecttype)",
    )
    blobs = [
        line.split()[0]
        for line in listing.splitlines()
        if line.split()[1:2] == ["blob"]
    ]
    for oid in blobs:
        data = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", oid],
            capture_output=True,
        ).stdout
        index.setdefault(sha256_bytes(data), oid)
    return index


def materialize(repo: Path, base: str, tree: Path, blobs: dict[str, str]) -> None:
    """Write the base tree into `tree`, then overlay candidate content."""
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", base],
        capture_output=True,
    ).stdout
    tree.mkdir(parents=True, exist_ok=True)
    import io
    import tarfile

    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(tree)


def overlay(tree: Path, index: dict[str, str], blob_specs: list[str]) -> list[str]:
    """Overlay candidate file content looked up by content SHA-256."""
    applied = []
    for spec in blob_specs:
        digest, _, rel = spec.partition(":")
        if not rel:
            raise SystemExit(f"--blob expects <sha256>:<path>, got {spec!r}")
        oid = index.get(digest)
        if oid is None:
            raise SystemExit(f"no blob in object DB with sha256 {digest} ({rel})")
        data = subprocess.run(
            ["git", "-C", str(tree.parent), "cat-file", "blob", oid],
            capture_output=True,
        ).stdout
        dest = tree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        applied.append(rel)
    return applied


def diff_variants(repo: Path, base: str, tree: Path, new_paths: list[str]) -> dict[str, str]:
    """Compute the diff-hash recipe variants for the reconstructed tree."""
    scratch = tree.parent
    env = dict(os.environ)
    env["GIT_INDEX_FILE"] = str(scratch / "idx")
    env["GIT_WORK_TREE"] = str(tree)

    def run_diff(extra: list[str]) -> str:
        out = scratch / "variant.diff"
        subprocess.run(
            ["git", "-C", str(repo), "diff", "--no-color", *extra],
            capture_output=True,
            text=True,
            env=env,
            stdout=out.open("w"),
        )
        return sha256_file(out)

    variants: dict[str, str] = {}

    # A: tracked-only (new files are not in the index, so not in the diff)
    idx = scratch / "idx"
    if idx.exists():
        idx.unlink()
    git(repo, "read-tree", base, env=env)
    variants["tracked-only"] = run_diff([])

    # B: new files included as additions via intent-to-add
    if new_paths:
        subprocess.run(
            ["git", "-C", str(repo), "add", "-N", "--", *new_paths],
            capture_output=True,
            text=True,
            env=env,
        )
    variants["tracked+new-as-additions"] = run_diff([])

    # C: fully staged
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"],
        capture_output=True,
        text=True,
        env=env,
    )
    staged = scratch / "staged.diff"
    subprocess.run(
        ["git", "-C", str(repo), "diff", "--no-color", "--cached", base],
        capture_output=True,
        text=True,
        env=env,
        stdout=staged.open("w"),
    )
    variants["fully-staged"] = sha256_file(staged)

    return variants


def combined_hash(tracked_diff: Path, tree: Path, new_paths: list[str]) -> str:
    """The 'tracked diff + --- new files --- + new file bodies' recipe."""
    out = tree.parent / "combined.diff"
    with out.open("w") as fh:
        fh.write(tracked_diff.read_text())
        fh.write("--- new files ---\n")
        for rel in new_paths:
            fh.write(f"+++ {rel} (untracked) +++\n")
            fh.write((tree / rel).read_text())
    return sha256_file(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--base", required=True)
    ap.add_argument("--scratch", required=True, type=Path)
    ap.add_argument("--blob", action="append", default=[])
    ap.add_argument("--tracked", action="append", default=[])
    ap.add_argument("--new", action="append", default=[])
    ap.add_argument("--claimed", action="append", default=[])
    args = ap.parse_args()

    repo = args.repo.resolve()
    scratch = args.scratch.resolve()
    tree = scratch / "tree"
    scratch.mkdir(parents=True, exist_ok=True)

    index = build_blob_index(repo)
    materialize(repo, args.base, tree, index)
    if args.blob:
        overlay(tree, index, args.blob)

    print("== reconstructed tree per-file sha256 ==")
    for rel in args.tracked + args.new:
        path = tree / rel
        if path.is_file():
            print(f"  {sha256_file(path)}  {rel}")
        else:
            print(f"  MISSING  {rel}")

    variants = diff_variants(repo, args.base, tree, args.new)
    if args.new:
        tracked_diff = scratch / "variant.diff"
        variants["combined"] = combined_hash(tracked_diff, tree, args.new)

    print("\n== diff hash variants ==")
    for name, digest in variants.items():
        mark = ""
        if digest in args.claimed:
            mark = "   <== MATCHES a claimed hash"
        print(f"  {name:28s} {digest}{mark}")

    unmatched = [c for c in args.claimed if c not in variants.values()]
    if unmatched:
        print("\n== claimed hashes not matched by any variant ==")
        for c in unmatched:
            print(f"  {c}")
        print("  (a mismatch is a finding about the RECIPE or the REPORT,")
        print("   not proof of tampering — try other recipes before reporting)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
