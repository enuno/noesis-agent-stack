# catalog/
# Model catalog governance registry for the Noesis agent stack.
#
# Lifecycle (charter §Model-catalog automation):
#   Provider discovery → normalized candidate catalog → static policy validation
#   → live smoke validation → profile-specific evaluation → scorecard → reviewed PR
#   → shadow test → canary rollout → approved signed routing catalog.
#
# Rules:
#   - A discovered model is NEVER automatically routable.
#   - Candidate must pass capability, privacy, provider-policy, authentication,
#     tool/schema, safety, quality, latency, and budget validation before promotion.
#   - Shadow routing + gradual canaries for R0–R2 profile changes.
#   - NEVER auto-promote R3 model changes. Human review required for R3
#     eligibility, security-sensitive routing, privacy-policy changes,
#     provider-policy exceptions.
#   - Keep last-known-good signed configuration; roll back automatically on
#     policy/health/quality/cost/privacy regression.

# Directory layout
#   README.md          <- this file
#   discovered/        <- raw provider discovery output (OpenRouter/Venice APIs, subscription manifests)
#   candidates/        <- normalized candidate models awaiting validation
#   validated/         <- passed static + smoke validation
#   approved/          <- reviewed + shadow/canary passed; routable (signed catalog)
#   quarantined/       <- removed/blocked models with reason
#   scored/            <- per-profile evaluation scorecards
#
# Maintain per-stage files: discovered/<provider>-<date>.yaml,
# candidates/<model-id>.yaml, approved/routing-catalog.yaml (signed).

version: "1.0.0"
updated: 2026-08-19
