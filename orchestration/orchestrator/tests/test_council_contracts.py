"""Council contract schema tests (Phase B — offline, no runtime).

Validates the proposed council-session and council-verdict contracts against
their fixtures, enforces the blind-first / anonymized-release structures
structurally (not by prompt), and rejects negative fixtures that violate
authority boundaries (peer leak, acceptance disposition).

Everything here is deterministic and offline: no provider calls, no
orchestrator runtime, no network.
"""

import json
import re
from pathlib import Path

import jsonschema
from referencing import Registry, Resource

FIXTURES = Path(__file__).parent / "fixtures" / "council"
CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "orchestration"

FORBIDDEN_ENVELOPE_HINTS = ("peers", "peer_positions", "other_seats", "positions")
PROFILE_NAMES_IN_SESSION = ("noesis-skeptic", "noesis-architect", "noesis-quill")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _load_schema(name: str):
    schema = _load_json(CONTRACTS / name)
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return jsonschema.Draft202012Validator(schema, registry=registry), schema


SESSION_VALIDATOR, SESSION_SCHEMA = _load_schema("council-session.schema.json")
VERDICT_VALIDATOR, VERDICT_SCHEMA = _load_schema("council-verdict.schema.json")


def _validate(validator, doc, label):
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    assert not errors, f"{label} failed validation: " + "; ".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors)


