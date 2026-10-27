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
import shutil
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
    """Write the base tree into `tree`, then overlay candidate content.

    The reconstruction directory is recreated only after git archive has
    returned a non-empty archive. Reusing a non-empty tree would keep
    leftover files from a previous candidate and let the fully-staged
    variant stage them as additions. An invalid base leaves the existing
    tree untouched.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "archive", base],
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        reason = err or "empty archive"
        raise SystemExit(
            f"git archive {base} failed (exit {result.returncode}): {reason}; "
            f"reconstruction directory left untouched"
        )
    archive = result.stdout
    if tree.exists():
        sys.stderr.write(
            f"reconstruction directory {tree} already exists; recreating it "
            f"before extracting the base so leftover files from a previous "
            f"candidate cannot contaminate this reconstruction\n"
        )
        try:
            shutil.rmtree(tree)
        except OSError as exc:
            raise SystemExit(
                f"refusing to extract into existing reconstruction directory {tree}: "
                f"could not recreate it ({exc}). Leftover files would contaminate "
                f"the candidate."
            ) from exc
    tree.mkdir(parents=True)
    import io
    import tarfile

    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(tree)


def overlay(repo: Path, tree: Path, index: dict[str, str], blob_specs: list[str]) -> list[str]:
    """Overlay candidate file content looked up by content SHA-256.

    Blobs are read from `repo`, not from the scratch directory. A failed
    cat-file writes nothing. The path from `<sha256>:<path>` is confined
    to the reconstruction tree before any write: an absolute path or a
    '..' segment is refused, and the resolved destination must stay under
    that tree.
    """
    applied = []
    for spec in blob_specs:
        digest, _, rel = spec.partition(":")
        if not rel:
            raise SystemExit(f"--blob expects <sha256>:<path>, got {spec!r}")
        blob_path = Path(rel)
        if blob_path.is_absolute() or ".." in blob_path.parts:
            raise SystemExit(
                f"refusing --blob path {rel!r}: absolute paths and '..' "
                f"segments are not allowed"
            )
        dest = (tree / blob_path).resolve()
        root = tree.resolve()
        try:
            dest.relative_to(root)
        except ValueError:
            raise SystemExit(
                f"refusing --blob path {rel!r}: resolved destination {dest} "
                f"is outside reconstruction tree {root}"
            ) from None
        oid = index.get(digest)
        if oid is None:
            raise SystemExit(f"no blob in object DB with sha256 {digest} ({rel})")
        result = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", oid],
            capture_output=True,
        )
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="replace").strip()
            raise SystemExit(
                f"git cat-file blob {oid} failed (exit {result.returncode}) "
                f"for {rel}: {err}"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(result.stdout)
        applied.append(rel)
    return applied


def diff_variants(repo: Path, base: str, tree: Path, new_paths: list[str]) -> dict[str, str]:
    """Compute the diff-hash recipe variants for the reconstructed tree."""
    scratch = tree.parent
    env = dict(os.environ)
    env["GIT_INDEX_FILE"] = str(scratch / "idx")
    env["GIT_WORK_TREE"] = str(tree)

    def run_diff(extra: list[str], out_name: str) -> str:
        # stdout goes to its own file; stderr is captured separately so a
        # failure is visible. capture_output cannot be combined with stdout.
        out = scratch / out_name
        with out.open("wb") as fh:
            result = subprocess.run(
                ["git", "-C", str(repo), "diff", "--no-color", *extra],
                stdout=fh,
                stderr=subprocess.PIPE,
                env=env,
            )
        err = result.stderr.decode("utf-8", errors="replace")
        if err:
            sys.stderr.write(err)
            if not err.endswith("\n"):
                sys.stderr.write("\n")
        # git diff exits 1 when the patch is non-empty; only >1 is a failure.
        if result.returncode > 1:
            raise RuntimeError(
                f"git diff --no-color {' '.join(extra)} failed "
                f"(exit {result.returncode}): {err.strip()}"
            )
        return sha256_file(out)

    variants: dict[str, str] = {}

    # A: tracked-only (new files are not in the index, so not in the diff)
    idx = scratch / "idx"
    if idx.exists():
        idx.unlink()
    git(repo, "read-tree", base, env=env)
    variants["tracked-only"] = run_diff([], "tracked-only.diff")

    # B: new files included as additions via intent-to-add
    if new_paths:
        subprocess.run(
            ["git", "-C", str(repo), "add", "-N", "--", *new_paths],
            capture_output=True,
            text=True,
            env=env,
        )
    variants["tracked+new-as-additions"] = run_diff([], "tracked-plus-new.diff")

    # C: fully staged
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"],
        capture_output=True,
        text=True,
        env=env,
    )
    variants["fully-staged"] = run_diff(["--cached", base], "staged.diff")

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
        overlay(repo, tree, index, args.blob)

    print("== reconstructed tree per-file sha256 ==")
    for rel in args.tracked + args.new:
        path = tree / rel
        if path.is_file():
            print(f"  {sha256_file(path)}  {rel}")
        else:
            print(f"  MISSING  {rel}")

    variants = diff_variants(repo, args.base, tree, args.new)
    if args.new:
        tracked_diff = scratch / "tracked-only.diff"
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
