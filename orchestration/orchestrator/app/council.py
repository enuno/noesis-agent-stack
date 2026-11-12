"""Council session assembly engine — Phase C vertical slice (duo mode, offline).

Advisory multi-perspective deliberation as a deterministic, offline protocol
engine. This module assembles sealed Round-1 envelopes, drives the duo round
sequence through a pluggable ``SeatRunner``, enforces route allowlists and
token budgets before any seat work is reserved, and assembles a
council-verdict-shaped artifact. It is deliberately NOT a dispatch path:

- It never imports TaskStore, DelegationStore, control_plane, delegation, or
  any other orchestrator mutator (guarded by test).
- It does not spawn workers, call providers, or mutate the authoritative
  ledger. The SeatRunner protocol is the seam where a governed, separately
  authorized dispatch adapter would plug in during runtime qualification
  (Phase E). In this slice only offline scripted runners are used.
- Verdicts assembled here are advisory evidence; acceptance stays with the
  orchestrator/human path.

Fail-closed posture: an unapproved seat route, an exhausted budget, or a
malformed seat output blocks the affected seat (or the session, before any
work is reserved) rather than falling back to another provider or route.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping, Protocol


class CouncilError(Exception):
    """Base for all council slice failures. Never silently swallowed."""


class RouteDenied(CouncilError):
    """A seat's inference route is not in the operator-approved allowlist."""


class BudgetExhausted(CouncilError):
    """Reservation would exceed the session cost ceiling."""


class MalformedSeatOutput(CouncilError):
    """A seat's structured output could not be parsed or violates shape."""


class EnvelopeLeak(CouncilError):
    """A seat output leaks peer identity or position information."""


CONFIDENCE_WEIGHTS = {"high": 1.0, "med": 0.75, "low": 0.5}
TALLY_METHOD = "confidence_weighted_2of3"
TALLY_THRESHOLD = 2.0 / 3.0

# Structural vocabulary that must never cross seat boundaries.
_FORBIDDEN_PEER_KEYS = ("peers", "peer_positions", "other_seats", "positions")

_REQUIRED_SEAT_FIELDS = ("option", "stance", "confidence")


@dataclass(frozen=True)
class SeatUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class SeatResult:
    seat_id: str
    ok: bool
    payload: dict | None = None
    error: str | None = None
    usage: SeatUsage = field(default_factory=SeatUsage)
    blocked_reason: str | None = None


class SeatRunner(Protocol):
    """Offline seam for seat round execution.

    Implementations receive exactly one envelope or release payload and
    return a JSON object string. Real dispatch is a separately authorized
    Phase-E concern; tests use scripted runners only.
    """

    def run_round(
        self, seat_id: str, payload: Mapping, budget: Mapping
    ) -> tuple[str, SeatUsage]: ...


def session_profile_names(session: Mapping) -> set[str]:
    names = {s["profile"] for s in session.get("seats", [])}
    chair = session.get("chairman") or {}
    if chair.get("profile"):
        names.add(chair["profile"])
    return names


def validate_seat_routes(session: Mapping, approved_routes: set[str]) -> None:
    """Fail closed: every seat route must be in the approved allowlist."""
    for seat in session.get("seats", []):
        route = (seat.get("inference_route") or "").strip()
        if route not in approved_routes:
            raise RouteDenied(
                f"seat '{seat.get('seat_id')}' route '{route or '<empty>'}' is not "
                f"in the approved allowlist {sorted(approved_routes)}"
            )


def reserve_session_budget(session: Mapping) -> int:
    """Compute the total reservation and refuse to exceed the cost ceiling.

    Reservation happens BEFORE any seat work: this function is the only
    budget guard in the offline slice. Observed-token accounting during the
    session is informational (recorded on the verdict's usage block); it is
    NOT enforced against the reservation or the ceiling here. Consumption
    enforcement belongs to the governed dispatch adapter (Phase E) and must
    reuse the existing delegation budget/lease protection, never a parallel
    system.
    """
    limits = session.get("limits", {})
    ceiling = limits.get("cost_ceiling", {})
    rounds = int(limits.get("rounds", 1))
    per_round = sum(int(s["budget"]["max_output_tokens"]) for s in session.get("seats", []))
    reservation = per_round * rounds
    ceiling_est = ceiling.get("estimated_tokens")
    if ceiling_est is not None and reservation > int(ceiling_est):
        raise BudgetExhausted(
            f"session reservation {reservation} tokens exceeds cost ceiling "
            f"{ceiling_est}; no seat work was reserved"
        )
    return reservation


