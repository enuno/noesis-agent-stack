---
name: noesis-praxis-ops
description: Use when deploying/verifying the noesis-praxis k3s stack.
---

# noesis-praxis-ops

Operating the private single-node k3s stack on `noesis-praxis` through the
`/Users/elvis/projects/noesis-ansible` repo (k3s, Hermes agent, Tailscale
operator). The deliverable is always: green verify playbooks + an updated
freeze manifest + evidence, never a narrative claim.

## When to Use

Any work against the noesis-praxis stack via the noesis-ansible repo:
installing or upgrading k3s / the Hermes agent / the Tailscale operator,
running verify playbooks, migrating workload placement (host ↔ cluster),
adding or changing roles/playbooks/inventory, freezing a reviewed candidate,
or investigating a regression on the target.

## Standing rules (every run)

- **Read-only first.** No remote writes until the operator explicitly
  approves the scoped change; irreversible/r3-class operations additionally
  need an approval manifest. Idempotence is mandatory — never wipe or
  recreate the cluster (or any workload) on rerun.
- **Never commit or push** in this repo unless the operator asks (when asked,
  follow the commit procedure below). Do not
  touch `roles/mempalace/`, `roles/noesis_codebase_state/`, `noesis-assets/`,
  `.claude/`, `.codex/`, `.cursor/`, `.github/` — they are other in-flight work.
- **No plaintext credentials.** Secrets come only from the encrypted vault
  file (passed via `-e @vault.yml`) or Bitwarden SM; set
  `ANSIBLE_VAULT_PASSWORD_FILE` to the scratch vaultpass first. `no_log` /
  `diff: false` on secret material. Never pass secrets via `-e key=value`
  (process-list exposure), never echo values, print only key names/lengths.
- **User architecture preference:** cluster-adjacent daemons belong in the
  cluster. When the operator redirects, deploy via the official upstream
  Helm chart as an in-cluster workload rather than host packages, and
  decommission the host daemon deliberately (logout → disable → purge) —
  never run two instances of an identity-bearing daemon (e.g. tailscaled).

## Procedure

1. **Preflight.** `export ANSIBLE_VAULT_PASSWORD_FILE=<scratch>/vaultpass`
   (never `ANSIBLE_CONFIG=/dev/null`); source the profile `.env` for bws;
   probe SSH with `ssh -o BatchMode=yes -o ConnectTimeout=8` before
   scheduling any playbook — a hung Secretive agent stalls at signing, not
   connect, so short timeouts do not detect it.
2. **Resolve and freeze upstream inputs before rendering.** For containerized
   workloads, verify the newest stable upstream release against both the source
   release feed and the complete registry tag set, then pin the multi-architecture
   OCI index digest (not `latest` or `main`). Follow
   `references/container-image-pinning.md`; a single registry tags response is
   commonly capped and can make an old tag look current.
3. **Offline-validate every candidate change before claiming it works:**
   `ansible-playbook --syntax-check` against the real inventory, plus a
   localhost render harness (template Jinja files to scratch with explicit
   vars, then `yaml.safe_load` the output). Render-checks catch what
   syntax-check cannot (escape layers, undefined vars at render time).
4. **Standard order:** `k3s-install.yml` → `k3s-verify.yml` →
   `hermes-deploy.yml` → `hermes-verify.yml` → Tailscale phase (post-pivot:
   `tailscale-k8s-migrate.yml` → `tailscale-k8s-verify.yml`; the host-level
   `tailscale-install/serve/serve-verify` playbooks are deprecated and kept
   only for rollback). Buzz sequence: `buzz-deps.yml` → `buzz-secret.yml` →
   `deploy_buzz.yml` → `buzz-verify.yml -e buzz_live_checks=true` (group_vars
   default is false = offline-only; without the override every live assert
   silently skips).
5. **Run conventions:** `-i inventory/praxis-k3s/hosts.ini -f 1` and a short
   sleep between consecutive plays — rapid SSH bursts trip sshd throttling.
6. **Empirical gates before asserting network truth.** Derive observed
   source IPs live (pods may lack ss/netstat/ip — read `/proc/net/tcp`
   inside the pod during a request) and set `trustedProxies` /
   `confirmed_backend_source_ip` from observation, never assumption. After
   any proxy-path change (e.g. host Serve → in-cluster Ingress), **re-derive
   rather than copy** the old values — the DNAT/SNAT chain differs.
