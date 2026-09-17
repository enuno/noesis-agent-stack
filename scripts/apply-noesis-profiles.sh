#!/usr/bin/env bash
# =============================================================================
# apply-noesis-profiles.sh  (ralplan T11/T12 — roster-driven rewrite)
# -----------------------------------------------------------------------------
# Applies the Noesis 16-agent profile fleet to a Hermes installation.
#
# SOURCE OF TRUTH:  profiles/noesis-roster.yaml in this repo (T12: the
#                   hardcoded ROSTER array and inline DESC vars were retired;
#                   profile mapping, wave, verified model lane, cwd, and
#                   description all derive from the roster file).
# TARGET:           HERMES_HOME (default ~/.hermes).
#
# Migration parity gates (ralplan §6 / Amendment A T12b):
#   (1) dry-run stdout byte-identical to the pre-migration script
#   (2) real-mode scratch-HOME tree identical (old inline vs new lib)
#   (3) idempotent re-apply produces an identical tree
# Rollback reference: git tag `pre-apply-common-lib` (pre-migration HEAD).
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
# =============================================================================
set -euo pipefail

# ---- defaults ---------------------------------------------------------------
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BUNDLE_SRC="${NOESIS_STACK_DIR:-$HOME/projects/noesis-agent-stack}"
MODE="wave1"          # wave1 | all
TUNE_MODELS=1
DRY=0
WANT=()               # empty = default set per MODE

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/apply-common.sh
source "$SELF_DIR/lib/apply-common.sh"

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

AC_DRY="$DRY"
[[ $TUNE_MODELS -eq 1 ]] || AC_NO_TUNE=1
# T12 fix: the pre-migration script never exported HERMES_HOME, so child
# hermes processes ignored --home (latent bug; harmless only when applying
# to the real default home). Export explicitly.
export HERMES_HOME

# ---- bundle resolution ------------------------------------------------------
BUNDLE="$(ac_resolve_bundle "$BUNDLE_SRC" "$SELF_DIR")" || {
  ac_warn "noesis bundle not found (looked in $BUNDLE_SRC and $SELF_DIR)."
  ac_warn "Expected agents/<name>/{SOUL.md,agent.yaml} and profiles/noesis-roster.yaml"
  exit 1
}

# ---- roster (name|profile|wave|model|provider|cwd) from roster yaml --------
ROSTER_FILE="$BUNDLE/profiles/noesis-roster.yaml"
[[ -f "$ROSTER_FILE" ]] || { ac_warn "missing roster: $ROSTER_FILE"; exit 1; }
mapfile -t ROSTER < <(ac_roster_rows_noesis "$ROSTER_FILE")

# descriptions from roster yaml (name -> single-line description)
declare -A DESC=()
while IFS=$'\t' read -r dname ddesc; do
  [[ -n "$dname" ]] && DESC[$dname]="$ddesc"
done < <(python3 - "$ROSTER_FILE" <<'PYEOF'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]))
for name, p in (data.get("profiles") or {}).items():
    desc = " ".join(str(p.get("description") or "").split())
    print(f"{name}\t{desc}")
PYEOF
)

# ---- main -------------------------------------------------------------------
ac_log "Noesis profile fleet installer"
ac_log "  Hermes home : $HERMES_HOME"
ac_log "  Bundle      : $BUNDLE"
ac_log "  Mode        : $MODE (${WANT[*]:+filtered to: ${WANT[*]}})"
ac_log "  Model tuning: $([ $TUNE_MODELS -eq 1 ] && echo ON || echo OFF)"
ac_log ""

[[ -x "$(command -v "$AC_PROFILE_CMD")" ]] || { ac_warn "$AC_PROFILE_CMD not on PATH; using hermes"; AC_PROFILE_CMD=hermes; }

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
  [[ -n "$row" ]] || { ac_warn "unknown profile '$name' in roster; skipping"; skipped=$((skipped+1)); continue; }

  # fields: name|profile|wave|model|provider|cwd
  IFS='|' read -r _ profile_name _ model provider cwd <<< "$row"
  desc="${DESC[$name]:-}"

  # Hermes-Core maps to the default profile
  target="$HERMES_HOME/profiles/$profile_name"
  if [[ "$profile_name" == "default" ]]; then
    target="$HERMES_HOME"
  fi

  # create if missing
  if [[ ! -d "$target" ]]; then
    ac_log "  + creating $name (profile '$profile_name')"
    args=(--description "$desc")
    [[ "$profile_name" == "default" ]] || args+=(--no-alias)
    ac_run "$AC_PROFILE_CMD" profile create "$profile_name" "${args[@]}" >/dev/null 2>&1 || {
      ac_warn "create failed for $name"; failed+=("$name"); continue; }
    # seed config + env from the new profile's home (post-create default)
    if [[ "$profile_name" != "default" ]]; then
      # copy source config/env if a source profile exists (reuse keys)
      if [[ -f "$HERMES_HOME/config.yaml" ]]; then
        ac_run cp "$HERMES_HOME/config.yaml" "$target/config.yaml" 2>/dev/null || true
        ac_run cp "$HERMES_HOME/.env" "$target/.env" 2>/dev/null || true
      fi
      created=$((created+1))
    fi
  else
    refreshed=$((refreshed+1))
    ac_log "  = exists   $name (profile '$profile_name'); refreshing SOUL"
  fi

  # SOUL.md
  if [[ -f "$BUNDLE/agents/$name/SOUL.md" ]]; then
    ac_run cp "$BUNDLE/agents/$name/SOUL.md" "$target/SOUL.md"
  else
    ac_warn "no SOUL.md for $name in bundle"
  fi

  # terminal.cwd
  ac_run "$AC_PROFILE_CMD" -p "$profile_name" config set terminal.cwd "$cwd" >/dev/null 2>&1 || true

  # model routing (verified)
  if [[ $TUNE_MODELS -eq 1 && -n "$model" && "$profile_name" != "default" ]]; then
    if ac_verify_lane "$model" "$provider" "$profile_name"; then
      ac_log "      model $model @ $provider [verified]"
      ac_run "$AC_PROFILE_CMD" -p "$profile_name" config set model.default "$model" >/dev/null 2>&1
      ac_run "$AC_PROFILE_CMD" -p "$profile_name" config set model.provider "$provider" >/dev/null 2>&1
    else
      ac_warn "lane $model@$provider failed verification; keeping current model for $name"
    fi
  fi
done

ac_log ""
ac_log "Done: created=$created refreshed=$refreshed skipped=$skipped"
[[ ${#failed[@]} -gt 0 ]] && { ac_log "Failed: ${failed[*]}"; exit 1; }
