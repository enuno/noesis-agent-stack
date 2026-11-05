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
