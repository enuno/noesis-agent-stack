# Credential reachability diagnostics

Use this reference when a specialist launch fails before a model turn because the isolated child cannot resolve credentials and the supervisor is not an executor.

## Decision sequence

1. Confirm non-delivery from the launch evidence: zero model turn/provider request and a local missing-credential category.
2. Preserve the failed task and quarantined idempotency key; never reuse either for the diagnostic.
3. Inspect the installed launcher and resolver source before invoking anything:
   - supported credential names;
   - target-profile binding;
   - source ordering and precedence;
   - whether each source is mapped or bulk;
   - helper command behavior;
   - environment inheritance/filtering;
   - cache, install, timeout, and error-output behavior.
4. Determine executor availability independently of credential availability. A broken child route does not grant the supervisor execution authority.
5. If an eligible executor already exists, give it one bounded, read-only contract. Otherwise prepare an operator-run procedure and stop awaiting its redacted receipt; do not ask again for authorization already granted.
6. Run non-secret evidence collection independently where possible, so a resolver stop does not prevent checksums or provenance capture.
7. Interpret the receipt conservatively and propose repair; never mutate credentials, routes, or block state during diagnosis.

## Probe construction rules

- Begin with an empty or explicit allowlisted process environment; preserve only the bootstrap variables required by the inspected source.
- Do not source an interactive shell or inherit the complete parent environment.
- Never copy `.env`, auth files, or resolver configuration into the isolated attempt home.
- Do not execute a configured command helper until its source has been inspected. Exclude it when it cannot supply one of the approved target names.
- For bulk sources, keep the returned mapping process-local, inspect only approved names, clear values before serialization, and document that the backend itself may enumerate a broader container.
- Disable auto-install and persistent secret caches for a one-shot diagnostic unless the operator expressly authorized them.
- Send helper stdout/stderr to a discard sink; do not retain it in an exception, receipt, transcript, or task ledger.
- Bound the whole process with an explicit deadline and one-attempt budget.
- Do not contact the inference provider. Secret-manager access is not provider validation.

## Receipt semantics

Allow only:

- target profile;
- resolver source location or API version;
- approved credential variable name;
- non-sensitive source type/name;
- source success/failure;
- winning source and authoritative status, when the resolver exposes them;
- `present: true|false|null`;
- sanitized error category;
- independent checksum/provenance result.

Interpretation:

| Source result | `present` | Meaning |
|---|---:|---|
| success, non-empty target | `true` | Locally resolvable only; provider acceptance/quota/funds remain unknown. |
| success, target absent/empty | `false` | The inspected source completed but did not supply the target. |
| source error, timeout, auth prerequisite, or unsafe helper | `null` | Unknown; never collapse to absent. |
| probe not executed | omitted or `null` plus `not_run` | Prepared work is not observed evidence. |

Never print, hash, fingerprint, persist, or return a credential value. A checksum applies to the authorized document/artifact only, never to a secret.

## Repair gate

If the target resolves, propose a provider-scoped launcher bridge that binds to the attested source profile, forwards only documented target names, replaces broad environment inheritance with an allowlist, preserves isolated-home/fallback denial, and tests missing source, source failure, wrong-profile access, unrelated-secret exclusion, and all output channels for redaction.

Treat that bridge as a qualified runtime/control-plane change: require fresh independent security and adversarial review plus regression qualification before another dispatch.

If the target does not resolve, request the smallest explicit binding decision. Do not create a credential or choose another provider implicitly.

## Full route-readiness record

Credential presence is one field, not the route verdict. For each proposed delegate, preserve these independently:

