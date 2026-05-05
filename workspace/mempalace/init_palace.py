#!/usr/bin/env python3
"""Initialize the on-disk MemPalace workspace and validate against taxonomy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TAXONOMY_PATH = REPO_ROOT / "contracts" / "mempalace" / "taxonomy.yaml"
PALACE_ROOT = REPO_ROOT / "workspace" / "mempalace"


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, "r") as fh:
        return yaml.safe_load(fh)


def ensure_directories(taxonomy: dict) -> list[str]:
    created: list[str] = []
    for wing in taxonomy.get("wings", []):
        wing_name = wing["wing"]
        for hall in wing.get("halls", []):
            hall_name = hall["hall"]
            for room in hall.get("rooms", []):
                room_name = room["room"]
                path = PALACE_ROOT / wing_name / hall_name / room_name
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    created.append(str(path.relative_to(REPO_ROOT)))
    return created


def validate_structure(taxonomy: dict) -> list[str]:
    errors: list[str] = []
    expected_rooms: set[str] = set()
    for wing in taxonomy.get("wings", []):
        wing_name = wing["wing"]
        for hall in wing.get("halls", []):
            hall_name = hall["hall"]
            for room in hall.get("rooms", []):
                room_name = room["room"]
                expected_path = PALACE_ROOT / wing_name / hall_name / room_name
                expected_rooms.add(str(expected_path))
                if not expected_path.exists():
                    errors.append(f"Missing room directory: {expected_path.relative_to(REPO_ROOT)}")
    return errors


def write_index(taxonomy: dict) -> None:
    index: dict = {"version": "1.0", "rooms": []}
    for wing in taxonomy.get("wings", []):
        wing_name = wing["wing"]
        for hall in wing.get("halls", []):
            hall_name = hall["hall"]
            for room in hall.get("rooms", []):
                room_name = room["room"]
                index["rooms"].append({
                    "wing": wing_name,
                    "hall": hall_name,
                    "room": room_name,
                    "owner": room.get("owner"),
                    "description": room.get("description", ""),
                    "path": f"workspace/mempalace/{wing_name}/{hall_name}/{room_name}",
                })
    index_path = PALACE_ROOT / "index.json"
    with open(index_path, "w") as fh:
        json.dump(index, fh, indent=2)


def main() -> int:
    if not TAXONOMY_PATH.exists():
        print(f"ERROR: taxonomy not found at {TAXONOMY_PATH}")
        return 1

    taxonomy = load_taxonomy()

    created = ensure_directories(taxonomy)
    if created:
        print(f"Created {len(created)} room directories:")
        for c in created:
            print(f"  + {c}")
    else:
        print("All room directories already exist.")

    errors = validate_structure(taxonomy)
    if errors:
        print(f"\nValidation errors ({len(errors)}):")
        for e in errors:
            print(f"  ! {e}")
        return 1

    write_index(taxonomy)
    print(f"\nWrote index.json with {len(taxonomy.get('wings', []))} wings.")
    print("Palace workspace initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
