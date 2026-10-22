# Protocol-adapter architecture planning

Use this recipe when extending Noesis delegation across native/local execution,
Agent Client Protocol (ACP), Agent2Agent (A2A), or another interoperability
transport. The output is an architecture amendment and implementation plan, not
implicit permission to install, activate, invoke, expose, or spend.

## Procedure

1. **Freeze the authority and authorization boundary.**
   - Record what may be inspected or edited and what remains held.
   - Keep task admission, approvals, budgets, leases, revocation, durable state,
     recovery, review, and acceptance under the existing Noesis control plane.
   - Treat transport sessions and remote task IDs as correlations, never grants
     of authority.

2. **Re-establish current repository and runtime identity.**
   - Capture `git branch --show-current`, `git rev-parse HEAD`, and
     `git status --short` for every relevant repository.
   - Capture the installed runtime version and source revision separately.
   - Read the actual dispatch, task-contract, persistence, cancellation,
     provenance, review, and acceptance paths before proposing fields or APIs.
   - Inspect deployment roles for pinning, configuration ownership, validation,
     rollback, ignored failures, and default enablement; a role or inventory
     toggle is not deployment proof.

3. **Classify every claim into four evidence strata.**
   Use one table with these columns:
   - intended architecture;
   - implemented repository behavior;
   - installed runtime capability; and
   - verified deployment.

   Label source presence as capability only. Require observed process/service,
   protocol, identity, and end-to-end evidence before calling something deployed.
   Preserve historical plans and registry entries as leads, not facts.

4. **Separate protocol direction and scope.**
   - For ACP, distinguish a worker/server surface from an outbound client.
     Confirm the exact protocol version, initialization/capability negotiation,
     session create/continue behavior, prompt/update/result flow, permission
     requests, cancellation, and failure handling against the chosen worker.
   - For A2A, distinguish inbound service exposure from an outbound client.
     Treat Agent Cards as untrusted discovery metadata; validate configured
     identity, endpoint, authentication, disclosure policy, capabilities,
     protocol version, status/artifacts, and cancellation before sending data.
   - Do not infer a general client from a protocol server or a vendor-specific
     shim; direction and worker compatibility are independent properties.

5. **Map onto the existing lifecycle before adding storage.**
   Reuse task ID, admitted attempt/epoch, assignee/runtime identity, contract
   revision, lease, approval, budget, launch reservation, handoff, artifact
   digest, review, and acceptance records. Add only missing adapter-neutral
   values, typically:
   - adapter kind;
   - expected and observed worker identity;
   - negotiated protocol/version/capability snapshot;
   - protocol session/task/context correlation;
   - ordered progress and partial-artifact records;
   - usage/cost when known; and
   - cancellation observations and uncertainty reason.

   Unknown usage remains unknown, never zero. Adapter-reported success creates a
   candidate at most; it never marks the task accepted.

6. **Make failure semantics explicit.**
   Model `cancel_requested`, `cancel_acknowledged`, `execution_stopped`, and
   `authority_revoked` separately. Do not promise exactly-once execution or
   equate transport cancellation with process termination. After an ambiguous
   outcome, revoke authority, retain partial evidence, quarantine the attempt,
   and block automatic redispatch until reconciliation proves retry safety.
   Adapter failure must not silently switch worker, profile, provider, model,
   transport, endpoint, or approval context.

7. **Choose the smallest qualification slice.**
   Start with one named existing specialist, one explicit transport, one process
   or endpoint, one admitted attempt, one session/task correlation, fail-closed
   permissions, bounded requests/concurrency/time/cost, and no fallback. Use a
   fake transport and transcript fixtures first. Preserve native/local execution
   as the regression baseline. Defer session continuation, discovery, fan-out,
   remote deployment, and live inference unless the first slice requires them.

8. **Gate A2A on a concrete remote-service requirement.**
   Require a named independently deployed service, owner, endpoint, authenticated
   identity, capability unavailable through native/ACP, data classification,
   remote state/lifetime, cancellation/status/artifact support, limits, and
   operational value. Start with an explicit allowlisted endpoint. Add a registry
   only when multiple approved dynamic services make static ownership materially
   inadequate; discovery never authorizes dispatch.

9. **Amend the existing durable goal.**
   - Locate the authoritative standing-goal document; do not create a duplicate.
   - Reconcile stale completion claims and acceptance tables so the amendment
     does not say both “complete” and “planned.” Preserve historical chronology
     explicitly when useful.
   - Include: amended goal, ADR, current-state/gap table, phased backlog with
     dependencies and acceptance criteria, smallest first slice, A2A trigger,
     exact held actions, and unresolved blockers.
   - Keep the current canary or qualification blockers separate; a new protocol
     is not a remedy without evidence.

