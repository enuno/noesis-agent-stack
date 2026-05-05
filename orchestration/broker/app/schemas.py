"""JSON Schema validation wrapper."""

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_BASE = Path(__file__).resolve().parents[3] / "contracts" / "broker-api"

_JOB_SCHEMA_PATH = _BASE / "job.schema.json"
_EVENTS_SCHEMA_PATH = _BASE / "events.schema.json"
_ARTIFACT_SCHEMA_PATH = _BASE / "artifact.schema.json"


def _load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_job_schema = _load_schema(_JOB_SCHEMA_PATH)
_events_schema = _load_schema(_EVENTS_SCHEMA_PATH)
_artifact_schema = _load_schema(_ARTIFACT_SCHEMA_PATH)

_job_validator = Draft202012Validator(_job_schema)
_events_validator = Draft202012Validator(_events_schema)
_artifact_validator = Draft202012Validator(_artifact_schema)


# Request-only schema: remove response-only required fields
_job_request_schema = copy.deepcopy(_job_schema)
_response_only = {
    "job_id", "status", "started_at", "finished_at",
    "exit_code", "health", "artifact_count", "warnings", "summary",
}
_job_request_schema["required"] = [
    f for f in _job_request_schema.get("required", [])
    if f not in _response_only
]
_job_request_validator = Draft202012Validator(_job_request_schema)


def validate_job_payload(payload: dict) -> None:
    """Raise ValidationError if payload does not conform to job.schema.json."""
    _job_validator.validate(payload)


def validate_job_request(payload: dict) -> None:
    """Raise ValidationError if request payload is invalid."""
    _job_request_validator.validate(payload)


def validate_event_payload(payload: dict) -> None:
    _events_validator.validate(payload)


def validate_artifact_payload(payload: dict) -> None:
    _artifact_validator.validate(payload)
