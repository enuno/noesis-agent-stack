"""Explicit seat credential contract for the canonical launcher.

New requirement, authored for ADR Phase D. Not a pre-existing ADR mandate.

The child discovers credentials from its process environment and from files
under ``$HERMES_HOME``. ``HermesCliAdapter._env`` copies the parent environment
and only strips a denylist of ambient inference keys. That is not an isolation
policy: undeclared parent secrets cross the seat boundary, and secrets that
exist only in a parent-side resolver never reach the isolated home.

This module does not read keyrings, ``.env`` files, or live stores. Callers
supply synthetic or already-resolved values. Presence is not validity.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

# Process necessities only. Credential names are never taken from this list.
BASELINE_ENV_NAMES = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "USER",
    "LOGNAME",
)

KNOWN_SCOPES = frozenset({"none", "api-key-env", "oauth-device-code", "synthetic-test"})
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SCOPE = re.compile(r"^[a-z]+(-[a-z]+)*$")
_CREDENTIAL_DIR = ".seat-credentials"


class CredentialUnavailable(RuntimeError):
    """Required credential missing or contract rejected. Message has no secret."""

    code = "credential_unavailable"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SeatLaunchRefused(RuntimeError):
    """Canonical launch refused or returned no honest seat verdict."""


@dataclass(frozen=True)
class SeatCredentialContract:
    """What may cross into one seat. Values are caller-supplied, never logged here."""

    scope: str
    allowed_env: tuple[str, ...] = ()
    required_env: tuple[str, ...] = ()
    values: Mapping[str, str] = field(default_factory=dict)
    files: Mapping[str, str] = field(default_factory=dict)


def validate_seat_credential_contract(contract: SeatCredentialContract) -> None:
    """Fail closed before any child process. Errors name variables, never values."""
    if not isinstance(contract, SeatCredentialContract):
        raise CredentialUnavailable("credential contract is missing or has the wrong type")
    if not isinstance(contract.scope, str) or _SCOPE.fullmatch(contract.scope) is None:
        raise CredentialUnavailable("credential scope is not a category name")
    if contract.scope not in KNOWN_SCOPES:
        raise CredentialUnavailable("credential scope is not a supported category")
    allowed = tuple(contract.allowed_env)
    required = tuple(contract.required_env)
    for name in allowed + required:
        if not isinstance(name, str) or _ENV_NAME.fullmatch(name) is None:
            raise CredentialUnavailable("credential env name is not an allowed identifier")
        if name in BASELINE_ENV_NAMES:
            raise CredentialUnavailable(f"credential env name collides with baseline env: {name}")
    if any(name not in allowed for name in required):
        raise CredentialUnavailable("required credential is not in the allowed set")
    if contract.scope == "none" and (allowed or required or contract.files):
        raise CredentialUnavailable("scope none cannot carry credentials")
    if contract.scope == "api-key-env" and not required:
        raise CredentialUnavailable("api-key-env requires at least one named credential")
    values = contract.values
    if not isinstance(values, Mapping):
        raise CredentialUnavailable("credential values must be a mapping")
    for name in allowed:
        if name not in values:
            continue
        value = values[name]
        if not isinstance(value, str) or value == "" or "\n" in value or "\x00" in value:
            raise CredentialUnavailable(f"credential value rejected: {name}")
    for name in required:
        value = values.get(name)
        if not isinstance(value, str) or value == "":
            raise CredentialUnavailable(f"required credential unavailable: {name}")
    files = contract.files
    if not isinstance(files, Mapping):
        raise CredentialUnavailable("credential files must be a mapping")
    for rel, content in files.items():
        if not isinstance(rel, str) or not isinstance(content, str):
            raise CredentialUnavailable("credential file entry rejected")
        if rel != Path(rel).name or rel in {"", ".", ".."}:
            raise CredentialUnavailable("credential file name must be a single path segment")
        if content == "" or "\x00" in content:
            raise CredentialUnavailable(f"credential file content rejected: {rel}")


def unsafe_parent_copy(parent: Mapping[str, str]) -> dict[str, str]:
    """The pre-repair behavior. Tests use this to show the leak. Production must not."""
    return dict(parent)


def build_spawn_env(
    parent: Mapping[str, str],
    contract: SeatCredentialContract,
) -> dict[str, str]:
    """Baseline process env plus explicitly allowed credential values. Nothing else."""
    validate_seat_credential_contract(contract)
    env: dict[str, str] = {}
    for name in BASELINE_ENV_NAMES:
        value = parent.get(name)
        if isinstance(value, str) and value != "" and "\n" not in value and "\x00" not in value:
            env[name] = value
    for name in contract.allowed_env:
        if name in contract.values:
            env[name] = contract.values[name]
    env["NOESIS_CREDENTIAL_SCOPE"] = contract.scope
    return env


def write_seat_credential_files(isolated_root: Path, contract: SeatCredentialContract) -> list[Path]:
    """Write declared files under the isolated home only. Mode 0600. No parent-store copy."""
    validate_seat_credential_contract(contract)
    if not contract.files:
        return []
    base = isolated_root / _CREDENTIAL_DIR
    base.mkdir(mode=0o700, exist_ok=True)
    os.chmod(base, 0o700)
    written: list[Path] = []
    for rel, content in contract.files.items():
        path = base / rel
        if path.parent != base:
            raise CredentialUnavailable("credential file escaped the seat directory")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(path, 0o600)
        written.append(path)
    return written


def remove_seat_credential_files(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
    parents = {path.parent for path in paths}
    for parent in parents:
        try:
            parent.rmdir()
        except OSError:
            continue


class HermesCouncilSeatLauncher:
    """Offline seam from a council seat callable to HermesCliAdapter.launch.

    This is not stream-json parsing and not a live provider call. A blocked
    launch raises. A stub stdout is passed through only when it is already a
    JSON object; token usage is not invented.
    """

    def __init__(
        self,
        adapter: Any,
        *,
        provider: str,
        model: str,
        credential_contract: SeatCredentialContract,
        workspace: Path,
        task_id: str,
    ) -> None:
        self.adapter = adapter
        self.provider = provider
        self.model = model
        self.credential_contract = credential_contract
        self.workspace = workspace
        self.task_id = task_id

    def __call__(self, seat: Mapping, payload: Mapping, max_output_tokens: int, round_timeout_s: float | None):
        import json

        profile_id = str(seat.get("profile") or "")
        if not profile_id or profile_id.startswith("-"):
            raise CredentialUnavailable("seat profile is missing")
        # Untrusted payload is prompt text. It does not select provider, model, or argv flags.
        prompt = json.dumps(payload, sort_keys=True)
        timeout = round_timeout_s if isinstance(round_timeout_s, (int, float)) and round_timeout_s > 0 else None
        if timeout is None:
            raise CredentialUnavailable("seat timeout is missing")
        result = self.adapter.launch(
            profile_id=profile_id,
            prompt=prompt,
            task_id=self.task_id,
            cwd=str(self.workspace),
            dry_run=False,
            provider=self.provider,
            model=self.model,
            timeout_s=timeout,
            remaining_lease_s=timeout,
            workspace=self.workspace,
            fallback_policy="deny",
            credential_contract=self.credential_contract,
        )
        if result.blocker_code == "credential_unavailable":
            detail = result.error or "required credential unavailable"
            for value in self.credential_contract.values.values():
                if isinstance(value, str) and value and value in detail:
                    detail = detail.replace(value, "[redacted]")
            raise CredentialUnavailable(detail)
        if not result.ok:
            detail = result.blocker_code or "seat launch refused"
            raise SeatLaunchRefused(detail)
        text = result.captured_stdout or ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SeatLaunchRefused("seat stdout is not a council verdict") from exc
        if not isinstance(parsed, dict) or "usage" not in parsed:
            raise SeatLaunchRefused("seat stdout has no reported usage")
        return {"text": text, "usage": parsed["usage"]}

