#!/usr/bin/env bash
# =============================================================================
# apply-noesis-profiles.sh
# -----------------------------------------------------------------------------
# Applies the Noesis 16-agent profile fleet to a Hermes installation.
#
# SOURCE OF TRUTH:  ~/projects/noesis-agent-stack/ (this repo) if present, else
#                   a local bundle copied next to this script (agents/ + roster).
# TARGET:           HERMES_HOME (default ~/.hermes).
#
# Idempotent: safe to re-run. Existing profiles are NOT recreated; their SOUL.md
# and (unless --no-model-tuning) model routing are refreshed from the bundle.
#
# Model routing is VERIFIED before apply (each assigned model gets a one-shot
# smoke call). Lanes that fail are skipped with a warning and left on the
# previous/default model rather than shipping a broken profile.
#
# Usage:
#   ./apply-noesis-profiles.sh [--home DIR] [--no-model-tuning] [--all] [--profile NAME] [--dry-run]
#
#   --home DIR         Hermes home to apply into (default: $HERMES_HOME or ~/.hermes)
#   --no-model-tuning  create profiles but leave model routing at the source default
#   --all              also create/refresh staged Wave 2-3 profiles (default: Wave 1 only
#                      when run against a fresh install, to match the reference's
#                      phased deployment; pass --all to bring up the full 16)
#   --profile NAME     apply only one profile (repeatable)
#   --dry-run          print what would run, change nothing
# =============================================================================
set -euo pipefail

# ---- defaults ---------------------------------------------------------------
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BUNDLE_SRC="${NOESIS_STACK_DIR:-$HOME/projects/noesis-agent-stack}"
MODE="wave1"          # wave1 | all
TUNE_MODELS=1
DRY=0
WANT=()               # empty = default set per MODE
PROFILE_CMD="${HERMES_BIN:-hermes}"

# ---- parse args -------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --home) HERMES_HOME="$2"; shift 2 ;;
    --no-model-tuning) TUNE_MODELS=0; shift ;;
    --all) MODE="all"; shift ;;
    --profile) WANT+=("$2"); shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- bundle resolution ------------------------------------------------------
# Prefer the canonical repo; fall back to a bundled copy shipped with the script.
if [[ -d "$BUNDLE_SRC/agents" && -f "$BUNDLE_SRC/profiles/noesis-roster.yaml" ]]; then
  BUNDLE="$BUNDLE_SRC"
else
  SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -d "$SELF_DIR/agents" ]]; then BUNDLE="$SELF_DIR"; else
    echo "ERROR: noesis bundle not found (looked in $BUNDLE_SRC and $SELF_DIR)." >&2
    echo "Expected agents/<name>/{SOUL.md,agent.yaml} and profiles/noesis-roster.yaml" >&2
    exit 1
  fi
fi

# ---- roster (name|role-description|cwd|wave|model|provider) -----------------
# Mirrors profiles/noesis-roster.yaml + the VERIFIED model-routing matrix.
# Model/provider pairs below were smoke-tested on 2026-08-28:
#   kimi-k2.7-code@kimi-coding, anthropic/claude-sonnet-5@openrouter,
#   deepseek/deepseek-v4-flash@nous  (all direct OK). Direct-anthropic was stale.
ROSTER=(
  # name              wave  model                    provider      cwd
  "noesis-core|default|1|deepseek/deepseek-v4-flash|nous|."
  "noesis-steward|noesis-steward|1|kimi-k2.7-code|kimi-coding|{WS}/steward"
  "noesis-cartographer|noesis-cartographer|1|anthropic/claude-sonnet-5|openrouter|{WS}/cartographer"
  "noesis-forge|noesis-forge|1|kimi-k2.7-code|kimi-coding|{PROJECTS}"
  "noesis-sentinel|noesis-sentinel|1|anthropic/claude-sonnet-5|openrouter|{WS}/review"
  "noesis-scribe|noesis-scribe|1|deepseek/deepseek-v4-flash|nous|{WIKI}"
  "noesis-signal|noesis-signal|1|anthropic/claude-sonnet-5|openrouter|{WS}/research"
  "noesis-substrate|noesis-substrate|2|kimi-k2.7-code|kimi-coding|{TOOLS}"
  "noesis-tracer|noesis-tracer|2|anthropic/claude-sonnet-5|openrouter|{WS}/evidence"
  "noesis-ledger|noesis-ledger|2|anthropic/claude-sonnet-5|openrouter|{WS}/crypto"
  "noesis-grid|noesis-grid|2|deepseek/deepseek-v4-flash|nous|{WS}/data"
  "noesis-quill|noesis-quill|2|anthropic/claude-sonnet-5|openrouter|{WS}/writing"
  "noesis-advocate|noesis-advocate|3|anthropic/claude-sonnet-5|openrouter|{WS}/advocacy"
  "noesis-herald|noesis-herald|3|anthropic/claude-sonnet-5|openrouter|{WS}/comms"
  "noesis-architect|noesis-architect|3|anthropic/claude-sonnet-5|openrouter|{WS}/design"
  "noesis-skeptic|noesis-skeptic|3|anthropic/claude-sonnet-5|openrouter|{WS}/redteam"
)

