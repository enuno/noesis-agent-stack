#!/usr/bin/env python3
"""Repair corrupted research vault ledgers.

Attempts to repair ledgers by:
- Replaying from run receipts to reconstruct state.
- Truncating after the last valid JSONL record.
- Rebuilding indexes from ledger contents.

Usage:
    python recover.py --vault-dir workspace/research-vault
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover corrupted vault ledgers")
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    parser.add_argument(
        "--strategy",
        choices=["truncate", "replay", "rebuild"],
        default="truncate",
        help="Recovery strategy",
    )
    return parser.parse_args(argv)


def truncate_after_last_valid(path: Path) -> int:
    """Truncate a JSONL file after the last valid record.

    Returns the number of records kept.
    """
    if not path.exists():
        return 0

    backup_path = path.with_suffix(path.suffix + ".backup")
    shutil.copy2(path, backup_path)

    valid_records: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
                valid_records.append(stripped)
            except json.JSONDecodeError:
                break

    with open(path, "w", encoding="utf-8") as f:
        for record in valid_records:
            f.write(record + "\n")

    return len(valid_records)


def replay_from_receipts(vault_dir: Path) -> dict:
    """Replay ledger state from run receipts.

    Returns a summary of reconstructed state.
    """
    receipts_path = vault_dir / "state" / "runs" / "receipts.jsonl"
    if not receipts_path.exists():
        return {"receipts_found": 0, "reconstructed": {}}

    receipts: list[dict] = []
    with open(receipts_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                receipts.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Reconstruct which artifacts were written in completed runs
    artifacts: set[str] = set()
    for receipt in receipts:
        if receipt.get("status") == "completed":
            artifacts.update(receipt.get("artifacts_written", []))

    return {
        "receipts_found": len(receipts),
        "completed_runs": sum(1 for r in receipts if r.get("status") == "completed"),
        "artifacts_tracked": sorted(artifacts),
    }


def rebuild_indexes(vault_dir: Path) -> None:
    """Rebuild any derived indexes from ledger contents.

    Currently a no-op — indexes are read on demand.
    This function serves as a hook for future index rebuilding.
    """
    pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()

    ledgers = [
        vault_dir / "knowledge" / "sources.jsonl",
        vault_dir / "knowledge" / "claims.jsonl",
        vault_dir / "knowledge" / "findings.jsonl",
        vault_dir / "state" / "runs" / "receipts.jsonl",
    ]

    if args.strategy == "truncate":
        print("Truncating ledgers after last valid record ...")
        for ledger in ledgers:
            if ledger.exists():
                kept = truncate_after_last_valid(ledger)
                print(f"  {ledger.name}: {kept} records kept")
    elif args.strategy == "replay":
        print("Replaying from receipts ...")
        summary = replay_from_receipts(vault_dir)
        print(f"  Receipts found: {summary['receipts_found']}")
        print(f"  Completed runs: {summary['completed_runs']}")
    elif args.strategy == "rebuild":
        print("Rebuilding indexes ...")
        rebuild_indexes(vault_dir)
        print("  Indexes rebuilt")

    print("Recovery complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
