"""Phase E Slice A tests — governed runtime dispatch adapter (offline).

CouncilSeatDispatch adapts the offline council engine (app.council) to a
governed dispatch seam: admission gates (cost-ceiling estimate, route
allowlist, fencing token), per-round revocation and abort with zero further
launcher calls, honest usage mapping (unreported fields stay None), and
observer reporting after the engine returns.

Everything here is deterministic and offline: the launcher is a scripted
injected callable; no provider calls, no orchestrator runtime, no network.
"""

import json
from pathlib import Path

import pytest

from app.council import CouncilError, SeatUsage, sealed_envelopes
from app.council_dispatch import (
    AdmissionError,
    CouncilSeatDispatch,
    MalformedLauncherResult,
    RevokedError,
)

FIXTURES = Path(__file__).parent / "fixtures" / "council"
ALLOWED = {"KIMI_CODE"}


def _session(**over):
    doc = json.loads((FIXTURES / "duo_session.json").read_text())
    doc.update(over)
    return doc


def _position(seat: str, option: str, confidence: str = "high") -> str:
    return json.dumps({
        "option": option,
        "stance": f"{seat} argues for {option}",
        "confidence": confidence,
        "confidence_basis": "scripted fixture",
        "known_limitations": ["scripted"],
        "evidence_labels": {"UNKNOWN": []},
    })


class _ScriptedLauncher:
    """Injected launcher callable: canned outputs per seat, records calls.

    Callable shape: launcher(seat, payload, max_output_tokens, round_timeout_s)
    -> {"text": str, "usage": {...}}. ``on_call`` lets a test abort or revoke
    mid-session at a chosen call count.
    """

    def __init__(self, outputs: dict, usage: dict | None = None, on_call=None):
        self.outputs = outputs
        self.calls: list[dict] = []
        self.usage = usage
        self.on_call = on_call

    def __call__(self, seat, payload, max_output_tokens, round_timeout_s):
        self.calls.append({
            "seat_id": seat["seat_id"],
            "payload": payload,
            "max_output_tokens": max_output_tokens,
            "round_timeout_s": round_timeout_s,
        })
        if self.on_call is not None:
            self.on_call(len(self.calls))
        out = self.outputs[seat["seat_id"]].pop(0)
        if isinstance(out, str):
            usage = dict(self.usage if self.usage is not None
                         else {"output_tokens": 200, "input_tokens": 100})
            return {"text": out, "usage": usage}
        return out


class _RecordingObserver:
    def __init__(self):
        self.records: list[dict] = []

    def observe_budget(self, task_id, requests=0, output_tokens=None,
                       input_tokens=None, cache_read_tokens=None,
                       cache_write_tokens=None):
        self.records.append({
            "task_id": task_id,
            "requests": requests,
            "output_tokens": output_tokens,
            "input_tokens": input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        })


def _dispatch(session, launcher, **kw) -> CouncilSeatDispatch:
    return CouncilSeatDispatch(session, launcher, allowed_routes=ALLOWED, **kw)


def _consensus_outputs(option: str = "ship duo first") -> dict:
    return {
        "s1": [_position("s1", option), _position("s1", option)],
        "s2": [_position("s2", option), _position("s2", option)],
    }


class TestAdmissionGate:
    def test_missing_cost_ceiling_estimate_refused(self):
        session = _session()
        del session["limits"]["cost_ceiling"]["estimated_tokens"]
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError, match="estimated_tokens"):
            _dispatch(session, launcher)
        assert launcher.calls == []

    def test_zero_cost_ceiling_estimate_refused(self):
        session = _session()
        session["limits"]["cost_ceiling"]["estimated_tokens"] = 0
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError, match="estimated_tokens"):
            _dispatch(session, launcher)
        assert launcher.calls == []

    def test_negative_cost_ceiling_estimate_refused(self):
        session = _session()
        session["limits"]["cost_ceiling"]["estimated_tokens"] = -100
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError, match="estimated_tokens"):
            _dispatch(session, launcher)
        assert launcher.calls == []

    def test_seat_route_outside_allowlist_refused_with_zero_launcher_calls(self):
        session = _session()
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError, match="KIMI_CODE"):
            CouncilSeatDispatch(session, launcher, allowed_routes={"SOME_OTHER_LANE"})
        assert launcher.calls == []

    def test_empty_allowlist_denies_everything(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError):
            CouncilSeatDispatch(_session(), launcher, allowed_routes=set())
        assert launcher.calls == []

    def test_fencing_token_required_when_declared(self):
        session = _session()
        session["fencing"]["attempt_id"] = ""
        launcher = _ScriptedLauncher(_consensus_outputs())
        with pytest.raises(AdmissionError, match="fencing"):
            _dispatch(session, launcher, fencing_required=True)
        assert launcher.calls == []

    def test_admission_passes_on_valid_fixture(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher, fencing_required=True)
        assert dispatch.dispatch_count == 0


class TestRevocation:
    def test_execution_revoked_refuses_before_any_launcher_call(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher, execution_revoked=lambda: True)
        with pytest.raises(RevokedError):
            dispatch.run_round("s1", {}, {"max_output_tokens": 100, "round_timeout_s": 30})
        assert launcher.calls == []
        assert dispatch.dispatch_count == 0

    def test_execution_revoked_checked_every_round(self):
        calls = {"n": 0}

        def revoked_after_two():
            calls["n"] += 1
            return calls["n"] > 2

        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher, execution_revoked=revoked_after_two)
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        assert verdict["session_metadata"]["rounds_run"] == 1
        assert len(launcher.calls) == 2  # both round-1 seats only
        assert dispatch.dispatch_count == 2


