# Ansible candidate review — 2026-10-22

Scope: the six candidate identifiers supplied for the Ansible skill
integration. Every one was resolved to a real GitHub repository and read at a
pinned commit through the GitHub API. Nothing was cloned; no candidate was
installed on the basis of its name, description, star count, or marketplace
listing.

## Summary

| Candidate | Repo | Pinned SHA | License | Payload | Decision |
|---|---|---|---|---|---|
| P1 ansible-roles | `vinnie357/claude-skills` | `a8152d79` | MIT (repo root) | 2 `.md` | **A — installed** |
| P2 ansible-playbook-dry-run-validator | `agentskillexchange/skills` | `5b15eb13` | MIT | 1 `.md`, **zero instructions** | **C — rejected** |
| G1 ansible | `greedychipmunk/agent-skills` | `641ae0c15` | MIT | 5 files, 16 KB | **C — rejected** |
| G2 ansible | `1mangesh1/dev-skills-collection` | `23e297e5` | **none** | multi-file | **C — rejected** |
| G3 ansible | `alisonaquinas/llm-ci-dev` | `2448f76d` | MIT | fork of G1 | **C — rejected** |
| G4 ansible-playbook | `nordz0r/skills` | `625309c3` | **none** | multi-file | **C — blocked** |

Nothing was BLOCKED for being un-retrievable — all six resolved. G4 is
*blocked* on licensing grounds, which is a different thing: its content is
readable and was read.

## Existing capability in this tree (why overlap decided most of this)

Before evaluating candidates, the tree was inventoried:

- `ansible-generator` — **already installed**, disposition A, from
  `akin-ozer/cc-devops-skills` @ `276af751`, Apache-2.0. Covers scaffolding new
  playbooks/roles from templates.
- `ansible-validator` — **already blocked**, disposition C, same upstream. Its
  SKILL.md mandates auto-`pip install` of molecule/ansible-core/ansible-lint/
  yamllint plus a real Molecule create/converge/verify/destroy cycle.
- `ansible-repo-change` — existed only as an **ungoverned runtime copy**, i.e.
  drift. Brought under governance as disposition N.

This matters: the validation gap the brief asks about was **already a known,
deliberate decision** in this tree, not an oversight. Any new "validator"
candidate had to beat a documented rejection on its merits.

## P1 — vinnie357/claude-skills : ansible-roles — ACCEPTED

- Path `plugins/tools/ansible/skills/ansible-roles`, MIT, 27★, last push 2026-10-08.
- Payload: `SKILL.md` (sha256 `dd67f1ff…`), `references/jinja2-filters.md`
  (sha256 `cf6bd9e2…`). Markdown only — no scripts, hooks, or installers.
- Safety review: no `pip install`, no `curl|sh`, no `host_key_checking = False`,
  no unprompted `become`, no deploy instruction. The single "Deploy" match is
  inside an example `galaxy_info.description` string.

**Accepted on non-overlap, which was measured rather than assumed.**
`ansible-generator` carries 2253 lines of references, but they are
*module-usage patterns* and best practices. Occurrence counts in that skill:

```
import_role     0
include_role    0
precedence      0
meta/main.yml   3
dependencies:   4
argument_specs  3
```

So role *semantics* — static `import_role` vs dynamic `include_role`,
`defaults/` vs `vars/` precedence, `meta/main.yml` dependency ordering, Jinja2
template syntax — are entirely absent from the installed generator. P1 supplies
exactly that and nothing the tree already has.

Its "Anti-fabrication" section records that its `default()` filter and `flatten`
claims were checked against a live ansible-core 2.21.2, found **inverted**, and
corrected — an epistemic practice worth preserving in a skill that makes
correctness claims.

**Known gap, accepted and mitigated.** P1 ships **no safety section at all** and
never mentions idempotency, `changed_when`, `creates`, or preferring a module
over `shell`. That discipline is supplied instead by the installed
`ansible-generator` and by `skills/ansible-repo-change`, and is asserted by
`tests/test_ansible_behaviour_fixtures.py`. P1 is accepted for role *architecture*
only, not as a safety reference.

