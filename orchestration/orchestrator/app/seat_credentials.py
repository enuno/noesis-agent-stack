"""Explicit seat credential contract for the canonical launcher.

New requirement, authored for ADR Phase D. Not a pre-existing ADR mandate.

The child discovers credentials from its process environment and from files
under ``$HERMES_HOME``. ``HermesCliAdapter._env`` (the profile-show
attestation child) is a baseline-name allowlist plus ``HERMES_HOME``; it does
not copy the parent environment, so undeclared parent secrets cannot cross the
seat boundary. The inference child uses ``build_spawn_env`` below.

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


class _CreatedFiles(list):
    """Paths this call created. Carries the directory fd used to create them."""

    def __init__(self) -> None:
        super().__init__()
        self.owned_directories: list = []
        self.dir_fd = -1
        self.names: list = []


def _symlink_span_rejection(isolated_root: Path, trust_root: Path | None) -> str | None:
    """Reject when a symlink lies on the span from the home up to the trust root."""
    if trust_root is None:
        return None
    home = Path(isolated_root).absolute()
    root = Path(trust_root).absolute()
    if root.is_symlink() or not root.is_dir():
        return "credential trust root is not a real directory"
    if home == root or root not in home.parents:
        return "credential trust root does not contain the seat home"
    cursor = home
    while cursor != root:
        if cursor.is_symlink():
            return "seat home path crosses a symlinked ancestor"
        parent = cursor.parent
        if parent == cursor:
            return "credential trust root does not contain the seat home"
        cursor = parent
    return None


def write_seat_credential_files(
    isolated_root: Path,
    contract: SeatCredentialContract,
    *,
    trust_root: Path | None = None,
) -> list[Path]:
    """Write declared files under the isolated home only. Mode 0600.

    Boundary. At or below isolated_root nothing may be a symlink: the home,
    the credential directory, and each file open fail closed through
    O_NOFOLLOW, so a rename cannot swap a symlink between check and open.
    A caller-supplied trust_root extends the no-symlink span upward to that
    root, refusing a symlinked ancestor that relocates the home into another
    tree. Ancestors above trust_root are caller scope: on this platform /var
    is a symlink, so a full ancestor walk requires a real trust root and is
    not claimed here. None of this is a race-free claim after return.

    Ownership. Only files this call created are rolled back, recorded before
    the write so a write failure cannot orphan them. A directory is removed
    only if this call created it and rollback leaves it empty. Cleanup
    failures are reported, never silently swallowed, and never mask the
    primary failure.
    """
    validate_seat_credential_contract(contract)
    created = _CreatedFiles()
    if not contract.files:
        return created
    if not isolated_root.is_dir() or isolated_root.is_symlink():
        raise CredentialUnavailable("isolated home is not a real directory")
    span_rejection = _symlink_span_rejection(Path(isolated_root), trust_root)
    if span_rejection:
        raise CredentialUnavailable(span_rejection)
    root_fd = -1
    base_fd = -1
    primary: BaseException | None = None
    try:
        root_fd = os.open(isolated_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            base_fd = os.open(_CREDENTIAL_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        except FileNotFoundError:
            os.mkdir(_CREDENTIAL_DIR, 0o700, dir_fd=root_fd)
            created.owned_directories = [Path(isolated_root) / _CREDENTIAL_DIR]
            base_fd = os.open(_CREDENTIAL_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        except OSError:
            raise CredentialUnavailable("credential directory is a symlink or not a real directory") from None
        try:
            os.fchmod(base_fd, 0o700)
        except OSError:
            raise CredentialUnavailable("credential directory permissions refused") from None
        for rel, content in contract.files.items():
            payload = content.encode("utf-8")
            path = Path(isolated_root) / _CREDENTIAL_DIR / rel
            fd = -1
            try:
                fd = os.open(rel, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=base_fd)
            except FileExistsError:
                raise CredentialUnavailable("credential file already exists") from None
            except OSError:
                raise CredentialUnavailable("credential file is not creatable in the seat directory") from None
            created.append(path)
            created.names.append(rel)
            try:
                written_n = os.write(fd, payload)
            finally:
                os.close(fd)
            if written_n != len(payload):
                raise CredentialUnavailable("credential file write was short")
        created.dir_fd = base_fd
        base_fd = -1
    except BaseException as exc:
        primary = exc
        if not isinstance(exc, CredentialUnavailable):
            raise CredentialUnavailable(type(exc).__name__) from exc
        raise
    finally:
        if primary is not None and getattr(created, "dir_fd", -1) < 0 and base_fd >= 0:
            created.dir_fd = base_fd
            base_fd = -1
        for fd in (base_fd, root_fd):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
        if primary is not None:
            notes = remove_seat_credential_files(created, owned_directories=created.owned_directories)
            if notes:
                detail = str(primary) if isinstance(primary, CredentialUnavailable) else type(primary).__name__
                for value in contract.values.values():
                    if isinstance(value, str) and value:
                        detail = detail.replace(value, "[redacted]")
                raise CredentialUnavailable(f"{detail} (cleanup_failed)") from primary
    return created


def remove_seat_credential_files(paths: list[Path], owned_directories: list | None = None) -> list[str]:
    """Remove only artifacts this attempt owns. Returns cleanup failure notes.

    When the creator kept the credential-directory fd, unlink by name through
    that fd. A later replacement of the pathname does not redirect cleanup.
    """
    if owned_directories is None:
        owned_directories = list(getattr(paths, "owned_directories", []))
    notes: list[str] = []
    dir_fd = getattr(paths, "dir_fd", -1)
    names = list(getattr(paths, "names", []))
    if isinstance(dir_fd, int) and dir_fd >= 0 and names:
        for name in names:
            try:
                os.unlink(name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
            except OSError:
                notes.append("unlink_failed")
        try:
            os.close(dir_fd)
        except OSError:
            notes.append("dir_fd_close_failed")
        try:
            setattr(paths, "dir_fd", -1)
        except AttributeError:
            pass
    else:
        for path in list(paths):
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                notes.append("unlink_failed")
    for directory in owned_directories:
        directory = Path(directory)
        if directory.is_symlink():
            notes.append("owned_directory_symlink")
            continue
        try:
            directory.rmdir()
        except FileNotFoundError:
            pass
        except OSError:
            notes.append("rmdir_failed")
    return notes


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
        self._round_counts: dict[str, int] = {}

    def attempt_key(self, seat_id: str, round_n: int) -> str:
        """Traceable attempt id. Not a random bypass of budget closure."""
        return f"{self.task_id}|{seat_id}|round-{round_n}|attempt-1"

    def __call__(self, seat: Mapping, payload: Mapping, max_output_tokens: int, round_timeout_s: float | None):
        import json

        profile_id = str(seat.get("profile") or "")
        seat_id = str(seat.get("seat_id") or "")
        if not profile_id or profile_id.startswith("-"):
            raise CredentialUnavailable("seat profile is missing")
        if not seat_id or seat_id.startswith("-"):
            raise CredentialUnavailable("seat id is missing")
        explicit_round = seat.get("round")
        if isinstance(explicit_round, bool) or not isinstance(explicit_round, int) or explicit_round <= 0:
            raise CredentialUnavailable("seat round is not a positive integer")
        round_n = explicit_round
        # Untrusted payload is prompt text. It does not select provider, model, or argv flags.
        prompt = json.dumps(payload, sort_keys=True)
        timeout = round_timeout_s if isinstance(round_timeout_s, (int, float)) and round_timeout_s > 0 else None
        if timeout is None:
            raise CredentialUnavailable("seat timeout is missing")
        epoch = seat.get("assignment_epoch", 0)
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise CredentialUnavailable("assignment epoch is not a non-negative integer")
        result = self.adapter.launch(
            profile_id=profile_id,
            prompt=prompt,
            task_id=self.task_id,
            budget_attempt_id=self.attempt_key(seat_id, round_n),
            cwd=str(self.workspace),
            dry_run=False,
            provider=self.provider,
            model=self.model,
            timeout_s=timeout,
            remaining_lease_s=timeout,
            workspace=self.workspace,
            fallback_policy="deny",
            credential_contract=self.credential_contract,
            max_output_tokens=max_output_tokens,
            assignment_epoch=epoch,
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
        usage = parsed.get("usage") if isinstance(parsed, dict) else None
        output_tokens = usage.get("output_tokens") if isinstance(usage, dict) else None
        if (
            not isinstance(parsed, dict)
            or not isinstance(parsed.get("text"), str)
            or not isinstance(output_tokens, int)
            or isinstance(output_tokens, bool)
            or output_tokens < 0
        ):
            raise SeatLaunchRefused("seat stdout has no council verdict text or reported usage")
        return {"text": parsed["text"], "usage": usage}
