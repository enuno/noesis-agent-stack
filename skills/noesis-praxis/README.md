# noesis-praxis skill tree

Canonical, reviewed source of record for the Docker/Kubernetes/IaC/networking
skills noesis-praxis (the Hermes infrastructure-operations profile) uses.
Deployed copies under a Hermes profile's `skills/` directory (e.g.
`~/.hermes/skills/noesis-praxis/<name>/`) are read-only runtime views of a
specific commit of this tree — never edit a deployed copy directly; see
`governance/MAINTENANCE.md`.

## Layout

```
skills/noesis-praxis/
├── README.md                 # this file
├── skills/<name>/             # one reviewed, runtime-loadable skill per dir
├── governance/
│   ├── MAINTENANCE.md        # mandatory sync/commit policy — READ FIRST
│   ├── REVIEW.md             # review methodology + disposition taxonomy + log
│   └── deployment-map.yaml   # requested → upstream → repo → runtime mapping
├── provenance/
│   ├── manifest.yaml         # per-skill source, pinned commit, disposition, license
│   ├── checksums.sha256      # sha256 of every payload file under skills/
│   ├── reviews/              # longer-form review notes; also holds reference-only
│   │                         # material for reviewed-but-blocked packages (outside
│   │                         # the runtime-discoverable skills/ root)
│   └── patches/<name>/       # ADAPTATION.md per disposition-B skill: what/why
└── tests/
    └── validate_skill_tree.py   # static validation, see below
```

`governance/` and `provenance/` are **not** runtime-discoverable skill
content — only `skills/<name>/` is activated as a Hermes skill root.

## Why this convention, specifically

The repository's existing `skills/` directory is a flat, un-namespaced list
(`skills/mempalace/`, `skills/electric-sheep/`, ...) with no governance,
provenance, or test subdirectories. This tree adds an agent-scoped,
auditable convention alongside it — purely additive, no existing skill was
touched or renamed. This is a proposed repository convention, not an
existing Hermes API.

## Ansible capability set

| Skill | Role | Disposition |
|---|---|---|
| `ansible-generator` | Scaffold new playbooks/roles from templates | A (installed) |
| `ansible-validator` | — | **C (blocked, not installed)** |
| `ansible-repo-change` | Change an *existing* repo in place, safely | N (Noesis-authored) |

`ansible-generator` and `ansible-repo-change` are complementary, not redundant.
`ansible-generator` says so itself: it assumes a blank or near-blank project and
reaches for `assets/templates/`, which produces files that ignore an existing
repo's layout. `ansible-repo-change` covers the in-place case — preserving an
existing deploy path when adding an alternate one, repo-wide
`become`/`remote_user` audits, secrets-manager escrow, and honest offline
validation when a vault password is unavailable.

`ansible-validator` is deliberately absent. It was blocked (disposition C)
because its SKILL.md documents, as mandatory default behaviour, auto-`pip
install` of molecule/ansible-core/ansible-lint/yamllint and unprompted
`checkov`, followed by a real Molecule create/converge/verify/destroy cycle —
not a dry run. Use the offline set instead: `ansible-lint --offline`,
`ansible-playbook --syntax-check`, `yamllint` on non-template YAML, and
`helm lint`/`helm template` for charts. Passing those is **not** authorization to
deploy.

Behaviour fixtures for scenarios A-F live in
`tests/test_ansible_behaviour_fixtures.py`. They are **static**: they assert the
guardrails are present in the skill text. They do not drive a model and are not
evidence of live agent behaviour.

## Maintenance policy

**Every change to a skill under `skills/noesis-praxis/skills/` — update,
patch, adaptation, rename, addition, or removal — must be synchronized into
this repository and committed as a scoped Git commit before it is
considered complete.** See `governance/MAINTENANCE.md` for the full policy,
including the runtime-first exception and the blocked-commit procedure.

## Review methodology

Every skill here carries one of four dispositions (A: installed unchanged,
B: installed with a documented adaptation, C: staged and blocked — not
installed, N: Noesis-authored — not a review of third-party content, cites
official tool documentation directly). See `governance/REVIEW.md` for the
full classification scheme and the review log, and `provenance/manifest.yaml`
for the per-skill record (source, pinned commit, disposition, license,
deployed path).

## Validation

```bash
python3 tests/validate_skill_tree.py                              # static checks only
python3 tests/validate_skill_tree.py --runtime-root ~/.hermes/skills   # + drift check
python3 tests/validate_skill_tree.py --write-checksums            # regenerate checksums after a reviewed change
```

Stdlib-only; falls back to a minimal built-in manifest parser if `pyyaml`
isn't installed (install `pyyaml` for full robustness — this repo does not
assume it or install it for you).

## Known open item: runtime name-shadowing

Several of these skills share a `name:` with a skill that already existed in
the noesis-praxis Hermes profile's default/bundled skill set
(`terraform-generator`, `helm-generator`, `k8s-debug`, `k8s-yaml-generator`,
`k8s-yaml-validator`, `logql-generator`, `promql-generator`,
`cloudflare-one`). Hermes's skill loader silently shows only one skill per
name; the governed copy deployed under `noesis-praxis/<name>/` is **not**
currently independently discoverable for those 8 names — the pre-existing,
ungoverned flat copy is what's active. This matters most for
`k8s-yaml-validator` and `helm-validator`-style scripts: the pre-existing flat
copies still contain the unpatched silent dependency-install behavior fixed
in this tree's `k8s-yaml-validator` adaptation. Resolving this (retiring or
renaming the old flat copies) is a Praxis-profile configuration change beyond
"minimal changes needed to load reviewed skills" and needs separate,
explicit authorization — see the final task report for detail.
