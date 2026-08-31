# Current Hermes profile snapshot

This directory is a sanitized snapshot of the live `~/.hermes/profiles/` tree.

Included for each profile directory:
- `config.yaml`
- `SOUL.md`

Excluded intentionally:
- `default/` (the base supervisor profile lives at `~/.hermes/` rather than a subdirectory)
- runtime state, logs, caches, auth material, databases, locks, and terminal session artifacts
- files that are not part of the long-lived profile contract

Snapshot generated from: `/home/elvis/.hermes/profiles`
