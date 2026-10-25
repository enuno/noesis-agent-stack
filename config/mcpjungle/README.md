# MCPJungle tool inventory and least-privilege groups — Noesis

Catalog of the tools exposed by the Noesis MCPJungle gateway and the tool groups
that narrow that surface for individual Noesis profiles.

**Status: all 41 groups are deployed and verified live** (2026-10-25).

```
config/mcpjungle/
  tool-inventory.json   sanitised discovery snapshot (observed + inferred metadata)
  tool-groups.json      Noesis aggregate catalog (governance metadata, NOT deployable)
  groups/
    <group-name>.json   one MCPJungle-compatible group definition per group
  backup/
    gateway-state-backup.json   live gateway state: servers, groups, inventory pointer
```

Validation: `python3 scripts/validate_mcpjungle_groups.py -v` (offline, read-only).

---

## 1. What was discovered, and what "complete" means here

| | |
|---|---|
| Endpoint | `https://mcpjungle.tailf99a0.ts.net/mcp` |
| Registry base URL | `https://mcpjungle.tailf99a0.ts.net` |
| MCPJungle CLI / server | v0.4.6 / v0.4.6 |
| Discovery method | MCP JSON-RPC over streamable HTTP — `initialize`, `notifications/initialized`, then `tools/list` with cursor pagination |
| Protocol version | 2025-06-18 |
| Pages fetched | 1 (`nextCursor` absent, so enumeration terminated on the protocol's own completion condition) |
| **Unique tools** | **308** |
| **Source servers** | **20** |
| Discovery timestamp | 2026-10-25T21:26:38.385639+00:00 |

### What "complete" means

This is a **complete server-wide inventory**, not merely the view one connection
happens to expose. Two independent enumerations were performed and reconciled
name-by-name:

1. `tools/list` on the authenticated connection — 308 canonical names.
2. `mcpjungle list tools --registry https://mcpjungle.tailf99a0.ts.net` — the
   gateway's own registry-wide listing, which is independent of any client's
   permissions — 308 canonical names.

The set difference is **empty in both directions**, and **zero** tools are
disabled registry-wide. Every one of the 20 registered server names is an exact
canonical prefix of at least one discovered tool, so no server was missed.

### Hermes reports 312 — why the numbers differ

`hermes mcp list` shows **312** tools for this server. The difference is
accounted for exactly: 308 upstream tools plus **4 Hermes-synthesised per-server
utilities** (`list_resources`, `read_resource`, `list_prompts`, `get_prompt`).
Those four are Hermes constructs, not MCPJungle canonical tools, so they are
excluded from the inventory and from every group.

### Scope limits

This catalog covers **only what the MCPJungle gateway exposes**. Other MCP
servers are connected to Hermes directly and do not traverse MCPJungle, so a group
here does not constrain them:

- **UniFi** — connected directly as `unifi-local` (stdio, via Docker). No UniFi
  server is registered in MCPJungle, so no network-operations group exists here.
- **Beacon, local endpoint** — connected directly as `beacon` (stdio,
  `/home/elvis/.local/bin/beacon`), exposing 7 tools
  (`search_memory`, `get_memory`, `get_memory_context`, `search_activity`,
  `summarize_activity`, `get_activity_event`, `list_activity_filters`) against the
  host's own per-profile runtime log. This is a **different surface** from the
  `beacon-managed` server registered in MCPJungle, which is the hosted
  `https://mcp.beacon.sh` endpoint exposing 25 tools. Both are Beacon, but they
  are separate connections with separate tool sets: the groups in this catalog
  constrain the hosted one and have no effect on the local one.

A group therefore controls only the tools reachable through *its own* group
endpoint. It does not constrain `/mcp` on the main gateway, and it does not
constrain any directly-configured MCP server.

---

## 2. Compatibility evidence

All claims below are verified against **MCPJungle 0.4.6**, whose release tag is
`0.4.6` (not `v0.4.6`).

| Question | Answer | Evidence |
|---|---|---|
| Supported group JSON schema | `name`, `description`, `included_tools`, `included_servers`, `excluded_tools` — and nothing else | `pkg/types/tool_group.go` |
| Canonical tool-name format | `<server-name>__<tool-name>`, split on the **first** `__` | `internal/service/mcp/util.go` (`serverToolNameSep`, `mergeServerToolNames`) |
| How exposed names map to group names | Identically — the names `tools/list` returns *are* the names `included_tools` accepts. No rewriting, splitting or renaming is performed. | Verified against `tools/list` and `mcpjungle list tools`, both returning the same 308 canonical names |
| Group naming constraints | `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` — must start alphanumeric; then alphanumerics, underscores, hyphens only | `internal/service/toolgroup/toolgroup.go` (`ValidGroupName`) |
| Creation syntax | `mcpjungle create group --conf <file>` | `mcpjungle create group --help` |
| Update syntax | `mcpjungle update group --conf <file>` — replaces the definition outright; removed tools stop being reachable immediately | `mcpjungle update group --help` |
| Group endpoint paths | `/v0/groups/{group-name}/mcp` (streamable HTTP, preferred); `/v0/groups/{group-name}/sse` and `/v0/groups/{group-name}/message` (SSE, deprecated upstream) | `internal/api/tool_groups.go` (`getToolGroupEndpoints`), `internal/api/server.go` (`V0PathPrefix = "/v0"`) |
| Unavailable / disabled / removed tools | Creation **fails** if a listed tool does not exist or is disabled. A tool disabled globally is removed from every group endpoint, though the group definition still lists it. On restart, a group whose tools cannot be resolved initialises **empty** rather than failing startup. | `internal/service/toolgroup/toolgroup.go` (`CreateToolGroup`, `initToolGroupMCPServers`) |
| Group name changes | Not possible — `update group` keeps the original name | `internal/service/toolgroup/toolgroup.go` (`UpdateToolGroup`) |
| Who may create groups | **Depends on server mode.** In enterprise mode only an admin may; in development mode `requireAdminUser` short-circuits and any caller may. **This gateway is in development mode**, so group creation succeeded with no admin token — see "Server mode" in section 7. | MCPJungle 0.4.6 source, `internal/api/middleware.go` (`requireAdminUser`); live server behaviour verified 2026-10-25 |

### Allowlist policy

Every group in `groups/` uses an explicit `included_tools` allowlist. **No group
uses `included_servers`.** Broad server membership would silently widen a group
whenever an upstream server adds a tool; an explicit allowlist cannot.

---

## 3. The groups

41 groups, 305 tools assigned, 3 held out. Risk is the highest level among the
member tools, raised to the group's declared floor where the declaration is the
stricter judgement.

### Research and discovery

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `web-research` | 14 | low | signal, tracer, ledger, cartographer, steward, quill, skeptic, substrate, advocate | General web search, fetch and Q&A |
| `web-retrieval` | 5 | medium | signal, tracer, quill, scribe | Fetch, parse and crawl specific documents |
| `web-monitoring` | 4 | low | signal, tracer, substrate | Read existing monitors and check history |
| `web-monitoring-config` | 4 | high | signal | Create, edit, trigger, delete recurring monitors |
| `autonomous-research` | 3 | high | signal, tracer | Multi-step autonomous research agents |
| `academic-research` | 5 | low | signal, ledger, tracer | Peer-reviewed literature |
| `market-research` | 4 | low | ledger, steward, grid | Company, market and filings research |
| `browser-automation` | 2 | review-required | *(none proposed)* | Live browser: navigate, click, run browser code |

### Legal and regulatory

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `legal-research` | 24 | medium | advocate, tracer, skeptic, signal | Case law, opinions, dockets, courts, judges, oral argument, filed documents, and the MISJustice/YWCA corpus |
| `legal-citation-analysis` | 9 | low | advocate, tracer, skeptic | Extract, parse, verify, batch-resolve citations |
| `legal-regulations-research` | 27 | medium | advocate, tracer, skeptic | Codified CFR, Federal Register, rulemaking dockets and comments |
| `legislative-research` | 10 | low | advocate, tracer | State bills, committees, legislators, events |
| `legal-alerts` | 6 | high | advocate | Create/cancel alert subscriptions; request documents |

**Legal research is deliberately split from general web search.** `legal-research`
contains only authoritative legal retrieval. The two general-purpose searches whose
*names* sound legal — `linear__search_legal` and `firecrawl-search__firecrawl_gov_search`
— return web-index results, not primary sources, and are held in `web-research`
instead. Labelling them legal would be exactly the error the boundary exists to
prevent.

**The YWCA Missoula GitBook MCP is included in `legal-research`.** The server
`misjusticeallinace-ywcaofmissoula-pub` is registered at exactly
`https://www.ywcaofmissoula.com/~gitbook/mcp` and publishes the MISJustice Alliance
/ YWCA Missoula / MPD / County Prosecutors (2012–2025) corpus. Two of its three
tools are in `legal-research`:

- `misjusticeallinace-ywcaofmissoula-pub__getPage`
- `misjusticeallinace-ywcaofmissoula-pub__searchDocumentation`

Its third tool, `misjusticeallinace-ywcaofmissoula-pub__sendFeedback`, submits a
message to the documentation site. That is an outbound external communication, so
it is held in `communications-send` rather than in the read-only legal group.

### Source control, coding and automation

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `source-control-readonly` | 18 | low | forge, sentinel, skeptic, architect, substrate, cartographer | Repository content, history, branches, tags, releases, directory |
| `source-control-issues-readonly` | 10 | low | forge, sentinel, skeptic, cartographer, substrate | Issues, pull requests, issue metadata, review state |
| `source-control-write` | 14 | high | forge | Branches, files, pull requests, issues, reviews |
| `autonomous-coding` | 2 | high | forge | Delegate to the Copilot coding agent; request automated review |
| `coding` | 12 | medium | forge, architect, quill | Code search, SDK references, workflow-code authoring |
| `workflow-inspection` | 11 | medium | substrate, sentinel, architect | Read n8n workflows, versions, executions, tags |
| `workflow-authoring` | 5 | high | substrate | Create, update, archive, restore, unpublish workflows |
| `workflow-execution` | 7 | high | substrate | Execute, test, publish workflows and agents |
| `agent-infrastructure` | 10 | high | architect, substrate | Create, mutate, validate, version, retire agent drafts |
| `credential-inventory` | 1 | review-required | *(none proposed)* | Enumerate n8n credential identities |

### Documentation, memory, data and observability

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `library-docs` | 2 | low | forge, sentinel, architect, scribe, quill, cartographer | Library and framework documentation |
| `repository-docs` | 3 | low | forge, sentinel, architect | Generated repository wiki documentation |
| `platform-docs` | 4 | low | architect, forge, scribe, substrate | MCPJungle and Mintlify documentation |
| `docs-site-read` | 7 | medium | scribe, quill, architect | Read the operator's Mintlify site |
| `docs-site-authoring` | 12 | high | scribe, quill | Edit docs content, navigation, images (staged) |
| `docs-site-publish` | 3 | high | scribe, quill | Publish staged changes; manage workflow runs and their PRs |
| `platform-administration` | 5 | high | *(none proposed)* | Access control, domains, git sources, members, settings |
| `memory-retrieval` | 13 | medium | orchestrator, scribe, skeptic, forge, substrate | Recall lessons; search sessions; read findings and trace metadata |
| `memory-management` | 4 | high | scribe, orchestrator | File candidates; record review decisions; adjust trace visibility |
| `database-readonly` | 4 | medium | grid, scribe | n8n data tables; Mintlify deployment databases |
| `database-write` | 8 | high | grid | Create/extend/rename/delete tables and columns; edit database rows |
| `data-analytics` | 3 | low | grid, scribe | Docs-site analytics queries and reports |
| `observability` | 7 | medium | substrate, steward | Deployment status, run history, provider usage and cost |
| `security-audit` | 3 | medium | sentinel, skeptic, substrate | Secret scanning; Beacon security findings |

### Communications and external effects

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `communications-readonly` | 1 | low | scribe, herald | Read docs-site comment threads |
| `communications-send` | 13 | high | herald | Comments, replies, feedback, shared traces |
| `external-publication` | 6 | high | architect, scribe | Publish Beacon lenses to the marketplace |

### Design

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `web-design` | 5 | low | *(none proposed)* | Inspect Framer workspaces, projects, docs, assets |

### Deliberate overlaps

Five tools appear in more than one group. Each is a genuine multi-workflow tool,
and the overlap is named rather than removed:

| Tool | Groups | Why |
|---|---|---|
| `github__search_code` | source-control-readonly, coding | Locating an implementation site vs. reading source control |
| `github__get_file_contents` | source-control-readonly, coding | Same |
| `n8n__create_workflow_from_code` | coding, workflow-authoring | The authoring *input* vs. a change to an existing workflow |
| `beacon-managed__beacon_findings_list` | memory-retrieval, security-audit | One read serving both a memory recall and a security review |
| `beacon-managed__beacon_get_finding` | memory-retrieval, security-audit | Same |

No generic tool is copied into every group.

---

## 4. Held out of all groups — review required

Three tools are classified `review-required` and are **not** in any deployable
group. A fourth (`firecrawl-search__firecrawl_interact`) is held inside the
`browser-automation` group, which is itself flagged review-required and has no
proposed consumer.

| Tool | Reason |
|---|---|
| `court-listener__call_endpoint` | Generic REST client for arbitrary CourtListener endpoints. Path and method are caller-supplied, so it can reach write paths the curated legal allowlist excludes. Upstream marks it `readOnlyHint=true`, which its own purpose contradicts. Group membership cannot constrain a caller-chosen endpoint. |
| `framer__exec` | Executes a caller-supplied JavaScript program against a third-party SaaS project. Arbitrary code execution; the arguments bound the effect, not the class of effect. |
| `framer__create_project` | Persistent third-party state creation with no verified Noesis consumer. |

**Operator decision required** for each: is the capability needed at all, and if so
which profile may hold it under what approval path?

---

## 5. Coverage gaps — requested categories the inventory cannot support

| Requested category | Status | Reason |
|---|---|---|
| `devops-readonly` | **gap** | No DevOps or infrastructure server is registered. No Docker, Kubernetes, Terraform, Ansible or CI tool exists among the 308. The nearest surfaces are `workflow-inspection` and `observability`; naming either "devops-readonly" would misrepresent it. Infrastructure execution lives in `noesis-ansible` and the Hermes terminal toolset, not MCPJungle. |
| `network-operations-readonly` | **gap** | No network-device or network-automation server is registered. UniFi is a separate, directly configured Hermes connection (`unifi-local`) that does not traverse MCPJungle, so it cannot be an MCPJungle group. |
| `cloud-infrastructure-readonly` | **gap** | No cloud-provider server (AWS, GCP, Azure, Cloudflare) is registered. |
| `cloud-infrastructure-write` | **gap** | Same. The closest mutation surface is `platform-administration`, which manages one documentation site. |
| `blockchain-research` | **gap** | No blockchain, wallet, miner or DePIN data server is registered. The `noesis-ledger` domain can only be served by `web-research`, `academic-research` and `market-research`. |
| `financial-actions` | **gap** | No spending, transfer, trading, payment or wallet tool exists anywhere in the inventory. Every financial capability present is read-only research under `market-research`. The one payment-adjacent tool, `court-listener__pray_for_document`, sits in `legal-alerts` under a spending control. |
| `communications-readonly` (broad inbox) | **partial** | No mail, chat or SMS server is registered. The only communications read surface is the Mintlify comment thread. The Herald workflow has no inbox to read from. |
| `database-readonly` / `database-write` | supported | n8n data tables and Mintlify deployment databases. No generic SQL server exists; the one SQL surface (`mintlify__query_analytics`) is confined to the docs deployment's own analytics tables and is held in `data-analytics`. |
| `observability` | supported | Deployment status, workflow run history, execution records, provider credit/usage. No metrics, log-aggregation or tracing server (Prometheus, Grafana, Loki) is registered, so infrastructure telemetry is not reachable through MCPJungle at all. |
| `agent-infrastructure` | supported | n8n agent authoring, versioning, validation, retirement; Beacon as the memory and trace substrate. |
| `security-audit` | supported, narrow | Only GitHub secret scanning and Beacon's security findings. No SAST, DAST, dependency-audit or container-scanning server. |
| `source-control-readonly` / `source-control-write` | supported | The GitHub server, split across three groups. It is the only source-control server registered. |

---

### Consumer names are verified roster profiles

Every name in `suggested_consumers` is a key in `profiles/noesis-roster.yaml`. The
roster declares **16** profiles, and the validator fails the build if a consumer
name is not one of them.

**NoesisPraxis is not one of them, and is deliberately not used as a consumer
name.** The repository's own `STANDING-GOAL-FINAL-DELIVERABLE.md` records the
verified position: *"`noesis-praxis` is not an entry in `profiles/noesis-roster.yaml`
or `platform/runtime-reconciliation.yaml`. The current roster consolidates
Hermes-Core into `noesis-orchestrator`, mapped historically to the default profile.
`agents/noesis-praxis/` is retained as a council/aeon skill/runbook and legacy
identity."* NoesisPraxis is an intake and persona boundary, not a deployed
profile.

The infrastructure-operator role that these groups are largely designed for is
therefore represented by **`noesis-substrate`** — the roster's `infra-engineer`
profile (*"Infra, DevOps, cloud, networking"*, *"no production changes without
approval"*). `noesis-orchestrator` is the supervisor, and is proposed only for
memory recall and memory review, which match its roster domain
(*"Supervisor/routing; approval-gate enforcement; memory index"*).

The validator enforces this rule mechanically, so a persona name cannot silently
re-enter as a consumer.

---

## 6. Grouping is exposure control, not authorization

**A tool group controls which tools a client can see. It does not, by itself,
authorise anything.** A group does not:

- prove the agent is permitted to perform the action;
- enforce an approval gate — nothing in the file format expresses one;
- constrain tool arguments — `mintlify__query_analytics` accepts a SELECT, and
  `n8n__execute_workflow` accepts arbitrary input;
- prevent bypass through another endpoint — the main `/mcp` endpoint still
  exposes all 308 tools to any credential that can reach it, and the UniFi and
  Beacon connections are separate paths entirely.

A README that says "approval required" is documentation, not a control. For each
higher-risk group, the following must be enforced **outside** MCPJungle:

| Control | Applies to |
|---|---|
| **Per-client MCP identity** — a dedicated client token per consuming profile, with an explicit allow-list, never a shared token | every group |
| **Credential scoping at the upstream provider** — a GitHub token limited to in-scope repositories; a Mintlify token scoped to one deployment; an n8n token scoped to one instance; a CourtListener token limited to read access | every group touching a credentialed upstream |
| **Approval gate in the runtime** — a human approval step in the agent runtime or broker *before* the tool call, enforced by the toolset the profile holds, not by prose | all `high` and `review-required` groups |
| **Argument constraints** — where a tool accepts a path, endpoint, SQL statement or credential id, constrain it in the runtime's policy layer | `data-analytics`, `legal-research`, `credential-inventory`, `web-retrieval` |
| **Profile isolation** — one MCP connection per profile, pointed at that profile's group endpoint, so a mis-scoped call cannot reach a broader surface | every group |
| **Audit** — tool calls through a group endpoint logged with the client identity, so an action can be attributed | all `high` groups |
| **Kill switch** — a per-group revoke path; `mcpjungle delete group <name>` removes the endpoint immediately | all `high` groups |
| **Separate change authority from review authority** — the profile that executes holds no reviewer group, and the reviewer profile holds no write group | `source-control-write`, `autonomous-coding`, `workflow-execution`, `docs-site-publish` |

The `suggested_consumers` field in `tool-groups.json` is a **recommendation**, not
an enforcement. It records which profile the group was designed for. Whether a
profile actually receives it is a Hermes connection-configuration decision made
outside this repository.

### Independent QA boundary

`noesis-sentinel` (code reviewer) and `noesis-skeptic` (adversarial reviewer) are
reviewer-only per `profiles/noesis-roster.yaml` and their own SOUL files.

The validator enforces the boundary at **member level**, not by group risk
level: a group may not list either reviewer as a consumer if any member is
classified as capable of acting — `mutating`, `unannotated-mutation`,
`destructive`, `external-communication`, `persistent-or-autonomous`,
`configuration-change`, `access-control-change`, `external-publication` or
`broad-capability`. A group whose overall risk is `medium` can still contain a
mutating member, so the group-level risk alone is not sufficient evidence.

Both reviewers hold groups whose members only read:

`sentinel`: `source-control-readonly`, `source-control-issues-readonly`,
`library-docs`, `repository-docs`, `workflow-inspection`, `security-audit`

`skeptic`: `source-control-readonly`, `source-control-issues-readonly`,
`legal-research`, `legal-citation-analysis`, `legal-regulations-research`,
`web-research`, `security-audit`, `memory-retrieval`

Neither can write, delete, publish, spend or delegate. Reviewers do hold groups
that read sensitive data (`security-audit`, `memory-retrieval`, `legal-research`),
which a reviewer needs; reading sensitive data is not acting.

Note that `coding` is **not** proposed for either reviewer. It contains
`n8n__create_workflow_from_code`, which creates a workflow draft and is
classified `mutating`. `noesis-forge` and `noesis-architect` hold it, and they
are not reviewer-only.

Conversely, the implementation profiles (`noesis-forge`, `noesis-substrate`)
hold write groups but are not listed as consumers of any reviewer-only group.

---

## 7. Reviewing and (later) deploying

### Review only — safe, read-only, no mutation

```bash
# Current registry state (read-only)
mcpjungle list groups --registry https://mcpjungle.tailf99a0.ts.net
mcpjungle list tools  --registry https://mcpjungle.tailf99a0.ts.net
mcpjungle list servers --registry https://mcpjungle.tailf99a0.ts.net

# Inspect one group after it exists (read-only)
mcpjungle get group <group-name> --registry https://mcpjungle.tailf99a0.ts.net

# List only the tools currently active in a group
mcpjungle list tools --group <group-name> --registry https://mcpjungle.tailf99a0.ts.net
```

Note `mcpjungle list tools --group` shows only tools that **currently exist and are
enabled**. To see a group's full stored definition, including tools that have since
been disabled or deleted, use `mcpjungle get group`.

### Deployment — completed 2026-10-25

All 41 groups were created on the live gateway and verified:

```bash
mcpjungle create group --conf config/mcpjungle/groups/<group-name>.json \
  --registry https://mcpjungle.tailf99a0.ts.net
```

**Result: 41 created, 0 failed.** Verification was two-layer:

1. Every group's live definition was compared name-by-name against its source
   file — `name`, `description` and `included_tools` are identical for all 41.
2. Every group's MCP endpoint was probed with `initialize` + `tools/list`
   (discovery only — no tool was invoked). Each endpoint serves **exactly** its
   declared `included_tools`: 41/41 matched, 0 mismatches.

The main `/mcp` endpoint still serves all 308 tools. **Creating tool groups does
not narrow the main gateway** — narrowing a client requires pointing it at a
group endpoint. No Hermes client connection was repointed.

For updates and removal:

```bash
mcpjungle update group --conf config/mcpjungle/groups/<group-name>.json \
  --registry https://mcpjungle.tailf99a0.ts.net

mcpjungle delete group <group-name> \
  --registry https://mcpjungle.tailf99a0.ts.net
```

### Server mode: development, not enterprise

The gateway runs with **`SERVER_MODE=development`**, set in
`noesis-ansible/inventory/mcpjungle-k8s/group_vars/all.yml`. It was a deliberate,
operator-authorised switch on 2026-10-23 to enable the Dashboard UI, and the
ansible inventory records that the trust boundary for the resulting open access
is the tailnet itself.

The practical consequence, verified against the live server and the 0.4.6
source: in development mode `verifyUserAuthForAPIAccess`, `requireAdminUser` and
`checkAuthForMcpProxyAccess` all short-circuit. A **bogus token and no
`Authorization` header at all both receive HTTP 200 on admin-only routes**, and
`/mcp` answers unauthenticated. The enterprise-only routes (`/users`,
`/clients`, `/users/whoami`) return HTTP 403 *"this request is only allowed in
enterprise mode"*.

Two consequences for this catalog:

- **Group creation needed no admin token.** The admin token in Bitwarden
  (`MCPJUNGLE_K3S_DEFAULT_ADMIN_TOKEN`) was retrieved and confirmed working
  against the admin API, but the server accepts group creation from any caller.
- **Every group endpoint is reachable by any tailnet peer without a credential.**
  The groups narrow *which tools* a client sees; they do not narrow *who* can
  reach them. Until the server is in enterprise mode, the per-client identity
  and credential-scoping controls in section 6 cannot be enforced by the
  gateway, and the tailnet ACL is the only access boundary in force.

Switching to enterprise mode is **not** a configuration change: the mode is set
once at first initialization and switching requires a destructive database reset
that destroys every registered server, user, client and group.

### Endpoints

The route shape `/v0/groups/{group-name}/mcp` was verified from the MCPJungle
0.4.6 source before deployment, and every URL below is live and serving:

```
https://mcpjungle.tailf99a0.ts.net/v0/groups/<group-name>/mcp
```

Each group file and catalog entry is marked `"endpoint_status": "live"`.

### Backup

`config/mcpjungle/backup/gateway-state-backup.json` captures the live gateway
state: the 20 registered upstream servers, the 41 group definitions, and a
pointer to the 308-tool main-endpoint inventory. Upstream credentials are
**not** recoverable from it — every secret-bearing value in the richer
`/api/v0/server_configs` view is replaced by a non-reversible shape marker, and
the file was verified to contain none of the live secret values. Re-apply
credentials from the Bitwarden escrow if a restore is ever needed.

---

## 8. Refreshing the inventory and reviewing drift

The inventory is a **point-in-time snapshot**. Refresh it whenever the upstream
registry changes:

```bash
# 1. Discover (read-only, authenticated MCP session, follows nextCursor to exhaustion)
#    -> write the result to a scratch location, never over the committed file directly

# 2. Compare against the committed snapshot
python3 - <<'PY'
import json
old = {t["name"] for t in json.load(open("config/mcpjungle/tool-inventory.json"))["tools"]}
# ... compare against a freshly discovered name set ...
PY

# 3. Validate the committed artifacts after any update
python3 scripts/validate_mcpjungle_groups.py -v
```

### Drift to check on every refresh

| Drift | Signal | Action |
|---|---|---|
| Tool removed upstream | Name in `tool-inventory.json`, absent from a fresh `tools/list` | The group now references a non-existent tool. MCPJungle would reject a *create* with it; an *update* removes it. Re-scope the group and re-review. |
| Tool disabled upstream | Name present but marked disabled | The tool disappears from every group endpoint but stays in the stored definition. The group silently exposes less than the file says. |
| Tool added upstream | New name absent from `tool-inventory.json` | **Not** automatically included. Every group uses an explicit allowlist, so a new tool cannot widen a group. Decide deliberately whether it belongs. |
| Server added upstream | New server name | Same: no automatic inclusion. Re-run the taxonomy. |
| Tool reclassified | `risk_classification` in the inventory no longer matches the current description or annotations | Re-review the affected groups; a group declared `low` that gains a mutating member is a validator failure. |
| Upstream schema change | `input_schema` or `output_schema` differs | The group membership may still resolve, but the tool's real capability has changed. Re-read the description before trusting the risk classification. |

### New tools are never automatically included

This is the reason every group uses `included_tools` and none uses
`included_servers`. If a group used `included_servers: ["github"]`, then the next
tool GitHub published would silently become callable by every profile holding that
group. An explicit allowlist makes the blast radius of an upstream change zero
until a human decides otherwise.

---

## 9. Rollback guidance

Rollback for MCPJungle groups is **declarative**: a group's definition is
replaced wholesale by `update group`, and removed by `delete group`.

### The current baseline is already backed up

`config/mcpjungle/backup/gateway-state-backup.json` holds the live state as of
2026-10-25: all 41 group definitions, the 20 registered upstream servers, and a
pointer to the 308-tool inventory. **Upstream credentials are not in it** — they
must come from the Bitwarden escrow if a restore is ever needed. Restore servers
before groups: group creation validates every listed tool and fails if a tool
does not exist.

### Before any future change

```bash
# 1. Export the current definition of every affected group and keep it.
mcpjungle get group <group-name> --registry https://mcpjungle.tailf99a0.ts.net \
  > "rollback/<group-name>.before.json"

# 2. Record the exact pre-change tool set.
mcpjungle list tools --group <group-name> --registry https://mcpjungle.tailf99a0.ts.net \
  > "rollback/<group-name>.tools.before.txt"
```

Keep both files. `get group` shows the stored definition including tools that are
already disabled or deleted; `list tools --group` shows what is actually callable
right now. You need both to reconstruct state exactly.

### Rolling back a group

```bash
mcpjungle update group --conf rollback/<group-name>.before.json \
  --registry https://mcpjungle.tailf99a0.ts.net
```

`update group` takes the **original group name** from the file, and the name
cannot be changed. It replaces the definition completely. Removed tools stop being
reachable through that group's endpoint **immediately** — which is precisely why
the previous definition must be captured first.

### Rolling back a group that must not exist at all

```bash
mcpjungle delete group <group-name> --registry https://mcpjungle.tailf99a0.ts.net
```

Deleting a group removes only the group and its endpoints. It does **not** delete
the underlying tools or servers. Any client still pointed at that endpoint stops
working immediately — so roll the **client connections back first**, then delete
the group.

### Ordering for a safe rollout

1. Snapshot every affected group's definition (above).
2. Point the consuming client at the group endpoint and verify it sees **only** the
   expected tools.
3. If verification fails, update the group back from the snapshot, or delete it and
   repoint the client to `/mcp`.
4. Only then, and only with explicit authorisation, retire the wider exposure.

### Partial rollback

Rollback is per group. A failed rollout of one group does not require reverting
the others — update that one group from its snapshot and leave the rest in place.

---

## 10. Redactions and information not available

**Redacted / not recorded:** no access token, authorization header, environment
secret or credential value appears in any artifact. The MCPJungle user token was
read from the local CLI credential store only to authenticate discovery.

A pattern scan across all 308 tools — bearer tokens, JWTs, provider API keys, cloud
access keys, 32-character hex secrets, credential assignments, credential-bearing
URLs and e-mail addresses — returned **zero hits**. Descriptions, schemas and
`_meta` are reproduced as returned; they contain tool contracts only, because no
live record data was retrieved during discovery.

**Not available:**

- Output schemas are absent for **270 of 308** tools because the upstream servers
  do not publish them. No output schema was inferred.
- MCP annotations carry no values for **6** tools (`CourtListener__status`,
  `GovInfo__describePackageOrGranule`, `GovInfo__searchGovInfo`,
  `deepwiki__ask_wiki_question`, `deepwiki__read_wiki_contents`,
  `deepwiki__read_wiki_structure`): the server returned an empty annotations object
  for each. The observed value is preserved verbatim. Each was classified from its
  description and schema alone, and each says so in its `risk_rationale`.
- Server-side per-client authorisation rules could not be inspected:
  `mcpjungle list mcp-clients` is refused for a user token in enterprise mode.
- Upstream credential scopes — which organisations, repositories, sites, cases or
  documents each configured upstream credential can reach — are not visible through
  this gateway and must be checked at the upstream provider.

---

## 11. Classification method

**Observed** metadata (name, source server, description, `inputSchema`,
`outputSchema`, MCP annotations) is copied verbatim from the server and stored
under its own keys. **Inferred** metadata (`inferred_capability_category`,
`risk_classification`, `risk_rationale`) is a Noesis judgement, kept separate so
the two are never conflated.

Annotations are **advisory only**. `readOnlyHint` and `destructiveHint` were
cross-checked against every description and input schema; where they disagreed,
the description and schema won. A tool whose name suggests a mutation was not
accepted as read-only on the strength of `readOnlyHint` alone. Twenty-two tools
carrying `destructiveHint=true` describe a configuration change rather than a
literal deletion — `manage_access_auth`, `update_workflow`, `mutate_agent` and
others — and each carries a corrected category and rationale in the inventory.

| Risk level | Meaning |
|---|---|
| `low` | Reads state and changes nothing. |
| `medium` | Changes state, reads sensitive data, or acts on records whose blast radius is not obvious from the tool name. |
| `high` | Destructive, publishes externally, spends money, or grants persistent autonomy. |
| `review-required` | Broad-capability or unusually ambiguous. Held out of ordinary groups pending an explicit operator decision. |

Distribution across the 308 tools: 197 `low` (`read-only`), 40 `medium` (`mutating`), 11 `medium` (`sensitive-data`), 26 `high` (`persistent-or-autonomous`), 14 `high` (`external-communication`), 9 `high` (`destructive`), 5 `high` (`configuration-change`), 2 `high` (`access-control-change`), 4 `review-required` (`broad-capability`).

---

## 12. Validation

`scripts/validate_mcpjungle_groups.py` is offline, deterministic and
non-mutating. It never contacts the gateway, never reads `~/.hermes`, never
invokes a tool, and never creates or updates a group.

```bash
python3 scripts/validate_mcpjungle_groups.py -v
```

It checks that all JSON parses; that every group file uses only MCPJungle
0.4.6-supported fields; that every group name satisfies the verified name
pattern; that no group is empty; that no group contains duplicate tool names;
that every membership resolves to an observed tool; that catalog membership
matches the individual group files; that every discovered tool is assigned or
explicitly unassigned with a reason; that a group declared `low` contains no
non-low member; that no group uses `included_servers`; that no reviewer-only
profile is offered a high-risk group; that no secret-shaped value is committed;
and that file and member ordering is deterministic.

Current result: **PASS**, 41 groups, 308 tools, 305 assigned, 3 held out.
