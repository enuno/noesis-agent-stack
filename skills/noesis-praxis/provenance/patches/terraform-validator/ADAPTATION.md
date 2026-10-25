# Adaptation: terraform-validator/references/security_checklist.md

Upstream source: akin-ozer/cc-devops-skills @ `276af751e659315aaf56d3ad13d7c26f4e72e28a`,
`devops-skills-plugin/skills/terraform-validator/references/security_checklist.md`.

## Finding

The Trivy section documented `curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin[ v0.59.1]`
as the recommended Linux install method. This is prose documentation, never
executed by any script in the skill, but it is an unpinned, unverified
curl-pipe-to-shell one-liner that an agent reading the doc verbatim could run.
Classified: documentation/labeled-insecure-example in intent, but not
explicitly labeled as risky in the original text — adapted to be explicit.

## Change

Rewrote both occurrences to instruct downloading the installer to a file,
reviewing it, then running it explicitly — instead of showing the piped form
as the primary recommended command. Package-manager and Docker alternatives
are preserved unchanged.

## Rationale

Consistent with the same documentation-safety standard applied to the actual
scripts in other B-disposition skills in this tree: don't present a
curl|sh one-liner as the default recommended path, even in documentation.

## Scope

Only this one reference file was touched; `SKILL.md`, `scripts/install_checkov.sh`
(already consent-gated by its own `--yes`/`--force` flags, reviewed and left
unchanged), and all other reference files are installed unchanged.
