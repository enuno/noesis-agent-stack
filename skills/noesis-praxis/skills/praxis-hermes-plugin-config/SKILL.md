---
name: praxis-hermes-plugin-config
description: Apply, verify, and roll back Hermes plugin settings blocks in a profile config.yaml. Use when asked to change plugin configuration (for example hermes-switchyard provider, routing, or opt-in feature settings), to apply a supplied settings JSON, or to confirm that plugin settings took effect. Never changes plugin code and never restarts a running gateway without explicit approval.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-hermes-plugin-config

Applying a plugin settings block to a Hermes profile, and proving the result
landed correctly. This skill covers the *host-side* mechanics of plugin
configuration; the plugin's own documentation covers what each setting does.

## Step 1 — establish the target profile and the authoritative writer

Resolve the real Hermes home before writing. A bare `hermes <subcommand>`
targets the sticky default profile; for any other profile use its wrapper
(`~/.local/bin/<name>`) or `hermes -p <name>`. Writing to the wrong profile
is silent — the command succeeds and the change goes nowhere you expected.

```bash
hermes config path          # the file actually being written
```

Two writers exist and they are not interchangeable:

- `hermes config set <dotted.path> <value>` — the supported writer. It
  validates the path against the plugin's `config_schema` and refuses an
  unknown path without `--force`. It merges into the existing tree without
  disturbing sibling entries.
- Direct editing of `config.yaml` — avoid. A stray indent corrupts the file
  and can break the live gateway.

Never use `hermes config get` on a secret-bearing path to verify a change:
it prints the fully resolved plaintext, unlike `config.yaml` reads and
`hermes mcp list`, which redact.

## Step 2 — check whether the file is managed elsewhere

Before writing, establish who owns the file. A config managed by Ansible,
Ansible Vault, or a provisioning repo will be overwritten on the next run,
and your change becomes silent drift.

```bash
grep -rn 'config\.yaml' ~/projects/*/playbooks/ 2>/dev/null
git -C ~/.hermes rev-parse --is-inside-work-tree
```

If the file is repo- or playbook-managed, the change belongs in that source,
not only in the live file. Say so in the report rather than quietly
patching the runtime copy.

## Step 3 — validate the requested keys against the plugin's schema

Each plugin declares its settings in its own `config_schema` (for
hermes-switchyard: `<plugin-dir>/plugin.yaml`, section `config_schema`).
Diff the requested block against it before writing:

- A key absent from the schema is either wrong or belongs to a different
  plugin — do not write it.
- A value whose type differs from the schema (`str` vs `list` vs `bool`)
  is a defect in the request, not something to coerce silently.
- A placeholder path (for example `/ABSOLUTE/PATH/TO/...`) is not a valid
  value even when it is syntactically absolute. Ask for the real path, or
  set the feature to off, rather than shipping a placeholder that registers
  a feature which then finds nothing.

Load the plugin's own operations skill and its configuration reference —
they are authoritative for defaults and for which settings are opt-in.

## Step 4 — apply the block, one key per call

Apply each key with its own `hermes config set` call so that one bad value
cannot take the rest of the block down with it, and so a per-key failure is
attributable.

**The empty-string trap.** A setting whose value is the empty string must
reach the CLI as a real empty argument. Shell-quoting `''` as a literal
two-character token writes the string `''`, which the plugin then reads as a
non-empty path and rejects. The symptom is a config.yaml line like
`browser_executable: "''"` instead of `""`.

**List values.** Pass one quoted YAML/JSON argument:
`hermes config set <path> '["all"]'`. An empty list is `'[]'`.

**Booleans and numbers.** Pass `true`/`false` and bare numerics; the CLI
coerces them to the schema type.

```bash
hermes config set plugins.entries.<plugin-id>.settings.<key> <value>
```

## Step 5 — verify by parsing the file, not by reading the CLI's echo

`hermes config get` renders empty strings and quoted-empty strings
ambiguously, so its output is not proof of what was stored. Parse
`config.yaml` with a real YAML parser and compare the stored mapping against
the requested one:

```python
import yaml
cfg = yaml.safe_load(open('/home/elvis/.hermes/config.yaml'))
stored = cfg['plugins']['entries']['<plugin-id>']['settings']
```

Diff key sets AND values, and report per key: missing, extra, or mismatched.
Treat any mismatch as a failure of the whole apply, not a footnote.

Then confirm the plugin accepts the result in a *fresh* process — settings are
read at plugin load, so the running session still holds the old values:

```bash
hermes switchyard status --json     # or the plugin's own status command
hermes plugins doctor <plugin-id>
```

For a setting whose effect is a registered hook or tool, prove the
difference rather than assuming it: count the registrations with the
feature on and off (`HERMES_PLUGINS_DEBUG=1` prints
`registered hook: <name>` lines) and show that the count changes.

## Step 6 — report what is live and what is not

Plugin settings are read when the plugin loads. A running gateway or an open
session keeps its old values until it restarts. Compare the service's start
time against the config's mtime and state plainly which surfaces have picked
the change up and which have not.

Do not restart a running gateway to "finish the job" without explicit
approval. Report the pending restart and let the operator decide.

## Boundaries

- This skill changes configuration only. It never edits plugin code, never
  edits a plugin's own git checkout (that is an upstream mirror; a local
  edit is drift and is lost on the next update), and never changes the
  plugin's shipped skills.
- Setting a provider, endpoint, model, or feature flag is a routing and
  billing decision. Confirm the intent against the plugin's documentation
  rather than assuming a value's effect.
- A configuration change is not a completed change until the stored bytes
  were read back and compared.
