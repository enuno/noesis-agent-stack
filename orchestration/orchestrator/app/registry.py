"""Roster-backed profile registry for the noesis-orchestrator control plane.

Single source of truth is profiles/noesis-roster.yaml (profile existence, tier,
toolsets) joined with agents/<profile>/agent.yaml (declared capabilities and
guardrails). Nothing here invents a profile name: an assignment naming a profile
that is not in the roster is rejected at dispatch time.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ROSTER_PATH = REPO_ROOT / "profiles" / "noesis-roster.yaml"
AGENTS_DIR = REPO_ROOT / "agents"

# Tiers that may never be handed executing work by the orchestrator.
REVIEWER_ONLY_TIERS = {"reviewer-only"}

# Profiles that supervise rather than execute. The orchestrator must not assign
# execution work to itself or to another supervisor.
SUPERVISOR_TIERS = {"supervisor"}


@dataclass(frozen=True)
class ProfileRecord:
    """A roster profile joined with its declared agent capabilities."""

    name: str
    display_name: str
    role: str
    tier: str
    toolsets: tuple[str, ...] = ()
    capabilities: frozenset[str] = field(default_factory=frozenset)
    status: str = "applied"

    @property
    def is_reviewer_only(self) -> bool:
        return self.tier in REVIEWER_ONLY_TIERS

    @property
    def is_supervisor(self) -> bool:
        return self.tier in SUPERVISOR_TIERS

    @property
    def can_execute(self) -> bool:
        """True when this profile may be assigned executing work."""
        return not (self.is_reviewer_only or self.is_supervisor)

    @property
    def has_terminal(self) -> bool:
        return "terminal" in self.toolsets or "code_execution" in self.toolsets


def _load_capabilities(profile_name: str) -> frozenset[str]:
    """Read declared capabilities from agents/<profile>/agent.yaml, if present."""
    agent_file = AGENTS_DIR / profile_name / "agent.yaml"
    if not agent_file.is_file():
        return frozenset()
    data = yaml.safe_load(agent_file.read_text(encoding="utf-8")) or {}
    caps = (data.get("agent") or {}).get("capabilities") or []
    return frozenset(str(c) for c in caps)


@functools.lru_cache(maxsize=1)
def load_registry() -> dict[str, ProfileRecord]:
    """Load and cache the roster. Cache is process-local; tests may clear it."""
    raw = yaml.safe_load(ROSTER_PATH.read_text(encoding="utf-8")) or {}
    profiles = raw.get("profiles") or {}
    registry: dict[str, ProfileRecord] = {}
    for name, spec in profiles.items():
        spec = spec or {}
        registry[name] = ProfileRecord(
            name=name,
            display_name=str(spec.get("name", name)),
            role=str(spec.get("role", "")),
            tier=str(spec.get("tier", "")),
            toolsets=tuple(spec.get("toolsets") or ()),
            capabilities=_load_capabilities(name),
            status=str(spec.get("status", "applied")),
        )
    return registry


def reset_registry_cache() -> None:
    load_registry.cache_clear()


def get_profile(name: str) -> ProfileRecord | None:
    return load_registry().get(name)


def profile_exists(name: str) -> bool:
    return name in load_registry()


def list_profiles() -> list[ProfileRecord]:
    return list(load_registry().values())


def executor_profiles() -> list[ProfileRecord]:
    return [p for p in load_registry().values() if p.can_execute]
