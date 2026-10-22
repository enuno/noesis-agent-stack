# Offline Ansible/Helm Artifact Validation

Controller-only validation for artifacts produced by delegated children
(playbooks, roles, inventories, Helm values/templates) when the
target is unreachable or the remote-write gate is closed. Nothing here
touches the target; every check runs locally.

## 1. Ansible playbooks: syntax and inventory binding

```bash
ansible-playbook --syntax-check -i <inventory> playbooks/<name>.yml
ansible-playbook --list-hosts  -i <inventory> playbooks/<name>.yml
```

- Run both against the inventory the playbook is actually meant for.
  A single-target playbook must list exactly one host; if it resolves
  to `localhost` or an unexpected group, the child validated against
  the wrong inventory — treat that as a deviation signal and inspect
  the play's `hosts:` line.
- `--syntax-check` catches YAML and structural errors without
  connecting anywhere.

## 2. Vault password harness (the common false failure)

Many repos' `ansible.cfg` references a `.vault_pass` file that does not
exist on the controller. Every `ansible-playbook` invocation then fails
or prompts before doing anything. Fix per-shell, never by editing the
repo config:

```bash
printf 'scratch-not-a-real-password\n' > /tmp/.vpw
export ANSIBLE_VAULT_PASSWORD_FILE=/tmp/.vpw
```

- The file must contain at least one non-empty line. Pointing the env
  var at `/dev/null` fails with
  `Invalid vault password was provided from file` — an empty password
  is rejected, so this failure is harness noise, not an artifact defect.
- Clean up the scratch file when done.

## 3. Template rendering

Jinja2 templates in roles/playbooks are not exercised by `--syntax-check`.
Render them with mock vars and parse the output:

```bash
python3 - <<'PY'
import jinja2, yaml, sys
env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
for t in sys.argv[1:]:
    rendered = env.get_template(t).render({"mock": "vars"})
    docs = list(yaml.safe_load_all(rendered))
    print(f"{t}: OK ({len(docs)} docs)")
PY roles/<role>/templates/<file>.j2
```

Rendering catches undefined variables, bad filters, and malformed
output YAML that syntax checks miss.

## 4. Helm charts and values

```bash
helm lint <chart-dir> -f <rendered-non-secret-values>
helm template <release> <chart-dir> -n <namespace> -f <values> > /tmp/rendered.yaml
```

Review the rendered documents programmatically, not by eye:

- Workload: strategy (e.g. `Recreate` for single-writer state), replica
  count, `automountServiceAccountToken`, securityContext
  (runAsNonRoot, dropped capabilities, seccomp).
- Exposure: every Service `type` must be `ClusterIP`; no Ingress,
  HTTPRoute, NodePort, hostPort, hostNetwork.
- Persistence: PVC storageClass/accessModes/size, mount path matches
  the documented state directory.
- Hooks/tests: what each hook Job mounts (a test mounting live state
  with a second writer must be replaced with non-conflicting checks).
- Never pass real secret values through `-f`; validate against
  placeholders only.

## 5. Repo hygiene

```bash
git status --porcelain
```

Confirm only the task's owned paths appear. Pre-existing modified or
untracked work in the repo is out of scope: verify it is untouched,
never commit or fold it into the task's change set.

Grep new playbooks for `role:` and `include_role`. An include of a role
outside the closed write set is scope coupling, even when
`--syntax-check` passes because that role already exists untracked on
this checkout. Remove the include. Assert the required binary on the
execution host from inside the owned role. A clean commit of only the
owned paths must still be a valid play.

## 6. Chart pin versus published distribution

Record three identities separately. Do not collapse them because
`Chart.yaml` version strings match:

- Published distribution: Helm HTTP repo, OCI reference plus tag and
  manifest digest, or git-packaged chart. Do not invent a registry URL.
- Chart-release git commit, when upstream tags chart publication
  separately from the default branch.
- The exact tree the role installs: an OCI pull, or a vendored directory
  from one immutable SHA.

A vendored default-branch SHA is an immutable pin of that SHA only. It
is not the published OCI chart and not the chart-release commit. Do not
claim byte-identity with a registry layer that was not unpacked and
hashed. Do not write that an OCI tag was unverified if a sourced
evidence file already verified it; say the role does not pull it.

If dependency download fails, keep the upstream lockfile unchanged and
say the fetch failed. Vendored tarballs are not a successful
`helm dependency build` unless that command exited 0.

## 7. Fail-open live checks

A flag that skips Secret, StorageClass, and release-adopt reads is not
offline mode if the install task still calls the Kubernetes API. Name
that skip as fail-open. Syntax-check and `helm template` do not prove
those preflight asserts run before Helm on a real inventory.

Close it on any play that installs or upgrades a named release:

1. Force the ownership check in play `vars:`. Play vars beat inventory,
   so a group_var cannot turn the guard off for that play. A role
   default of false is not a guard.
2. Set a same-run fact only after the adopt assert passes. Do not set
   the fact on the same `when` as a skipped preflight.
3. Assert that fact is true in the install task before
   `kubernetes.core.helm`. A skipped preflight must not fall through to
   Helm, especially when `reset_values` is true — Helm will upgrade a
   same-name release that is not this chart.
4. Lock the order with a static test: the deploy play sets the forcing
   var, and the fact assignment appears before the helm module. A test
   that only renders values does not close this finding.
5. Keep verify/syntax paths able to skip live reads. Do not treat a
   green `--syntax-check` as proof the guard runs.

## 8. Quick checklist before accepting a child's report

1. Artifact exists at the claimed path; spot-read the top matter.
2. `--syntax-check` passes under the correct inventory.
3. `--list-hosts` resolves the intended target(s) and no others.
4. Templates render and parse.
5. `helm lint`/`helm template` review shows no forbidden exposure.
   Re-run them before calling that check PASS. A child's exit is a claim.
6. `git status` shows only owned paths.
7. No `role:` / `include_role` points outside the closed write set.
8. Chart pin names distribution, release commit, and installed tree
   separately.
9. Any child-reported hash or pin is recomputed after the last write
   returns, not in parallel with a patch.
