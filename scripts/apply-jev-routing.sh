#!/usr/bin/env bash
# =============================================================================
# apply-jev-routing.sh — install + configure the hermes-jev-routing plugin
# -----------------------------------------------------------------------------
# Installs the plugin into a Hermes profile, writes the profile's routing
# config, and wires the plugin settings block. Idempotent.
#
# SOURCE OF TRUTH:
#   platform/hermes-jev-routing.yaml     (eligibility, mode, activation gate)
#   docs/hermes-jev-routing/config/      (the tier tables)
#   shared/provider-policies.yaml        (typesafe provider policy)
#
# TARGET: HERMES_HOME (default ~/.hermes) and its per-profile homes.
#
# This script NEVER sets mode=auto. `auto` rewrites the model on the wire and
# requires explicit human approval per platform/hermes-jev-routing.yaml
# (activation.auto_requires_explicit_approval). The ceiling this script
# applies is `shadow`: the plugin loads, classifies, reports, and writes the
# spend ledger, but the model on the request is unchanged.
#
# It also NEVER writes a configuration to a profile that platform/
# hermes-jev-routing.yaml lists as ineligible.
#
# Usage:
#   ./apply-jev-routing.sh [--home DIR] [--profile NAME]... [--all]
#                          [--config FILE] [--mode shadow|notify|off]
#                          [--dry-run] [--verify-only]
# =============================================================================
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_SRC="${NOESIS_STACK_DIR:-$HOME/projects/noesis-agent-stack}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_ID="hermes-jev-routing"
PLUGIN_CATALOG="hermes-jev-routing"
PINNED_REF="06a53646587c33174a0fbfbb3713eca90bbb8586"

DRY=0
VERIFY_ONLY=0
MODE="shadow"
CONFIG=""
WANT=()
ALL=0

usage() { sed -n '2,26p' "$0"; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --home) HERMES_HOME="$2"; shift 2 ;;
    --profile) WANT+=("$2"); shift 2 ;;
    --all) ALL=1; shift ;;
    --config) CONFIG="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --verify-only) VERIFY_ONLY=1; shift ;;
    -h|--help) usage ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# The child `hermes` processes must see the selected home, or an alternate
# --home would install and configure the NORMAL home instead. This mirrors
# apply-noesis-profiles.sh, which exports it for the same reason.
export HERMES_HOME

case "$MODE" in
  shadow|notify|off) ;;
  auto) echo "refusing: mode=auto requires explicit approval (see platform/hermes-jev-routing.yaml)" >&2; exit 3 ;;
  *) echo "bad --mode '$MODE' (shadow|notify|off)" >&2; exit 2 ;;
esac

# --- profile registry (name|config file|bound provider) ----------------------
# The bound provider decides WHICH config file applies: the plugin rewrites
# the model only on the provider the turn is already bound to, so a config
# whose first tier row names a different provider never routes.
registry() {
  cat <<'EOF'
default|hermes-jev-routing.json|minimax
builder-ventures|hermes-jev-routing.codex.json|openai-codex
terrahash-intel|hermes-jev-routing.codex.json|openai-codex
EOF
}

# Profiles the policy excludes. Listed here as a guard as well as in the
# policy file, so a policy drift cannot silently widen the blast radius.
INELIGIBLE="misjustice-advocacy"

# --- helpers -----------------------------------------------------------------
say()  { printf '%s\n' "$*"; }
run()  { if [[ $DRY -eq 1 ]]; then say "  [dry-run] $*"; else "$@"; fi; }

profile_home() {
  if [[ "$1" == "default" ]]; then printf '%s' "$HERMES_HOME"; else printf '%s/profiles/%s' "$HERMES_HOME" "$1"; fi
}

hermes_for() {
  if [[ "$1" == "default" ]]; then printf 'hermes'; else printf 'hermes -p %s' "$1"; fi
}

verify_profile() {
  # Parse the STORED bytes, never the CLI's echo. Reports per key:
  # missing / extra / mismatched. Any mismatch fails the whole apply.
  local p="$1" home="$2" expect_config="$3" expect_mode="$4"
  local cfg="$home/config.yaml"
  /usr/bin/python3 - "$cfg" "$expect_config" "$expect_mode" "$p" <<'PY'
import sys, yaml
cfg_path, expect_config, expect_mode, profile = sys.argv[1:5]
try:
    cfg = yaml.safe_load(open(cfg_path)) or {}
except Exception as e:
    print(f"    FAIL {profile}: cannot parse {cfg_path}: {e}")
    raise SystemExit(1)
plugins = cfg.get("plugins") or {}
entry = (plugins.get("entries") or {}).get("hermes-jev-routing") or {}
settings = entry.get("settings") or {}
problems = []
if settings.get("config_path") != expect_config:
    problems.append(f"config_path={settings.get('config_path')!r} expected {expect_config!r}")
if settings.get("mode") != expect_mode:
    problems.append(f"mode={settings.get('mode')!r} expected {expect_mode!r}")
if "hermes-jev-routing" not in (plugins.get("enabled") or []):
    problems.append("not in plugins.enabled")
if "hermes-jev-routing" in (plugins.get("disabled") or []):
    problems.append("present in plugins.disabled")
if problems:
    for pb in problems:
        print(f"    FAIL {profile}: {pb}")
    raise SystemExit(1)
print(f"    OK   {profile}: config_path+mode+enabled all match")
PY
}

