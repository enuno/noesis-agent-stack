# Specialist plugin canary

Use this recipe when the Noesis control plane works directly but the operator
needs proof that a fresh Hermes model session can see and call the specialist
router plugin. This is a temporary canary procedure, not persistent activation.

## Evidence boundaries

Keep these claims separate:

1. **Source path works:** classification, selection, policy, explicit `-p`, and
   launcher attestation pass through the direct CLI.
2. **Plugin loads offline:** Hermes `PluginManager` registers the tool and
   recognizes its toolset in an isolated home.
3. **Installed bytes are current:** repository and installed plugin hashes match.
4. **Live profile exposes the tool:** plugin is enabled and its toolset is in the
   profile's CLI toolset list.
5. **Model-facing canary succeeds:** a fresh model turn actually calls the tool.

Never promote an earlier boundary to a later one. In particular, a direct handler
call bypasses model inventory, and `requested_profile == loaded_profile` from a
direct dry-run does not prove the parent model could call the plugin.

## Procedure

1. **Pin the repository and inspect actual wiring.** Record branch, HEAD, dirty
   state, plugin entrypoint, dispatch call site, launcher, and installation script.
   Compare repository and installed plugin files by content hash; filenames and
   plugin version strings are not freshness evidence.
2. **Read live exposure and derived-cache state without changing it.** Record the
   target profile's plugin status, `platform_toolsets.cli`, and
   `cache/plugin_toolset_keys.json` hash-or-absence. Treat plugin installed,
   plugin enabled, configured toolset, cached key, registered tool/toolset, and
   final model-facing schema as independent states. Read the plugin's declared
   schema too: if the handler consumes route, workspace, ledger, fallback, or
   request-bound fields that the schema does not expose, model-driven execution
   is blocked even when direct handler tests pass.
3. **Prove the zero-inference path first.** Run one direct CLI dry-run with a
   durable input, task ledger, event ledger, and result file. Require a concrete
   specialist, no generic/parent fallback, an explicit `hermes -p` command, and
   matching requested/loaded profile attestation.
   - **Shape the payload as a representative task of the target class.** The
     classifier reads title and intent text: review-flavored wording ("verify
     the…", "check the…") classifies as `review`, which admits only
     sentinel/skeptic candidates and then refuses them on
     `capability_mismatch:<capability>` when they do not declare it — the dry-run
     burns on `no_eligible_specialist`. For an implementation-class probe, word
     the task as an implementation ("Implement … with tests") and set
     `required_capability` to the canonical string from the routing table
     (e.g. `code_modify`), never an invented near-match.
4. **Run targeted and full tests in the repository's existing environment.** The
   plugin-host test must load through the real `PluginManager`; a fake context is
   only a unit test. Record current exit status and counts rather than relying on
   historical totals.
5. **Gate local profile mutation.** Installing current bytes, changing toolsets,
   enabling a plugin, or restarting a gateway are distinct actions. Obtain the
   exact authorization needed. If only a temporary canary is approved, persistent
   activation remains prohibited.
6. **Snapshot for exact rollback.** Copy the profile config and installed plugin
   directory to durable task artifacts; record plugin status, toolset list,
   content hashes, and `cache/plugin_toolset_keys.json` hash-or-absence. Derived
   caches matter because discovery can populate them after an early warning;
   restoring only config and plugin bytes does not restore the complete startup
   baseline. Do not print config contents because settings may contain sensitive
   references. Prepare restoration before applying changes.
7. **Apply only the canary delta.** Use the repository installer for plugin bytes,
   `hermes -p PROFILE config set platform_toolsets.cli '[hermes-cli, noesis_specialist_router]'`,
   and `hermes -p PROFILE plugins enable noesis-specialist-router`. Before any
   model turn, run the supported offline plugin doctor and an isolated blocking
   discovery/schema-assembly check through the installed Hermes implementation.
   Verify the exact tool name, toolset key, schema fields, and all three exposure
   surfaces without relying on manual cache warming.
8. **Run exactly the authorized fresh-session canary.** Point repository-root,
   task-ledger, and event-ledger environment variables at durable paths. Require
   exactly one `noesis_specialist_delegate` call with `dry_run=true`, generic
   fallback disabled, and unchanged JSON output. Bound turns and wall clock.
   If the approval allows only one provider attempt, do not spend a separate
   model preflight and then call that preflight outside the budget.
   - **When calling the tool in a desktop session, pass `ledger_path` and
     `events_path` explicitly in the tool arguments.** Desktop plugin tool
     hosts do not inherit the profile's `.env` (dotenv is loaded by the CLI
     bootstrap, not the plugin host), so the handler's
     `os.environ["NOESIS_TASK_LEDGER"]` fallback is unset and the call refuses
     `no_configured_ledger` even though the session worker process carries the
     variable. The explicit args are the handler's documented escape hatch;
     verify the record landed by tailing the ledger rather than trusting env
     inheritance from any other process.
