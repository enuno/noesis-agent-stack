"""Synthetic PROCESS seam for the council canary qualification harness.

SyntheticSeatProcessLauncher implements the governed dispatch adapter's
launcher callable contract (app.council_dispatch.CouncilSeatDispatch):

    launcher(seat, payload, max_output_tokens, round_timeout_s)
        -> {"text": str, "usage": {...}}

across a real process boundary: it spawns tests.fixtures.council_canary's
fake_seat.py under sys.executable (no provider credentials, no network, no
external inference). Every call spawns the child in its OWN PROCESS GROUP
(start_new_session=True, i.e. os.setsid on POSIX) so that a round-timeout
kill (os.killpg SIGKILL, with a proc.kill() fallback) takes down the whole
group — including any descendant the seat spawned.

Behavioral contract:
- Records one event per SPAWN in self.events (seat_id, profile,
  inference_route, scenario, max_output_tokens, round_timeout_s, pid, pgid,
  outcome) for assertions.
- The scenario comes from an injectable per-seat mapping (seat_scenarios,
  seat_id -> scenario name); seats not present default to "normal".
- round_timeout_s expiry: kill the process group, record outcome "timeout",
  reap the child, raise SeamTimeout (carrying pgid and output tails).
- Non-zero child exit: raise SeamChildError carrying rc and captured
  stdout/stderr tails.
- Child stdout that is not a parseable JSON envelope is passed through as
  {"text": <raw stdout>} with NO usage key, so the ADAPTER refuses it with
  its typed MalformedLauncherResult — the seam never invents zeros.
- threading.Event self.cancelled is checked BEFORE spawning: if set, raise
  SeamCancelled without recording an event or starting a process.
- No blind retry: exactly one spawn per call; every outcome is terminal.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Mapping, Optional

_FAKE_SEAT = Path(__file__).resolve().with_name("fake_seat.py")

_TAIL_CHARS = 2000


class SeamTimeout(Exception):
    """round_timeout_s expired; the child's whole process group was SIGKILLed.

    Carries the killed process group id and captured output tails so callers
    can prove the group is gone (and, for the descendant scenario, identify
    the grandchild that must also be dead).
    """

    def __init__(
        self,
        message: str,
        *,
        seat_id: Optional[str] = None,
        scenario: Optional[str] = None,
        pgid: Optional[int] = None,
        stdout_tail: str = "",
        stderr_tail: str = "",
    ):
        super().__init__(message)
        self.seat_id = seat_id
        self.scenario = scenario
        self.pgid = pgid
        self.stdout_tail = stdout_tail
        self.stderr_tail = stderr_tail


class SeamChildError(Exception):
    """The seat child exited non-zero; carries rc and captured output tails."""

    def __init__(
        self,
        message: str,
        *,
        rc: Optional[int] = None,
        stdout_tail: str = "",
        stderr_tail: str = "",
    ):
        super().__init__(message)
        self.rc = rc
        self.stdout_tail = stdout_tail
        self.stderr_tail = stderr_tail


class SeamCancelled(Exception):
    """The seam's cancelled event was set before spawn; no process started."""


def _tail(text: str) -> str:
    return (text or "")[-_TAIL_CHARS:]


class SyntheticSeatProcessLauncher:
    """Process-backed launcher for the offline canary qualification harness.

    Callable shape matches the adapter contract exactly:
    launcher(seat, payload, max_output_tokens, round_timeout_s).
    """

    def __init__(self, seat_scenarios: Optional[Mapping[str, str]] = None):
        self.seat_scenarios = dict(seat_scenarios or {})
        self.events: list[dict] = []
        self.cancelled = threading.Event()

    def _kill_group(self, proc: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return
        except OSError:
            pass
        try:
            proc.kill()
        except OSError:
            pass

    def __call__(
        self,
        seat: Mapping,
        payload: Mapping,
        max_output_tokens: int,
        round_timeout_s: Optional[float],
    ) -> Mapping:
        if self.cancelled.is_set():
            raise SeamCancelled(
                f"seat '{seat.get('seat_id')}' launch cancelled before spawn; "
                "no process was started"
            )
        seat_id = seat["seat_id"]
        scenario = self.seat_scenarios.get(seat_id, "normal")
        cmd = [sys.executable, str(_FAKE_SEAT), "--scenario", scenario]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Own session/process group on POSIX (os.setsid semantics) so a
            # timeout kill reaches every descendant of the seat child.
            start_new_session=True,
            text=True,
        )
        event = {
            "seat_id": seat_id,
            "profile": seat.get("profile"),
            "inference_route": seat.get("inference_route"),
            "scenario": scenario,
            "max_output_tokens": max_output_tokens,
            "round_timeout_s": round_timeout_s,
            "pid": proc.pid,
            "pgid": os.getpgid(proc.pid),
        }
        self.events.append(event)
        try:
            stdout, stderr = proc.communicate(timeout=round_timeout_s)
        except subprocess.TimeoutExpired:
            self._kill_group(proc)
            stdout, stderr = proc.communicate()
            event["outcome"] = "timeout"
            raise SeamTimeout(
                f"seat '{seat_id}' scenario '{scenario}' exceeded "
                f"round_timeout_s={round_timeout_s}; process group "
                f"{event['pgid']} was SIGKILLed",
                seat_id=seat_id,
                scenario=scenario,
                pgid=event["pgid"],
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
            )
        if proc.returncode != 0:
            event["outcome"] = "child_error"
            raise SeamChildError(
                f"seat '{seat_id}' scenario '{scenario}' child exited "
                f"rc={proc.returncode}",
                rc=proc.returncode,
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
            )
        event["outcome"] = "ok"
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            envelope = None
        if not isinstance(envelope, dict):
            # Unparseable envelope (child exit 0 but stdout is not the
            # expected JSON object): pass the raw stdout through as text with
            # NO usage key so the adapter refuses it with its typed
            # MalformedLauncherResult — the seam never invents zeros.
            return {"text": stdout}
        return envelope
