# Council phase labels and seat credentials

Use when a Council mission names a gate letter, or when changing how a seat child gets credentials.

## Phase letters

Read the Council ADR phase table before using a gate letter from a mission packet. In that table, Phase D is security and failure testing. Phase E is runtime qualification plus a separately authorized live canary. A packet that calls the live canary Gate D is using the wrong name. Correct new documents. Do not rewrite historical packets so they look as if they always used the ADR names.

If the operator has authorized you to author the missing threat model, author it and label every new requirement as new. Do not stop solely because the ADR exit line has no checklist. A newly authored model is not proof the phase passed. Report verified controls and residual rows separately.

## Seat credential isolation

Trace how the child discovers credentials before choosing a fix. The canonical child reads process environment and files under the isolated HERMES_HOME. A parent-environment copy plus a denylist of ambient inference keys is not isolation: undeclared secrets still cross, and secrets that exist only in a parent resolver never reach the isolated home.

Repair with an explicit contract:

1. Allow only named env vars and caller-supplied values. Never copy a parent .env, auth store, or keyring into the seat home.
2. Fail closed before any child process when a required name is missing or empty. The error names the variable and must not contain the value.
3. Write declared files only as a single path segment under the isolated home, mode 0600, and remove them when the spawn call returns. Unlink is not secure delete.
4. Keep identity files (SOUL.md, honcho.json) separate from credential files.
5. scope none means no credentials are declared. It is not evidence that credentials exist. A live canary must not use it.
6. Profile-show may still copy the parent environment. Do not claim that path is isolated unless that call was changed and tested.
7. An injected council launcher is not the canonical adapter. A new seam class does not bind every dispatch caller. Say which callers remain unbound.
8. Do not treat an offline -z stub as stream-json readiness, monetary enforcement, or production process control.

## Tests and CI bookkeeping

The combined orchestrator workflow asserts an exact passed count, not a floor. Run the suite, record the observed count, then update only that assertion and the comment that records why the count moved. The local pytest line is not execution of the workflow job. Focused-job floors are separate; do not change them unless those jobs gained tests.

A source scan rejects sk- shaped literals in the test tree. Build synthetic secrets by concatenation in the test source so the file does not contain the contiguous token. The runtime value can still exercise redaction.

Replace declared secret values before the token regex. The regex can consume an `sk-` prefix and leave the rest of the same value in stdout, stderr, timeout text, and re-raised exceptions. A test whose secret is entirely matched by that regex stays green if the declared-secret replace is removed. Use a synthetic value the regex does not fully consume, and assert both that the tail is absent and that the declared-secret marker is present.

## Repair base

Do not stack a local launcher experiment onto a pull-request repair merely because the experiment exists. Read whether its real-subprocess refusal would block the spawn the pull request still intends to make. If it would, keep the experiment on its own commit and repair the demonstrated defects on the pull-request head. Do not spend the authorized repair cycle producing only that experiment, and do not block the offline repair on the broken worker route repairing itself.

An owner-lock symlink prepared in the effective named-profile home is path preparation only. It does not prove gateway liveness, authentication, selected profile, or successful attachment. Do not start a real subprocess to qualify it unless that launch is separately authorized. A rejected placement stays a negative control. Do not reuse its digest.

## Credential write and attempt identity

On a partial write failure, remove only files this call created. Leave pre-existing files. Refuse a symlink credential directory, and a symlink isolated home, before any write. State the remaining check-then-open race. Do not claim race-free containment from one existence check.

Budget closure keys the execution attempt, not the parent task alone. A later seat or round needs its own traceable key built from parent, seat, round, and attempt. The parent task id stays in the child environment. Repeating the same explicit round must still be refused after closure. Do not disable closure, and do not mint an untraceable random id, to make a second seat succeed.

When you add a required seat or round field, update every existing test call that constructs the seat. A call that omits the new field fails before it reaches the behavior the test was written to check.

Unlink credential files by name through the directory descriptor captured at creation. A later pathname lookup follows a rename and can delete a replacement of the same name. `O_NOFOLLOW` on that open covers the opened directory's final component only. Do not claim ancestors above the workspace were walked.

Transfer that descriptor onto the created-files object before the failure path closes it. Assigning it only after every write succeeds leaves rollback on a pathname unlink, which a replacement directory can redirect. Record the created name when the file is opened, not after the write returns, or a failed write is omitted from the descriptor unlink.

Do not put created-name or owned-directory lists on the class body of a list subclass. Every instance shares those lists, so one attempt's cleanup unlinks another attempt's names. Initialize them on the instance.

Do not invent a round from the launcher's call count. Require the caller's explicit positive integer. A missing round must fail before inference, or existing tests no longer prove the behavior they name.

