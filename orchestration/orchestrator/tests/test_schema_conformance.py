"""Every persisted task contract must validate against its published schema.

Guards contracts/orchestration/task-contract.schema.json against drift from
app/models.py, and asserts no secret-like material reaches the ledger.
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.control_plane import Orchestrator
from app.models import Verification
from tests.conftest import drive_to_running, make_task

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "orchestration"
    / "task-contract.schema.json"
)

# Patterns that must never appear in a persisted task artifact.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class TestSchemaConformance:
    def test_schema_file_is_valid(self, validator):
        assert validator is not None

    def test_proposed_task_validates(self, orch, validator):
        task = make_task(orch)
        errors = list(validator.iter_errors(task.to_dict()))
        assert errors == [], [e.message for e in errors]

    def test_completed_task_validates(self, orch, validator, passing_handoff):
        task = make_task(orch)
        drive_to_running(orch, task)
        orch.submit_handoff(task.task_id, passing_handoff)
        done = orch.succeed(task.task_id)
        errors = list(validator.iter_errors(done.to_dict()))
        assert errors == [], [e.message for e in errors]

    def test_r3_task_validates(self, orch, validator):
        task = make_task(
            orch,
            assignee_profile="noesis-substrate",
            required_capability="terraform",
            risk_tier="r3",
            irreversible_operations=["production_mutation"],
            idempotency_key="noesis-substrate:terraform:prod:2026-09-18",
        )
        errors = list(validator.iter_errors(task.to_dict()))
        assert errors == [], [e.message for e in errors]

    def test_every_ledger_record_validates(self, ledger, validator, passing_handoff):
        orch = Orchestrator(ledger)
        task = make_task(orch)
        drive_to_running(orch, task)
        orch.submit_handoff(task.task_id, passing_handoff)
        orch.succeed(task.task_id)

        records = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
        assert len(records) >= 4
        for record in records:
            errors = list(validator.iter_errors(record["task"]))
            assert errors == [], (record["event"], [e.message for e in errors])

    def test_schema_states_match_the_state_machine(self, validator):
        from app.models import ALLOWED_TRANSITIONS

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema_states = set(schema["properties"]["state"]["enum"])
        assert schema_states == set(ALLOWED_TRANSITIONS.keys())


class TestNoSecretsInArtifacts:
    def test_ledger_contains_no_secret_material(self, ledger, passing_handoff):
        orch = Orchestrator(ledger)
        task = make_task(orch)
        drive_to_running(orch, task)
        orch.submit_handoff(task.task_id, passing_handoff)
        orch.succeed(task.task_id)

        content = ledger.read_text()
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(content), f"secret-like match: {pattern.pattern}"

    def test_repo_orchestrator_sources_contain_no_secret_material(self):
        root = Path(__file__).resolve().parents[1]
        for path in list(root.rglob("*.py")) + list(root.rglob("*.md")):
            if "__pycache__" in str(path):
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in SECRET_PATTERNS:
                assert not pattern.search(text), f"{path}: {pattern.pattern}"
