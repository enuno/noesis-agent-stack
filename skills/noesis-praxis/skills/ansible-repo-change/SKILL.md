---
name: ansible-repo-change
description: Change an existing Ansible repo in place, safely.
license: MIT
metadata:
  hermes:
    tags: [ansible, infrastructure-as-code, secrets, helm]
    related_skills: [ansible-generator, helm-validator, terraform-validator]
---

# Ansible Repo Change

Changing Ansible code that **already runs somewhere**. The defining constraint is
that someone else's working setup is one careless edit away from breaking, so
every stage is about not being that person.

## When to Use

- The target is a repo with existing roles, conventions, and deployed state.
- Adding a second way to do something the repo already does.
- Wiring a secrets manager, collection, or chart into an existing role.
- A repo-wide audit (privilege, remote user, version pinning) across many plays.
- Any change where a re-run must not damage what is already running.

Do **not** use for greenfield scaffolding from templates — that is
`ansible-generator`. Do not scaffold into a repo that already has conventions.

Triggers: "add a Helm/Kubernetes install method next to our existing Docker one",
"wire Bitwarden/Vault into this role", "audit every playbook for become /
remote user", "update the chart this role deploys".

## Stage 0 — Read the repo before writing a line

The repo's own instructions outrank any generic pattern.

1. `AGENTS.md` / `CLAUDE.md` / `README.md` — layout rules, role shape, naming.
2. `git status --porcelain` — **if the tree is dirty, that is someone else's work.
   Do not reset, stash, or clean it.** Note it and stay out of those files.
3. Existing sibling roles/playbooks. **Mirror them.** A new role that looks nothing
   like its neighbours is a review failure even if it works.
4. Does a role for this already exist? Extending beats parallel-building.

## Stage 1 — Extend, never replace

When adding a second way to do something the repo already does:

- Keep the original path byte-for-byte in behaviour; move it to its own task file
  if needed, then dispatch on an explicit variable.
- Default the selector variable to the **existing** method so every current caller
  is unaffected.
- Leave genuinely pre-existing defects alone unless asked. Renaming a shared var to
  satisfy a linter can break the path you were not asked to touch.

```yaml
mcpjungle_deploy_method: "docker"      # existing path stays the default
```

## Stage 2 — Targeting, privilege, and remote user

When asked to standardise `become` / `remote_user`, or to point a play at a host:

1. **Verify the premise from the system, not from memory.** Read the real sudoers
   grant (`sudo cat /etc/sudoers.d/<user>`) before asserting passwordless sudo.
2. Scope by target. `remote_user` must **not** be applied to hosts that are a
   different machine or a different account — a remote macOS box whose login is a
   different user will break.
3. Leave deliberate `become: false` alone; it is a decision, not an omission.
4. Make the user overridable via one variable so it is auditable in one place
   rather than hardcoded 40 times.
5. Note the side effect: with `remote_user` set, tasks run as that user and may no
   longer be able to **write** files owned by the invoking user in the repo.

Bulk-edit plays programmatically, then review the diff — do not hand-edit dozens of
files.

### Inventory host entries

0. **Resolve the target explicitly, or stop.** Before running anything, establish
   the concrete host scope: which inventory, which group, which hosts, which
   context. Never default to `all`, never default to the ambient current
   `kubectl` context, and never let a missing `-i` silently widen the blast
   radius. If the target cannot be resolved from what the user said, stop and ask
   — do not pick the most convenient one. Prove what you resolved with
   `ansible-inventory --graph` / `--list-hosts` before the first task runs.
6. **Never put two names for the same machine in one target group.** A tailnet-IP
   entry and a `localhost` entry for the same host in the same group makes one run
   execute every task twice against one cluster — two upgrades, two escrow passes.
   Keep the same-host entry in a separate opt-in group or a different inventory.
   Prove it with `ansible <group> --list-hosts` and confirm the count is what you
   intend.
7. **Split inventory settings by whose they are.** `ansible_host`/`ansible_user`
   describe the CLUSTER and stay valid when the deployer moves. `ansible_ssh_private_key_file`
   describes the DEPLOYER and must be a variable a different machine can override.
   Credentials the tasks read (kubeconfig, secrets tokens) are consumed **on the
   target**, not on the controller — state that in the file, since it is the
   assumption most likely to break when the deployer changes.