## P2 — agentskillexchange/skills : ansible-playbook-dry-run-validator — REJECTED

Rejected on **content, not licensing** — this skill is properly MIT-licensed, and
an earlier draft of this record wrongly left its SHA and licence as
unresolved. Corrected to `5b15eb13…`, MIT.

The decisive finding is that the SKILL.md contains **zero actual instructions**.
Measured: **0 code fences, 0 occurrences of `--check`, 0 of `--syntax-check`**,
and `ansible-lint` appears only inside the description string — never as an
instruction. The body is machine-scraped from the upstream `ansible/ansible`
README. The name promises dry-run validation; the content delivers none. It
self-asserts `verification: "security_reviewed"` with no supporting artifact
plus an unverifiable `github_stars: 68364`, and the repo's own history contains
`revert: restore canonical skill files after unsafe sync`.

This is the worst failure mode in the whole set: an agent loading it would
believe validation is handled when it is not. **Nothing copied.**

## G1 — greedychipmunk/agent-skills : ansible — REJECTED

MIT and properly licensed, and its `SKILL.md` guardrails are **genuinely good**:
always `--check --diff` first, `--limit` before a full run, avoid `command`/`shell`
when an idempotent module exists, "`become: true` requires explicit approval",
never commit plaintext passwords. Worth crediting, because the rejection is not
about those.

**Rejected because the bundled reference contradicts them.**
`ansible/resources/install-and-setup.md` recommends `host_key_checking = False`
**twice**:

```
host_key_checking = False        # disable for dynamic cloud environments
- "Host key verification failed" — set `host_key_checking = False` in `ansible.cfg`
  or accept the host key manually.
```

The second is the more serious: it prescribes permanently disabling SSH host-key
verification as the routine fix for a verification failure. That is exactly the
MITM shortcut this tree's policy forbids, and it is the highest-impact finding in
the whole candidate set. Only G4 among the six sets it `True`.

Compounding: the skill is self-contradictory — it opens with "All modules are
idempotent by default", then demonstrates `shell` tasks with no `changed_when`,
including `shell: cat /etc/passwd | grep deploy` with no guard — and recommends
`groups: [sudo, docker]` and `generate_ssh_key: yes` with no authorization
framing.

> Verification note: an earlier check of mine reported 0 occurrences of
> `host_key_checking` in G1. That was **my error** — I fetched the wrong path
> (`resources/…` instead of `ansible/resources/…`) and got a 404, which I initially
> read as a clean result rather than a failed fetch. Re-fetched at the correct
> path, the two occurrences above are confirmed. Recorded because "0 found" from
> a 404 is exactly the kind of false negative that would have flipped this
> decision.

## G2 — 1mangesh1/dev-skills-collection : ansible — REJECTED

Two independent grounds:

1. **No licence.** README claims MIT, but `LICENSE` returns HTTP 404 and the
   GitHub API `license` field is `null`. Redistribution rights cannot be
   established.
2. **Unsafe content.** Recommends `host_key_checking = False` — precisely the
   routine TLS/host-key shortcut this tree's policy forbids — and unprompted
   `pip install molecule`.

## G3 — alisonaquinas/llm-ci-dev : ansible — REJECTED

Verbatim fork of G1. All four shared resource files are byte-identical by
sha256 (`command-cookbook.md` `18c584b9…`, `install-and-setup.md` `b975b5b4…`,
`inventory-and-variables.md` `77759bce…`, `playbook-patterns.md` `4ba01cc3…`);
only SKILL.md differs, by path renames. Inherits every G1 rejection and would
introduce a duplicate. Installing both would be strictly worse than either.

## G4 — nordz0r/skills : ansible-playbook — BLOCKED (licence)

**Strongest anti-unsafe content of all six**, and still not installable:

- `host_key_checking = True` — the deliberate opposite of G2
- "`--check` lies if the module doesn't support check mode (`shell` almost
  always)", plus watching for `module does not support check mode`
