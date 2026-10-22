# Ansible lifecycle prompt checklist

Use this table while inspecting automation and before claiming a prompt set is complete.

| Field | Evidence to collect |
|---|---|
| Repository identity | URL, canonical path, branch, full HEAD, upstream, dirty/divergent status |
| Inventory | Exact inventory path, resolved groups/hosts, environment variable |
| Entry point | Existing playbook path and verified tags |
| Roles | Included roles, task files, defaults, handlers, and feature toggles |
| Inputs | Required variables, precedence, placeholders, credential references |
| Secret path | Existing vault/Bitwarden mechanism; no literal secret values |
| Preflight | Syntax check, inventory graph, check/diff limitations, target-scope check |
| Approval | Disruptive, production, network, security, secret, data, and service gates |
| Verification | Exact validation playbook/task and what it actually proves |
| Failure | First-failure preservation, ignored-error handling, stop conditions |
| Recovery | Existing rollback/restore task, source requirements, limitations |
| Report | Commands, exit status, changed scope, warnings, unresolved issues |

Validation sequence:

1. Resolve every referenced playbook and role path in the current checkout.
2. Parse each referenced inventory with `ansible-inventory --graph`.
3. Run syntax checks with the repository's normal configuration first.
4. If the normal configuration lacks a vault-password file, use a temporary external config containing only safe path settings; never create a guessed vault credential.
5. Run `git diff --check` and a focused secret-pattern scan over prompt files.
6. Verify each prompt contains the freshness requirement, missing-input rule, preflight, approval, verification, failure/recovery, and completion-report sections.
7. Report environmental blockers and unsupported automation separately from prompt-library validation results.

Do not use a README-only claim as evidence for a lifecycle capability. Read the playbook and role tasks that implement it, especially when tasks use `ignore_errors`, debug-only operations, default-OFF toggles, or placeholder inventories.
