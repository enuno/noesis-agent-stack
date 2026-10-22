# Adaptation: k8s-yaml-validator/scripts/detect_crd_wrapper.sh

Upstream source: akin-ozer/cc-devops-skills @ `276af751e659315aaf56d3ad13d7c26f4e72e28a`,
`devops-skills-plugin/skills/k8s-yaml-validator/scripts/detect_crd_wrapper.sh`.

## Finding

When PyYAML was missing from system Python, the wrapper silently created a
temporary venv and ran `pip install --quiet pyyaml` into it with no user
prompt. Classified: unsafe-automatic-behavior (minor — scoped to a throwaway
venv, but still an unprompted network package install, same pattern flagged
in `setup_tools.sh`'s sibling validators).

## Change

Replaced the silent venv-creation-and-install path with a hard failure that
tells the user PyYAML is missing and gives the exact command to install it
themselves, then exits non-zero.

## Rationale

Matches MAINTENANCE.md: missing dependencies fail with actionable
prerequisite information rather than being silently installed. Note this
skill's own `scripts/setup_tools.sh` already behaves this way (print-only); this
change brings `detect_crd_wrapper.sh` in line with that same skill's existing
convention.

## Scope

Only `scripts/detect_crd_wrapper.sh` was touched.
