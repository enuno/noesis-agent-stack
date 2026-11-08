"""Council seat dispatch adapter — Phase E Slice A (offline implementation).

CouncilSeatDispatch is the governed SeatRunner seam promised by
app.council: the offline engine drives the duo protocol and calls back into
this adapter per seat round; the adapter owns the runtime-adjacent duties
that must NEVER live inside the engine:

- Admission before any seat work is reserved: a missing/non-positive
  cost-ceiling estimate, a seat route outside the operator allowlist, or a
  missing fencing token (when fencing is declared required) refuses with a
  dedicated AdmissionError. Fail closed; never treat a missing estimate as
  unbounded.
- Per-round revocation: an injected ``execution_revoked`` callable and the
  adapter's own ``abort()`` flag are honored before every launcher call.
  A revoked round raises RevokedError and makes NO launcher call; on abort
  mid-session ``run()`` converts the raised RevokedError into the schema-valid
  partial verdict with stop_condition "operator_cancel" (the engine's own
  partial-verdict shape), and reports usage for the rounds that did complete.
- Honest usage mapping: the injected launcher reports what it reported.
  Fields it did not report stay None in the adapter's records and in the
  observer calls — zeros are never invented.

The launcher itself is injected and out of scope for this slice: it is any
callable ``launcher(seat, payload, max_output_tokens, round_timeout_s)`` ->
``{"text": <json str>, "usage": {...}}`` where usage MUST carry
``output_tokens`` and MAY carry ``input_tokens``, ``cache_read_tokens``,
``cache_write_tokens``.

Still deliberately NOT a dispatch path: no provider calls, no subprocess,
no ledger mutation, no network. Consumption enforcement against the cost
ceiling remains a separately authorized concern and is not implemented here.
"""

from __future__ import annotations

from typing import Callable, Mapping, Optional

from app.council import (
    CouncilError,
    SeatUsage,
    _partial_verdict,
    run_duo_session,
)


class AdmissionError(CouncilError):
    """Session refused before any seat work was reserved (fail closed)."""


class RevokedError(CouncilError):
    """Execution was revoked or aborted; no launcher call was made."""


class MalformedLauncherResult(CouncilError):
    """The injected launcher returned a result the adapter cannot map honestly."""


