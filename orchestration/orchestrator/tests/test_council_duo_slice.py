"""Phase C vertical slice tests — duo council session, fully offline.

Drives app.council.run_duo_session with scripted SeatRunners through the
governed stages: route allowlist (fail closed), pre-work budget reservation,
sealed blind Round 1, anonymized release, final blind round, weighted tally,
split/dissent preservation, partial panels, and leak rejection.

No provider calls, no orchestrator runtime state, no network.
"""

import ast
import json
from pathlib import Path

import pytest

from app.council import (
    BudgetExhausted,
    CouncilError,
    RouteDenied,
    anonymized_release,
    reserve_session_budget,
    run_duo_session,
    sealed_envelopes,
    validate_seat_routes,
    weigh_tally,
)
from app.council import SeatUsage

FIXTURES = Path(__file__).parent / "fixtures" / "council"
CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "orchestration"
ALLOWED = {"KIMI_CODE"}


def _session(**over):
    doc = json.loads((FIXTURES / "duo_session.json").read_text())
    doc.update(over)
    return doc


class _ScriptedRunner:
    """Returns canned JSON per seat; records payloads seen by each seat."""

    def __init__(self, outputs: dict[str, list[str]], usage: SeatUsage | None = None):
        self.outputs = outputs
        self.seen: dict[str, list] = {}
        self.usage = usage or SeatUsage(input_tokens=100, output_tokens=200)

    def run_round(self, seat_id, payload, budget):
        self.seen.setdefault(seat_id, []).append(payload)
        out = self.outputs[seat_id].pop(0)
        return out, self.usage


def _position(seat: str, option: str, confidence: str = "high", **extra) -> str:
    payload = {
        "option": option,
        "stance": f"{seat} argues for {option}",
        "confidence": confidence,
        "confidence_basis": "scripted fixture",
        "known_limitations": ["scripted"],
        "evidence_labels": {"UNKNOWN": []},
    }
    payload.update(extra)
    return json.dumps(payload)


class TestAuthorityIsolation:
    def test_engine_imports_no_mutators(self):
        """Static guard: council.py must never import ledger/delegation/control
        plane mutators (skills/noesis-control-plane-dev authority-isolation)."""
        src = Path(__import__("app.council").council.__file__).read_text()
        banned = {"store", "control_plane", "delegation", "lease_lifecycle",
                  "launcher", "subagent_development"}
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                names = {a.name.split(".")[-1] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[-1]}
            else:
                continue
            assert not (names & banned), f"council.py imports mutator module(s): {names & banned}"


class TestFailClosedGuards:
    def test_unapproved_route_denied_before_any_work(self):
        session = _session()
        with pytest.raises(RouteDenied):
            validate_seat_routes(session, {"SOME_OTHER_LANE"})
        with pytest.raises(RouteDenied):
            run_duo_session(session, _ScriptedRunner({}), {"SOME_OTHER_LANE"})

    def test_empty_allowlist_denies_everything(self):
        with pytest.raises(RouteDenied):
            validate_seat_routes(_session(), set())

    def test_budget_reservation_refuses_over_ceiling(self):
        session = _session()
        session["limits"]["cost_ceiling"]["estimated_tokens"] = 100
        with pytest.raises(BudgetExhausted) as exc:
            reserve_session_budget(session)
        assert "no seat work was reserved" in str(exc.value)
        with pytest.raises(BudgetExhausted):
            run_duo_session(session, _ScriptedRunner({}), ALLOWED)

    def test_non_duo_mode_rejected(self):
        session = _session(mode="full")
        with pytest.raises(CouncilError, match="duo mode only"):
            run_duo_session(session, _ScriptedRunner({}), ALLOWED)

    def test_chairman_must_be_excluded_from_panel(self):
        session = _session()
        session["chairman"] = {"profile": "noesis-skeptic", "excluded_from_panel": False}
        with pytest.raises(CouncilError, match="excluded"):
            run_duo_session(session, _ScriptedRunner({}), ALLOWED)


