# Adaptation: bash-script-validator/scripts/shellcheck_wrapper.sh

Upstream source: akin-ozer/cc-devops-skills @ `276af751e659315aaf56d3ad13d7c26f4e72e28a`,
`devops-skills-plugin/skills/bash-script-validator/scripts/shellcheck_wrapper.sh`.

## Finding

`install_shellcheck()` silently ran `pip3 install --upgrade pip` followed by
`pip3 install shellcheck-py` into a cached venv with no user prompt whenever the
system `shellcheck` binary was absent. Classified: unsafe-automatic-behavior
(scoped to an isolated venv, not system-wide, but still an unprompted network
package install).

## Change

Replaced the silent install with a hard failure that prints the exact command the
user needs to run themselves (`pip3 install --user shellcheck-py`, or their OS
package manager) and instructs them to re-run the validator afterward. The dead
success-path lines were kept unreachable behind `if false; then ... fi` rather than
deleted, so the diff against upstream stays minimal and auditable.

## Rationale

Matches governance/MAINTENANCE.md and governance/REVIEW.md: missing dependencies
must fail with actionable prerequisite information, never silently install
anything on the user's behalf.

## Scope

Only `scripts/shellcheck_wrapper.sh` was touched. `SKILL.md`, `docs/`, `examples/`,
and the other three scripts in this skill are installed unchanged.
