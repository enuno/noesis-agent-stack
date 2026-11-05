#!/usr/bin/env python3
"""Measure a candidate's frozen identity and cross-check a review packet.

A review packet is evidence. The reviewer is asked to certify the artifact
against the identity tuple the packet declares, so the packet's numbers are
load-bearing: a mismatch does not cost a finding, it costs the whole review.
Every number in that block must therefore be GENERATED from the artifacts and
checked before dispatch -- never typed.

Digest recipe (path-prefixed, NUL-separated, sorted by path):

    h = sha256()
    for path in sorted(paths):
        h.update(path.encode()); h.update(b"\\0")
        h.update(sha256_hex_of_file_at_path.encode()); h.update(b"\\0")

Usage:
    packet_identity.py render --manifest M --root R [--artifact label=path]...
    packet_identity.py verify --manifest M --root R --packet P
                              [--artifact label=path]...

`render` prints the measured identity block to paste into the packet.
`verify` exits 0 when the packet agrees with the artifacts, 1 on a mismatch,
and 2 on a usage or I/O error. Run `verify` in the launcher's pre-dispatch
gates so a mismatch refuses the dispatch before any provider call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

NUM_BYTES = re.compile(r"([\d][\d,]{2,})\s*bytes\b")
COUNT_PATTERNS = (
    re.compile(r"frozen\s+file\s+count\s*[:=]?\s*(\d+)", re.I),
    re.compile(r"file\s+count\s*[:=]?\s*(\d+)", re.I),
    re.compile(r"(\d+)\s+frozen\s+files", re.I),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: str) -> tuple[dict[str, str], dict]:
    """Accept {"path": "sha"} or {"files": {"path": "sha"}}."""
    raw = json.loads(Path(path).read_text())
    data = raw["files"] if isinstance(raw.get("files"), dict) else raw
    if not isinstance(data, dict):
        raise SystemExit("manifest must be a JSON object of path -> sha256")
    return {str(k): str(v) for k, v in data.items()}, raw


def combined_digest(per_file: dict[str, str]) -> str:
    h = hashlib.sha256()
    for key in sorted(per_file):
        h.update(key.encode())
        h.update(b"\0")
        h.update(per_file[key].encode())
        h.update(b"\0")
    return h.hexdigest()


def measure(manifest: str, root: str) -> tuple[dict[str, str], dict[str, str], list[str], dict]:
    per_file, raw = load_manifest(manifest)
    base = Path(root)
    live: dict[str, str] = {}
    missing: list[str] = []
    for key in sorted(per_file):
        target = base / key
        if not target.is_file():
            missing.append(key)
            continue
        live[key] = sha256_bytes(target.read_bytes())
    return per_file, live, missing, raw


def count_by(names: list[str], directory: str, pattern: str) -> int:
    """Count files under `directory` whose name matches `pattern`.

    Use fnmatch, not str.endswith: `endswith("test_*.py")` compares a literal
    suffix and silently matches nothing.
    """
    return sum(1 for n in names if directory in n and fnmatch(Path(n).name, pattern))


def parse_artifacts(pairs: list[str]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--artifact expects label=path, got {pair!r}")
        label, path = pair.split("=", 1)
        artifacts[label] = path
    return artifacts


def render(manifest: str, root: str, artifacts: dict[str, str]) -> str:
    _, live, missing, raw = measure(manifest, root)
    names = sorted(live)
    lines = [
        "  base commit            " + str(raw.get("base_commit", "(unknown)")),
        "  frozen file count      %d  (%d under tests/)"
        % (len(live), count_by(names, "tests", "test_*.py")),
        "  frozen combined digest " + combined_digest(live),
        "",
        "  The frozen file set is exactly:",
    ]
    for n, key in enumerate(names, 1):
        lines.append("   %2d. %s" % (n, key))
    if missing:
        lines.append("")
        lines.append("  MISSING FROM THE TREE (declared but absent):")
        for key in missing:
            lines.append("   !! " + key)
    for label, path in sorted(artifacts.items()):
        data = Path(path).read_bytes()
        text = data.decode("utf-8", errors="replace")
        lines.append("")
        lines.append(
            "  %-8s %d bytes on disk, %d characters, sha256 %s"
            % (label, len(data), len(text), sha256_bytes(data))
        )
    return "\n".join(lines)


def verify(manifest: str, root: str, packet: str, artifacts: dict[str, str]) -> int:
    _, live, missing, _ = measure(manifest, root)
    text = Path(packet).read_text()
    problems: list[str] = []

    if missing:
        problems.append(
            "%d declared file(s) absent from the tree: %s"
            % (len(missing), ", ".join(missing[:5]))
        )

    combined = combined_digest(live)
    if combined not in text:
        problems.append("combined digest %s does not appear in the packet" % combined)

    for key, digest in sorted(live.items()):
        if key not in text:
            problems.append("frozen file not listed in the packet: %s" % key)
        if digest not in text:
            problems.append("digest for %s does not appear in the packet" % key)

    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern in COUNT_PATTERNS:
            for match in pattern.finditer(line):
                declared = int(match.group(1))
                if declared != len(live):
                    problems.append(
                        "line %d declares %d frozen files, the manifest holds %d: %s"
                        % (lineno, declared, len(live), line.strip()[:90])
                    )

    for label, path in sorted(artifacts.items()):
        data = Path(path).read_bytes()
        nbytes = len(data)
        nchars = len(data.decode("utf-8", errors="replace"))
        base = Path(path).name
        for lineno, line in enumerate(text.splitlines(), 1):
            if label not in line and base not in line:
                continue
            for match in NUM_BYTES.finditer(line):
                declared = int(match.group(1).replace(",", ""))
                if declared != nbytes:
                    problems.append(
                        "line %d declares %s bytes for %s but the file is %d bytes "
                        "on disk (character count is %d): %s"
                        % (lineno, match.group(1), label, nbytes, nchars, line.strip()[:90])
                    )

    print("MEASURED  file_count=%d  combined=%s" % (len(live), combined))
    for label, path in sorted(artifacts.items()):
        data = Path(path).read_bytes()
        print(
            "MEASURED  %s: %d bytes / %d chars"
            % (label, len(data), len(data.decode("utf-8", errors="replace")))
        )
    if problems:
        print("PACKET IDENTITY: INCONSISTENT")
        for problem in problems:
            print("   -", problem)
        return 1
    print("PACKET IDENTITY: CONSISTENT with the artifacts")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["render", "verify"])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--packet")
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()

    artifacts = parse_artifacts(args.artifact)
    if args.command == "render":
        print(render(args.manifest, args.root, artifacts))
        return 0
    if not args.packet:
        parser.error("verify requires --packet")
    return verify(args.manifest, args.root, args.packet, artifacts)


if __name__ == "__main__":
    sys.exit(main())