# ---- descriptions (kept inline so the script is self-contained) -------------
DESC_noesis_core="Noesis supervisor and router (Hermes-Core). Intake tasks, classify domain and risk tier, assign the narrowest-mandate specialist, enforce approval gates; never executes domain work."
DESC_noesis_steward="Noesis chief of staff. Daily triage and prioritization across workstreams; surfaces blockers and deadline risks; delegates planning to Cartographer."
DESC_noesis_cartographer="Noesis project decomposition specialist. Turns goals into phased task graphs with dependencies, risk registers, and owner assignments; never executes."
DESC_noesis_forge="Noesis software engineering executor. Writes and modifies code, IaC, and CI/CD; never deploys to production or merges unreviewed."
DESC_noesis_sentinel="Noesis independent code/security reviewer. Reviews diffs for correctness, security, quality; reviewer-only, blocks on exposed secrets."
DESC_noesis_scribe="Noesis knowledge archivist. Structures, versions, cross-links KB entries, changelogs, indexes with provenance preserved; never originates technical content."
DESC_noesis_signal="Noesis research and synthesis specialist. Multi-source deep research with cross-validation and cited briefs."
DESC_noesis_substrate="Infrastructure and DevOps engineer. Designs and operates containers, K8s, cloud/edge, networking; no production changes without approval."
DESC_noesis_tracer="OSINT / evidence / timeline specialist. Builds verifiable timelines and evidence tables from public sources, labeled fact/allegation/inference/unknown."
DESC_noesis_ledger="Crypto, mining, and DePIN research analyst. Researches and tracks on-chain/mining/DePIN developments; never financial advice, never transactions."
DESC_noesis_grid="Data analysis and reporting. Structures, analyzes, and visualizes data into CSV/XLSX/charts/tables; never fabricates or silently interpolates."
DESC_noesis_quill="Technical writing and editing. Drafts and polishes docs, runbooks, ADRs, reports; flags technical ambiguities rather than guessing."
DESC_noesis_advocate="Legal and administrative advocacy support. Researches and drafts supporting documents; never legal advice, never external submission."
DESC_noesis_herald="Strategic comms drafter. Drafts external-facing communications with risk/tone notes; never sends autonomously."
DESC_noesis_architect="Agent and orchestration designer. Designs agent profiles, prompts, memory systems, MCP/ACP/A2A integration; never implements infra directly."
DESC_noesis_skeptic="Adversarial / red-team reviewer. Challenges outputs from other Noesis agents pre-high-stakes-use; reviewer-only, uses a distinct model ecosystem."

# ---- path token expansion ---------------------------------------------------
# Prefer the canonical workspace under $HOME; fall back to a sibling of HERMES_HOME.
WS="$HOME/projects/noesis-agent-stack/workspace"
if [[ ! -d "$WS" ]]; then
  WS="$(cd "$HERMES_HOME/.." 2>/dev/null && pwd)/projects/noesis-agent-stack/workspace"
fi
PROJECTS="$HOME/projects"
WIKI="$HOME/wiki"
TOOLS="$HOME/tools"
expand() { local s="$1"; s="${s//\{WS\}/$WS}"; s="${s//\{PROJECTS\}/$PROJECTS}"; s="${s//\{WIKI\}/$WIKI}"; s="${s//\{TOOLS\}/$TOOLS}"; echo "$s"; }

# ---- helpers ----------------------------------------------------------------
log()  { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }

profile_exists() { [[ -d "$HERMES_HOME/profiles/$1" ]]; }

# verify a model/provider lane with a real one-shot call
verify_lane() {
  local model="$1" provider="$2" name="$3"
  local out
  out=$(timeout 90 "$PROFILE_CMD" -p "$name" chat -q "Reply with exactly: LANE_OK" -Q \
        -m "$model" --provider "$provider" 2>&1 || true)
  if [[ "$out" == *LANE_OK* ]]; then return 0; fi
  return 1
}

