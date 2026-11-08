"""Synthetic council seat executable for the offline canary qualification harness.

Spawned by tests.fixtures.council_canary.synthetic_seam across a real PROCESS
boundary (sys.executable, no provider credentials, no network, no external
inference). Stdout is exactly one JSON object for every scenario — the
"envelope" the seam parses — except where a scenario deliberately violates
that (``nonzero`` prints a partial envelope; ``malformed`` prints non-JSON).
All diagnostics go to stderr only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

# Seat position for the duo fixture question (alternatives "A"/"B").
# Shape confirmed against app.council._parse_seat_output (read BEFORE writing):
# top-level "option" (must be one of the session alternatives), "stance"
# (truthy string), "confidence" (one of "high"/"med"/"low" — the engine's
# CONFIDENCE_WEIGHTS vocabulary, NOT a float); extra keys are tolerated by the
# engine. "rationale": "synthetic" and "minority": null honor the harness
# contract flavor. The stance text must never contain a peer seat_id or a
# profile name (engine leak check).
SEAT_POSITION = {
    "option": "A",
    "stance": "Synthetic seat favors option A for the canary question.",
    "confidence": "high",
    "confidence_basis": "synthetic canary fixture",
    "known_limitations": ["synthetic process boundary; no inference performed"],
    "evidence_labels": {"UNKNOWN": []},
    "rationale": "synthetic",
    "minority": None,
}

NORMAL_USAGE = {
    "output_tokens": 100,
    "input_tokens": 50,
    "cache_read_tokens": 20,
    "cache_write_tokens": 0,
}

_PARTIAL_ENVELOPE = '{"text": "partial synthetic envelope", "usage": {'


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _normal_envelope(usage: dict | None = None) -> dict:
    return {
        "text": json.dumps(SEAT_POSITION),
        "usage": dict(NORMAL_USAGE if usage is None else usage),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="synthetic council seat")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--sleep", type=float, default=30.0)
    args = parser.parse_args(argv)

    if args.scenario == "normal":
        _emit(_normal_envelope())
        return 0
    if args.scenario == "nonzero":
        # Partial envelope + non-zero exit: the seam must surface a typed
        # child error carrying the rc, never a parse attempt on partial JSON.
        sys.stdout.write(_PARTIAL_ENVELOPE)
        sys.stdout.flush()
        return 3
    if args.scenario == "malformed":
        sys.stdout.write("this is not json <<synthetic-malformed>>\n")
        sys.stdout.flush()
        return 0
    if args.scenario == "missing_usage":
        _emit({"text": json.dumps(SEAT_POSITION)})
        return 0
    if args.scenario == "zero_output_tokens":
        _emit(_normal_envelope(usage={"output_tokens": 0}))
        return 0
    if args.scenario == "partial_usage":
        # output_tokens reported; optional fields omitted (Q11: unknown stays
        # unknown — the adapter must record None, never invented zeros).
        _emit(_normal_envelope(usage={"output_tokens": 100}))
        return 0
    if args.scenario == "invalid_position":
        # Envelope + usage are well formed; the TEXT is valid JSON but not a
        # valid seat position, so the ENGINE blocks the seat
        # (MalformedSeatOutput -> quorum_shortfall partial verdict).
        _emit(_normal_envelope() | {"text": json.dumps({"note": "no position taken"})})
        return 0
    if args.scenario == "timeout":
        time.sleep(args.sleep)
        _emit(_normal_envelope())
        return 0
    if args.scenario == "descendant":
        # Spawn a grandchild in the SAME process group, report its pid on
        # stderr, then sleep long enough for the seam's round timeout to
        # fire: killpg must take down the whole group, grandchild included.
        # Stay in this process group so killpg reaches the grandchild, but do
        # not inherit the seat's stdout/stderr pipes. An inherited pipe makes
        # the seam's communicate() wait until the grandchild's own sleep ends,
        # so a missing group-kill looks like a slow success.
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        sys.stderr.write(f"grandchild_pid={child.pid}\n")
        sys.stderr.flush()
        time.sleep(args.sleep)
        _emit(_normal_envelope())
        return 0
    sys.stderr.write(f"unknown scenario {args.scenario!r}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
