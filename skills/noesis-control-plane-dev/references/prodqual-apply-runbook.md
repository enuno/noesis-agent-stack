# Prodqual loopback target — authorized apply runbook

How to execute (and how to halt) the `noesis-prodqual-macos-arm64-loopback-control-plane`
apply phase after the operator authorizes deployment. This is operational
depth for step 10 of the SKILL.md rollout gates; qualification and review
discipline live in the closed-loop skill.

## Configuration selection

The repo-root `ansible.cfg` sets `vault_password_file = .vault_pass`, which
is intentionally not committed — every ansible invocation from the repo root
dies with a vault error even though no prodqual task needs vault. The
prodqual fixture config has no vault reference. Always set:

```bash
export ANSIBLE_CONFIG=tests/prodqual_loopback/ansible.cfg
```

before running any prodqual playbook or test.

## Host binding (nothing stored in the repo)

The fixture inventory is the reusable identity; the binding contract
(`inventory/prodqual_loopback_fixture/BINDING-CONTRACT.md`) requires the
physical host and approval flags to be passed as command-line extra-vars at
apply time only:

```bash
ansible-playbook -i inventory/prodqual_loopback_fixture/hosts.ini \
  playbooks/macos-prodqual-loopback.yml \
  -e prodqual_approval_inventory_alias=<alias-never-the-laptop-hostname> \
  -e prodqual_approval_ansible_host=127.0.0.1 \
  -e prodqual_apply_authorized=true --check        # dry-run first
```

`prodqual_activation_authorized` is a separate later approval and must NOT be
supplied at apply time. Never edit `inventory/production/` to add this
target — the contract forbids it.

## Live destination preflight (read-only, before any apply attempt)

- Inspect `/opt/noesis`. It must be absent on a first apply; after a halted
  partial apply, inventory every surviving path, owner, group, mode, flag, and
  hash instead of deleting it. Back up any unrecognized pre-existing bytes.
- Inventory `noesis-authority` and `noesis-worker`. They must be absent on a
  first apply; after a halted partial apply, verify their UID/GID, non-login
  shell, authentication lock, and group membership exactly. Do not delete and
  recreate identities merely to restart an idempotent play.
- `launchctl print system/ai.noesis.orchestrator` — no system unit may be active
  before the separately approved activation phase.
- `df -h /opt` — verify headroom.
- `pgrep -fl noesis` — inventory running dev-prototype processes; document and
  preserve them until an exact cutover authorization resolves any label
  conflict.

## The same-UID prototype-label halt (expected on the operator's machine)

The role preflight (`tasks/preflight.yml`) fail-closes when user-domain
(UID 501) launchd units occupy production labels. The dev prototype
runnning on the operator's laptop holds exactly these labels:

- `ai.noesis.orchestrator`
- `ai.hermes.gateway`
- `ai.openclaw.gateway`
- `ai.noesis.broker`

The apply then fails with `same-UID prototype unit refused: <label> uid=501`
at the preflight assert, with `changed=0` — this is the designed stop, not a
package defect. Do NOT boot out, rename, or edit around the prototype units:
that is a fleet-impacting, separately authorized action. Halt, record the
halt verbatim in the preflight packet, and return the exact decision to the
operator (release the four labels vs. some other resolution). Any resolution
that changes the package (e.g. renaming the production label) changes
reviewed bytes and starts a new review cycle.

## Privilege and invocation (read before re-attempting any apply)

The role sets `become: false` at play level, which silently overrides a
CLI `--become`. That single fact drives every gate below — read the actual
asserts in `tasks/identity.yml` and the pre_task `setup` in the playbook
before choosing an invocation; do not guess from a prior halt message, do
not retry with a different privilege mode just because the last one failed,
and do not trust this section's earlier advice without re-deriving it from
the current package.

Derive and verify this privilege matrix from the candidate before every
apply; never infer it from the CLI flags alone:

- Keep the play at `become: false` so ordinary read-only tasks and
  `/usr/bin/id -u` operator discovery execute as the connection user.
- Put `become: true` directly on the conditional pre-task `setup` that gathers
  privileged execution facts. This makes `ansible_effective_user_id` an
  observed sudo-elevated fact while preserving the real unprivileged operator
  UID for the later discovery task.
- Keep every mutation task's explicit `become: true` and effective-root assert.
  Do not replace those boundaries with play-level or CLI-wide elevation.

Run the corrected playbook as the ordinary operator user. Do not wrap the
whole command in `sudo`: the named setup and mutation tasks establish their
own reviewed `become: true` boundaries, while operator discovery must remain
unprivileged. A CLI `--become` is unnecessary and the play-level
`become: false` overrides it; the task-level declarations are authoritative.
During the authorized `--check`, require evidence that privileged setup
observed effective uid 0 and unprivileged `/usr/bin/id -u` observed the real
operator uid before treating the structural repair as live-validated.

If the setup task lacks task-level elevation, the gates are jointly
unsatisfiable: invoking as the operator yields a non-root effective-user fact,
while invoking as root makes operator discovery return uid 0. Halt as a package
defect. Do NOT bypass it with `-e ansible_effective_user_id=0`; extra-vars
outrank gathered facts and would substitute an asserted value for observed
execution identity.