10. **Verify the documentation amendment.**
    - Run `git diff --check -- <goal-file>`.
    - Check balanced code fences, required headings, and table row delimiters
      with a small deterministic script.
    - Scan the edited document for credential-shaped literals. Use a high-entropy
      pattern (for example `sk-` followed by at least 20 token characters), not a
      short prefix that misclassifies ordinary words containing `sk-`.
    - Record the scoped diff, path, and SHA-256; state whether markdown lint was
      available rather than implying it ran.
    - Recheck repository status and report that implementation, runtime changes,
      commit, push, and merge did not occur unless independently authorized.

11. **Execute a bounded offline contract slice without creating new authority.**
    - Freeze the dirty-worktree baseline before editing: branch, full HEAD,
      upstream, complete porcelain status, staged and unstaged diff names,
      worktree list, a binary tracked diff, and hashes for pre-existing untracked
      files. Save this outside the repository so unrelated work remains provable.
    - Trace the existing adapter protocol, launcher call site, authoritative task
      model, serialization/rehydration, schemas, duplicate reservation path,
      cancellation path, and acceptance gate before introducing types.
    - Prefer immutable projection types over persistent fields. A request/result
      projection can carry task/attempt/epoch, worker binding, approval/scope,
      lease/revocation, budget, provenance, progress, artifacts, cancellation,
      and unknown usage without changing the ledger schema. If no durable value
      is missing, do not change serialization or schemas merely for symmetry.
    - Preserve native compatibility with an additive adapter entrypoint: let the
      control plane build the normalized request when the runtime supports it,
      but retain the legacy launch signature for existing test doubles and
      adapters. Validate the expected runtime profile against the persisted
      binding; do not require assignee and runtime profile strings to be equal,
      because a legitimate roster may map one to the other.
    - Write the contract test before the module so the first run fails for the
      missing boundary. Then implement the smallest mapping and rerun focused
      native, schema, artifact, cleanup, and acceptance suites before the full
      suite.
    - Keep the fake protocol peer in-memory and dependency-injected. It must have
      no subprocess, network, credential, model, tool, or operational path.
      Pin its vocabulary as test assumptions and label wire framing, exact method
      names, continuation, and acknowledgement semantics unverified against the
      installed runtime.
    - Test request/capability/session correlation, ordered progress and terminal
      result, fail-closed permission requests, malformed/unsupported messages,
      early exit, timeout, partial uncertainty, cancellation request vs
      acknowledgement vs observed stop vs authority revocation, duplicate
      suppression, and explicit restart reconciliation. Keep unknown usage/cost
      as `None`; never infer a delivery guarantee from the fixture.

12. **Freeze a dirty-worktree candidate for external review.**
    - Enumerate only the files in the authorized slice and hash their final bytes
      into a pure `candidate-files.sha256` file that `shasum -a 256 -c` can verify.
      Keep baseline metadata and test chronology in a separate manifest; mixing
      prose into the checksum file creates format warnings and weakens the review
      recipe.
    - Build the review patch from both tracked and new files. `git diff` omits
      untracked files, so append `git diff --no-index --binary /dev/null <file>`
      for each new candidate file. Hash the resulting patch separately.
    - Re-run checksum verification after every final document edit. Any byte
      change creates a new candidate identity and invalidates pending verdicts.
    - Prepare Sentinel first and Skeptic only on Sentinel PASS, both bound to the
      pure file-manifest digest. If the authorization forbids provider requests
      or real worker invocation and review is operator-mediated, stage one
      copy-ready packet and report `Sentinel pending / Skeptic gated`; do not
      substitute an in-session reviewer route or claim a disposition.

## Evidence ladder

Report each level separately; a lower level never qualifies a higher one:

1. mocked protocol contract;
2. real local process/session behavior;
3. installed-runtime integration;
4. live model-facing delegation; and
5. verified distributed operation.

## Pitfalls

- **Never collapse persona, profile, host, stack name, and service identity.**
  Verify each independently because legacy naming often survives after control
  authority moved elsewhere.
- **Never use an enabled inventory flag as deployment evidence.** Configuration
  expresses intent; it does not prove a running, reachable, qualified service.
- **Never reuse a vendor-specific protocol shim as a general adapter without a
  capability gap review.** Vendor defaults, permission behavior, continuation,
  model selection, and cancellation can violate Noesis policy.
- **Never let protocol metadata expand admitted scope.** Advertised capabilities
  and Agent Cards are untrusted inputs, not approvals.
- **Never bury authorization boundaries at the end of the plan.** Put the
  permitted and held actions in the standing goal so later phases cannot treat
  architecture acceptance as execution approval.
