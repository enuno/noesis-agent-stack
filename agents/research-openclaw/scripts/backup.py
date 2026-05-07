#!/usr/bin/env python3
"""Backup the research vault to a compressed archive.

Creates a timestamped .tar.gz of the entire vault directory.

Usage:
    python backup.py --vault-dir workspace/research-vault \
                     --backup-dir backups/
"""

from __future__ import annotations

import argparse
import datetime
import sys
import tarfile
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup research vault")
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Path to store backup archives",
    )
    return parser.parse_args(argv)


def create_backup(vault_dir: Path, backup_path: Path) -> None:
    """Create a tar.gz archive of the vault."""
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(vault_dir, arcname=vault_dir.name)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    backup_dir = args.backup_dir.resolve()

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_name = f"{vault_dir.name}-{timestamp}.tar.gz"
    backup_path = backup_dir / backup_name

    create_backup(vault_dir, backup_path)

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"Backup created: {backup_path}")
    print(f"  Size: {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
