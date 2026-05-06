#!/usr/bin/env python3
"""
validate_handoff.py

Validate a handoff JSON file against its declared schema.

Usage:
    python validate_handoff.py <handoff-file> <schema-file>

Features:
- Uses jsonschema if available; falls back to basic key-presence checks.
- Validates required fields, type checks, and enum values.
- Verifies artifact path existence for fields named 'artifact_path'.
- Returns exit code 0 on success, 1 on validation failure, 2 on usage/error.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Try to import jsonschema; gracefully degrade if absent.
try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    from jsonschema.exceptions import SchemaError

    HAS_JSONSCHEMA = True
except Exception:  # pragma: no cover
    HAS_JSONSCHEMA = False


class HandoffValidationError(Exception):
    """Raised when handoff validation fails."""

    pass


def load_json(path: str) -> Any:
    """Load and return JSON from *path*."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_type(value: Any, expected_type: str) -> bool:
    """Return True if *value* conforms to JSON Schema *expected_type*."""
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "null":
        return value is None
    return True


def _collect_enums(schema: dict, path: str = "") -> dict[str, list]:
    """Recursively collect enum constraints from a JSON schema."""
    enums: dict[str, list] = {}
    if not isinstance(schema, dict):
        return enums

    if "enum" in schema and path:
        enums[path] = schema["enum"]

    if schema.get("type") == "object" and "properties" in schema:
        for prop, subschema in schema["properties"].items():
            child_path = f"{path}.{prop}" if path else prop
            enums.update(_collect_enums(subschema, child_path))

    if schema.get("type") == "array" and "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            enums.update(_collect_enums(items, f"{path}[]"))
        elif isinstance(items, list):
            for idx, item in enumerate(items):
                enums.update(_collect_enums(item, f"{path}[{idx}]"))

    # Handle oneOf / anyOf / allOf / if-then-else lightly
    for key in ("oneOf", "anyOf", "allOf"):
        for sub in schema.get(key, []):
            enums.update(_collect_enums(sub, path))

    if "then" in schema:
        enums.update(_collect_enums(schema["then"], path))
    if "else" in schema:
        enums.update(_collect_enums(schema["else"], path))

    return enums


def _collect_required(schema: dict, path: str = "") -> list[str]:
    """Recursively collect required field paths from a JSON schema."""
    required: list[str] = []
    if not isinstance(schema, dict):
        return required

    for field in schema.get("required", []):
        required.append(f"{path}.{field}" if path else field)

    if schema.get("type") == "object" and "properties" in schema:
        for prop, subschema in schema["properties"].items():
            child_path = f"{path}.{prop}" if path else prop
            required.extend(_collect_required(subschema, child_path))

    if schema.get("type") == "array" and "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            required.extend(_collect_required(items, f"{path}[]"))
        elif isinstance(items, list):
            for idx, item in enumerate(items):
                required.extend(_collect_required(item, f"{path}[{idx}]"))

    for key in ("oneOf", "anyOf", "allOf"):
        for sub in schema.get(key, []):
            required.extend(_collect_required(sub, path))

    return required


def _get_value(data: Any, path: str) -> Any:
    """Navigate into *data* using dot-bracket notation and return the value."""
    parts = []
    current = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if current:
                parts.append(current)
                current = ""
            i += 1
        elif ch == "[":
            if current:
                parts.append(current)
                current = ""
            # collect until ]
            j = path.find("]", i)
            if j == -1:
                current += ch
                i += 1
            else:
                idx_str = path[i + 1 : j]
                parts.append(("idx", idx_str))
                i = j + 1
        else:
            current += ch
            i += 1
    if current:
        parts.append(current)

    node = data
    for part in parts:
        if node is None:
            return None
        if isinstance(part, tuple) and part[0] == "idx":
            idx_str = part[1]
            if idx_str == "":
                # iterate all items
                if isinstance(node, list):
                    return node
                return None
            try:
                idx = int(idx_str)
                if isinstance(node, list) and 0 <= idx < len(node):
                    node = node[idx]
                else:
                    return None
            except ValueError:
                return None
        else:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return None
    return node


def _collect_type_checks(schema: dict, path: str = "") -> dict[str, str]:
    """Recursively collect type constraints from a JSON schema."""
    types: dict[str, str] = {}
    if not isinstance(schema, dict):
        return types

    if "type" in schema and path:
        types[path] = schema["type"]

    if schema.get("type") == "object" and "properties" in schema:
        for prop, subschema in schema["properties"].items():
            child_path = f"{path}.{prop}" if path else prop
            types.update(_collect_type_checks(subschema, child_path))

    if schema.get("type") == "array" and "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            types.update(_collect_type_checks(items, f"{path}[]"))
        elif isinstance(items, list):
            for idx, item in enumerate(items):
                types.update(_collect_type_checks(item, f"{path}[{idx}]"))

    for key in ("oneOf", "anyOf", "allOf"):
        for sub in schema.get(key, []):
            types.update(_collect_type_checks(sub, path))

    return types