run() {
  if [[ $DRY -eq 1 ]]; then log "  [dry-run] $*"; else "$@"; fi
}

# ---- main -------------------------------------------------------------------
log "Noesis profile fleet installer"
log "  Hermes home : $HERMES_HOME"
log "  Bundle      : $BUNDLE"
log "  Mode        : $MODE (${WANT[*]:+filtered to: ${WANT[*]}})"
log "  Model tuning: $([ $TUNE_MODELS -eq 1 ] && echo ON || echo OFF)"
log ""

[[ -x "$(command -v "$PROFILE_CMD")" ]] || { warn "$PROFILE_CMD not on PATH; using hermes"; PROFILE_CMD=hermes; }

# Determine which profiles to apply
if [[ ${#WANT[@]} -gt 0 ]]; then
  APPLY=("${WANT[@]}")
else
  APPLY=()
  for row in "${ROSTER[@]}"; do
    name="${row%%|*}"
    wave=$(echo "$row" | cut -d'|' -f3)
    if [[ "$MODE" == "all" || "$wave" == "1" ]]; then APPLY+=("$name"); fi
  done
fi

created=0; refreshed=0; skipped=0; failed=()
for name in "${APPLY[@]}"; do
  # resolve row
  row=""
  for r in "${ROSTER[@]}"; do [[ "${r%%|*}" == "$name" ]] && row="$r" && break; done
  [[ -n "$row" ]] || { warn "unknown profile '$name' in roster; skipping"; skipped=$((skipped+1)); continue; }

  # fields: name|hermes_profile|wave|model|provider|cwd
  IFS='|' read -r _ profile_name _ model provider cwd_tpl <<< "$row"
  cwd=$(expand "$cwd_tpl")
  desc_var="DESC_${name//-/_}"
  desc="${!desc_var:-}"

  # Hermes-Core maps to the default profile
  target="$HERMES_HOME/profiles/$profile_name"
  if [[ "$profile_name" == "default" ]]; then
    target="$HERMES_HOME"
  fi

  # create if missing
  if [[ ! -d "$target" ]]; then
    log "  + creating $name (profile '$profile_name')"
    args=(--description "$desc")
    [[ "$profile_name" == "default" ]] || args+=(--no-alias)
    run "$PROFILE_CMD" profile create "$profile_name" "${args[@]}" >/dev/null 2>&1 || {
      warn "create failed for $name"; failed+=("$name"); continue; }
    # seed config + env from the new profile's home (post-create default)
    if [[ "$profile_name" != "default" ]]; then
      # copy source config/env if a source profile exists (reuse keys)
      if [[ -f "$HERMES_HOME/config.yaml" ]]; then
        run cp "$HERMES_HOME/config.yaml" "$target/config.yaml" 2>/dev/null || true
        run cp "$HERMES_HOME/.env" "$target/.env" 2>/dev/null || true
      fi
      created=$((created+1))
    fi
  else
    refreshed=$((refreshed+1))
    log "  = exists   $name (profile '$profile_name'); refreshing SOUL"
  fi

  # SOUL.md
  if [[ -f "$BUNDLE/agents/$name/SOUL.md" ]]; then
    run cp "$BUNDLE/agents/$name/SOUL.md" "$target/SOUL.md"
  else
    warn "no SOUL.md for $name in bundle"
  fi

  # terminal.cwd
  run "$PROFILE_CMD" -p "$profile_name" config set terminal.cwd "$cwd" >/dev/null 2>&1 || true

  # model routing (verified)
  if [[ $TUNE_MODELS -eq 1 && -n "$model" && "$profile_name" != "default" ]]; then
    if verify_lane "$model" "$provider" "$profile_name"; then
      log "      model $model @ $provider [verified]"
      run "$PROFILE_CMD" -p "$profile_name" config set model.default "$model" >/dev/null 2>&1
      run "$PROFILE_CMD" -p "$profile_name" config set model.provider "$provider" >/dev/null 2>&1
    else
      warn "lane $model@$provider failed verification; keeping current model for $name"
    fi
  fi
done

log ""
log "Done: created=$created refreshed=$refreshed skipped=$skipped"
[[ ${#failed[@]} -gt 0 ]] && { log "Failed: ${failed[*]}"; exit 1; }
