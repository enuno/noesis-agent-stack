"""Phase E readiness: production dispatch wiring (T6) and token budget gate (T10).

Offline only. The adapter doubles never spawn a process; the seam path is
exercised through a recording fake adapter, not HermesCliAdapter with a real
transport.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.council import BudgetExhausted
from app.council_dispatch import AdmissionError, CouncilSeatDispatch
from app.seat_credentials import HermesCouncilSeatLauncher, SeatCredentialContract

ALLOWED = {"KIMI_CODE"}


def _session(ceiling: int = 100) -> dict:
    return {
        "parent_task_id": "task-phase-e-0001",
        "fencing": {"task_version": 0, "epoch": 0, "attempt_id": "attempt-0001"},
        "seats": [
            {
                "seat_id": "s1",
                "profile": "noesis-skeptic",
                "inference_route": "KIMI_CODE",
                "budget": {"max_output_tokens": 40, "round_timeout_s": 60},
            }
        ],
        "limits": {
            "rounds": 1,
            "cost_ceiling": {
                "unit": "tokens",
                "estimated_tokens": ceiling,
                "observed_tokens": 0,
                "currency_value": None,
            },
        },
    }


class _FakeAdapter:
    """Recording adapter double; never touches a process or network."""

    def __init__(self, output_tokens: int = 5):
        self.calls: list[dict] = []
        self._output_tokens = output_tokens

    def launch(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            ok=True,
            blocker_code=None,
            error=None,
            captured_stdout=json.dumps(
                {"text": "pong", "usage": {"output_tokens": self._output_tokens}}
            ),
        )


def _contract() -> SeatCredentialContract:
    return SeatCredentialContract(scope="none")


def test_production_factory_builds_governed_seam(tmp_path: Path):
    adapter = _FakeAdapter()
    dispatch = CouncilSeatDispatch.production(
        _session(ceiling=44),
        adapter=adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path,
        task_id="task-phase-e-0001",
        allowed_routes=ALLOWED,
    )
    assert isinstance(dispatch.launcher, HermesCouncilSeatLauncher)
    # Production wiring is pinned here: dropping either flag from production()
    # makes one of these assertions fail.
    assert dispatch.require_governed_launcher is True
    assert dispatch.enforce_budget is True
    budget = {"max_output_tokens": 40, "round_timeout_s": 60, "round": 1}
    text, usage = dispatch.run_round("s1", {"ask": "pong"}, budget)
    assert text == "pong"
    assert usage.output_tokens == 5
    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    assert call["provider"] == "approved-provider"
    assert call["model"] == "approved-model"
    assert call["fallback_policy"] == "deny"
    assert call["budget_attempt_id"] == "task-phase-e-0001|s1|round-1|attempt-1"
    # The factory's budget gate is non-optional: observed 5 + requested 40
    # exceeds the ceiling of 44, so the second round is refused pre-inference.
    with pytest.raises(BudgetExhausted, match="no launcher call was made"):
        dispatch.run_round("s1", {"ask": "pong"}, budget)
    assert len(adapter.calls) == 1


def test_production_dispatch_refuses_injected_callable():
    with pytest.raises(AdmissionError, match="governed seat launcher"):
        CouncilSeatDispatch(
            _session(),
            lambda seat, payload, cap, timeout: {"text": "{}", "usage": {"output_tokens": 1}},
            allowed_routes=ALLOWED,
            require_governed_launcher=True,
        )


def test_production_factory_requires_fencing_token():
    session = _session()
    del session["fencing"]["attempt_id"]
    with pytest.raises(AdmissionError, match="fencing"):
        CouncilSeatDispatch.production(
            session,
            adapter=_FakeAdapter(),
            provider="approved-provider",
            model="approved-model",
            credential_contract=_contract(),
            workspace=Path("/tmp/unused-phase-e-readiness"),
            task_id="task-phase-e-0001",
            allowed_routes=ALLOWED,
        )


def test_budget_enforcement_refuses_before_inference():
    calls = {"n": 0}

    def launcher(seat, payload, cap, timeout):
        calls["n"] += 1
        return {"text": "pong", "usage": {"output_tokens": 10}}

    dispatch = CouncilSeatDispatch(
        _session(ceiling=45), launcher, allowed_routes=ALLOWED, enforce_budget=True
    )
    dispatch.run_round("s1", {}, {"max_output_tokens": 40, "round_timeout_s": 60})
    with pytest.raises(BudgetExhausted, match="no launcher call was made"):
        dispatch.run_round("s1", {}, {"max_output_tokens": 40, "round_timeout_s": 60})
    assert calls["n"] == 1


def test_budget_enforcement_allows_within_ceiling():
    calls = {"n": 0}

    def launcher(seat, payload, cap, timeout):
        calls["n"] += 1
        return {"text": "pong", "usage": {"output_tokens": 10}}

    dispatch = CouncilSeatDispatch(
        _session(ceiling=100), launcher, allowed_routes=ALLOWED, enforce_budget=True
    )
    dispatch.run_round("s1", {}, {"max_output_tokens": 40, "round_timeout_s": 60})
    dispatch.run_round("s1", {}, {"max_output_tokens": 40, "round_timeout_s": 60})
    assert calls["n"] == 2
    assert dispatch._consumed_output_tokens() == 20


def test_budget_gate_off_by_default_preserves_offline_contract():
    calls = {"n": 0}

    def launcher(seat, payload, cap, timeout):
        calls["n"] += 1
        return {"text": "pong", "usage": {"output_tokens": 10}}

    dispatch = CouncilSeatDispatch(_session(ceiling=1), launcher, allowed_routes=ALLOWED)
    dispatch.run_round("s1", {}, {"max_output_tokens": 40, "round_timeout_s": 60})
    assert calls["n"] == 1