def _collect_artifact_paths(data: Any, path: str = "") -> list[tuple[str, str]]:
    """Recursively collect (path, value) for any key named 'artifact_path'."""
    results: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            child_path = f"{path}.{k}" if path else k
            if k == "artifact_path" and isinstance(v, str):
                results.append((child_path, v))
            else:
                results.extend(_collect_artifact_paths(v, child_path))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            results.extend(_collect_artifact_paths(item, f"{path}[{idx}]"))
    return results


def _fallback_validate(handoff: Any, schema: dict, handoff_file: str) -> list[str]:
    """Run basic validation without jsonschema and return a list of errors."""
    errors: list[str] = []

    # 1. Required fields
    required = _collect_required(schema)
    for req_path in required:
        value = _get_value(handoff, req_path)
        if value is None:
            errors.append(f"Missing required field: {req_path}")

    # 2. Type checks
    type_checks = _collect_type_checks(schema)
    for type_path, expected in type_checks.items():
        value = _get_value(handoff, type_path)
        if value is not None and not _check_type(value, expected):
            errors.append(
                f"Type mismatch at {type_path}: expected {expected}, got {type(value).__name__}"
            )

    # 3. Enum checks
    enums = _collect_enums(schema)
    for enum_path, allowed in enums.items():
        value = _get_value(handoff, enum_path)
        if value is not None and value not in allowed:
            errors.append(
                f"Invalid enum value at {enum_path}: {value!r} not in {allowed}"
            )

    # 4. Artifact path existence (relative to repo root or absolute)
    artifact_paths = _collect_artifact_paths(handoff)
    base_dir = Path(handoff_file).resolve().parent
    repo_root = base_dir
    while repo_root != repo_root.parent:
        if (repo_root / "contracts").exists() or (repo_root / "platform").exists():
            break
        repo_root = repo_root.parent

    for field_path, artifact_path in artifact_paths:
        # Try resolving relative to repo root first, then relative to handoff file
        checked = False
        for anchor in (repo_root, base_dir):
            candidate = anchor / artifact_path
            if candidate.exists():
                checked = True
                break
        if not checked:
            errors.append(
                f"Artifact path not found: {artifact_path} (field: {field_path})"
            )

    return errors


def validate_handoff(handoff_path: str, schema_path: str) -> list[str]:
    """
    Validate *handoff_path* against *schema_path*.

    Returns a list of error strings (empty on success).
    """
    handoff = load_json(handoff_path)
    schema = load_json(schema_path)
    errors: list[str] = []

    if HAS_JSONSCHEMA:
        try:
            validate(instance=handoff, schema=schema)
        except JsonSchemaValidationError as exc:
            errors.append(f"Schema validation error: {exc.message} (path: {list(exc.path)})")
        except SchemaError as exc:
            errors.append(f"Invalid schema: {exc.message}")
    else:
        errors.extend(_fallback_validate(handoff, schema, handoff_path))

    # Even when jsonschema is available, perform supplementary checks:
    # - artifact path existence
    # - enum values for status / priority / severity (defense in depth)
    artifact_paths = _collect_artifact_paths(handoff)
    base_dir = Path(handoff_path).resolve().parent
    repo_root = base_dir
    while repo_root != repo_root.parent:
        if (repo_root / "contracts").exists() or (repo_root / "platform").exists():
            break
        repo_root = repo_root.parent

    for field_path, artifact_path in artifact_paths:
        found = False
        for anchor in (repo_root, base_dir):
            candidate = anchor / artifact_path
            if candidate.exists():
                found = True
                break
        if not found:
            errors.append(
                f"Artifact path not found: {artifact_path} (field: {field_path})"
            )

    # Supplementary enum checks (jsonschema may not cover const + enum overlap)
    enums = _collect_enums(schema)
    for enum_path, allowed in enums.items():
        value = _get_value(handoff, enum_path)
        if value is not None and value not in allowed:
            errors.append(
                f"Invalid enum value at {enum_path}: {value!r} not in {allowed}"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 2:
        print(f"Usage: {sys.argv[0]} <handoff-file> <schema-file>", file=sys.stderr)
        return 2

    handoff_path, schema_path = argv[0], argv[1]

    if not os.path.isfile(handoff_path):
        print(f"Error: handoff file not found: {handoff_path}", file=sys.stderr)
        return 2
    if not os.path.isfile(schema_path):
        print(f"Error: schema file not found: {schema_path}", file=sys.stderr)
        return 2

    errors = validate_handoff(handoff_path, schema_path)

    if errors:
        print(f"Validation failed for {handoff_path}")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"Validation passed for {handoff_path} against {schema_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