7. **Freeze after each accepted change:** manifest of `"<sha256>  <relpath>\n"`
   lines sorted by relpath, digest = sha256 of the concatenation; scope =
   the prior freeze's files plus new ones (exclude `noesis-assets/` and the
   freeze manifests themselves). Review/re-review rounds diff against the
   digest.
8. **Report with chronology.** Preserve the full test history including
   failed or environment-defect runs; per-reviewer status must be explicit
   (e.g. SENTINEL_SPEC_PASS / SKEPTIC_PENDING); never carry a historical
   verdict onto a new candidate.

## Committing and pushing (only when the operator explicitly asks)

1. **Scope the working tree before staging.** This repo mixes several
   in-flight workstreams; `git status --porcelain` first, then stage by
   category (e.g. platform plays + roles + pins as one commit, application
   deploy plays + inventory + docs as the next). Never stage the
   do-not-touch paths, and never sweep `git add -A`.
2. **Scan the staged diff for secret material before every commit:**
   `git diff --cached -U0 | grep -inE '(BEGIN (RSA|EC|OPENSSH|PGP)
   PRIVATE|AKIA[0-9A-Z]{16})'` — expect zero hits. (`-U0` keeps the scan
   fast on large vendored trees; doc placeholders like `<strong
   password>` are fine, real key material is not.) Confirm credential
   files stay ignored: `git check-ignore .vault_pass`.
3. **Commit with conventional messages and the Assisted-by trailer** per
   the `commit` skill. An explicit operator directive to "commit and push"
   is the Step-4 approval — do not re-ask.
4. **Push to `origin main`; never amend, force-push, or rewrite history.**
   Report the pushed range (`old..new`) and the paths deliberately left
   uncommitted.

## Pitfalls (step-attached)

- **Step 3/4 — Helm v4 broke kubernetes.core <6.6.0** (`helm list --all`
  removed). Pin `kubernetes.core >=6.6.0` in `requirements.yml`; the
  homebrew-installed 5.2.0 shadows it — keep 6.6.0 in
  `~/.ansible/collections` ahead in the collection path.
- **Step 4 — every playbook that calls kubernetes.core modules on the target
  needs the target-side interpreter.** The `kubernetes` Python lib exists
  ONLY in the shared venv `/opt/ansible-kubernetes` (pinned
  `kubernetes==34.1.0`). Copy the hermes-{deploy,verify} pre_tasks pattern
  (apt python3-venv → `python3 -m venv` with `creates:` → pip into venv →
  `set_fact ansible_python_interpreter: <venv>/bin/python`). Without it the
  k8s module fails with "Failed to import the required Python library
  (kubernetes)". And any `ansible.builtin.apt` task under the play-wide venv
  interpreter fails (no python3-apt in the venv) — pin
  `ansible_python_interpreter: /usr/bin/python3.14` back onto apt tasks.
  New playbooks must replicate both halves, not just the venv creation.
- **Step 4 — pass `kubeconfig: /etc/rancher/k3s/k3s.yaml` explicitly on EVERY
  kubernetes.core.{k8s,k8s_info,helm,helm_info} call.** There is no usable
  default kubeconfig for the module's runtime context (venv python, become
  root → no /root/.kube/config); without the param the call fails with
  "Could not create API client: Invalid kube-config file. No configuration
  found." The hermes role does this on every call — any new role must too
  (one role-level default var, referenced everywhere).
