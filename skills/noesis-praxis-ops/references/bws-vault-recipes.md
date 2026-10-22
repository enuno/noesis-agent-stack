# Bitwarden SM (bws) + ansible-vault recipes

## Reading secrets without printing them

```sh
set -a; source ~/.hermes/profiles/noesis-orchestrator/.env; set +a
export BWS_ACCESS_TOKEN
bws secret list <project-id> | python3 -c '
import json,sys
for s in json.load(sys.stdin):
    if s["key"]=="WANTED_KEY": print(s["value"])'
```

- CLI is at `~/.cargo/bin/bws` (project id for the noosphere project lives in
  MEMORY.md).
- Print only key names, lengths, or prefixes — never values. Pipe through
  python JSON parsing rather than grepping raw output.
- Note `bws secret list --project-id X` is rejected by the arg parser; pass
  the project id positionally.

## Programmatic ansible-vault edit (add/update a key, never print it)

1. `ansible-vault view <file>` (with `ANSIBLE_VAULT_PASSWORD_FILE` set) into
   a variable; `yaml.safe_load` it.
2. Mutate the dict; `yaml.safe_dump` to a temp file.
3. `ansible-vault encrypt <tmp> --output <tmp>.enc`; copy the original to a
   `*.bak-*` sibling; move the `.enc` over the original.
4. Verify by `ansible-vault view` again and comparing against the in-memory
   value (print lengths/boolean match only).

Pull the secret value from bws into an env var inside the same shell so it
never appears in argv, stdout, or the transcript.

## Playbook-side conventions

- Vault-provided vars land via `-e @<encrypted>.yml`; the vault password
  file comes from `ANSIBLE_VAULT_PASSWORD_FILE` (scratch vaultpass).
- `no_log: true` + `diff: false` on any task touching secret material; the
  staged values file on the target stays non-secret by design (secrets ride
  in k8s Secrets rendered via `lookup('ansible.builtin.template')`, never in
  helm values files).
