"""Fail-closed canary preflight. No launch, no credential values."""
from __future__ import annotations

import pytest

from app.canary_preflight import (
    DOCS_ONLY_SUCCESSOR,
    QUALIFIED_AGENT_STACK,
    QUALIFIED_HERMES,
    CanaryRefused,
    preflight,
)


def _complete(**overrides):
    proposal = {
        "parent_task_id": "11111111-1111-4111-8111-111111111111",
        "reviewer": "operator-mediated",
        "host": "noesis-lab disposable container",
        "provider": "approved-provider",
        "model": "approved-model",
        "credential_env_name": "CANARY_KEY",
        "credential_supplier": "operator-at-execution",
        "monetary_mechanism": "D1",
        "spend_control_evidence": "prepaid-balance-receipt",
        "agent_stack_revision": QUALIFIED_AGENT_STACK,
        "hermes_revision": QUALIFIED_HERMES,
        "authorization_text": "operator authorized this exact proposal",
    }
    proposal.update(overrides)
    return proposal


def test_missing_proposal_refuses_without_launching():
    with pytest.raises(CanaryRefused) as exc:
        preflight(None)
    assert exc.value.reasons == ["proposal_not_a_mapping"]


def test_unresolved_fields_are_named_and_not_filled():
    with pytest.raises(CanaryRefused) as exc:
        preflight({"parent_task_id": "UNRESOLVED", "host": ""})
    assert "unresolved:parent_task_id" in exc.value.reasons
    assert "unresolved:provider" in exc.value.reasons
    assert "unresolved:monetary_mechanism" in exc.value.reasons
    assert "11111111" not in str(exc.value)


def test_d3_defers_rather_than_executing():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(monetary_mechanism="D3"))
    assert "deferred:D3" in exc.value.reasons


def test_d1_without_evidence_refuses():
    proposal = _complete()
    del proposal["spend_control_evidence"]
    with pytest.raises(CanaryRefused) as exc:
        preflight(proposal)
    assert "unresolved:spend_control_evidence" in exc.value.reasons


def test_unqualified_hermes_pin_does_not_inherit():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(hermes_revision="bf0203a794a07aac3ff764972ab9087baa4e4f4e"))
    assert "unqualified_hermes" in exc.value.reasons


def test_unknown_agent_stack_refuses():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(agent_stack_revision="0" * 40))
    assert "unqualified_agent_stack" in exc.value.reasons


def test_darwin_host_does_not_satisfy_t11():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(host="Darwin laptop"))
    assert "host_does_not_satisfy_t11" in exc.value.reasons


def test_credential_value_is_refused_and_not_echoed():
    marker = "synthetic-marker-not-a-credential"
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(credential_value=marker))
    assert any(r.startswith("credential_value_present:") for r in exc.value.reasons)
    assert marker not in str(exc.value)
    assert marker not in " ".join(exc.value.reasons)


def test_complete_d1_proposal_passes_without_launching():
    accepted = preflight(_complete())
    assert accepted["agent_stack_revision"] == QUALIFIED_AGENT_STACK
    assert accepted["hermes_revision"] == QUALIFIED_HERMES
    assert accepted["monetary_mechanism"] == "D1"
    assert "credential_value" not in accepted


def test_docs_only_successor_is_accepted_as_behavior_identical():
    accepted = preflight(_complete(
        agent_stack_revision=DOCS_ONLY_SUCCESSOR,
        monetary_mechanism="D2",
        manual_stop_acceptance="operator accepts manual stop in writing",
    ))
    assert accepted["agent_stack_revision"] == DOCS_ONLY_SUCCESSOR
    assert accepted["manual_stop_acceptance"].startswith("operator accepts")


def test_docs_only_successor_d1_is_accepted_without_inventing_d2():
    accepted = preflight(_complete(agent_stack_revision=DOCS_ONLY_SUCCESSOR))
    assert accepted["monetary_mechanism"] == "D1"
    assert accepted["agent_stack_revision"] == DOCS_ONLY_SUCCESSOR


def test_malformed_parent_task_id_refuses():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(parent_task_id="not-a-uuid"))
    assert "malformed:parent_task_id" in exc.value.reasons


def test_macos_host_refuses():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(host="macOS-27 lab"))
    assert "host_does_not_satisfy_t11" in exc.value.reasons


def test_weak_manual_stop_refuses():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(
            monetary_mechanism="D2",
            manual_stop_acceptance="yes",
        ))
    assert "unresolved:manual_stop_acceptance" in exc.value.reasons


def test_reviewer_cannot_be_the_implementer():
    with pytest.raises(CanaryRefused) as exc:
        preflight(_complete(reviewer="same-person", implementer="same-person"))
    assert "reviewer_is_implementer" in exc.value.reasons


def test_secret_key_is_case_insensitive():
    proposal = _complete()
    proposal["API" + "_KEY"] = "synthetic-marker-not-a-credential"
    with pytest.raises(CanaryRefused) as exc:
        preflight(proposal)
    assert any(r.startswith("credential_value_present:") for r in exc.value.reasons)
    assert "synthetic-marker-not-a-credential" not in str(exc.value)