def sealed_envelopes(session: Mapping) -> dict[str, dict]:
    """Build Round-1 blind envelopes by construction.

    Each envelope carries only the decision framing and evidence references.
    Peer seat_ids, profile names, and positions are structurally absent.
    """
    decision = session["decision"]
    evidence_refs = [e["ref"] for e in session.get("evidence_manifest", [])]
    base = {
        "question": decision["question"],
        "alternatives": list(decision["alternatives"]),
        "constraints": list(decision.get("constraints", [])),
        "evidence_refs": evidence_refs,
        "sensitivity": (session.get("retention") or {}).get("sensitivity_class", "internal"),
    }
    return {seat["seat_id"]: dict(base) for seat in session["seats"]}


def _check_output_leak(seat_id: str, text: str, session: Mapping, envelopes: Mapping[str, Mapping]) -> None:
    """Structural leak check: no peer seat_id, profile name, or peer-key."""
    for other in envelopes:
        if other != seat_id and other in text:
            raise EnvelopeLeak(f"seat '{seat_id}' output references peer seat '{other}'")
    for name in session_profile_names(session):
        if name in text:
            raise EnvelopeLeak(f"seat '{seat_id}' output leaks profile name '{name}'")
    for key in _FORBIDDEN_PEER_KEYS:
        if f'"{key}"' in text:
            raise EnvelopeLeak(f"seat '{seat_id}' output carries forbidden key '{key}'")


