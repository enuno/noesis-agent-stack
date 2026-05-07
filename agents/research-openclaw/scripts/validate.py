#!/usr/bin/env python3
"""Validate ledger integrity and schema compliance.

Checks that all JSONL files contain valid JSON, that records comply
with their schemas, and that cross-references (e.g., claim.source_id
-> sources.jsonl) are consistent.

Usage:
    python validate.py --vault-dir workspace/research-vault
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.schemas import SchemaManager


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate research vault ledgers")
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    return parser.parse_args(argv)


def validate_jsonl(path: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    """Validate a JSONL file.

    Returns (valid_records, [(line_number, error_message), ...]).
    """
    records: list[dict] = []
    errors: list[tuple[int, str]] = []
    if not path.exists():
        return records, errors
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    errors.append((i, "Record is not a JSON object"))
                else:
                    records.append(obj)
            except json.JSONDecodeError as exc:
                errors.append((i, f"Invalid JSON: {exc}"))
    return records, errors


def validate_schema(
    records: list[dict], schema_name: str, schemas: SchemaManager
) -> list[tuple[int, list[str]]]:
    """Validate records against their schema.

    Returns [(index, [errors]), ...].
    """
    invalid: list[tuple[int, list[str]]] = []
    for i, record in enumerate(records):
        errs = schemas.validate(record, schema_name)
        if errs:
            invalid.append((i, errs))
    return invalid


def validate_cross_references(
    sources: list[dict], claims: list[dict], findings: list[dict]
) -> list[str]:
    """Check cross-reference consistency.

    Returns a list of error messages.
    """
    errors: list[str] = []
    source_ids = {s.get("source_id") for s in sources}

    for i, claim in enumerate(claims):
        sid = claim.get("source_id")
        if sid and sid not in source_ids:
            errors.append(f"Claim[{i}] source_id {sid!r} not found in sources")
        pfid = claim.get("promoted_to_finding_id")
        if pfid:
            finding_ids = {f.get("finding_id") for f in findings}
            if pfid not in finding_ids:
                errors.append(f"Claim[{i}] promoted_to_finding_id {pfid!r} not found in findings")

    for i, finding in enumerate(findings):
        for j, ev in enumerate(finding.get("evidence", [])):
            ev_sid = ev.get("source_id")
            if ev_sid and ev_sid not in source_ids:
                errors.append(
                    f"Finding[{i}] evidence[{j}] source_id {ev_sid!r} not found in sources"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    schemas = SchemaManager()

    ledgers = {
        "sources": vault_dir / "knowledge" / "sources.jsonl",
        "claims": vault_dir / "knowledge" / "claims.jsonl",
        "findings": vault_dir / "knowledge" / "findings.jsonl",
        "receipts": vault_dir / "state" / "runs" / "receipts.jsonl",
    }

    total_errors = 0
    all_records: dict[str, list[dict]] = {}

    for name, path in ledgers.items():
        print(f"Validating {name} ...")
        records, json_errors = validate_jsonl(path)
        all_records[name] = records

        if json_errors:
            print(f"  JSON errors: {len(json_errors)}")
            for line_no, msg in json_errors[:5]:
                print(f"    Line {line_no}: {msg}")
            total_errors += len(json_errors)

        schema_errors = validate_schema(records, name, schemas)
        if schema_errors:
            print(f"  Schema errors: {len(schema_errors)}")
            for idx, errs in schema_errors[:5]:
                print(f"    Record {idx}: {'; '.join(errs)}")
            total_errors += len(schema_errors)

        if not json_errors and not schema_errors:
            print(f"  OK ({len(records)} records)")

    # Cross-reference validation
    print("Validating cross-references ...")
    xref_errors = validate_cross_references(
        all_records.get("sources", []),
        all_records.get("claims", []),
        all_records.get("findings", []),
    )
    if xref_errors:
        print(f"  Cross-reference errors: {len(xref_errors)}")
        for msg in xref_errors[:10]:
            print(f"    {msg}")
        total_errors += len(xref_errors)
    else:
        print("  OK")

    if total_errors:
        print(f"\nValidation FAILED: {total_errors} error(s)")
        return 1
    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
