# Adaptation: helm-validator/scripts/detect_crd_wrapper.sh

Upstream source: akin-ozer/cc-devops-skills @ `276af751e659315aaf56d3ad13d7c26f4e72e28a`,
`devops-skills-plugin/skills/helm-validator/scripts/detect_crd_wrapper.sh`.

## Finding

Identical pattern to k8s-yaml-validator's wrapper of the same name: when
PyYAML was missing, the script silently created a temp venv and ran
`pip install --quiet --disable-pip-version-check pyyaml` with no prompt.
Classified: unsafe-automatic-behavior (minor).

## Change

Replaced the silent venv-creation-and-install path with a hard failure that
tells the user PyYAML is missing and gives the exact command to install it
themselves, then exits non-zero.

## Rationale

Matches MAINTENANCE.md: missing dependencies fail with actionable
prerequisite information. Brings this script in line with this same skill's
own `scripts/setup_tools.sh`, which was verified (by direct read) to already
only print installation suggestions rather than auto-install anything — the
skill's own "read-only by default" claim in `SKILL.md` line 12 now holds for
this script too.

## Scope

Only `scripts/detect_crd_wrapper.sh` was touched.
