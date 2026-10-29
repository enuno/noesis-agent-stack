#!/usr/bin/env python3
"""Flag read-only-classified tools whose description admits a write.

Upstream annotations are advisory. A tool can advertise readOnlyHint=true
and still describe a path that writes records, and a tool can describe a
write that happens only under a condition ("it saves to the user's leads when
the user explicitly asks"). When such a path exists the tool is mutating,
because the caller -- not the tool -- decides which path runs.

This scans an inventory for that contradiction and prints the matching
sentence, so the classification is reviewed rather than assumed. It reads the
inventory and writes nothing.

Usage
    scan_readonly_writes.py --inventory config/mcpjungle/tool-inventory.json
    scan_readonly_writes.py --inventory ... --catalog config/mcpjungle/tool-groups.json
    scan_readonly_writes.py --inventory ... --json

Exit codes
    0  no read-only-classified tool admits a write
    1  at least one candidate needs review
    2  the inventory is missing or unreadable
"""
from __future__ import annotations

import argparse
import json
import re
import sys

WRITE_PATTERNS = [
    re.compile(r"\bsaves?\s+to\s+(?:the\s+)?user", re.I),
    re.compile(r"\bsaves?\s+(?:the\s+)?\w+\s+(?:to|into)\s+(?:the\s+)?user", re.I),
    re.compile(r"\bcreates?\s+(?:a|an|the|new)\b", re.I),
    re.compile(r"\bwill\s+(?:save|create|write|add|insert|store)\b", re.I),
    re.compile(r"\bwrites?\s+(?:to|into)\b", re.I),
    re.compile(r"\badds?\s+(?:it|them|the\s+\w+)\s+(?:to|into)\b", re.I),
    re.compile(r"\bwhen\s+the\s+user\s+explicitly\s+asks\b", re.I),
    re.compile(r"\b(?:inserts?|deletes?|removes?|updates?)\s+(?:a|an|the|its|their)\b", re.I),
]


def sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", required=True, help="path to tool-inventory.json")
    ap.add_argument("--catalog", help="optional tool-groups.json, to report each tool's group")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    try:
        with open(args.inventory, encoding="utf-8") as fh:
            inv = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"FATAL: could not read inventory: {exc}", file=sys.stderr)
        return 2

    group_of: dict[str, str] = {}
    if args.catalog:
        try:
            with open(args.catalog, encoding="utf-8") as fh:
                cat = json.load(fh)
            for g in cat.get("groups", []):
                for t in g.get("tools", []):
                    group_of[t] = g["name"]
        except (OSError, ValueError) as exc:
            print(f"FATAL: could not read catalog: {exc}", file=sys.stderr)
            return 2

    findings = []
    for tool in inv.get("tools", []):
        if tool.get("risk_classification") != "low":
            continue
        if tool.get("inferred_capability_category") != "read-only":
            continue
        name = tool.get("name", "")
        for sent in sentences(tool.get("description") or ""):
            for pat in WRITE_PATTERNS:
                m = pat.search(sent)
                if m:
                    findings.append({
                        "tool": name,
                        "group": group_of.get(name),
                        "category": tool.get("inferred_capability_category"),
                        "risk": tool.get("risk_classification"),
                        "matched": m.group(0),
                        "sentence": sent,
                    })
                    break
            else:
                continue
            break

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        if not findings:
            print("PASS: no read-only-classified tool admits a write")
        else:
            for f in findings:
                print(f"REVIEW {f['tool']}  [group={f['group']}]  matched: {f['matched']!r}")
                print(f"       {f['sentence'][:300]}")
            print(f"\n{len(findings)} candidate(s): a tool that admits a write is not read-only")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