class TestBlindFirstStructure:
    def test_envelopes_carry_no_peer_content(self):
        session = _session()
        envelopes = sealed_envelopes(session)
        assert set(envelopes) == {"s1", "s2"}
        for sid, env in envelopes.items():
            blob = json.dumps(env)
            assert sid not in blob  # own id not needed inside payload
            assert "noesis-" not in blob
            for peer_key in ("peers", "peer_positions", "other_seats", "positions"):
                assert f'"{peer_key}"' not in blob

    def test_each_seat_sees_only_its_own_envelope_then_release(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first"), _position("s1", "ship duo first")],
            "s2": [_position("s2", "build full protocol before any release"),
                   _position("s2", "build full protocol before any release")],
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        assert verdict["consensus"]["reached"] is False
        s1_payloads, s2_payloads = runner.seen["s1"], runner.seen["s2"]
        assert len(s1_payloads) == len(s2_payloads) == 2
        # Round 1 payloads are the sealed envelopes (identical framing, no peer data).
        assert s1_payloads[0] == s2_payloads[0] == sealed_envelopes(session)["s1"]
        # Round 2 payloads are the anonymized release (same for both, keyed by seat_id).
        assert s1_payloads[1] == s2_payloads[1]
        assert set(s1_payloads[1]) == {"s1", "s2"}
        assert "noesis-" not in json.dumps(s1_payloads[1])


class TestTallyAndDissent:
    def test_split_verdict_preserved_and_escalated(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first", "high")] * 2,
            "s2": [_position("s2", "build full protocol before any release", "high")] * 2,
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        assert verdict["tally"]["no_option_carried"] is True
        assert verdict["consensus"]["reached"] is False
        assert "No consensus reached" in verdict["consensus"]["explanation"]
        assert verdict["dissent"]["minority_report"]
        assert {p["seat_id"] for p in verdict["positions"]} == {"s1", "s2"}

    def test_consensus_clears_threshold(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first", "high")] * 2,
            "s2": [_position("s2", "ship duo first", "med")] * 2,
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        assert verdict["consensus"]["reached"] is True
        assert verdict["consensus"]["position"] == "ship duo first"
        assert verdict["tally"]["no_option_carried"] is False

    def test_unknown_evidence_collects_into_unresolved_questions(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first", "high",
                             evidence_labels={"UNKNOWN": ["quorum floor for triad"]})] * 2,
            "s2": [_position("s2", "ship duo first", "high")] * 2,
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        assert "quorum floor for triad" in verdict["unresolved_questions"]

    def test_weigh_tally_rejects_unknown_option(self):
        with pytest.raises(Exception, match="not in alternatives"):
            weigh_tally({"s1": {"option": "nonsense", "confidence": "high"}}, ["a", "b"])


class TestFailureBehavior:
    def test_malformed_output_blocks_seat_and_yields_partial_panel(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first"), _position("s1", "ship duo first")],
            "s2": ["not json at all", _position("s2", "ship duo first")],
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "quorum_shortfall"
        assert verdict["positions"] == []
        assert "s2" in verdict["synthesis_notes"]

    def test_leaking_output_rejected_structurally(self):
        session = _session()
        leak = json.dumps({"option": "x", "stance": "s2 says y", "confidence": "high"})
        verdict = run_duo_session(
            session,
            _ScriptedRunner({"s1": [leak, leak], "s2": [_position("s2", "a")] * 2}),
            ALLOWED,
        )
        # Leaks block the offending seat; the panel goes partial rather than
        # silently substituting or continuing with a compromised seat.
        assert verdict["session_metadata"]["stop_condition"] == "quorum_shortfall"
        assert "s1(EnvelopeLeak)" in verdict["synthesis_notes"]
        name_leak = json.dumps({"option": "x", "stance": "per noesis-architect", "confidence": "high"})
        verdict2 = run_duo_session(
            session,
            _ScriptedRunner({"s1": [name_leak, name_leak],
                             "s2": [_position("s2", "a")] * 2}),
            ALLOWED,
        )
        assert verdict2["session_metadata"]["stop_condition"] == "quorum_shortfall"

    def test_observed_usage_accumulates_and_stays_distinct_from_estimates(self):
        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first")] * 2,
            "s2": [_position("s2", "ship duo first")] * 2,
        }, usage=SeatUsage(input_tokens=10, output_tokens=20))
        verdict = run_duo_session(session, runner, ALLOWED)
        # 2 seats x 2 rounds x (10 in / 20 out)
        assert verdict["usage"]["observed"]["input_tokens"] == 40
        assert verdict["usage"]["observed"]["output_tokens"] == 80
        assert "currency value" in verdict["usage"]["unknown_fields"]


class TestVerdictContractConformance:
    def test_assembled_verdict_validates_against_contract(self):
        jsonschema = pytest.importorskip("jsonschema")
        from referencing import Registry, Resource

        schema = json.loads((CONTRACTS / "council-verdict.schema.json").read_text())
        registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
        validator = jsonschema.Draft202012Validator(schema, registry=registry)

        session = _session()
        runner = _ScriptedRunner({
            "s1": [_position("s1", "ship duo first")] * 2,
            "s2": [_position("s2", "build full protocol before any release")] * 2,
        })
        verdict = run_duo_session(session, runner, ALLOWED)
        errors = list(validator.iter_errors(verdict))
        assert not errors, "; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors)
