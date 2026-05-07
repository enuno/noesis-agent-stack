#!/usr/bin/env python3
"""Bootstrap the research vault.

Creates the vault directory structure, initializes empty ledger files,
validates that all referenced schemas exist, and writes an initial
health report.

Usage:
    python bootstrap.py --vault-dir workspace/research-vault \
                        --config-dir agents/research-openclaw/config
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.schemas import SchemaManager
from lib.ledger import Ledger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the research vault")
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to the vault directory",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("agents/research-openclaw/config"),
        help="Path to the config directory",
    )
    return parser.parse_args(argv)


def create_directories(vault_dir: Path) -> None:
    """Create the vault directory structure."""
    dirs = [
        vault_dir / "knowledge",
        vault_dir / "output" / "dossiers",
        vault_dir / "output" / "operator-briefs",
        vault_dir / "output" / "handoff-candidates",
        vault_dir / "state" / "health",
        vault_dir / "state" / "runs",
        vault_dir / "state" / "queue",
        vault_dir / "state" / "config",
        vault_dir / "signals",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def init_ledgers(vault_dir: Path, schemas: SchemaManager) -> None:
    """Initialize empty ledger files with schema validation ready."""
    ledgers = {
        "sources": vault_dir / "knowledge" / "sources.jsonl",
        "claims": vault_dir / "knowledge" / "claims.jsonl",
        "findings": vault_dir / "knowledge" / "findings.jsonl",
        "receipts": vault_dir / "state" / "runs" / "receipts.jsonl",
    }
    for name, path in ledgers.items():
        ledger = Ledger(path)
        ledger.ensure_exists()
        # Verify schema exists
        schemas.load(name)


def write_initial_health_report(vault_dir: Path) -> None:
    """Write the first health report."""
    report = {
        "report_id": "bootstrap",
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "overall_status": "healthy",
        "vault_version": "1.0.0",
        "ledgers": {
            "sources": {"record_count": 0, "last_write": None, "schema_valid": True},
            "claims": {"record_count": 0, "last_write": None, "schema_valid": True},
            "findings": {"record_count": 0, "last_write": None, "schema_valid": True},
            "receipts": {"record_count": 0, "last_write": None, "schema_valid": True},
        },
        "collector_health": [],
        "issues": [],
    }
    health_dir = vault_dir / "state" / "health"
    health_dir.mkdir(parents=True, exist_ok=True)
    path = health_dir / "health-bootstrap.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    config_dir = args.config_dir.resolve()

    print(f"Bootstrapping vault at {vault_dir}")

    schemas = SchemaManager()
    create_directories(vault_dir)
    init_ledgers(vault_dir, schemas)
    write_initial_health_report(vault_dir)

    print("Bootstrap complete.")
    print(f"  Vault: {vault_dir}")
    print(f"  Ledgers: sources, claims, findings, receipts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