Repair this class of defect with strict TDD before the one-line YAML change.
The regressions must parse the YAML structure and prove all four invariants:

1. the named setup task has `become: true` while the play remains
   `become: false` and `gather_facts: false`;
2. both operator-discovery paths remain exact `/usr/bin/id -u` commands with
   no task-level become;
3. no play var, `set_fact`, default filter, or documented extra-var injects an
   execution-identity fact;
4. every mutation task still carries explicit elevation and the effective-root
   assertion.

Preserve the RED run from the missing task-level elevation, then the GREEN
focused tests and package refusal probes. Structural regressions prove the
supported invocation layout, not that sudo actually elevated on the target;
that boundary is proven by the fresh authorized `--check`/apply and its
observed facts. Freeze a new package identity, independently recompute the
delta hashes, and obtain bounded Sentinel then Skeptic review before resuming.
Preserve the superseded package and receipts unchanged.

## Partial-apply state

A halted apply (e.g. an identity assert mid-run) leaves real destination
state behind: OS identities, `/opt/noesis` filesystem entries. Inventory
exactly what the partial run created (`dscl . -list /Users | grep -i noesis`,
`find /opt/noesis`, launchd unit list) before deciding anything. The
playbook is written idempotently — re-running after fixing the assert is
the normal resume path, not a rollback trigger. Rollback of a partial
apply is a separately authorized decision, never automatic.

## Prototype cutover execution (only after explicit operator authorization)

When the operator authorizes replacing the four UID-501 prototype units:

- Resolve each target exactly (`launchctl print gui/501/<label>`) — state,
  PID, program, arguments, plist path — and verify your own process
  ancestry is not a descendant of any target before stopping anything.
- Back up plist bytes, ledger state, permissions, and enabled flags first;
  record `shasum -a 256` of every backed-up file.
- `launchctl bootout gui/501/<label>` returns before teardown finishes —
  verify post-state with `launchctl print gui/501/<label>` after a short
  delay; exit 0 is not stopped. Add `launchctl disable gui/501/<label>`
  to prevent auto-reload.
- A desktop app that owns orphan processes (e.g. Hermes.app) respawns its
  children under its own PID after bootout — the label is gone but new
  PIDs appear under a different parent; verify by parent PID, not by label
  or by "the old PID is dead."
- Stage the recovery executor STOPPED with the restore command ready to
  fire — never leave an armed window/session that auto-runs the restore
  script; a pre-loaded tmux window will execute it the moment it attaches.

## Post-apply (before activation)

Verify destination file hashes against the pinned per-file SHA-256 table;
verify owner/group/mode/flags, authority/worker separation, runtime/module
provenance, state/replay paths, supervisor/reaper configuration, logs, backup,
and rollback artifacts. Inspect the rendered launchd unit and require it to
name `noesis-authority`, but confirm the unit is **not active** until the
separately approved activation probe begins.

If a paid live canary, normalize the approval envelope into a separate durable
amendment before execution. If one message contains conflicting ceilings, do
not choose the larger value or infer intent: obtain or consume the operator's
explicit correction, record the single authoritative ceiling, and replace all
later calculations with it. Treat the ceiling as an upper bound, not a target;
verify pricing or a conservative enforceable token/request bound before the
request, and skip live inference when the bound cannot be reliably enforced.

## Concrete failure signatures seen in the 2026-10-12 prodqual loop (operator-confirmed)

These are the specific halts and their cause that this loop produced. They
are not abstract; the receipt SHA-256 and contract ID are recorded so a
future run can re-verify the same failure mode without re-discovering it.

### Whole-playbook `sudo -n` wrap → "operator_uid must be a positive UniqueID"

If the apply contract wraps `ansible-playbook` in `sudo -n` (or any
whole-playbook root wrap), the role's `Discover operator UniqueID` task
runs `/usr/bin/id -u` without `become` and observes `ansible_user_id = 0`.
The `prodqual_identity_policy_errors` filter fail-closes with the literal
message:

```
operator_uid must be a positive UniqueID
```

This is not a package defect; it is the role working as designed (the
filter refuses an unspecified operator). The correct invocation is the
operator's own user, with per-task `become: true` for the privileged
tasks. Symptom recognition: the identity phase fails before the
filesystem phase; `ok=37 changed=4 failed=1` with the failure in
`Re-run full identity/path/policy validation after discovery`
(`identity.yml:160`).

### `dscl -create AuthenticationAuthority` rc 0 + empty stderr is a silent failure

The c3 v2 live apply log records, for each of the 4 `dscl` lock tasks:

