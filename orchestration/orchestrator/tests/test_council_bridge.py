"""Phase E Slice A tests — council verdict → review bridge (offline).

council_bridge prepares a handoff-evidence payload binding a CouncilVerdict
to its parent task (digest over the canonical verdict JSON, advisory-only
authority marker, dissent preserved verbatim) and validates the verdict
against the repo's council-verdict contract before review. No ledger writes,
no review recording — the orchestrator owns acceptance.

Deterministic and offline: fixtures only, no network, no runtime.
"""

import hashlib
import json
from pathlib import Path

import pytest

from app.council import CouncilError, SeatUsage, run_duo_session
from app.council_bridge import (
    ADVISORY_AUTHORITY_MARKER,
    HandoffValidationError,
    build_handoff,
    validate_for_review,
)

FIXTURES = Path(__file__).parent / "fixtures" / "council"
CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "orchestration"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _canonical_digest(verdict: dict) -> str:
    canonical = json.dumps(verdict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@pytest.fixture
def session():
    return _load("duo_session.json")


@pytest.fixture
def split_verdict():
    return _load("duo_verdict_split.json")


class TestBuildHandoff:
    def test_handoff_binds_parent_revision_session_and_digest(self, session, split_verdict):
        handoff = build_handoff(split_verdict, session)
        assert handoff["parent_task_id"] == session["parent_task_id"]
        assert handoff["session_id"] == session["session_id"]
        assert handoff["council_revision"]["upstream_rev"] == \
            session["council_revision"]["upstream_rev"]
        assert handoff["council_revision"]["protocol_mode_version"] == \
            session["council_revision"]["protocol_mode_version"]
        assert handoff["mode"] == "duo"
        assert handoff["stop_condition"] is None
        assert handoff["verdict"] == split_verdict
        assert handoff["digest"] == _canonical_digest(split_verdict)

    def test_dissent_preserved_verbatim_and_advisory_marker_present(self, session, split_verdict):
        handoff = build_handoff(split_verdict, session)
        assert handoff["dissent"] == split_verdict["dissent"]
        assert handoff["dissent"]["minority_report"]
        assert handoff["authority"] == ADVISORY_AUTHORITY_MARKER
        assert "advisory_only" in handoff["authority"]

    def test_digest_is_canonical_not_key_order_dependent(self, session, split_verdict):
        # Rebuild the verdict with reversed top-level key order; the digest
        # must match the canonical sorted-keys computation.
        reordered = dict(reversed(list(split_verdict.items())))
        handoff = build_handoff(reordered, session)
        assert handoff["digest"] == _canonical_digest(split_verdict)

    def test_parent_task_mismatch_refused(self, session, split_verdict):
        session = dict(session)
        session["parent_task_id"] = "task-someone-else"
        with pytest.raises(CouncilError, match="parent_task_id"):
            build_handoff(split_verdict, session)


class TestBuildHandoffIdentityRefusal:
    """F-1: a verdict may only bind to the session that produced it.

    Provenance comes from two sources today: the session (parent_task_id,
    council_revision projection) and the verdict (session_id, content). A
    cross-session bind was silently accepted as long as parent_task_id
    matched, producing a handoff with internally contradictory provenance.
    """

    def test_session_id_mismatch_refused_naming_both_values(self, session, split_verdict):
        other = dict(session)
        other["session_id"] = "council-demo-duo-9999"
        with pytest.raises(CouncilError) as exc:
            build_handoff(split_verdict, other)
        message = str(exc.value)
        assert split_verdict["session_id"] in message
        assert other["session_id"] in message

    def test_council_revision_mismatch_refused_naming_both_values(self, session, split_verdict):
        verdict = json.loads(json.dumps(split_verdict))
        verdict["council_revision"]["protocol_mode_version"] = "duo@2"
        with pytest.raises(CouncilError) as exc:
            build_handoff(verdict, session)
        message = str(exc.value)
        assert "duo@2" in message
        assert session["council_revision"]["protocol_mode_version"] in message

    def test_refusal_happens_before_handoff_construction(self, session, split_verdict):
        # Both new identity checks fire before any handoff dict exists; the
        # exception is the only outcome (no partial artifact is returned).
        other = dict(session)
        other["session_id"] = "council-demo-duo-9999"
        with pytest.raises(CouncilError):
            build_handoff(split_verdict, other)

    def test_engine_produced_verdict_bound_with_own_session_accepted(self, session):
        class _ScriptedRunner:
            def run_round(self, seat_id, payload, budget):
                option = "ship duo first"
                text = json.dumps({
                    "option": option,
                    "stance": f"{seat_id} argues for {option}",
                    "confidence": "high",
                    "confidence_basis": "scripted fixture",
                    "known_limitations": ["scripted"],
                    "evidence_labels": {"UNKNOWN": []},
                })
                return text, SeatUsage(input_tokens=100, output_tokens=200)

        verdict = run_duo_session(session, _ScriptedRunner(), {"KIMI_CODE"})
        handoff = build_handoff(verdict, session)
        # Field order/values identical to pre-fix construction for a genuine
        # engine verdict bound with its own session.
        assert list(handoff.keys()) == [
            "parent_task_id", "council_revision", "session_id", "mode",
            "stop_condition", "verdict", "digest", "dissent", "authority",
        ]
        assert handoff["session_id"] == session["session_id"]
        assert handoff["council_revision"] == verdict["council_revision"]
        assert handoff["digest"] == _canonical_digest(verdict)
        assert handoff["authority"] == ADVISORY_AUTHORITY_MARKER
        assert handoff["mode"] == "duo"
        assert handoff["stop_condition"] is None
        assert validate_for_review(handoff) is handoff


class TestValidateForReview:
    def test_accepts_split_verdict_fixture(self, session, split_verdict):
        handoff = build_handoff(split_verdict, session)
        validated = validate_for_review(handoff)
        assert validated is handoff

    def test_accepts_explicit_schema_path(self, session, split_verdict):
        handoff = build_handoff(split_verdict, session)
        validated = validate_for_review(
            handoff, verdict_schema_path=CONTRACTS / "council-verdict.schema.json")
        assert validated is handoff

    def test_rejects_tampered_verdict_via_digest_mismatch(self, session, split_verdict):
        handoff = build_handoff(split_verdict, session)
        handoff["verdict"]["consensus"]["reached"] = True  # tamper, digest not updated
        with pytest.raises(HandoffValidationError, match="digest"):
            validate_for_review(handoff)

    def test_rejects_schema_invalid_verdict_with_fresh_digest(self, session, split_verdict):
        # A completed-shape violation (empty positions on a verdict whose
        # stop_condition is null) with an honestly recomputed digest must
        # still fail schema validation.
        bad = json.loads(json.dumps(split_verdict))
        bad["positions"] = []
        handoff = build_handoff(bad, session)
        assert handoff["digest"] == _canonical_digest(bad)
        with pytest.raises(HandoffValidationError) as exc:
            validate_for_review(handoff)
        assert "positions" in str(exc.value)

    def test_rejects_malformed_handoff_missing_verdict(self, session):
        with pytest.raises(HandoffValidationError, match="verdict"):
            validate_for_review({"parent_task_id": session["parent_task_id"]})