class TestAbort:
    def test_abort_mid_round_one_blocks_second_seat(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher)
        launcher.on_call = lambda n: dispatch.abort() if n == 1 else None
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        assert verdict["session_metadata"]["rounds_run"] == 0
        assert len(launcher.calls) == 1
        assert dispatch.dispatch_count == 1

    def test_abort_between_rounds_stops_final_round(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher)
        launcher.on_call = lambda n: dispatch.abort() if n == 2 else None
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        assert verdict["session_metadata"]["rounds_run"] == 1
        assert len(launcher.calls) == 2
        assert dispatch.dispatch_count == 2

    def test_run_round_after_abort_raises_revoked_with_no_launcher_call(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher)
        dispatch.abort()
        with pytest.raises(RevokedError):
            dispatch.run_round("s1", {}, {"max_output_tokens": 100, "round_timeout_s": 30})
        assert launcher.calls == []


class TestHappyPath:
    def test_full_duo_run_blind_round_one_and_usage_reported(self):
        session = _session()
        launcher = _ScriptedLauncher(_consensus_outputs())
        observer = _RecordingObserver()
        dispatch = _dispatch(session, launcher, observer=observer)
        verdict = dispatch.run(ALLOWED)
        assert verdict["consensus"]["reached"] is True
        assert verdict["session_metadata"]["stop_condition"] is None
        assert dispatch.dispatch_count == 4  # 2 seats x 2 rounds
        # Round 1 blindness asserted via the engine's own guarantees: the
        # payloads the launcher saw are the sealed envelopes (no peer data).
        expected = sealed_envelopes(session)
        for call in launcher.calls[:2]:
            assert call["payload"] == expected[call["seat_id"]]
            blob = json.dumps(call["payload"])
            assert "noesis-" not in blob
            assert '"peers"' not in blob and '"positions"' not in blob
        # Round 2 payloads are the anonymized release (identical for both).
        assert launcher.calls[2]["payload"] == launcher.calls[3]["payload"]
        # Usage reported for each completed seat round; unreported fields None.
        assert len(observer.records) == 4
        for rec in observer.records:
            assert rec["task_id"] == session["parent_task_id"]
            assert rec["requests"] == 1
            assert rec["output_tokens"] == 200
            assert rec["input_tokens"] == 100
            assert rec["cache_read_tokens"] is None
            assert rec["cache_write_tokens"] is None
        # Engine-level observed totals: 4 rounds x (100 in / 200 out).
        assert verdict["usage"]["observed"]["input_tokens"] == 400
        assert verdict["usage"]["observed"]["output_tokens"] == 800

    def test_unreported_usage_fields_stay_none(self):
        launcher = _ScriptedLauncher(
            _consensus_outputs(), usage={"output_tokens": 55})
        observer = _RecordingObserver()
        dispatch = _dispatch(_session(), launcher, observer=observer)
        dispatch.run(ALLOWED)
        assert len(observer.records) == 4
        for rec in observer.records:
            assert rec["output_tokens"] == 55
            assert rec["input_tokens"] is None
            assert rec["cache_read_tokens"] is None
            assert rec["cache_write_tokens"] is None
        # The adapter's own call records keep the honest None too; the
        # engine-facing SeatUsage falls back to its own int defaults.
        for call in dispatch.calls:
            assert call["input_tokens"] is None
            assert call["cache_read_tokens"] is None

    def test_launcher_usage_missing_output_tokens_raises(self):
        launcher = _ScriptedLauncher(_consensus_outputs(), usage={"input_tokens": 10})
        dispatch = _dispatch(_session(), launcher)
        with pytest.raises(MalformedLauncherResult, match="output_tokens"):
            dispatch.run_round("s1", {}, {"max_output_tokens": 100, "round_timeout_s": 30})

    def test_unknown_seat_refused(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        dispatch = _dispatch(_session(), launcher)
        with pytest.raises(CouncilError, match="unknown seat"):
            dispatch.run_round("s9", {}, {"max_output_tokens": 100, "round_timeout_s": 30})
        assert launcher.calls == []


class TestMalformedSeatOutput:
    def test_malformed_json_blocks_seat_and_usage_stays_correct(self):
        session = _session()
        outputs = {
            "s1": [_position("s1", "ship duo first"), _position("s1", "ship duo first")],
            "s2": ["not json at all", _position("s2", "ship duo first")],
        }
        launcher = _ScriptedLauncher(outputs)
        observer = _RecordingObserver()
        dispatch = _dispatch(session, launcher, observer=observer)
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "quorum_shortfall"
        assert verdict["session_metadata"]["rounds_run"] == 0
        assert verdict["positions"] == []
        # Both seats were dispatched in round 1; only s1 produced a parseable
        # output. Both launcher calls really consumed budget, so both are
        # honestly reported to the observer.
        assert dispatch.dispatch_count == 2
        assert len(observer.records) == 2
        assert observer.records[0]["output_tokens"] == 200
        # Observed totals count completed rounds only (s1's single round).
        assert verdict["usage"]["observed"]["output_tokens"] == 200
        assert verdict["usage"]["observed"]["input_tokens"] == 100

    def test_usage_reported_even_when_engine_raises_revoked(self):
        launcher = _ScriptedLauncher(_consensus_outputs())
        observer = _RecordingObserver()
        dispatch = _dispatch(_session(), launcher, observer=observer)
        launcher.on_call = lambda n: dispatch.abort() if n == 1 else None
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        # The one completed round is still reported to the observer.
        assert len(observer.records) == 1
        assert observer.records[0]["output_tokens"] == 200
