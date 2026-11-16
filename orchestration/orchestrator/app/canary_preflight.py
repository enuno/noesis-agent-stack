"""Fail-closed preflight for a proposed Phase E canary.

This module does not launch a worker, contact a provider, read a credential
value, or choose a monetary policy. It refuses a proposal whose
safety-critical fields are missing, marked UNRESOLVED, or outside the
qualified immutable combination. A passing preflight is not authorization
to execute.
"""
from __future__ import annotations

import uuid
from typing import Any

# T11 evidence binds to this pair. A different Hermes pin does not inherit it.
QUALIFIED_AGENT_STACK = "338ac8399d92a8b5e42d453ccaaef81ad22a22e7"
QUALIFIED_HERMES = "3b421578588243f920886e6fe79a6faa87ea026e"
# Merge of the T11 record (docs + one docstring). Launcher behavior is
# identical to QUALIFIED_AGENT_STACK. Not a new qualification.
DOCS_ONLY_SUCCESSOR = "35464faba8ea05d6eee67bbdb2151c3c741bcce6"

_ALLOWED_STACK = frozenset({QUALIFIED_AGENT_STACK, DOCS_ONLY_SUCCESSOR})
_EXECUTABLE_MECHANISMS = frozenset({"D1", "D2"})
_BLANK = frozenset({"", "unresolved", "none", "null", "tbd"})
_SECRET_KEYS = frozenset({
    "credential_value",
    "api_key",
    "token",
    "secret",
    "password",
})
_MIN_ACCEPTANCE = 24


class CanaryRefused(Exception):
    """Proposal is not executable. ``reasons`` names fields, never values."""

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = list(reasons)
        super().__init__("canary preflight refused: " + ", ".join(self.reasons))


def _blank(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    return value.strip().lower() in _BLANK


def preflight(proposal: dict[str, Any] | None) -> dict[str, str]:
    """Validate a proposal. Return the accepted field map, or raise.

    Never launches. Never copies a credential value into the result.
    """
    reasons: list[str] = []
    if not isinstance(proposal, dict):
        raise CanaryRefused(["proposal_not_a_mapping"])
    leaked = sorted(k for k in proposal if str(k).lower() in _SECRET_KEYS)
    if leaked:
        reasons.append("credential_value_present:" + ",".join(leaked))

    required = (
        "parent_task_id",
        "reviewer",
        "host",
        "provider",
        "model",
        "credential_env_name",
        "credential_supplier",
        "monetary_mechanism",
        "agent_stack_revision",
        "hermes_revision",
        "authorization_text",
    )
    for name in required:
        if _blank(proposal.get(name)):
            reasons.append(f"unresolved:{name}")

    mechanism = proposal.get("monetary_mechanism")
    if isinstance(mechanism, str) and mechanism.strip() and not _blank(mechanism):
        token = mechanism.strip()
        if token == "D3":
            reasons.append("deferred:D3")
        elif token not in _EXECUTABLE_MECHANISMS:
            reasons.append("unresolved:monetary_mechanism")
        elif token == "D1" and _blank(proposal.get("spend_control_evidence")):
            reasons.append("unresolved:spend_control_evidence")
        elif token == "D2" and (
            _blank(proposal.get("manual_stop_acceptance"))
            or len(str(proposal.get("manual_stop_acceptance")).strip()) < _MIN_ACCEPTANCE
        ):
            reasons.append("unresolved:manual_stop_acceptance")

    stack = proposal.get("agent_stack_revision")
    if isinstance(stack, str) and stack.strip() and stack.strip() not in _ALLOWED_STACK:
        reasons.append("unqualified_agent_stack")
    hermes = proposal.get("hermes_revision")
    if isinstance(hermes, str) and hermes.strip() and hermes.strip() != QUALIFIED_HERMES:
        reasons.append("unqualified_hermes")

    parent = proposal.get("parent_task_id")
    if isinstance(parent, str) and parent.strip() and not _blank(parent):
        try:
            uuid.UUID(parent.strip())
        except ValueError:
            reasons.append("malformed:parent_task_id")

    host = proposal.get("host")
    if isinstance(host, str) and any(w in host.lower() for w in ("darwin", "macos")):
        reasons.append("host_does_not_satisfy_t11")

    reviewer = proposal.get("reviewer")
    implementer = proposal.get("implementer")
    if (
        isinstance(reviewer, str)
        and isinstance(implementer, str)
        and reviewer.strip()
        and reviewer.strip() == implementer.strip()
    ):
        reasons.append("reviewer_is_implementer")

    if reasons:
        raise CanaryRefused(reasons)

    accepted = {name: str(proposal[name]).strip() for name in required}
    accepted["monetary_mechanism"] = str(proposal["monetary_mechanism"]).strip()
    if accepted["monetary_mechanism"] == "D1":
        accepted["spend_control_evidence"] = str(proposal["spend_control_evidence"]).strip()
    else:
        accepted["manual_stop_acceptance"] = str(proposal["manual_stop_acceptance"]).strip()
    return accepted
