#!/usr/bin/env python3
"""Restore the research vault from a backup archive.

Extracts a .tar.gz backup into the vault directory.

Usage:
    python restore.py --backup-file backups/research-vault-20260101-120000.tar.gz \
                      --vault-dir workspace/research-vault
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore research vault from backup")
    parser.add_argument(
        "--backup-file",
        type=Path,
        required=True,
        help="Path to backup archive",
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    return parser.parse_args(argv)


def restore_backup(backup_file: Path, vault_dir: Path) -> None:
    """Extract a tar.gz archive into the vault directory."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    # Remove existing vault contents
    if vault_dir.exists():
        print(f"Removing existing vault at {vault_dir}")
        shutil.rmtree(vault_dir)

    vault_dir.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=vault_dir.parent)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    backup_file = args.backup_file.resolve()
    vault_dir = args.vault_dir.resolve()

    restore_backup(backup_file, vault_dir)
    print(f"Restored from {backup_file} to {vault_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
