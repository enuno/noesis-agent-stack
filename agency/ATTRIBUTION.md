# ATTRIBUTION.md — Agency Agent Catalog

Persona content in this integration is derived from **The Agency** agent
catalog:

- **Upstream:** https://github.com/msitarzewski/agency-agents
- **Pinned commit:** `ad9264e309bd5e5422c04784372d7841b1e5d604` (see `agency/SOURCE`)
- **License:** MIT (verbatim copy: `agency/LICENSE`)
- **Copyright:** (c) 2025 AgentLand Contributors

## What is used

- Agent persona documents (`<division>/<agent>.md`, frontmatter + body) are
  extracted 1:1 (byte-identical persona core) into Noesis Tier A profile
  specs by `agency/convert.py`.
- The lazy-router plugin under `agency/integrations/hermes-plugin/` is
  **generated output** of the upstream `scripts/build-hermes-plugin.py`
  (vendored per the consensus plan; regenerate, do not hand-edit).

## What is NOT used

- No upstream tooling configuration, CI, or app code is imported.
- The `strategy/` playbooks are out of scope (not agent frontmatter).
- `integrations/` and `examples/` in upstream are conversion outputs /
  samples, not source agents.

## Modification notice

Per MIT, persona bodies are reproduced with the Noesis integration contract
(appended advisory/risk/reporting block) clearly delimited after the verbatim
persona. The appended block is Noesis-original content and does not modify
the persona text itself.