- "`-vvv` prints secrets. Don't paste the full log into chat."
- CI guidance: use `ANSIBLE_VAULT_PASSWORD_FILE`, **not** `--ask-vault-pass`
- An idempotency proof procedure (run twice, diff the output)

But **no licence exists anywhere** — API `license` is `null`, `/LICENSE` returns
404, and no license file appears among the 39 repo-root entries. Content must
not be vendored without redistribution rights.

Those lessons are captured Noesis-side instead, as behaviour fixtures in
`tests/test_ansible_behaviour_fixtures.py` (scenarios D and F) and as explicit
rules in `skills/ansible-repo-change/SKILL.md`. That is the permitted mechanism:
we take no G4 text, only the idea that those guards must exist.

**If the upstream author adds a licence, G4 becomes a strong candidate for a
future review.** That is recorded here so the decision can be revisited on new
evidence rather than re-litigated from memory.

## Deferred candidates

Not reviewed and not installed. None was needed: the tree's actual gaps
(role *semantics* and in-place repo change) were filled by P1 and by
Noesis-authored work. `ansible-collection-skeleton-skill` and
`ansible-playbook-template-library` would overlap `ansible-generator`;
`ilude/dotfiles:ansible` is a personal dotfiles repo; `renovate-triage` is not
Ansible. Installing any of them would add surface without a current requirement.

## Evidence standard applied to negative findings

A "pattern is absent" claim is only valid when all four gates pass:

1. retrieval succeeded (HTTP 200 / the path exists),
2. the artifact retrieved is the **intended** file (checked by frontmatter/name,
   not merely that bytes came back),
3. the inspected content is non-empty and complete enough to support the claim,
4. the search itself ran to completion.

If any gate fails, the result is **UNKNOWN** or **BLOCKED** — never "0
occurrences", "clean", or "none found".

This is not academic: it caught a real error during this review. An early check
of G1 reported zero occurrences of `host_key_checking`, because the fetch used
the wrong path (`resources/...` instead of `ansible/resources/...`) and returned
a 404 body. `grep` correctly found nothing in an error page, and that zero was
indistinguishable from a genuine absence without checking the HTTP status. The
real finding — `host_key_checking = False` twice, once as the prescribed fix for
"Host key verification failed" — was missed until it was re-fetched at the
correct path. Re-fetching changed G1's rejection basis from a weaker argument to
the highest-impact safety finding in the set.

### Re-verification of P1's negative safety claims

P1 was accepted partly on "no unsafe patterns found". That claim was re-run
under all four gates rather than trusted:

| Gate | Result |
|---|---|
| 1. retrieval | HTTP 200 for `SKILL.md` (6,898 chars) and `references/jinja2-filters.md` (7,912 chars) |
| 2. intended file | frontmatter `name: ansible-roles`, `license: MIT`; local sha256 `dd67f1ff99531b6f` matches the manifest |
| 3. non-empty/complete | 2 files, **14,810 chars scanned** |
| 4. search completed | 8 patterns, each reported individually |

All eight returned **VERIFIED-ABSENT** (0 matches): `curl|sh`, `wget|sh`, auto
`pip install`/`apt-get install`, `host_key_checking = False`, TLS/verify
disabling, unprompted `become`, and deploy-to-production instructions.

One finding is confirmed rather than merely carried: `changed_when` /
`idempotent` are **VERIFIED-ABSENT** from P1, confirming the accepted gap
recorded above.

Note on byte counts: the GitHub API reports blob *bytes*; decoded content is
fewer *characters* because the skill contains multi-byte UTF-8 (em-dashes,
arrows). That gap is expected and is not truncation — the sha256 is the
authoritative content identifier.

## Independent QA

**Not performed for this change.** A bounded subagent did the upstream
resolution and content reading, which is research, not review. No separate
reviewer inspected the resulting repository diff. The MCPJungle automation
earlier in the session did get an independent review; this skill integration
did not. Stated plainly rather than implied.