class CouncilSeatDispatch:
    """Governed SeatRunner adapting the offline council engine to dispatch.

    Constructor admission gate (raises AdmissionError):
      * limits.cost_ceiling.estimated_tokens absent or <= 0;
      * any seat inference_route not in ``allowed_routes`` (fail closed,
        including an empty allowlist);
      * fencing token (fencing.attempt_id) absent/empty when
        ``fencing_required`` is True.

    ``observer`` optionally exposes
    ``observe_budget(task_id, requests=, output_tokens=, input_tokens=,
    cache_read_tokens=, cache_write_tokens=)``; it is called once per
    completed seat round after the engine returns (or after a mid-session
    abort), with unreported fields passed as None.
    """

    def __init__(
        self,
        session: Mapping,
        launcher: Callable,
        *,
        allowed_routes: set[str],
        observer: Optional[object] = None,
        execution_revoked: Optional[Callable[[], bool]] = None,
        parent_task_id: Optional[str] = None,
        fencing_required: bool = False,
    ):
        if not callable(launcher):
            raise AdmissionError("launcher must be a callable")
        self.session = session
        self.launcher = launcher
        self.allowed_routes = set(allowed_routes)
        self.observer = observer
        self.execution_revoked = execution_revoked
        self.parent_task_id = parent_task_id or session.get("parent_task_id", "")
        self._aborted = False
        self.calls: list[dict] = []
        self._seats = {s["seat_id"]: s for s in session.get("seats", [])}
        self._admission_checks(fencing_required=fencing_required)

    def _admission_checks(self, *, fencing_required: bool) -> None:
        limits = self.session.get("limits", {})
        ceiling = limits.get("cost_ceiling", {})
        estimate = ceiling.get("estimated_tokens")
        if estimate is None or int(estimate) <= 0:
            raise AdmissionError(
                "cost ceiling estimated_tokens is absent or non-positive "
                f"({estimate!r}); a missing estimate is never treated as unbounded"
            )
        for seat in self.session.get("seats", []):
            route = (seat.get("inference_route") or "").strip()
            if route not in self.allowed_routes:
                raise AdmissionError(
                    f"seat '{seat.get('seat_id')}' route '{route or '<empty>'}' is not "
                    f"in the approved allowlist {sorted(self.allowed_routes)}"
                )
        if fencing_required:
            fencing = self.session.get("fencing", {})
            token = (fencing.get("attempt_id") or "").strip()
            if not token:
                raise AdmissionError(
                    "fencing is declared required but the fencing token "
                    "(fencing.attempt_id) is absent or empty"
                )

    @property
    def dispatch_count(self) -> int:
        """Number of launcher calls actually dispatched (none after abort)."""
        return len(self.calls)

    def abort(self) -> None:
        """Cancel the session: every subsequent run_round raises RevokedError."""
        self._aborted = True

    def _revoked(self) -> bool:
        if self._aborted:
            return True
        if self.execution_revoked is not None and self.execution_revoked():
            return True
        return False

    def run_round(
        self, seat_id: str, payload: Mapping, budget: Mapping
    ) -> tuple[str, SeatUsage]:
        if self._revoked():
            raise RevokedError(
                f"seat '{seat_id}' round refused: execution revoked or aborted; "
                "no launcher call was made"
            )
        seat = self._seats.get(seat_id)
        if seat is None:
            raise CouncilError(f"unknown seat '{seat_id}' in council session")
        result = self.launcher(
            seat,
            payload,
            budget["max_output_tokens"],
            budget.get("round_timeout_s"),
        )
        if not isinstance(result, Mapping) or "text" not in result:
            raise MalformedLauncherResult(
                "launcher must return a mapping with a 'text' field"
            )
        usage = result.get("usage") or {}
        if "output_tokens" not in usage:
            raise MalformedLauncherResult(
                "launcher usage must report output_tokens; refusing to invent zeros"
            )
        text = result["text"]
        record = {
            "seat_id": seat_id,
            "output_tokens": usage["output_tokens"],
            "input_tokens": usage.get("input_tokens"),
            "cache_read_tokens": usage.get("cache_read_tokens"),
            "cache_write_tokens": usage.get("cache_write_tokens"),
        }
        self.calls.append(record)
        # SeatUsage is int-typed (its own defaults are 0); fields the launcher
        # did not report fall back to SeatUsage's defaults, while the adapter's
        # records and observer calls keep them honestly None.
        seat_usage = SeatUsage(
            input_tokens=record["input_tokens"]
            if record["input_tokens"] is not None else 0,
            output_tokens=record["output_tokens"],
        )
        return text, seat_usage

    def _report_usage(self) -> None:
        if self.observer is None:
            return
        observe = getattr(self.observer, "observe_budget", None)
        if not callable(observe):
            raise CouncilError("observer must expose observe_budget(...)")
        for call in self.calls:
            observe(
                self.parent_task_id,
                requests=1,
                output_tokens=call["output_tokens"],
                input_tokens=call["input_tokens"],
                cache_read_tokens=call["cache_read_tokens"],
                cache_write_tokens=call["cache_write_tokens"],
            )

    def _completed_rounds(self) -> int:
        """Rounds that finished with full panel quorum (min per-seat dispatch)."""
        if not self._seats:
            return 0
        per_seat = {}
        for call in self.calls:
            per_seat[call["seat_id"]] = per_seat.get(call["seat_id"], 0) + 1
        return min(per_seat.get(sid, 0) for sid in self._seats)

    def run(self, allowed_routes: set[str]) -> dict:
        """Convenience: drive the offline engine with this adapter as runner.

        After the engine returns, report observed usage to the observer.
        On RevokedError (abort/revocation mid-session) convert to the engine's
        partial-verdict shape with stop_condition "operator_cancel" — no
        further launcher calls happen after abort, by construction of
        run_round. Usage for completed rounds is reported on both paths.
        """
        try:
            verdict = run_duo_session(self.session, self, allowed_routes)
        except RevokedError:
            self._report_usage()
            observed = {
                "input_tokens": sum(c["input_tokens"] or 0 for c in self.calls),
                "output_tokens": sum(c["output_tokens"] or 0 for c in self.calls),
            }
            return _partial_verdict(
                self.session,
                list(self.session.get("seats", [])),
                [],
                observed,
                "operator_cancel",
                self._completed_rounds(),
            )
        self._report_usage()
        return verdict
