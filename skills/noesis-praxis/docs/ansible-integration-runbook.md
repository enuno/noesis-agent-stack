# Ansible skill integration — install, verify, update, rollback

Scope of this change: the Ansible capability set in this tree. Nothing else in
`noesis-agent-stack` was touched, and `noesis-ansible` was **not** modified by
this integration (it carried unrelated uncommitted work that was left alone).

## What changed

| Path | Change |
|---|---|
| `skills/ansible-repo-change/` | **New.** Noesis-authored (disposition N). Previously existed only as an ungoverned runtime copy — that drift is now closed. |
| `skills/ansible-generator/SKILL.md` | **Patched.** Removed a dangling instruction to run `ansible-validator`, which is disposition C and not installed. The old text sent an agent to a skill that does not exist. Replaced with the real offline command set plus an explicit "passing validation is not deploy authorization". |
| `provenance/manifest.yaml` | Added the `ansible-repo-change` entry (disposition N) and the candidate dispositions. |
| `provenance/checksums.sha256` | Regenerated. |
| `governance/deployment-map.yaml` | Added the `ansible-repo-change` mapping. |
| `tests/test_ansible_behaviour_fixtures.py` | **New.** Scenarios A–F, static. |
| `README.md` | Ansible capability set section. |

## Runtime profile integration

Active profile: **`default` (`noesis-praxis`)**. Verified via `HERMES_HOME=/home/elvis/.hermes`
with `HERMES_PROFILE` unset, and by the profile-scoped skill directory
`~/.hermes/skills/noesis-praxis/` existing and being the location the validator
drift-check resolves.

Deployed copies live at `~/.hermes/skills/noesis-praxis/<name>/`. This repo is
canonical; those are read-only runtime views.

Nothing was installed into `~/.hermes/skills/` at the top level, so no other
profile (`builder-ventures`, `misjustice-advocacy`, `terrahash-intel`) is
affected. Those profiles have their own skill roots and were not touched.

## Verify

```bash
cd ~/projects/noesis-agent-stack/skills/noesis-praxis

# Static tree + runtime drift. Expect: 0 errors, 0 warnings.
python3 tests/validate_skill_tree.py --runtime-root ~/.hermes/skills

# Behaviour fixtures (static; NOT live agent behaviour). Expect: Ran 18 ... OK
python3 -m unittest discover -s tests -p 'test_ansible_behaviour_fixtures.py'

# The three Ansible skills are discoverable in the active profile.
ls -d ~/.hermes/skills/noesis-praxis/ansible-*
```

`validate_skill_tree.py` prefers `pyyaml` and falls back to a built-in parser
without it. To get full coverage use an interpreter that has it:

```bash
/home/elvis/.hermes/tools/python-3.14.7+202****0901-linux-x64/bin/python3 \
  tests/validate_skill_tree.py --runtime-root ~/.hermes/skills
```

## Install / sync into the profile

Sync is a snapshot of a pinned reviewed commit, per `governance/deployment-map.yaml`
(`rsync -a --delete`). It is done per skill, not with a blanket `--delete` over the
whole profile root:

```bash
S=~/projects/noesis-agent-stack/skills/noesis-praxis
RT=~/.hermes/skills/noesis-praxis

# back up the non-secret files needed for rollback first
mkdir -p ~/noesis-rollback-$(date +%Y%m%d)
cp -a "$RT/ansible-repo-change" "$RT/ansible-generator" ~/noesis-rollback-$(date +%Y%m%d)/ 2>/dev/null

for s in ansible-repo-change ansible-generator; do
  mkdir -p "$RT/$s"
  rsync -a --delete "$S/skills/$s/" "$RT/$s/"
done

# prove it landed and matches
diff -rq "$S/skills/ansible-repo-change" "$RT/ansible-repo-change"
python3 tests/validate_skill_tree.py --runtime-root ~/.hermes/skills
```

**Activation:** skills are read at session start. A live gateway/dashboard
session may need a reload or restart before it sees new skill content. This was
**not** performed — restarting a live gateway needs separate approval.

## Rollback

```bash
S=~/projects/noesis-agent-stack/skills/noesis-praxis
RT=~/.hermes/skills/noesis-praxis
BK=~/noesis-rollback-<date>

# remove the skill that did not previously exist
rm -rf "$RT/ansible-repo-change"

# restore the pre-change generator copy
rsync -a --delete "$BK/ansible-generator/" "$RT/ansible-generator/"

# confirm the tree matches the repo at the pre-change commit
cd ~/projects/noesis-agent-stack && git stash list     # nothing should be stashed
python3 "$S/tests/validate_skill_tree.py" --runtime-root ~/.hermes/skills
```

Rolling the repository back to the pre-integration commit is the authoritative
revert; the runtime sync above only removes the deployed view.

## Future update path

1. **Fetch pinned candidate.** Resolve the identifier to a real repo + path, then
   pin the commit SHA. Never install from a floating branch.
2. **Review the diff** against the copy already in `skills/`. Read every file,
   not just `SKILL.md` — scripts, references, templates move together. Check for
   executable code, auto-installers, hooks, hard-coded hosts/paths.
3. **Check the licence** permits redistribution. If not, do not vendor; record a
   blocked disposition instead.
4. **Classify** A/B/C/N per `governance/REVIEW.md`. For B, write
   `provenance/patches/<name>/ADAPTATION.md`.
5. **Test.** Extend `tests/test_ansible_behaviour_fixtures.py` if the skill carries
   a guardrail. Run the tree validator.
6. **Update the repository copy**, then `manifest.yaml`, `checksums.sha256`
   (`--write-checksums`), and `deployment-map.yaml`.
7. **Sync into the profile** (commands above) and re-run the drift check.
8. **Scoped local commit**, explicit path staging. Never `git add -A`.
9. **Do not push** without separate explicit authorization.

## What was deliberately NOT done

- No `pip install` of ansible tooling was performed by this integration. The host
  already had `ansible` (core 2.21.5), `ansible-galaxy`, `ansible-lint`,
  `yamllint`, `helm`, and the `kubernetes.core` collection from prior operator
  action.
- No playbook was executed, not even `--check`, against any managed host.
- No Bitwarden or Kubernetes secret was read to validate skill installation.
- No independent subagent review was run for this change; the earlier independent
  review covered the MCPJungle automation, not this skill integration.