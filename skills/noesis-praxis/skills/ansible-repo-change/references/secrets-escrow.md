# Secrets-manager escrow for infrastructure automation

When IaC creates a credential, the secrets manager is the **authoritative durable
record**. A Kubernetes Secret, `.env`, or config file is a runtime **delivery copy
only** — never the only copy.

## Ordering (enforce in code, not by convention)

```
resolve-or-generate -> STORE -> verify stored -> DELIVER -> expose
```

Two hard rules:

- **Exposure is a separate phase that asserts the escrow flag.** Do not inline
  ingress/endpoint creation into the same task run as provisioning. The assert is
  what makes "unexposed until escrow succeeds" true rather than aspirational.
- **Dependent resources are created only after their secret is stored.** A
  database Secret created before its password is escrowed violates the guarantee
  even if it "works".
- **Phase order must be enforced by task order in the play, not by intent.** An
  escrow step placed in a later block than the install step leaves the gate
  permanently false: the Secret is silently skipped and the release comes up
  pointing at a Secret that does not exist. Escrow belongs in `pre_tasks`, before
  the role runs. After wiring it, trace the gate's only writer and its only reader
  and confirm the writer can actually run first.

## Idempotency rules

- **Generate only after a *successful* lookup proves absence.** A permission error,
  timeout, or ambiguous result is NOT absence. Fail the run instead — silently
  regenerating is how you end up with a credential nobody can recover.
- **Re-runs reuse the stored value.** Never regenerate a password or re-issue a
  token just because a bootstrap step re-ran.
- **Never overwrite an existing stored value** because a later step re-ran.
- **Never rotate without explicit authorization.**
- **Build the record lookup by projecting fields, never by positional tricks.** An
  index built as `map('dict2items') | map('last')` yields each record's LAST FIELD
  (`revisionDate`), not the record, so every lookup matches nothing, absence is
  "proven", and a fresh credential is generated on every single run — the exact
  rotation the rules above forbid, arriving through a correct-looking expression.
  Use an explicit projection such as `json_query('[*].{id: id, key: key}')`, and
  assert the index round-trips: feed a known record list through the expression and
  confirm `key` and `id` come back.

## The duplicate-key trap

Secret names are **not unique**. Shared org projects accumulate collisions fast.

- A helper that returns the first match is selecting an **arbitrary record** — a
  correctness bug that will eventually hand you the wrong credential.
- Count matches per key and **fail closed** when the count is `> 1`. Zero is the
  legitimate empty state (first deploy), so the guard must be `<= 1`, never `== 1`.
- Offer a pinned record-id map as the escape hatch so ambiguity can be resolved
  without renaming keys.
- Scope new keys by environment/cluster/release so two environments cannot collide.

Before designing naming, **measure** the existing project: count records, distinct
keys, and duplicates. Use metadata-only listing; never print values.

## Partial-failure recovery

- If storage fails **after** generation, do not regenerate — you may destroy the
  only copy. Stop, report the state, leave the service unexposed.
- **Give the in-memory value a crash-safe staging file.** A generated credential
  that lives only in an Ansible fact is unrecoverable the moment the play aborts,
  and the next run mints a different one. Write it to a `0600` controller-side
  file *before* the store call, have the next run read and reuse that file instead
  of generating, and delete it only after the store is verified. This is what
  makes the "do not regenerate" rule enforceable rather than aspirational.
- Prefer generating credentials on the controller, before provisioning, so the
  store-then-deliver order is achievable.
- If an application issues credentials itself at runtime, that credential **cannot
  be pre-escrowed**. Say so explicitly. A post-install capture phase is still
  required before the endpoint is useful, and the gap belongs in the handoff, not
  in an implied guarantee.
- Secret deletion and credential revocation are separate, separately-authorized
  operations. Uninstall must not remove escrow records.

## Secret hygiene

- `no_log: true` on any task that touches a value, plus `diff: false` on the
  Kubernetes apply.
- Prefer delivering secrets by **file** (`*_FILE` env vars + mounted Secret) over
  environment variables — env vars show up in `kubectl describe`, process listings,
  and crash dumps.
- **Check CLI tools for argv exposure.** A CLI taking the secret as a positional
  argument (`create KEY VALUE PROJECT_ID`) puts it in `ps` for the process
  lifetime. `no_log` hides it from logs but does not hide it from the process
  table. If the tool offers an API/SDK path carrying the value in a request body,
  prefer it and record the trade-off.
- Keep example inventories credential-free: empty token vars, write gates defaulting
  to **false**, commit only non-secret identifiers.
- Rendered output and CI logs count as disclosure surfaces. Do not retain sensitive
  render artifacts in the repo.

## Bitwarden Secrets Manager specifics

- Secrets Manager (`bws secret ...`) is a different product surface from Password
  Manager vault items. Do not mix their commands or data models.
- Machine accounts need **read, write** to create records. Read-only access proves
  nothing about write; treat unverified write scope as a provisioning blocker, not
  a reason to store credentials elsewhere.
- Obtain the access token through the existing approved controller credential
  mechanism. Never bootstrap secrets-manager access from inside the workload, and
  never persist that access token as an application credential.
- Check the CLI's actual signature for the installed version before writing tasks
  against it; the write path and read path often differ, and versions drift.

## Verification to report

Per credential: purpose, project id, record id/name, runtime consumer, and
storage/delivery status. **Never the value.** State plainly which records exist and
which are still unverified.