def _parse_seat_output(seat_id: str, text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedSeatOutput(f"seat '{seat_id}' output is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MalformedSeatOutput(f"seat '{seat_id}' output is not an object")
    missing = [k for k in _REQUIRED_SEAT_FIELDS if not payload.get(k)]
    if missing:
        raise MalformedSeatOutput(f"seat '{seat_id}' output missing fields {missing}")
    if payload["confidence"] not in CONFIDENCE_WEIGHTS:
        raise MalformedSeatOutput(
            f"seat '{seat_id}' confidence '{payload['confidence']}' not in {sorted(CONFIDENCE_WEIGHTS)}"
        )
    return payload


def anonymized_release(positions: Mapping[str, Mapping]) -> dict[str, str]:
    """Round-2 controlled release: keyed by seat_id only, profile names absent."""
    return {sid: str(p["stance"])[:1200] for sid, p in positions.items()}


def _run_seat(
    runner: SeatRunner,
    seat: Mapping,
    payload: Mapping,
    session: Mapping,
    envelopes: Mapping[str, Mapping],
    observed: dict[str, int],
    round_n: int,
) -> SeatResult:
    sid = seat["seat_id"]
    budget = dict(seat["budget"])
    budget["round"] = round_n
    fencing = session.get("fencing") or {}
    epoch = fencing.get("epoch", fencing.get("assignment_epoch"))
    if isinstance(epoch, int) and not isinstance(epoch, bool) and epoch >= 0:
        budget["assignment_epoch"] = epoch
    try:
        text, usage = runner.run_round(sid, payload, budget)
        _check_output_leak(sid, text, session, envelopes)
        payload_obj = _parse_seat_output(sid, text)
        observed["output_tokens"] = observed.get("output_tokens", 0) + usage.output_tokens
        observed["input_tokens"] = observed.get("input_tokens", 0) + usage.input_tokens
        return SeatResult(seat_id=sid, ok=True, payload=payload_obj, usage=usage)
    except (EnvelopeLeak, MalformedSeatOutput) as exc:
        return SeatResult(seat_id=sid, ok=False, error=str(exc), blocked_reason=type(exc).__name__)


def weigh_tally(positions: Mapping[str, Mapping], alternatives: list[str]) -> dict:
    """Confidence-weighted 2/3 tally (duo slice: no domain multiplier — the
    1.5x seat is a full-mode feature; its absence is a recorded deviation)."""
    totals: dict[str, dict] = {}
    for sid, p in positions.items():
        opt = p["option"]
        if opt not in alternatives:
            raise MalformedSeatOutput(f"seat '{sid}' option '{opt}' not in alternatives {alternatives}")
        w = CONFIDENCE_WEIGHTS[p["confidence"]]
        entry = totals.setdefault(opt, {"weight": 0.0, "backers": []})
        entry["weight"] += w
        entry["backers"].append(f"{sid} [{p['confidence']}]")
    total_weight = sum(e["weight"] for e in totals.values()) or 1.0
    threshold = TALLY_THRESHOLD * total_weight
    options = [
        {"option": opt, "weight": round(e["weight"], 3), "backers": e["backers"],
         "cleared_threshold": e["weight"] >= threshold}
        for opt, e in totals.items()
    ]
    carried = [o for o in options if o["cleared_threshold"]]
    return {
        "method": TALLY_METHOD,
        "threshold": round(threshold, 3),
        "options": options,
        "no_option_carried": not carried,
        "carried": carried[0]["option"] if carried else None,
    }


def _revision_projection(session: Mapping) -> dict:
    rev = session["council_revision"]
    return {k: rev[k] for k in ("upstream_repo", "upstream_rev", "protocol_mode_version")}


def _fencing_projection(session: Mapping) -> dict:
    """Record the parent task's fencing position (version + epoch) only; the
    verdict must not carry attempt-binding keys."""
    fencing = session.get("fencing", {})
    return {
        "task_version": fencing.get("task_version", 0),
        "epoch": fencing.get("epoch", 0),
    }


def run_duo_session(
    session: Mapping,
    runner: SeatRunner,
    approved_routes: set[str],
) -> dict:
    """Drive the full duo protocol offline and assemble the verdict artifact.

    Stages: route validation (fail closed) → budget reservation (pre-work,
    checked against the cost ceiling only when the session declares
    estimated_tokens) → sealed Round 1 → anonymized release → final blind
    round → weighted tally → verdict assembly. Split verdicts are preserved
    and escalated. The pre-work reservation is the only budget guard in
    this slice; observed consumption is recorded but never enforced here
    (Phase E scope).
    """
    if session.get("mode") != "duo":
        raise CouncilError("this slice implements duo mode only")
    seats = session["seats"]
    if len(seats) != 2:
        raise CouncilError(f"duo mode requires exactly 2 seats, got {len(seats)}")
    chair = session.get("chairman") or {}
    if not chair.get("excluded_from_panel") or chair.get("profile") in {s["profile"] for s in seats}:
        raise CouncilError("chairman must exist and be excluded from the duo panel")

    validate_seat_routes(session, approved_routes)
    reserve_session_budget(session)

    envelopes = sealed_envelopes(session)
    observed: dict[str, int] = {}

    # Round 1 — blind.
    round1 = [_run_seat(runner, s, envelopes[s["seat_id"]], session, envelopes, observed, 1) for s in seats]
    ok1 = {r.seat_id: r for r in round1 if r.ok}
    if len(ok1) < 2:
        return _partial_verdict(session, seats, round1, observed, "quorum_shortfall", 0)

    release = anonymized_release({sid: r.payload for sid, r in ok1.items()})

    # Final round — blind again, each seat sees the anonymized release only.
    final = [_run_seat(runner, s, release, session, envelopes, observed, 2) for s in seats]
    ok_final = {r.seat_id: r for r in final if r.ok}
    if len(ok_final) < 2:
        # Round 1 completed with full quorum; only the final round fell short.
        return _partial_verdict(session, seats, final, observed, "quorum_shortfall", 1)

    positions = {
        sid: {
            "seat_id": sid,
            "profile": next(s["profile"] for s in seats if s["seat_id"] == sid),
            "lens": next(s.get("lens") for s in seats if s["seat_id"] == sid),
            "stance": r.payload["stance"],
            "option": r.payload["option"],
            "confidence": r.payload["confidence"],
            "confidence_basis": r.payload.get("confidence_basis", "recorded by seat"),
            "known_limitations": r.payload.get("known_limitations", []),
            "evidence_labels": r.payload.get("evidence_labels", {}),
        }
        for sid, r in ok_final.items()
    }
    tally = weigh_tally(positions, list(session["decision"]["alternatives"]))
    reached = tally["carried"] is not None
    return {
        "schema_version": "noesis.council-verdict/v1",
        "session_id": session["session_id"],
        "parent_task_id": session["parent_task_id"],
        "council_revision": _revision_projection(session),
        "mode": "duo",
        "decision_question": session["decision"]["question"],
        "positions": [
            {k: v for k, v in p.items() if k not in ("option", "confidence")}
            | {"stance": p["stance"]}
            for p in positions.values()
        ],
        "tally": {k: v for k, v in tally.items() if k != "carried"},
        "consensus": {
            "reached": reached,
            "position": tally["carried"],
            "explanation": (
                f"Option '{tally['carried']}' cleared the weighted threshold."
                if reached
                else "No consensus reached: no option cleared the 2/3 weighted threshold. "
                     "Round budget spent; split escalated to the orchestrator/operator. "
                     "No extra round was run."
            ),
        },
        "acceptable_compromises": [],
        "kill_criteria": [
            {
                "condition": "seat output leak check rejects a payload the structural tests did not cover",
                "observable_by": session["decision"].get("deadline", "2026-12-05T00:00:00Z"),
                "action_on_trigger": "halt council session; revert to direct-answer workflow",
            }
        ],
        "concrete_next_step": {
            "verb": "record",
            "object": "the verdict as advisory evidence on the parent task",
            "owner": "noesis-orchestrator",
            "due": session["decision"].get("deadline", "2026-12-05T00:00:00Z"),
        },
        "unresolved_questions": [
            u for p in positions.values() for u in (p["evidence_labels"].get("UNKNOWN") or [])
        ],
        "dissent": (
            {}
            if reached
            else {
                "minority_report": (
                    "Split panel: "
                    + "; ".join(
                        f"{p['seat_id']} holds '{p['option']}'" for p in positions.values()
                    )
                ),
                "points_of_disagreement": [tally["method"]],
            }
        ),
        "synthesis_notes": (
            "Duo slice: chairman excluded by construction; no domain multiplier applied "
            "(recorded deviation from full-mode upstream protocol)."
        ),
        "usage": {
            "observed": {
                "input_tokens": observed.get("input_tokens", 0),
                "output_tokens": observed.get("output_tokens", 0),
                "duration_s": 0,
            },
            "estimated": {"input_tokens": 0, "output_tokens": 0},
            "unknown_fields": [
                f for f in ("currency value", "observed duration_s")
            ],
        },
        "session_metadata": {
            "panel_size": len(seats),
            "rounds_run": 2,
            "enforcement_breakdown": {},
            "chairman_failed_fallback": False,
            "fallbacks_triggered": [],
            "fencing": _fencing_projection(session),
            "stop_condition": None,
        },
    }


def _partial_verdict(session, seats, results, observed, stop_condition: str, rounds_completed: int) -> dict:
    """Partial panel: blocked seats reported, never silently substituted.

    rounds_completed is the number of rounds that finished with full panel
    quorum (0 when Round 1 itself fell short, 1 when only the final round
    did). positions stays empty — Round-1 outputs are not final positions
    and fabricating entries to satisfy completed-verdict minimums would be
    dishonest; the tally records null/empty to say "no tally performed".
    """
    return {
        "schema_version": "noesis.council-verdict/v1",
        "session_id": session["session_id"],
        "parent_task_id": session["parent_task_id"],
        "council_revision": _revision_projection(session),
        "mode": "duo",
        "decision_question": session["decision"]["question"],
        "positions": [],
        "tally": {
            "method": TALLY_METHOD,
            "threshold": None,
            "options": [],
            "no_option_carried": True,
        },
        "consensus": {
            "reached": False,
            "explanation": f"Partial panel ({stop_condition}); quorum floor for duo is two-of-two. "
                           "Escalated to the orchestrator/operator.",
        },
        "acceptable_compromises": [],
        "kill_criteria": [],
        "concrete_next_step": {
            "verb": "report",
            "object": "the partial panel and blocked seats to the operator",
            "owner": "noesis-orchestrator",
            "due": session["decision"].get("deadline", "2026-12-05T00:00:00Z"),
        },
        "unresolved_questions": [],
        "dissent": {},
        "synthesis_notes": "Partial panel; blocked seats: "
                           + ", ".join(f"{r.seat_id}({r.blocked_reason})" for r in results if not r.ok),
        "usage": {
            "observed": {
                "input_tokens": observed.get("input_tokens", 0),
                "output_tokens": observed.get("output_tokens", 0),
                "duration_s": 0,
            },
            "estimated": {"input_tokens": 0, "output_tokens": 0},
            "unknown_fields": ["currency value", "observed duration_s"],
        },
        "session_metadata": {
            "panel_size": len(seats),
            "rounds_run": rounds_completed,
            "enforcement_breakdown": {},
            "chairman_failed_fallback": False,
            "fallbacks_triggered": [],
            "fencing": _fencing_projection(session),
            "stop_condition": stop_condition,
        },
    }
