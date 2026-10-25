# Adaptation: github-actions-validator/scripts/install_tools.sh

Upstream source: akin-ozer/cc-devops-skills @ `276af751e659315aaf56d3ad13d7c26f4e72e28a`,
`devops-skills-plugin/skills/github-actions-validator/scripts/install_tools.sh`.

## Finding

The skill's own documented "Initial Setup" step runs this script, which
auto-piped two unpinned, unverified remote scripts into `bash`:
- `curl ... https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b "${TOOLS_DIR}"`
- `bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)`

Classified: unsafe-automatic-behavior — this is a textbook `curl|bash` installer
pattern reachable from the skill's own default/documented workflow, not an
edge-case doc snippet.

## Change

Both `install_act()` and `install_actionlint()` now fail with an actionable
message when the tool is missing, instructing the user to download the
installer to a local file, review it (`less`), and run it themselves. No
install step in this skill copy ever auto-pipes a remote script into a shell.

## Rationale

Matches governance/REVIEW.md category 4 (unsafe automatic behavior) and the
MAINTENANCE.md adaptation rule: missing dependencies fail with actionable
prerequisite information; prerequisites are never silently installed.

## Scope

Only `scripts/install_tools.sh` was touched. The documentation references
(`references/act_usage.md`, `references/actionlint_usage.md`) still show the
vendor's own documented one-liners as prose — these are documentation-only
(not executed by anything in this skill) and were left unchanged, matching how
the tailscale and k3s skills' own documented official installers were treated.
The skill's `act`-driven local CI execution capability itself (running workflow
steps via Docker) is unchanged — it is a legitimate operational capability that
requires the user to explicitly invoke `act`, same as before.