- **Step 4 — PodSecurity on the tailscale namespace: `enforce: baseline`,
  never `restricted`.** The operator Deployment AND the operator-spawned
  ingress proxy pods (NET_ADMIN userspace tailscaled) ship no
  restricted-compatible securityContext; `enforce: restricted` rejects the
  pod, Deployment sits 0/1, helm `--wait` times out and `--atomic` rolls
  the release back ("resource ... not ready ... context deadline
  exceeded"). Keep `audit: restricted` for visibility.
- **Step 4 — OAuth clients mint authkeys ONLY for tags they themselves
  bear, and each such tag must self-own in the ACL.** Diagnose with token
  introspection: POST /api/v2/oauth/token with client_id:secret returns a
  `tags` field naming the client's tags. The operator chart's
  `operatorConfig.defaultTags` must equal that list exactly (ours is
  `tag:k3s`, so defaultTags=["tag:k3s"]); the proxy tag
  (proxyConfig.defaultTags, `tag:k8s`) must be owned by the client's tag in
  the ACL tagOwners. A mint probe (`POST /api/v2/tailnet/-/keys`, ephemeral
  key, immediate DELETE) is the fastest 400-vs-propagation discriminator.
  ACL changes go through the `tailscale-lab-acl` GitOps repo
  (~/projects/tailscale-lab-acl): branch → PR (CI `test` validates policy)
  → merge to main (CI `apply` pushes to the tailnet).
- **Step 4 — `kubernetes.core.k8s` `definition:` does not Jinja-render a raw
  manifest file** passed via a `template:`-style path (raw `{% for %}`
  reaches the API). Use
  `definition: "{{ lookup('ansible.builtin.template', role_path + '/templates/<manifest>.yml.j2') }}"`
  with `apply: true`, `no_log: true` for secret-bearing manifests.
- **Step 6 — dashboard auth contract:** page routes (`/`, `/settings`)
  return 302 → `/login?next=...`; only API routes return 401. Assert
  unauthenticated state against `/api/sessions`, not `/`.
- **Step 3 — task-level `vars:` must be a mapping**, not `"{{ some_dict }}"`
  (string vars fail obscurely in include/template tasks).
- **Step 4 — Deployment pod specs live at `spec.template.spec.*`** (reading
  `spec.containers` silently yields nothing); two same-named `register:`
  tasks where one is `when:`-skipped let the skip overwrite the real read —
  merge into one task; `random` minted in play vars re-templates on every
  reference — pin markers via `set_fact`.
- **Step 4 — Buzz relay image: never deploy the chart default tag.**
  Chart `appVersion` `0.1.0` is a 2026-06-14 relay that predates the
  `BUZZ_AUTO_MIGRATE` startup flow the chart documents — on an empty schema
  it crash-loops (`relation "events" does not exist`) and helm `--wait`
  burns the full timeout. The production pin is a digest in
  `inventory/praxis-k3s/group_vars/buzz_k3s.yml`
  (`ghcr.io/block/buzz@sha256:55574c…`, main rev `6e6173a`). Diagnose relay
  boot failures by logs first; the relay prints
  named startup phases (`buzz_relay::startup_steps`) ending in the failing
  phase. See docs/buzz.md.
- **Step 4 — `bws` reads must run controller-side.**
  `ansible.builtin.command` with `delegate_to: localhost`, `run_once: true`,
  `become: false`, and retries (transient bws failures happen). Run on the
  managed host it fails with command-not-found; run under `become` it can
  miss the operator's BWS_ACCESS_TOKEN.
- **Step 4 — Bitwarden SM values can carry stray trailing newlines.**
  A `\n` on an R2 secret key surfaced in-cluster as S3
  `SignatureDoesNotMatch`. Diagnose by length/whitespace metadata only
  (never print values); fix with `bws secret edit <id> --value <trimmed>`
  and harden playbooks with `| trim` when assembling secret data maps
  (buzz-secret.yml does). Validate creds out-of-band (signed
  ListObjectsV2) before re-running a 10-minute helm `--wait`.
- **Step 4 — Secret changes do NOT roll pods.** Env from `secretKeyRef` is
  resolved at pod creation; `helm upgrade` re-applies the Deployment
  unchanged and crash-looping pods keep the stale env forever. After
  `buzz-secret.yml` (or any Secret edit), `kubectl rollout restart
  deployment/<name> -n <ns>` and watch the new pod. A failed helm
  rollback can also leave the deployment pointing at the OLD spec — rerun
  the deploy play to converge once pods are healthy.
- **Step 4 — Tailscale Ingress exposure creates a dedicated device.** With
  IngressClass `tailscale`, each ingress gets its own tailnet device/IP
  (buzz → 100.99.117.67), NOT the operator's IP (100.94.198.124). Verify
  end-to-end from a tailnet client: `curl -sI
  https://buzz.tailf99a0.ts.net` expecting HTTP/2 200.
- **Jinja/YAML escape-depth traps** (regex backslashes, `dict.items` being a
  method, inline flow-dicts breaking `assert that:` YAML, the
  `mapping_has_key` test not existing) are catalogued in
  `references/ansible-jinja-pitfalls.md` — consult before writing matchers.

## References

- `references/tailscale-operator-chart.md` — official Tailscale Helm chart:
  auth model, Ingress exposure model, OAuth/ACL prerequisites. Read before
  touching anything Tailscale on this stack.
- `references/bws-vault-recipes.md` — Bitwarden SM read patterns and
  programmatic ansible-vault edit recipe (never print secrets).
- `references/ansible-jinja-pitfalls.md` — escape layers and dict/test
  gotchas with the mechanism and the working formulation.
- `references/container-image-pinning.md` — paginated registry discovery,
  source-release cross-check, OCI index digest selection, and chart/appVersion
  provenance.