9. **Classify the outcome at the earliest failed boundary.** If Hermes says the
   message was not sent, or no session/model turn exists, record
   `dispatch_not_delivered`; no plugin call, child launch, or reviewer verdict
   occurred. Preserve stdout, stderr, timing, profile/provider/model, and absence
   of plugin ledgers. Diagnose `Unknown toolsets` by correlating the warning time,
   plugin-discovery completion, cache mtime/key list, and the installed source's
   nonblocking-vs-blocking lookup order. If the key appears only when discovery
   completes later in the same startup, the root cause is stale pre-discovery
   validation—not a naming error; propose synchronization of explicit-include
   validation and platform-tool assembly rather than cache prewarming. Diagnose
   credentials independently: an unscoped `no available entries` line plus a
   generic model error does not distinguish absent applicable entries,
   exhaustion, cooldown, expiry, profile/store mismatch, or route mismatch.
   Never infer one from the other or reset credentials to probe.
10. **Restore immediately and verify by content.** Disable the plugin, restore the
    exact config, plugin bytes, and plugin-toolset cache (or its original absence),
    then verify status, toolsets, and every manifest entry. When comparing
    `shasum` manifests produced from backup and restored paths, compare digest
    columns rather than whole lines—the path columns necessarily differ. Label
    restoration as a checkpoint with its verification timestamp: a later,
    independently authorized config write can make the current file differ
    without invalidating the earlier rollback evidence, and must be reported
    separately rather than silently reverted. Do not retry a failed canary unless
    the authorization includes retry and route budgets.
11. **Resolve source drift through a deployment owner.** Hash repository and
    installed plugin files individually; a matching manifest does not imply a
    matching entrypoint. Inspect the existing configuration-management role
    before proposing installation changes. A one-time copy script explains stale
    bytes but is not ongoing ownership: persistent rollout needs one declarative
    owner that pins source identity, stages and doctors bytes, installs atomically,
    changes profile config through supported commands, records a secret-free
    manifest, and restores config/plugin/cache on failure.

## Verifying the launch record

A `success: true` canary payload proves routing and identity, not result
validation. Check, in order:

1. `launch_command` argv carries the enforced pair (`--provider <provider-id>
   -m <model>`). The payload's `model_provider`/`model_id` fields are
   capability-index defaults, not the launched pair — never cite them as
   execution evidence.
2. `attestation.requested_profile == loaded_profile`, and `profile_path` sits
   under `<workspace>/.noesis-fallback-session/profiles/<id>` — that path shape
   is the workspace-isolation proof, and `manifest_sha256` binds the loaded
   identity bytes.
3. The reservation records epoch, preflight decision, and
   `fallback_policy: deny`.
4. After the child exits, look for artifacts in the workspace. Exit 0 with an
   empty workspace means no artifact-level verification was possible — say so.
   The child's handoff text is the `captured_stdout` field (bounded, redacted)
   inside the ledger's `launch_handle_persisted` record under
   `task.delegation.launch_reservation`, alongside `stdout_digest`; read it
   from there for the ACCEPT-phase audit.

## Reporting

Report implemented, tested, direct-attested, plugin-loaded, model-facing-called,
executed, accepted, activated, and restored as separate statuses. Lead with the
first unproven boundary. Give the durable artifact path and result hash, and state
whether any provider request, specialist inference, persistent config, source
change, commit, push, merge, or deployment occurred.
