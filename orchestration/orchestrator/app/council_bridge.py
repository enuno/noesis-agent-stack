"""Council verdict → review bridge — Phase E Slice A (offline implementation).

The bridge prepares handoff evidence binding a CouncilVerdict to its parent
task and validates the verdict against the repo's council-verdict contract
before review. It is deliberately inert beyond that:

- No ledger writes, no review recording, no acceptance state: the
  orchestrator owns acceptance; a council verdict is advisory evidence only.
- An explicit authority marker travels with every handoff so downstream
  consumers cannot mistake the artifact for authorization.

Validation reuses the repo's own contract-checking approach: the shared
contracts loader in app.contracts if it is importable, otherwise the
jsonschema + referencing recipe used by tests/test_council_contracts.py
against contracts/orchestration/council-verdict.schema.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Optional

from app.council import CouncilError, _revision_projection

ADVISORY_AUTHORITY_MARKER = (
    "advisory_only — council outputs propose actions; only the control "
    "plane and human approval authorize them"
)

_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[3] / "contracts" / "orchestration"
)
_DEFAULT_VERDICT_SCHEMA = _CONTRACTS_DIR / "council-verdict.schema.json"


class HandoffValidationError(CouncilError):
    """A handoff failed structural or contract validation before review."""


def verdict_digest(verdict: Mapping) -> str:
    """sha256 over the canonical JSON of the verdict dict (sorted keys)."""
    canonical = json.dumps(verdict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_handoff(verdict: Mapping, session: Mapping) -> dict:
    """Bind a CouncilVerdict to its parent task as review-ready evidence."""
    if not isinstance(verdict, Mapping) or not verdict.get("session_id"):
        raise HandoffValidationError("handoff requires a council verdict dict")
    if verdict.get("parent_task_id") != session.get("parent_task_id"):
        raise CouncilError(
            "verdict parent_task_id "
            f"{verdict.get('parent_task_id')!r} does not match session "
            f"parent_task_id {session.get('parent_task_id')!r}; refusing to "
            "bind a verdict to a different parent task"
        )
    session_metadata = verdict.get("session_metadata", {})
    return {
        "parent_task_id": session["parent_task_id"],
        "council_revision": _revision_projection(session),
        "session_id": verdict["session_id"],
        "mode": verdict.get("mode"),
        "stop_condition": session_metadata.get("stop_condition"),
        "verdict": dict(verdict),
        "digest": verdict_digest(verdict),
        "dissent": verdict.get("dissent", {}),
        "authority": ADVISORY_AUTHORITY_MARKER,
    }


def _validate_with_contracts_module(verdict: Mapping, schema_path: Path) -> Optional[list[str]]:
    """Repo-owned validation via app.contracts, if that module is importable.

    Returns the error list, an empty list on success, or None when the
    module/ API is not importable so the caller falls back to jsonschema.
    """
    try:
        from app import contracts  # type: ignore
    except ImportError:
        return None
    load = getattr(contracts, "load", None) or getattr(contracts, "load_schema", None)
    validate = getattr(contracts, "validate", None)
    if not callable(load) or not callable(validate):
        return None
    schema = load(schema_path)
    result = validate(schema, verdict)
    if isinstance(result, (list, tuple)):
        return [str(e) for e in result]
    return [] if result else ["contract validation failed"]


def _validate_with_jsonschema(verdict: Mapping, schema_path: Path) -> list[str]:
    """jsonschema + referencing recipe consistent with test_council_contracts.py."""
    import jsonschema
    from referencing import Registry, Resource

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(verdict), key=lambda e: list(e.path))
    return [
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    ]


def validate_for_review(handoff: Mapping, verdict_schema_path: Optional[Path] = None) -> Mapping:
    """Validate a handoff's verdict against the council-verdict contract.

    Checks, in order: structural handoff shape, digest integrity (tamper
    evidence), then schema validation. Returns the handoff payload on success;
    raises HandoffValidationError with the failures otherwise.
    """
    verdict = handoff.get("verdict") if isinstance(handoff, Mapping) else None
    if not isinstance(verdict, Mapping):
        raise HandoffValidationError("handoff carries no verdict dict to validate")
    digest = handoff.get("digest")
    if not digest:
        raise HandoffValidationError("handoff carries no digest")
    recomputed = verdict_digest(verdict)
    if digest != recomputed:
        raise HandoffValidationError(
            f"handoff digest {digest} does not match the verdict's canonical "
            f"digest {recomputed}; the verdict was tampered with or re-bound"
        )
    schema_path = Path(verdict_schema_path) if verdict_schema_path else _DEFAULT_VERDICT_SCHEMA
    if not schema_path.is_file():
        raise HandoffValidationError(f"verdict schema not found at {schema_path}")

    errors = _validate_with_contracts_module(verdict, schema_path)
    if errors is None:
        errors = _validate_with_jsonschema(verdict, schema_path)
    if errors:
        raise HandoffValidationError(
            "verdict failed council-verdict contract validation: " + "; ".join(errors)
        )
    return handoff