8. **Verify the target's prerequisites by executing as the target user over the
   transport you will actually use** — `ssh <user>@<host>` and check readability of
   the kubeconfig, presence of the CLI, and whether the token exists in that
   account's environment. A credential that lives only in your interactive shell
   profile is absent to a non-interactive remote user.
9. **Do not auto-fix unmet credential access.** Granting a service account read
   access to a cluster-admin kubeconfig, or an org-wide secrets token, is a
   security decision for the owner. Add a preflight that fails with that
   explanation instead of letting the run die on an opaque permission error, and
   offer the account that already owns both.

## Stage 3 — Secrets-manager escrow

See `references/secrets-escrow.md` for the full ordering, ambiguity guard, and
Bitwarden SM specifics. The non-negotiables:

- Store **before** deliver; deliver **before** expose.
- Exposure is a separate phase that asserts the escrow flag — never inline.
- Check mode refuses credential generation and any external write.
- A value that can only be generated by the application cannot be pre-escrowed;
  say so rather than pretending the pre-install phase covers it.

## Stage 4 — Validate offline, honestly

Run what genuinely works offline and **name what you could not run**.

| Check | Command | Note |
| --- | --- | --- |
| Chart lint | `helm lint <chart>` | authoritative for charts |
| Chart render | `helm template` | proves values are actually consumed |
| YAML shape | `yamllint` | **not** on Helm templates — see pitfall |
| Ansible parse | `ansible-playbook --syntax-check` | see vault pitfall |
| Lint | `ansible-lint` | separate pre-existing findings from yours |

## Stage 5 — Independent review

Dispatch a bounded reviewer for work that mutates infrastructure. The reviewer
reports; it does not deploy, write secrets, or publish policy. It earns its place
only if you actually verify it:

1. **Verify every finding by execution before you act on it.** Reviewers assert;
   they do not run your system. Reproduce each blocker with the real templar, the
   real module directory, or a `helm template` before changing code. Some findings
   are simply wrong — confirm the tool really is absent rather than trusting the
   claim.
2. **A reviewer reading a tree you are still editing reports against stale code.**
   Either finish the edits before dispatching, or tell the reviewer the tree is
   live and ask it to pin findings to file hashes so you can tell which are
   current. Otherwise you "fix" code that already changed.
3. **Do not let a green suite stand in for correctness.** A suite that passed every
   assertion can still hide a credential rotated on every run, a module removed in
   a collection major, or a values dict nothing populates. Suites catch what you
   thought to assert; review catches what you did not.
4. Fix what is verified, re-run the full offline suite after each batch, and report
   remaining findings as explicit blockers rather than closing the task.

## Pitfalls

- **A `.gitignore` pattern can silently swallow a new source file.** Patterns like
  `**/secrets.yml` are common in Ansible repos. A role task file named `secrets.yml`
  will be written, work perfectly, and never be committed. After adding files, run
  `git status --porcelain --untracked-files=all <paths>` and `git check-ignore -v`
  on each new file. Prefer **renaming** the file over adding a negation rule to a
  secrets-protection pattern — do not weaken the protection to make your file visible.

- **Helm templates are not valid YAML before rendering.** Any tool that
  YAML-parses `.yaml` paths (yamllint, and write tooling with a YAML linter) will
  report false syntax errors on `{{- ... }}` templates, and may refuse to write them
  at all. Judge templates with `helm lint` + `helm template`. If a write tool refuses
  a template for YAML reasons, stage it under a non-`.yaml` extension and copy it
  into place.

- **A missing vault password blocks syntax-check repo-wide.** `ansible.cfg` pointing
  at an absent `vault_password_file` fails every play before parsing. Do not
  fabricate a password and do not decrypt real secrets to get past it. Build an
  isolated tree: copy `roles playbooks charts library module_utils inventory`,
  delete the encrypted `group_vars/secrets.yml`, drop in a minimal `ansible.cfg`,
  and syntax-check there. Report the real inventory as unvalidated.