# --- target selection --------------------------------------------------------
if [[ $ALL -eq 1 ]]; then
  while IFS='|' read -r name cfgfile prov; do
    [[ -z "$name" ]] && continue
    WANT+=("$name")
  done < <(registry)
fi
if [[ ${#WANT[@]} -eq 0 ]]; then
  say "no targets selected. Use --profile NAME or --all."
  exit 2
fi

say "jev-routing apply -> HERMES_HOME=$HERMES_HOME  mode=$MODE  dry=$DRY"
say ""

rc=0
for profile in "${WANT[@]}"; do
  row="$(registry | awk -F'|' -v p="$profile" '$1==p{print; exit}')"
  [[ -z "$row" ]] && { say "  SKIP $profile: not in the registry"; continue; }
  IFS='|' read -r _name cfgfile prov <<<"$row"

  if [[ " $INELIGIBLE " == *" $profile "* ]]; then
    say "  SKIP $profile: ineligible under platform/hermes-jev-routing.yaml (data classification)"
    continue
  fi

  home="$(profile_home "$profile")"
  src_cfg="$BUNDLE_SRC/docs/hermes-jev-routing/config/$cfgfile"
  dst_cfg="$home/hermes-jev-routing.json"

  say "  == $profile (bound provider: $prov)"
  [[ -f "$src_cfg" ]] || { say "    FAIL missing source config $src_cfg"; rc=1; continue; }
  [[ -d "$home" ]] || { say "    FAIL no profile home $home"; rc=1; continue; }

  if [[ $VERIFY_ONLY -eq 1 ]]; then
    verify_profile "$profile" "$home" "$dst_cfg" "$MODE" || rc=1
    say ""
    continue
  fi

  # 1. install the plugin from the CATALOG. The catalog entry carries the
  #    pinned commit; passing --ref would bypass the catalog's own pin.
  run $(hermes_for "$profile") plugins install "$PLUGIN_CATALOG" --yes-deps --no-enable >/dev/null 2>&1 \
    || say "    WARN plugin install reported a problem; continuing to configure"

  # 1b. verify the commit that actually landed matches the pin. A mismatch
  #     (or missing metadata) means the installed revision is not the
  #     approved one, so this profile is NOT configured any further: the
  #     settings and the allow-list must not be written for a plugin
  #     revision that was just rejected.
  meta="$home/plugins/$PLUGIN_ID/.hermes-catalog.json"
  pin_ok=1
  if [[ -f "$meta" ]]; then
    got="$(/usr/bin/python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("sha",""))' "$meta")"
    if [[ "$got" != "$PINNED_REF" ]]; then
      say "    FAIL installed sha $got != pinned $PINNED_REF"
      pin_ok=0
    else
      say "    OK   pinned commit $got"
    fi
  else
    say "    FAIL no .hermes-catalog.json at $meta — cannot verify the pinned commit"
    pin_ok=0
  fi
  if [[ $pin_ok -eq 0 ]]; then
    say "    SKIP configuring $profile — the installed revision was not verified"
    rc=1
    say ""
    continue
  fi

  # 2. the routing table
  run mkdir -p "$home"
  run cp "$src_cfg" "$dst_cfg"

  # 3. the settings block, one key per call
  run $(hermes_for "$profile") config set plugins.entries.hermes-jev-routing.settings.config_path "$dst_cfg" >/dev/null
  run $(hermes_for "$profile") config set plugins.entries.hermes-jev-routing.settings.mode "$MODE" >/dev/null

  # 4. the load-time allow-list. Read it from the STORED config rather
  #    than parsing CLI output: an empty list must produce a valid
  #    singleton list, and a `grep` that selects no lines exits 1, which
  #    under `set -euo pipefail` would abort the whole apply after the
  #    settings were already written.
  new_enabled="$(/usr/bin/python3 - "$home/config.yaml" <<'PY'
import sys, yaml
try:
    cfg = yaml.safe_load(open(sys.argv[1])) or {}
except Exception:
    cfg = {}
plugins = cfg.get("plugins") or {}
enabled = list(plugins.get("enabled") or [])
if "hermes-jev-routing" not in enabled:
    enabled.append("hermes-jev-routing")
print(",".join(enabled))
PY
)"
  if [[ -n "$new_enabled" ]]; then
    run $(hermes_for "$profile") config set plugins.enabled "[$new_enabled]" >/dev/null
  fi

  # 5. verify the stored bytes
  if [[ $DRY -eq 0 ]]; then
    verify_profile "$profile" "$home" "$dst_cfg" "$MODE" || rc=1
  else
    say "    [dry-run] would verify $src_cfg against $dst_cfg (mode=$MODE)"
  fi
  say ""
done

if [[ $rc -ne 0 ]]; then
  say "RESULT: FAILED — see the per-key mismatches above."
  exit 1
fi
say "RESULT: OK"
[[ $DRY -eq 1 ]] && say "(dry run — nothing was written)"
exit 0