| Dimension | Required evidence | Do not infer from |
|---|---|---|
| Profile-local auth | Local, refresh-free presence or pool status for the target profile | Another profile's status or ambient supervisor credentials |
| Selected route | Launcher/policy resolution of lane, provider, and pinned model | Capability-index metadata or a profile filename |
| Child credential | Presence through the exact child `HERMES_HOME` and spawn environment, with values suppressed | Installed-profile auth status |
| Provider acceptance | One authorized bounded request accepted by the named endpoint | Dry-run, model listing, or local presence |
| Entitlement | Provider response or supported account interface for the exact model | A model appearing in a static catalog |
| Capacity | Supported quota/usage/status interface for rolling allowance, RPM/TPM, credits, and spend limits | Login success or one tiny accepted request |
| Budget | Operator-approved envelope plus an enforceable admission/control point | Timeout, token estimate, or undocumented subscription headroom |

Use four labels only:

- `verified`: fresh direct evidence for the named boundary and fact;
- `currently_callable`: a bounded request was accepted, but task capacity is not proven;
- `unknown`: no supported fresh evidence exists;
- `blocked`: an affirmative auth, entitlement, policy, reconciliation, rate, quota, or control denial exists.

Every readiness row records collection time, expiry, evidence boundary, and sanitized failure category. Expire it immediately on credential, route, model, profile-manifest, policy, or relevant provider-state change. Never reuse historical success as fresh readiness.

## Source-convergence gate

Before proposing a persistent route update, compare every authoritative or materialized layer that can disagree:

1. profile roster/application source;
2. agent contract;
3. canonical model catalog and aliases;
4. routing policy and reconciliation record;
5. generated/live repository artifact;
6. installed profile metadata;
7. materializer input and validation behavior;
8. launcher-resolved tuple and child manifest.

List each layer separately and ask for a source-precedence decision when they conflict. Do not pick the most convenient declaration. Never hand-edit generated/live artifacts; repair the source and materializer, then prove source/materialized equality.

Inspect materialization smoke tests before relying on them. A `LANE_OK`-style check is a real provider request, not read-only validation, and may omit request, output-token, turn, and USD controls. Keep it disabled until its exact request/cost envelope is approved; profile presence alone is not route convergence.

## Workload- and cost-aware selection

Apply the ordering below; cost optimization starts only after the first three gates pass:

1. policy, privacy, execution compatibility, and reviewer independence;
2. demonstrated workload capability and required quality;
3. current authentication, entitlement, availability, and approved capacity;
4. lowest expected cost per accepted result;
5. latency when it materially affects the task.

Treat subscription capacity as a cost class, not as unlimited allowance. Prefer it only when the installed execution interface can use it and current capacity evidence supports the bounded task. Do not replace complex architecture, legal synthesis, implementation, or security review with a smaller model solely because its nominal price is lower. Reviewer route independence is a correctness gate, never a discountable cost.

When no route passes every required gate, report “no qualified route” and list preferred candidates separately. Do not call a candidate “recommended” without its unresolved gates beside it.

## Canary-control checklist

Represent and verify each control independently:

- subprocess deadline;
- agent runtime budget;
- model-turn limit;
- provider-request limit, including internal retries;
- input and output token ceilings;
- monetary pre-spend ceiling;
- provider/account quota or subscription cap;
- fallback policy;
- task retry budget.

A capture-byte limit is not a generation-token limit; one subprocess attempt is not one provider request; a wall-clock timeout is not a USD cap; a post-hoc usage ledger is not pre-spend admission. Trace every requested limit to the actual child command, config field, provider API parameter, or admission gate. If a hard limit cannot be enforced, stop before the probe or delegation and ask the operator to approve either a reviewed control-plane change or a revised envelope that explicitly leaves that limit unenforced.

## Live probe sequence

Only probe after source convergence, policy eligibility, child credential reachability, and canary controls are established. The probe contract must name the exact profile/lane/provider/model, synthetic prompt, one request including internal retry behavior, minimum supported output limit, maximum cost, no tools, no external actions, deadline, expiry, and sanitized receipt fields.

Classify success as `currently_callable` only. Keep capacity `unknown` unless a supported account/status/usage interface reports enough remaining allowance for the bounded task. Classify authentication, entitlement, quota, rate limit, provider outage, and policy denial separately; never relabel one as another. Do not retry an unchanged auth, quota, or policy failure.