class TestPositiveFixtures:
    def test_duo_session_validates(self):
        _validate(SESSION_VALIDATOR, _load_json(FIXTURES / "duo_session.json"), "duo_session")

    def test_duo_split_verdict_validates(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        _validate(VERDICT_VALIDATOR, doc, "duo_verdict_split")
        # A split verdict must be representable: no consensus, dissent present.
        assert doc["consensus"]["reached"] is False
        assert doc["dissent"]["minority_report"]
        assert doc["tally"]["no_option_carried"] is True

    def test_round1_envelopes_validate_against_sealed_envelope_def(self):
        session = _load_json(FIXTURES / "duo_session.json")
        sealed = {"registry": Registry()}

        def _sealed_validator():
            registry = Registry().with_resource(
                SESSION_SCHEMA["$id"], Resource.from_contents(SESSION_SCHEMA)
            )
            return jsonschema.Draft202012Validator(
                {"$ref": f"{SESSION_SCHEMA['$id']}#/$defs/sealed_envelope"}, registry=registry
            )

        envelopes = _load_json(FIXTURES / "round1_sealed_envelopes.json")["envelopes"]
        assert len(envelopes) == len(session["seats"])
        for entry in envelopes:
            _validate(_sealed_validator(), entry["envelope"], f"envelope[{entry['seat_id']}]")

    def test_round2_release_validates_and_is_anonymized(self):
        registry = Registry().with_resource(
            SESSION_SCHEMA["$id"], Resource.from_contents(SESSION_SCHEMA)
        )
        validator = jsonschema.Draft202012Validator(
            {"$ref": f"{SESSION_SCHEMA['$id']}#/$defs/anonymized_release"}, registry=registry
        )
        release_doc = _load_json(FIXTURES / "round2_anonymized_release.json")
        release = release_doc["release"]
        _validate(validator, release, "round2_release")
        for key in release:
            assert re.fullmatch(r"s[0-9]+", key), f"release key '{key}' is not a seat_id"
        blob = json.dumps(release)
        for name in PROFILE_NAMES_IN_SESSION:
            assert name not in blob, f"profile name '{name}' leaked into anonymized release"


class TestSeatIdentifierConsistency:
    """Codex review (PR #27): seat_id shape must be identical across session
    seats, verdict positions, and the Round-2 release keys, so a schema-valid
    session always produces a schema-valid release keyed by its actual seats."""

    def _release_validator(self):
        registry = Registry().with_resource(
            SESSION_SCHEMA["$id"], Resource.from_contents(SESSION_SCHEMA)
        )
        return jsonschema.Draft202012Validator(
            {"$ref": f"{SESSION_SCHEMA['$id']}#/$defs/anonymized_release"}, registry=registry
        )

    def test_noncanonical_seat_id_rejected_by_both_contracts(self):
        session = _load_json(FIXTURES / "duo_session.json")
        session["seats"][0]["seat_id"] = "seat-a"
        errors = list(SESSION_VALIDATOR.iter_errors(session))
        assert any(
            "seats" in str(e.absolute_path) and "seat_id" in str(e.absolute_path)
            for e in errors
        ), f"expected seat_id pattern error, got: {[e.message for e in errors]}"

        verdict = _load_json(FIXTURES / "duo_verdict_split.json")
        verdict["positions"][0]["seat_id"] = "seat-a"
        errors = list(VERDICT_VALIDATOR.iter_errors(verdict))
        assert any(
            "seat_id" in str(e.absolute_path) for e in errors
        ), f"expected seat_id pattern error, got: {[e.message for e in errors]}"

    def test_release_built_from_valid_session_seat_ids_validates(self):
        session = _load_json(FIXTURES / "duo_session.json")
        release = {seat["seat_id"]: "synthetic stance for cross-check" for seat in session["seats"]}
        _validate(self._release_validator(), release, "release_from_valid_session_seats")
        bad = dict(release)
        bad["seat-a"] = "stance keyed by a noncanonical id"
        errors = list(self._release_validator().iter_errors(bad))
        assert errors, "release with a noncanonical key must fail the anonymized_release def"


class TestBlindFirstStructure:
    """Blind Round 1 is enforced by construction: no seat ever sees another
    seat's identity or position. Checked structurally, not by prompt."""

    def test_envelopes_contain_no_peer_identity(self):
        envelopes = _load_json(FIXTURES / "round1_sealed_envelopes.json")["envelopes"]
        seat_ids = {e["seat_id"] for e in envelopes}
        for entry in envelopes:
            own = entry["seat_id"]
            blob = json.dumps(entry["envelope"])
            for hint in FORBIDDEN_ENVELOPE_HINTS:
                assert f'"{hint}"' not in blob, f"{own} envelope carries forbidden key '{hint}'"
            for other in seat_ids - {own}:
                assert other not in blob, f"{own} envelope leaks peer seat_id '{other}'"
            for name in PROFILE_NAMES_IN_SESSION:
                assert name not in blob, f"{own} envelope leaks profile name '{name}'"

    def test_round1_text_does_not_appear_in_other_envelopes(self):
        envelopes = _load_json(FIXTURES / "round1_sealed_envelopes.json")["envelopes"]
        # Round-1 envelopes are inputs, not positions; assert no envelope
        # carries stance-like content at all (positions only exist post-round).
        for entry in envelopes:
            blob = json.dumps(entry["envelope"]).lower()
            for stance_word in ("i believe", "my position", "i argue", "stance:"):
                assert stance_word not in blob, f"{entry['seat_id']} envelope contains position text"


class TestNegativeFixtures:
    def test_peer_leak_envelope_rejected(self):
        doc = _load_json(FIXTURES / "invalid_envelope_peer_leak.json")
        registry = Registry().with_resource(
            SESSION_SCHEMA["$id"], Resource.from_contents(SESSION_SCHEMA)
        )
        validator = jsonschema.Draft202012Validator(
            {"$ref": f"{SESSION_SCHEMA['$id']}#/$defs/sealed_envelope"}, registry=registry
        )
        assert list(validator.iter_errors(doc["envelope"])), "peer-leak envelope must be rejected"

    def test_verdict_with_acceptance_rejected(self):
        doc = _load_json(FIXTURES / "invalid_verdict_acceptance.json")
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "verdict carrying acceptance_disposition must be rejected"

    def test_verdict_schema_has_no_authority_fields(self):
        """Guard: the verdict artifact must not contain approval/acceptance/
        lifecycle/spend fields. A council verdict is never authorization."""
        banned = re.compile(
            r"\b(acceptance|accepted|approv\w+|authoriz\w+|lifecycle|spend\w*|release_decision)\b", re.I
        )
        props = VERDICT_SCHEMA["properties"]
        hits = [k for k in props if banned.search(k)]
        assert not hits, f"verdict schema carries authority fields: {hits}"
        assert "risk_tier" not in props


class TestNegativeMechanismPinned:
    """F-3: pin the intended negative-validation mechanism. The peer-leak
    fixture must fail because of the `not` clause (not incidentally), a
    control case must fail additionalProperties for a distinguishable
    reason, and removing the `not` clause must make the leak validate —
    proof the clause is what carries the protection."""

    def _envelope_validator(self, schema=None):
        schema = schema or SESSION_SCHEMA
        registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
        return jsonschema.Draft202012Validator(
            {"$ref": f"{schema['$id']}#/$defs/sealed_envelope"}, registry=registry
        )

    def test_peer_leak_fails_on_not_clause(self):
        doc = _load_json(FIXTURES / "invalid_envelope_peer_leak.json")
        errors = list(self._envelope_validator().iter_errors(doc["envelope"]))
        assert errors, "peer-leak envelope must be rejected"
        assert any(e.validator == "not" for e in errors), (
            f"expected a 'not' failure, got validators {[e.validator for e in errors]}"
        )

    def test_additional_properties_control_case(self):
        envelope = {
            "question": "Should we proceed?",
            "alternatives": ["yes", "no"],
            "constraints": [],
            "mystery_key": "not a peer structure, just unknown",
        }
        errors = list(self._envelope_validator().iter_errors(envelope))
        assert any(e.validator == "additionalProperties" for e in errors), (
            f"expected an additionalProperties failure, got {[e.validator for e in errors]}"
        )
        assert not any(e.validator == "not" for e in errors), (
            "control case must not trip the not clause"
        )

    def test_removing_not_clause_accepts_leak(self):
        import copy

        schema = copy.deepcopy(SESSION_SCHEMA)
        del schema["$defs"]["sealed_envelope"]["not"]
        doc = _load_json(FIXTURES / "invalid_envelope_peer_leak.json")
        errors = list(self._envelope_validator(schema).iter_errors(doc["envelope"]))
        assert not errors, (
            "without the not clause the peer-leak envelope validates — "
            "the clause is load-bearing and the regression test would fail"
        )


class TestPartialResultShape:
    """F-1: explicit schema-valid partial-result shape. Completed-verdict
    constraints are preserved unchanged (allOf conditional keyed on
    session_metadata.stop_condition == null); partial results may carry
    empty positions/tally/kill_criteria instead of fabricating entries."""

    def _partial(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["session_metadata"]["stop_condition"] = "quorum_shortfall"
        doc["positions"] = []
        doc["tally"] = {
            "method": "confidence_weighted_2of3",
            "threshold": None,
            "options": [],
            "no_option_carried": True,
        }
        doc["kill_criteria"] = []
        return doc

    def test_partial_result_validates(self):
        _validate(VERDICT_VALIDATOR, self._partial(), "partial_result")

    def test_completed_verdict_still_requires_positions(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")  # stop_condition: null
        doc["positions"] = []
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "completed verdict with empty positions must fail"

    def test_completed_verdict_still_requires_tally_rows_and_kill_criteria(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["tally"]["options"] = []
        doc["kill_criteria"] = []
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "completed verdict with empty tally options or kill_criteria must fail"

    def test_completed_verdict_requires_numeric_threshold(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["tally"]["threshold"] = None
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "completed verdict with null threshold must fail"


class TestModeAndBudgetSemantics:
    def test_modes_are_distinct_from_risk_tiers(self):
        modes = set(SESSION_SCHEMA["properties"]["mode"]["enum"])
        assert modes.isdisjoint({"r0", "r1", "r2", "r3"}), "council modes must not be risk tiers"

    def test_round_budget_matches_mode(self):
        session = _load_json(FIXTURES / "duo_session.json")
        verdict = _load_json(FIXTURES / "duo_verdict_split.json")
        assert verdict["session_metadata"]["rounds_run"] <= session["limits"]["rounds"]

    def test_every_session_seat_has_a_position(self):
        session = _load_json(FIXTURES / "duo_session.json")
        verdict = _load_json(FIXTURES / "duo_verdict_split.json")
        session_seats = {s["seat_id"] for s in session["seats"]}
        verdict_seats = {p["seat_id"] for p in verdict["positions"]}
        assert session_seats == verdict_seats

    def test_cost_ceiling_never_presents_estimates_as_observations(self):
        session = _load_json(FIXTURES / "duo_session.json")
        ceiling = session["limits"]["cost_ceiling"]
        assert ceiling["unit"] == "tokens"
        assert ceiling["currency_value"] is None
        verdict = _load_json(FIXTURES / "duo_verdict_split.json")
        usage = verdict["usage"]
        assert "observed" in usage and "estimated" in usage and "unknown_fields" in usage
        assert "observed input_tokens" in usage["unknown_fields"]

    def test_session_has_no_execution_surface(self):
        """Guard against scope creep: session schema must not carry provider
        auto-detection, native-host fallback, or tool-grant vocabulary."""
        src = json.dumps(SESSION_SCHEMA).lower()
        for banned in ("detect-providers", "auto_route", "auto-route", "native_host",
                       "fallback_provider", "grants"):
            assert banned not in src, f"session schema carries '{banned}'"


class TestF4OriginalSubject:
    """Repair-2 regression: the ORIGINAL F-4 subject — the positive fixture's
    concrete_next_step verb must not express an authorization action, and the
    schema tripwire must reject authority-shaped verbs. The tripwire is a
    naming guard, NOT semantic authority isolation."""

    def test_positive_fixture_uses_advisory_verb(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        _validate(VERDICT_VALIDATOR, doc, "duo_verdict_split")
        verb = doc["concrete_next_step"]["verb"]
        assert verb == "review", (
            f"positive fixture must model an advisory action; found {verb!r}"
        )
        assert verb.lower() not in {"authorize", "authorise", "approve", "accept",
                                    "merge", "deploy", "release", "spend"}

    @staticmethod
    def _verdict_with_verb(verb: str) -> dict:
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["concrete_next_step"]["verb"] = verb
        return doc

    @staticmethod
    def _verb_errors(verb: str):
        return [
            e for e in VERDICT_VALIDATOR.iter_errors(TestF4OriginalSubject._verdict_with_verb(verb))
            if "concrete_next_step" in "/".join(str(p) for p in e.absolute_path)
        ]

    def test_authority_verbs_rejected_by_tripwire(self):
        for banned in ("authorize", "Authorize", "AUTHORIZE", "approve", "accepted",
                       "merge", "Deploy", "release", "spent"):
            errors = self._verb_errors(banned)
            assert errors, f"verb {banned!r} was accepted; tripwire failed"

    def test_advisory_verbs_still_accepted(self):
        for advisory in ("review", "file", "draft", "run", "halt"):
            errors = self._verb_errors(advisory)
            assert not errors, (
                f"advisory verb {advisory!r} rejected: "
                + "; ".join(e.message for e in errors)
            )


class TestStopConditionCompatibility:
    """Repair-2 option A: preserve council-verdict v1 compatibility. A
    completed artifact with stop_condition ABSENT (the pre-repair v1 shape)
    remains valid; only partial results must carry a non-null stop_condition.
    Completed minimums are unchanged in every branch."""

    @staticmethod
    def _completed_v1_without_stop_condition() -> dict:
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        del doc["session_metadata"]["stop_condition"]
        return doc

    @staticmethod
    def _partial_without_stop_condition() -> dict:
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["session_metadata"]["stop_condition"] = None
        doc["positions"] = []
        doc["tally"] = {"method": doc["tally"]["method"], "threshold": None,
                        "options": [], "no_option_carried": True}
        del doc["session_metadata"]["stop_condition"]
        return doc

    def test_completed_v1_artifact_without_stop_condition_validates(self):
        _validate(VERDICT_VALIDATOR, self._completed_v1_without_stop_condition(),
                  "completed v1 without stop_condition")

    def test_completed_with_explicit_null_still_validates(self):
        _validate(VERDICT_VALIDATOR, _load_json(FIXTURES / "duo_verdict_split.json"),
                  "completed with stop_condition null")

    def test_partial_without_stop_condition_rejected(self):
        errors = list(VERDICT_VALIDATOR.iter_errors(self._partial_without_stop_condition()))
        assert errors, "partial result without stop_condition must not validate"
        # completed minimums re-apply when stop_condition is absent: the
        # empty-positions completed shape must be among the failures.
        paths = {"/".join(str(p) for p in e.absolute_path) for e in errors}
        assert any("positions" in p for p in paths), f"errors at unexpected paths: {paths}"

    def test_malformed_stop_condition_rejected(self):
        doc = _load_json(FIXTURES / "duo_verdict_split.json")
        doc["session_metadata"]["stop_condition"] = "banana"
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "non-enum stop_condition must be rejected"
        assert any("stop_condition" in "/".join(str(p) for p in e.absolute_path)
                   for e in errors)

    def test_invalid_completed_outcome_still_rejected(self):
        doc = self._completed_v1_without_stop_condition()
        doc["positions"] = []  # completed shape with no positions
        errors = list(VERDICT_VALIDATOR.iter_errors(doc))
        assert errors, "empty positions on a completed verdict must fail"
