# Ansible/Jinja pitfalls (mechanism + working formulation)

Escape layers stack: file bytes → YAML quoting style → Jinja string literal →
regex engine. Count the layers for every backslash; test the rendered
string, never the file text.

- **Single-quoted YAML scalars pass backslashes through unchanged; Jinja
  string literals process them.** `'\\\\.'` in a single-quoted YAML line
  is a Jinja literal containing `\\.`, which the regex engine reads as one
  escaped dot — correct. The same four backslashes in a YAML *folded scalar*
  reach Jinja unchanged too, but in a *double-quoted* YAML scalar
  `\\\\` collapses to `\\` before Jinja sees it, breaking the regex.
  Rule: keep regexes in single-quoted scalars, and A/B-test the rendered
  output (match a known IP) instead of eyeballing the file.
- **`dict.items` is a method, not a key.** `some_dict.items` resolves to the
  bound method. Use the subscript: `some_dict['items']`.
- **The `mapping_has_key` test does not exist.** To test a dict key inside
  `selectattr`, extract with `set_fact` + `dict.get()` or
  `| default({})` — see the NetworkPolicy assertion in
  `playbooks/hermes-verify.yml`.
- **Inline flow dicts break `assert that:` lists.** A line like
  `== {'key': 'x', 'value': 'y'}` inside a YAML list is parsed as YAML, and
  the `: ` inside the flow mapping kills parsing. Build the expected value
  in `set_fact` or compare primitive fields individually.
- **Subscript-then-default beats `first`-then-default.**
  `( ... | list | first | default({}) )` still raises on an empty list
  because `first` errors before `default` runs; use
  `( ... | list)[0] | default({})`.
- **Task-level `vars:` must be a mapping.** `vars: "{{ some_dict }}"` fails
  obscurely; either inject keys as top-level facts via `include_vars`
  without `name:`, or list the keys explicitly.
- **`include_vars` paths resolve from `playbook_dir`** of the invoking
  playbook — a scratch-dir playbook needs absolute paths.
- **`random` re-templates per reference** when minted inline in play vars;
  a marker written and asserted from two references mismatches. Pin once in
  `pre_tasks` via `set_fact`.
- **Same-named `register:` on two `when:`-gated tasks:** the skipped task
  overwrites the variable with its skip result. Merge into one task with a
  `ternary()` name.
- **Deployment pod specs are at `spec.template.spec.*`** — reading
  `spec.containers` yields empty and counts silently become 0.
- **`kubernetes.core.k8s` does not Jinja-render a manifest file** supplied as
  a path; `definition:` needs the rendered string:
  `definition: "{{ lookup('ansible.builtin.template', role_path + '/templates/x.yml.j2') }}"`
  with `apply: true` (and `no_log: true` for secret-bearing manifests).
