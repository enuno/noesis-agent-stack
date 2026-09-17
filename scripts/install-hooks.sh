#!/usr/bin/env bash
# install-hooks.sh — wire the T16 pre-commit hook into .git/hooks (T16 / O1).
# Idempotent; refuses to clobber a foreign hook (saves it as pre-commit.local).

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_SRC="$REPO/scripts/hooks/pre-commit"
HOOK_DST="$REPO/.git/hooks/pre-commit"

cd "$REPO"

if [[ ! -d .git ]]; then
    echo "install-hooks: not a git repository root ($REPO)" >&2
    exit 1
fi

if [[ -e "$HOOK_DST" || -L "$HOOK_DST" ]]; then
    if [[ "$(readlink -f "$HOOK_DST")" == "$(readlink -f "$HOOK_SRC")" ]]; then
        echo "install-hooks: already installed"
    else
        mv "$HOOK_DST" "$HOOK_DST.local"
        echo "install-hooks: existing hook preserved as .git/hooks/pre-commit.local"
    fi
fi

ln -sf "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_SRC"

# Negative test — prove the guard fires on a planted hardcoded ROSTER.
"$HOOK_SRC" --self-test

echo "install-hooks: installed $HOOK_DST (negative test passed)"