- **A Helm template only breaks on the values path you never render in CI.** A
  `{{ include "x.fullname" . }}` nested inside a `{{ range }}` silently rebinds `.`
  to the loop item, so `.Values` becomes nil and the ENTIRE chart fails to render
  — but only when the guarding value is enabled. Use `$` (root context) for any
  `.Values` access inside a `range`, and always render the chart once per
  meaningful feature flag (ingress off AND on), not just with defaults.

- **Lint the RENDERED manifests, not the templates.** yamllint cannot parse `{{- }}`
  at all, and `helm lint` does not validate the output's shape. Pipe
  `helm template ... | yamllint -` to check the actual manifests. Disable the
  `indentation` rule for rendered output only: Go's marshaller emits
  machine-generated, stylistically inconsistent indentation and un-indented
  sequences that are valid and accepted by the API server. Keep every other rule
  so duplicate keys and trailing whitespace are still caught, and prove the lint is
  not a no-op by feeding it a deliberately bad manifest.
  A grant to use a tool is not a capability it has: when a permitted tool cannot do
  the job, find the variant that can rather than force-fitting the input or
  reporting the task blocked.

- **A module or parameter can be REMOVED between collection majors.** A role can
  lint and syntax-check cleanly and still fail at run time because
  `kubernetes.core.kubectl_info` no longer exists in kubernetes.core 6.x (it is
  `k8s_cluster_info`), or because `wait_condition.timeout` is not a valid key
  (`wait_timeout` is). Assert against the INSTALLED collection's module directory
  and `ansible-doc` output in the offline suite, not against your memory of the API.

- **Review cannot prove Jinja runs; execute it.** A `set_fact` merge like
  `rendered.ingress | combine(...)` reads fine but hard-fails on an empty dict, and
  `(x | default({})).combine(...)` works only on Ansible-wrapped mappings, not plain
  dicts. Prefer the filter form `(x | default({})) | combine(...)`, which is correct
  for both. Prove it by extracting the real expression from the task file and running
  it through a throwaway `ansible-playbook` with `vars: {x: {}}` — a grep-based test
  cannot catch either failure.

- **A values dict that nothing populates is a silent no-op.** If a role passes
  `values: "{{ rendered_values }}"` to a Helm/module call, confirm some earlier task
  actually builds it from the role's own variables. Otherwise the install silently
  succeeds using chart defaults and none of the documented variables have any effect.

- **A file path in defaults/inventory can look right and resolve to nothing.** Resolve
  paths that a role `lookup()`s with `{{ role_path }}`, never `{{ playbook_dir }}`:
  the playbook location varies by caller, and an off-by-one `../` silently escapes
  the repo entirely (`playbook_dir/../../charts/...` from `playbooks/` lands outside
  the project root) while looking plausible in review. Assert the resolved path is
  an existing file in the offline suite: substitute the literal `role_path`, run
  `os.path.normpath`, and `os.path.isfile` it. That check is cheap and catches a
  class of bug that only otherwise appears at deploy time as a failed lookup.

- **An equality guard written as `== 1` blocks first-ever deploys.** Guards over
  "how many records match" must be `<= 1`; zero is the legitimate empty state and
  two is the ambiguity you are trying to catch.

- **Do not route around a tool's safety guard.** If a tool refuses to write a config
  or security-sensitive file, that is the user-facing control. Use the sanctioned
  CLI, or report it as needing the user — do not shell out to defeat it.

- **Spending a granted permission silently reads as overreach.** When the user grants
  blanket capability ("you can write to all repos", "install any missing packages"),
  the grant covers doing the work, not silence about it. Use the permission, and name
  the specific grant you leaned on when reporting. Doing it unannounced forces the
  user to reconstruct afterwards whether they had authorised it.

- **Verify third-party charts and images before adopting them.** Check the chart repo
  actually exists, whether its image is pullable, whether it carries a licence, and
  whether every env var and CLI flag it passes exists upstream. A chart can lint
  clean and still reference a nonexistent image.

## Output

Report files changed per repo, what was validated vs merely prepared, and
blockers/unverified items as explicit lists. Never describe prepared work as
deployed, or a rendered chart as a running release.