Stamp that round onto a copy of the seat budget at the engine call, not only in the dispatch adapter. A duo session's two rounds must be distinct integers. One fixed value on the seat budget cannot separate them. Copy the session fencing epoch onto that same budget when it is already a non-negative integer. Do not hardcode epoch 0 on the launcher call if the session carries an epoch. If an absent epoch still defaults, say that residual. Do not claim parent-task epoch fencing.

If the pinned hermes argv has no verified output-token flag, refuse a real spawn before inference when a cap is requested. An injected process runner proves the adapter seam, not that the real transport enforces the cap. Do not invent a CLI flag to make the suite green.

Do not turn an unexpected spawn exception into a returned blocked result. The control plane records an uncertain handle only when the exception escapes. Redact declared secret values, then re-raise the same exception type.

An in-process attempt budget does not survive restart. Do not add a second ledger or sidecar file for closure.

If the mission has not authorized a schema or replay change, stop and name the existing store method that would have to be passed into the launcher. `reserve_launch` is one reservation on the parent task and moves that task through claimed/running. Do not reuse it for per-seat, per-round attempts.

If schema and replay changes are authorized, fold the attempt on the existing store:

1. Fence before any inference spawn, and wait for the store's durable write. A close recorded only after spawn does not cover a crash in between. A crash after a successful fence must not look unused on replay.
2. If the store is missing, replay is already failed, or the write fails, refuse the spawn. Do not fall back to the in-process budget.
3. Replay must fold the new event. A control-event writer that current replay ignores is not durable. Malformed payloads set `replay_error` and fail closed, the same way quarantine does.
4. Transitions are monotonic: absent to fenced, then fenced to closed or uncertain. Closed and uncertain are not retryable. Duplicate admission under the store's existing exclusive lock must not both pass.
5. Stamp the new schema version only on the new records. Do not bump the constant used by breaker and quarantine events, or existing records change version.
6. Do not append attempt or schema-fence records to the breaker-event list. `latest_breaker_event` would then return the wrong record.
7. When settling, copy task, seat, round, and epoch from the fenced record. Do not re-parse the attempt id or substitute epoch 0.
8. An older reader that ignores unknown events can reuse a fenced attempt. That is not safe compatibility. The fence record must be a shape that reader already fails closed on, such as a `task` object it cannot rehydrate, and the new reader must recognize that record before the generic task branch. Say so. Do not call the pair compatible. A test that calls the current rehydrate helper on that marker is not execution of a historical binary. Do not write the workflow comment as if it were.

After an ambiguous timeout, assert the reconstructed ledger outcome is `uncertain`. A second-launch refusal also passes when only the pre-spawn fence, or the in-process budget, closed the attempt.

## Publication after review

An expired exact-action confirmation is not approval. Re-present the same commit, push, body, or merge action. Do not restart implementation or review when the candidate digest is unchanged.

Recompute the reviewed digest immediately before staging and again from the committed paths. Index bytes must match the working tree. A green pre-commit line is not proof the hook left the bytes alone. If the committed digest differs, stop. Do not amend to hide it.

A workflow count comment edited after review is a new candidate. Do not treat the earlier approval as covering that comment.

After a non-force push, read the pull-request head again if the first read still shows the previous SHA. The branch tip can move before the pull-request object does. Do not treat that lag as a failed push or as a completed publication.

Do not request a merge confirmation while the limitation ledger or threat-model exit reading still says the phase exit is not met, unless a cited policy explicitly allows source merge to precede that exit. A mergeable pull request and an empty review decision are not that policy. A file-tool APPROVE is not a GitHub review.

Scratch copies of a prepared pull-request body are pruned. Before re-asking
a timed-out confirmation, confirm the body file still exists and restore the
exact previously presented text if it does not. Do not draft a new body and
call it the same confirmation.

`gh pr view --repo` without a number errors even after create printed a URL.
Read the number from that URL and view that pull request before claiming the
head binding.

## Canary preflight and signal confirmation

A token gate, attempt lock, or post-hoc usage report is not a hard currency
ceiling. Do not fill an unresolved safety field (host, pin, provider, model,
credential env, reviewer, monetary mechanism) with an assumption. A fail-closed
preflight refuses missing, blank, and the literal UNRESOLVED; refuses a deferral
choice; refuses a Hermes pin other than the one that was actually qualified;
and refuses a credential value present in the proposal without echoing it.
A passing preflight is not authorization to launch.

Do not treat `_signal_process_group` returning False as "still running" or as
permission to spawn again. False means not confirmed gone within the grace,
including a zombie the caller has not yet reaped. Callers must quarantine,
settle the attempt uncertain, and close the budget.
