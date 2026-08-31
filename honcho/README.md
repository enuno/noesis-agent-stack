# Honcho module for noesis-agent-stack

This module is the canonical memory/configuration layer for Honcho-backed Noesis agents.

## Layout

- `agent-memory-profile.schema.json` — validation schema for per-agent memory profiles
- `topology.yaml` — workspace and peer namespace map
- `overlays/` — environment overlays for local, dev, stage, and prod
- `profiles/` — per-agent memory profiles for the 16 Noesis identities
- `mcp/mempalace.yaml` — Mempalace MCP policy and tool allowlist

## Verification

- run `python3 scripts/validate-honcho-profiles.py`
- run `ansible-playbook -i inventory/local/hosts.ini playbooks/honcho.yml --check`
- compare live config to the Git-tracked profile files before rotation or rollback