- `rc: 0`
- `stderr: ""` (empty)
- `stdout: ""` (empty)
- `changed: true` (Ansible's `changed_when: true` override)

yet the post-apply readback shows `AuthenticationAuthority: <absent>` on
both `noesis-authority` and `noesis-worker`. The role treats success as
`rc 0 + changed`, which is not a valid success criterion for `dscl`
against `dsAttrTypeStandard:*` keys on this host's OD. The fix is
readback-compare at task boundary, not relaxation of the policy. See
the bounded implementer contract for the canonical shape
(`identity-lock-readback-and-invocation-guard-r9-task.md` in the
qualification scratch).

### Offline-validate play is structural, not probe-evidence

`macos-prodqual-loopback-validate.yml` uses `tasks_from: offline.yml`,
which structurally excludes `identity.yml` and `filesystem.yml`. A clean
offline-validate run (`ok=35 changed=0 failed=0`) does NOT exercise the
worker-isolation probes or the privilege-validation stat blocks. Use it
only as a structural preflight; the real apply (or a `--check` run of
`macos-prodqual-loopback.yml` with the four `when: not (ansible_check_mode
| bool)` guards on the new integrity tasks) is the gate that exercises
the probes.

## Dispatch-loop pattern for the prodqual chain (2026-10-12)

The apply chain can fail in two distinct ways; the right next step is
different for each.

- **Contract error** (c1 fixture-inventory override): the role's
  preflight fails because the inventory is wrong. Fix the contract
  (e.g. dedicated loopback inventory, no `sudo -n` wrap, extra-vars
  via JSON file with real booleans) and re-dispatch the same role
  against the same package. The package itself is unchanged; no new
  review is needed.
- **Package defect** (c2 `Assert authority path integrity` under
  `--check`): the role fail-closes because a task added in the
  candidate is unsatisfiable in `--check` mode. The fix is a new
  candidate branch with a bounded change (e.g. add a `when:` guard
  to skip the unsatisfiable task in check mode), Sentinel + Skeptic
  reviews on the new candidate, PR + squash-merge to a new
  integrated commit, then rebind the apply task to the new
  integrated revision. Do NOT re-dispatch the old apply contract
  against the old package; that re-creates the same failure.

Both flavors preserve the failed apply's evidence (full result file,
SHA-256, dispatch log, preflight-before / preflight-after captures).
The operator authorizes the next step; the orchestrator does not
auto-pivot.

## Provider-lane exhaustion recovery

When the configured provider is exhausted (HTTP 403
`personal-team-blocked:spending-limit`, HTTP 400 `credit balance too
low`, or HTTP 403 weekly-quota exceeded) and the fallback chain
returns the same errors:

- Do not retry the exhausted route. The fallback will fail identically.
- Do not edit the profile's `default` or `fallback_providers`; the
  Hermes CLI refuses config-file edits for security-sensitive
  settings ("Refusing to write to Hermes config file").
- Pin per-dispatch on the operator-authorized alternative route:
  `hermes -p <profile> --provider <new> --model <new/model> chat -q
  <contract>`. This is the supported escape and survives the config
  guard.
- Preserve a snapshot of the prior `~/.hermes/profiles/<p>/config.yaml`
  at a timestamped path (e.g. `…/route-amendment-YYYY-MM-DD/config.yaml.snapshot.*`)
  so rollback is a one-line `cp`. Document the resolved primary
  identifier, the backup identifier, and any quota / authentication
  observations in a separate `route-amendment.md`.
- Sentinel and Skeptic dispatches under the new route are still
  separate independent contexts. Model choice does not establish
  independence or review quality; the separate processes do.
- The live canary route (Probe 2) is NOT automatically switched. The
  operator must separately authorize a canary-route amendment.

## Fence-aware Rich-markup audit (concrete recipe)

The SKILL.md references a fence-aware audit but does not pin a single
copy-paste recipe. This is the version that has been verified against
real contracts that crashed and real contracts that survived. Run it
on every contract that is about 1 KiB or larger, or that contains
inline backticks, before dispatch.

```bash
python3 - <<'PY'
import sys
p = sys.argv[1]
src = open(p).read()
in_code = False
flag = []
for i, ch in enumerate(src):
    if i + 3 <= len(src) and src[i:i+3] == "```":
        in_code = not in_code
        continue
    if in_code:
        continue
    if ch in "[]<>":
        line = src[:i].count("\n") + 1
        ctx = src[max(0, i - 30):i + 30].replace("\n", " ")
        flag.append((line, ch, ctx))
for f in flag[:30]:
    print(f)
print("count_in_plain:", len(flag))
PY
```

The dispatch is safe when the printed count is `0`. A non-zero count
in non-code regions means rephrase before launch. Inline-backtick
contexts (e.g. `\`/usr/bin/python3 … <tmp>/target\``) are non-code
regions; the audit will flag them.

## Working-tree identity for an apply contract

The apply contract's "frozen candidate" is a **commit identity**, not
a working-tree identity. An executor that edits files in the
working tree without committing leaves the worktree divergent from
the frozen candidate. When the apply contract's preconditions include
"HEAD equals <commit>", the orchestrator must re-verify

```
git rev-parse HEAD
git status --porcelain
```

immediately before the apply, not at the time the contract was
written. If HEAD is on a branch tip (not detached) when the apply
contract was written for a specific commit, the contract is
unsatisfiable: re-attach the worktree with `git checkout --detach
<commit>` before the next dispatch. The c3 v1 → c3 v2 transition
in this loop was exactly this fix.
