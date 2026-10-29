# MCPJungle tool inventory and least-privilege groups — Noesis

Catalog of the tools exposed by the Noesis MCPJungle gateway and the tool groups
that narrow that surface for individual Noesis profiles.

**Status: all 86 groups are deployed and verified live** (last reconciled 2026-10-29; first deployed 2026-10-26).

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

The catalog, the coverage gaps and this README are generated, not hand-edited:

```bash
python3 scripts/generate_mcpjungle_catalog.py --deployed   # inventory, groups, group files
python3 scripts/update_mcpjungle_coverage_gaps.py           # coverage-gap categories
python3 scripts/generate_mcpjungle_readme.py                # this file
```

The generator is idempotent: running it twice against a tree that already
contains its own output reproduces it byte for byte, so the committed artifacts
and the live gateway can always be reconciled against a fresh run.

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
| **Unique tools** | **978** |
| **Source servers** | **34** |
| Discovery timestamp | `2026-10-29T22:02:10.429087+00:00` |

### What "complete" means

This is a **complete server-wide inventory**, not merely the view one connection
happens to expose. Two independent enumerations were performed and reconciled
name-by-name:

1. `tools/list` on the authenticated connection — 978 canonical names.
2. `mcpjungle list tools --registry https://mcpjungle.tailf99a0.ts.net` — the
   gateway's own registry-wide listing, which is independent of any client's
   permissions — 978 canonical names.

The set difference is **empty in both directions**, and **zero** tools are
disabled registry-wide. Every one of the 34 registered server names is an exact
canonical prefix of at least one discovered tool, so no server was missed.

### What changed on 2026-10-26

Four upstream servers were registered on this gateway, adding **392 tools**:

| Server | Tools | Surface |
|---|---|---|
| `unifi` | 212 | The operator's own UniFi controller estate, via the k3s deployment |
| `hunter` | 103 | The operator's own Hunter.io account |
| `notion` | 65 | The operator's own Notion workspace |
| `gitbook-management` | 12 | The operator's own GitBook organization |

All 670 new tools are **additive**: the previous 308 are still present, and
no canonical name was reused or removed.

### What changed on 2026-10-29

Ten more upstream servers were discovered live and reconciled into this catalog,
adding **278 tools** (700 -> 978): `betterstack-noesis` and `betterstack-ryno`
(two separate BetterStack tenant accounts -- `ryno` has no matching profile in
`profiles/noesis-roster.yaml` and is granted no default consumer in any of its
three groups), the Cloudflare family (`cloudflare`, `cloudflare-agents-sdk`,
`cloudflare-blog`, `cloudflare-browser`, `cloudflare-docs`), `noesis-aeon` (the
operator's own Aeon agent-automation instance), `twilio-docs` and
`wolframalpha`. 13 new groups were created and deployed; one tool
(`cloudflare__execute`, a generic code-execution dispatcher against the full
Cloudflare REST API) was classified `review-required` and held out of every
group, matching the existing `framer__exec` precedent. All 278 new
tools are additive: the previous 700 are still present unchanged.

### Hermes reports 312 — why the numbers differ

`hermes mcp list` shows **312** tools for this server. That figure was captured
when the Hermes connection last enumerated the registry, before the four servers
above were registered. The gateway itself now serves **978**. On the next
reconnection Hermes will report **982**: 978 upstream tools plus **4
Hermes-synthesised per-server utilities** (`list_resources`, `read_resource`,
`list_prompts`, `get_prompt`). Those four are Hermes constructs, not MCPJungle
canonical tools, so they are excluded from the inventory and from every group.

### Scope limits

This catalog covers **only what the MCPJungle gateway exposes**. Other MCP
servers are connected to Hermes directly and do not traverse MCPJungle, so a group
here does not constrain them:

- **UniFi** — the gateway now registers a `unifi` server pointing at the
  operator's own k3s UniFi deployment. It is a **separate surface** from the
  directly-configured `unifi-local` Hermes connection, and the two are not
  equivalent:

  | | `unifi` (in this gateway) | `unifi-local` (direct Hermes connection) |
  |---|---|---|
  | Registered where | MCPJungle, `http://10.43.11.10:3000/mcp` | Hermes, stdio over Docker |
  | Tools | 212 | 347 |
  | Mutating tools | **none** — the deployment sets `UNIFI_READ_ONLY=true`, so no mutating UniFi tool is registered at all | present |
  | Constrained by this catalog | **yes**, by the `network-*` groups | **no** |

  The gateway's `unifi` server is therefore strictly narrower than the direct
  connection. A group here constrains the gateway surface only.
- **Beacon, local endpoint** — connected directly as `beacon` (stdio,
  `/home/elvis/.local/bin/beacon`), exposing 7 tools
  (`search_memory`, `get_memory`, `get_memory_context`, `search_activity`,
  `summarize_activity`, `get_activity_event`, `list_activity_filters`) against the
  host's own per-profile runtime log. This is a **different surface** from the
  `beacon-managed` server registered in MCPJungle, which is the hosted
  `https://mcp.beacon.sh` endpoint exposing 25 tools. Both are
  Beacon, but they are separate connections with separate tool sets: the groups in
  this catalog constrain the hosted one and have no effect on the local one.

A group therefore controls only the tools reachable through *its own* group
endpoint. It does not constrain `/mcp` on the main gateway, and it does not
constrain any directly-configured MCP server.

### Registered servers

['| Server | Tools |', '|---|---|', '| `CourtListener` | 34 |', '| `GovInfo` | 2 |', '| `OpenStates` | 10 |', '| `beacon-managed` | 25 |', '| `betterstack-noesis` | 73 |', '| `betterstack-ryno` | 148 |', '| `cloudflare` | 4 |', '| `cloudflare-agents-sdk` | 1 |', '| `cloudflare-blog` | 4 |', '| `cloudflare-browser` | 13 |', '| `cloudflare-docs` | 2 |', '| `context7` | 2 |', '| `court-listener` | 19 |', '| `deepwiki` | 3 |', '| `eCFR` | 3 |', '| `exa` | 3 |', '| `federal-regulations` | 7 |', '| `firecrawl-search` | 30 |', '| `framer` | 7 |', '| `gitbook-management` | 12 |', '| `github` | 49 |', '| `hunter` | 103 |', '| `linear` | 9 |', '| `mcpjungle-docs` | 3 |', '| `mintlify` | 42 |', '| `mintlify-docs` | 3 |', '| `misjusticeallinace-ywcaofmissoula-pub` | 3 |', '| `n8n` | 50 |', '| `noesis-aeon` | 28 |', '| `notion` | 65 |', '| `perplexity` | 4 |', '| `twilio-docs` | 2 |', '| `unifi` | 212 |', '| `wolframalpha` | 3 |']

---

## 2. Compatibility evidence

All claims below are verified against **MCPJungle 0.4.6**, whose release tag is
`0.4.6` (not `v0.4.6`).

| Question | Answer | Evidence |
|---|---|---|
| Supported group JSON schema | `name`, `description`, `included_tools`, `included_servers`, `excluded_tools` — and nothing else | `pkg/types/tool_group.go` |
| Canonical tool-name format | `<server-name>__<tool-name>`, split on the **first** `__` | `internal/service/mcp/util.go` (`serverToolNameSep`, `mergeServerToolNames`) |
| How exposed names map to group names | Identically — the names `tools/list` returns *are* the names `included_tools` accepts. No rewriting, splitting or renaming is performed. | Verified against `tools/list` and `mcpjungle list tools`, both returning the same 978 canonical names |
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

86 groups, 974 tools assigned, 4 held out. Risk is
the highest level among the member tools, raised to the group's declared floor
where the declaration is the stricter judgement.

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
| `legal-research` | 24 | medium | advocate, tracer, skeptic, signal | Case law, opinions, dockets, courts, judges, filed documents, and the MISJustice/YWCA corpus |
| `legal-citation-analysis` | 9 | low | advocate, tracer, skeptic | Extract, parse, verify, batch-resolve citations |
| `legal-regulations-research` | 27 | medium | advocate, tracer, skeptic | Codified CFR, Federal Register, rulemaking dockets and comments |
| `legislative-research` | 10 | low | advocate, tracer | State bills, committees, legislators, events |
| `legal-alerts` | 6 | high | advocate | Create/cancel alert subscriptions; request documents |

**Legal research is deliberately split from general web search.**
`legal-research` contains only authoritative legal retrieval. The two
general-purpose searches whose *names* sound legal — `linear__search_legal` and
`firecrawl-search__firecrawl_gov_search` — return web-index results, not primary
sources, and are held in `web-research` instead. Labelling them legal would be
exactly the error the boundary exists to prevent.

**The YWCA Missoula GitBook MCP is included in `legal-research`.** The server
`misjusticeallinace-ywcaofmissoula-pub` is registered at exactly
`https://www.ywcaofmissoula.com/~gitbook/mcp` and publishes the MISJustice Alliance
/ YWCA Missoula / MPD / County Prosecutors (2012–2025) corpus. Two of its three
tools are in `legal-research`:

- `misjusticeallinace-ywcaofmissoula-pub__getPage`
- `misjusticeallinace-ywcaofmissoula-pub__searchDocumentation`

Its third tool, `misjusticeallinace-ywcaofmissoula-pub__sendFeedback`, submits a message to the documentation
site. That is an outbound external communication, so it is held in
`communications-send` rather than in the read-only legal group.

Note that this public documentation server is a **different surface** from the
`gitbook-management` server registered on 2026-10-26, which reaches the
operator's own GitBook organization and is grouped separately. The two must not
be confused: one is a published third-party corpus, the other is private
first-party content.

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
| `credential-inventory` | 2 | review-required | *(none proposed)* | Enumerate n8n and Hunter credential identities |

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
| `database-readonly` | 4 | medium | grid, scribe | n8n data tables; Mintlify databases; Notion data sources |
| `database-write` | 8 | high | grid | Create/extend/rename/delete tables and columns; edit database rows |
| `data-analytics` | 3 | low | grid, scribe | Docs-site analytics queries and reports |
| `observability` | 8 | medium | substrate, steward | Deployment status, run history, provider usage and cost, Hunter quota |
| `security-audit` | 3 | medium | sentinel, skeptic, substrate | Secret scanning; Beacon security findings |
| `twilio-docs-read` | 2 | low | architect, forge, scribe | Search Twilio product documentation |
| `wolframalpha-knowledge-query` | 3 | low | architect, forge | Query Wolfram|Alpha and evaluate Wolfram Language in a stateless sandbox |

### Communications and external effects

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `communications-readonly` | 1 | low | scribe, herald | Read docs-site comment threads |
| `communications-send` | 15 | high | herald | Comments, replies, feedback, shared traces, provider feedback |
| `external-publication` | 6 | high | architect, scribe | Publish Beacon lenses to the marketplace |

### Network operations — the operator's own UniFi estate

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `network-inventory` | 36 | low | substrate | Devices, WLANs, networks, WANs, topology |
| `network-diagnostics` | 12 | low | substrate | Health, speed, spectrum, RF, AP neighbourhood, events |
| `network-switching` | 9 | low | substrate | Switch stacks, LAG, MLAG, port profiles, device tags |
| `network-addressing` | 10 | low | substrate | DHCP reservations, MAC tags, DNS, VLANs, port mappings |
| `network-security-policy` | 27 | medium | substrate | Firewall, zones, ACLs, RADIUS, filters, traffic matching |
| `network-telemetry` | 28 | medium | substrate | Client identity and per-client network activity |
| `network-protect` | 43 | medium | substrate | Cameras, alarms and premises security |
| `network-fleet` | 11 | low | substrate | Multi-controller, multi-site and Site Manager view |
| `network-backup` | 8 | medium | substrate | Backup and restore state; topology export |
| `network-controller` | 3 | medium | substrate | Inspect and select the controller calls target |
| `network-integration` | 22 | low | substrate | Site Manager and integration API views of the estate |
| `network-proxy` | 3 | review-required | *(none proposed)* | Held review-required: caller-selected proxy paths and fleet fan-out |

### Workspace and agent sessions — the operator's own Notion workspace

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `notion-workspace-read` | 19 | medium | scribe, quill, architect | Pages, databases, comments, members, skills, file references |
| `notion-data-query` | 3 | medium | grid, scribe | Read-only SQL over Notion data sources and meeting notes |
| `notion-workspace-authoring` | 16 | medium | scribe, quill | Create and edit pages, views, comments, folders, uploads |
| `notion-workspace-destructive` | 5 | high | scribe | Remove pages, databases, comments; rewrite schemas |
| `notion-agent-session-read` | 9 | medium | architect, scribe | Read agent sessions, session events and saved memories |
| `notion-agent-sessions` | 5 | high | architect | Start, feed and stop Custom Agents; change enabled skills |
| `notion-calendar-read` | 5 | medium | steward, herald | Calendars, events, contacts and room resources |
| `notion-calendar-write` | 3 | high | steward, herald | Create, change and cancel events |

### Documentation platform — the operator's own GitBook organization

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `gitbook-org-read` | 8 | low | scribe, quill | Sites, navigation, pages, topics, plan state, operation catalogue |
| `gitbook-change-request` | 1 | medium | scribe, quill | Open a change request without publishing |
| `gitbook-publish` | 1 | high | scribe, quill | Merge a change request and publish its edits |
| `gitbook-proxy` | 1 | review-required | *(none proposed)* | Held review-required: caller-selected GitBook API operations |

### Sales prospecting — the operator's own Hunter account

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `hunter-account-read` | 25 | low | *(none proposed)* | Account lists, tags, templates, sequences, apps, webhooks, search |
| `hunter-contact-records` | 16 | medium | *(none proposed)* | Look up real contact records and company facts |
| `hunter-record-authoring` | 29 | medium | *(none proposed)* | Create and edit leads, lists, tags, attributes, searches |
| `hunter-sequence-authoring` | 9 | medium | *(none proposed)* | Author sequences, steps, message bodies and schedules |
| `hunter-record-destructive` | 15 | high | *(none proposed)* | Delete leads, lists, tags, templates, searches, API keys |
| `hunter-outbound-email` | 3 | high | *(none proposed)* | Start, resume and add recipients to sending sequences |
| `hunter-prospecting-flow` | 1 | medium | *(none proposed)* | Plan and begin an end-to-end prospecting run |
| `hunter-crm-integration` | 3 | high | *(none proposed)* | Push leads to a CRM; repoint a webhook; mint API keys |

### Design

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `web-design` | 5 | low | *(none proposed)* | Inspect Framer workspaces, projects, docs, assets |

### Monitoring — two separate BetterStack tenant accounts

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `betterstack-noesis-monitoring-read` | 73 | low | substrate, steward | Read the operator's own BetterStack monitoring (incidents, dashboards, monitors, logs) |
| `betterstack-ryno-monitoring-read` | 73 | low | *(none proposed)* | Read a third-party ('ryno') BetterStack tenant's monitoring, read-only |
| `betterstack-ryno-monitoring-operate` | 55 | high | *(none proposed)* | Ack incidents, edit dashboards, update monitors/heartbeats on the 'ryno' tenant |
| `betterstack-ryno-monitoring-destructive` | 20 | high | *(none proposed)* | Delete monitors/dashboards, change team roles, mint credentials on the 'ryno' tenant |

### Cloud platform — the operator's own Cloudflare account

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `cloudflare-docs-and-blog-read` | 10 | low | architect, forge, scribe, substrate | Search Cloudflare developer docs, blog, Agents SDK and Pages migration guides |
| `cloudflare-browser-render` | 8 | medium | *(none proposed)* | Fetch/render a single caller-chosen URL via Cloudflare's remote browser |
| `cloudflare-browser-crawl-and-sessions` | 5 | high | *(none proposed)* | Start/cancel async multi-page crawls; manage browser sessions |

### Agent automation — the operator's own Aeon instance

| Group | Tools | Risk | Intended consumers | Purpose |
|---|---|---|---|---|
| `noesis-aeon-read` | 18 | low | steward, substrate | Read the Aeon instance's runs, skills, packs, memory, settings, strategy/soul |
| `noesis-aeon-configure` | 4 | medium | steward | Toggle/schedule skills, switch harness/model, switch active instance |
| `noesis-aeon-identity-write` | 4 | high | *(none proposed)* | Write/replace the Aeon agent's SOUL.md, STYLE.md, STRATEGY.md |
| `noesis-aeon-execute` | 2 | review-required | *(none proposed)* | Held review-required: dispatch any registered skill; install third-party skill packs |

### Deliberate overlaps

6 tools appear in more than one group. Each is a genuine
multi-workflow tool, and the overlap is named rather than removed:

| Tool | Groups | Why |
|---|---|---|
| `beacon-managed__beacon_findings_list` | memory-retrieval, security-audit | One read serving both a memory recall and a security review |
| `beacon-managed__beacon_get_finding` | memory-retrieval, security-audit | Same |
| `github__get_file_contents` | coding, source-control-readonly | Same |
| `github__search_code` | coding, source-control-readonly | Locating an implementation site vs. reading source control |
| `hunter__Get-Usage` | hunter-account-read, observability | The Hunter quota read is provider usage for the observability workflow, and account state for the Hunter workflow |
| `n8n__create_workflow_from_code` | coding, workflow-authoring | The authoring *input* vs. a change to an existing workflow |

No generic tool is copied into every group.

---

## 4. Held out of all groups — review required

11 tools are classified `review-required`. 4 are held
out of **every** group; the remaining 7 sit inside a
group that is itself flagged review-required and has no proposed consumer, which is
how `browser-automation` holds `firecrawl-search__firecrawl_interact`.

| Tool | Reason |
|---|---|
| `court-listener__call_endpoint` | Generic REST client for arbitrary CourtListener API endpoints. The endpoint path and HTTP method are caller-supplied, so it can reach write paths (alert creation, document requests) that the curated legal-research allowlist deliberately excludes. The upstream readOnlyHint=true annotation is contradicted by the tool's own purpose: group membership cannot constrain a caller-chosen endpoint and method. |
| `firecrawl-search__firecrawl_interact` | Opens or reuses a live browser session and can run browser code against authenticated third-party sites. The session survives between calls and the code it runs is caller-supplied, so the effect class is not bounded by the tool. Treated as broad capability rather than a page-reading helper. |
| `framer__create_project` | Creates a new project inside the operator's external Framer SaaS account. It is persistent third-party state creation with no verified Noesis consumer, so granting it would add an unreviewed external surface for no workflow benefit. |
| `framer__exec` | Executes a caller-supplied JavaScript program that mutates a Framer project. This is arbitrary code execution against a third-party SaaS project; the arguments bound the effect, not the class of effect. |
| `gitbook-management__invoke_operation` | Runs one caller-selected GitBook API operation discovered through search, with caller-supplied path, query and body parameters. The upstream states that the operation surface includes actions that are visible to the public or cannot be undone, such as publishing a site or merging a change request, so the caller chooses the target and therefore the effect class. This is the same shape as court-listener__call_endpoint, and the curated GitBook tools are not a constraint on what it can reach. |
| `unifi__connector_network_get` | Generic GET proxy for the UniFi Network application: the caller supplies the console id and the sub-path under the Cloud Connector proxy prefix, and the raw upstream response is returned. The upstream restricts the request to GET and validates every path segment against traversal, but the endpoint itself is caller-selected, so group membership cannot constrain which UniFi endpoint is read. It is narrower than court-listener__call_endpoint, which also exposes the HTTP method, but it is the same shape: a caller-chosen target. In this deployment the tool is additionally inert, because UNIFI_SITE_MANAGER_ENABLED is unset and the call raises 'Site Manager API is not enabled'. |
| `unifi__connector_protect_get` | Generic GET proxy for the UniFi Protect application: the caller supplies the console id and the sub-path under the Cloud Connector proxy prefix, and the raw upstream response is returned. The upstream restricts the request to GET and validates every path segment against traversal, but the endpoint itself is caller-selected, so group membership cannot constrain which Protect endpoint is read, including the camera and event endpoints. In this deployment the tool is additionally inert, because UNIFI_SITE_MANAGER_ENABLED is unset and the call raises 'Site Manager API is not enabled'. |
| `unifi__fleet_fanout` | Runs one caller-named read tool across every controller in scope at once. The upstream enforces that only read-tier controller tools can be fanned out and rejects fleet-prefixed and unknown tool names, so the effect class is bounded to reads, but the caller still chooses which tool runs: a holder of this tool reaches every read-tier controller tool whether or not that tool is in the group it was granted. Group membership therefore cannot constrain the target, which is the property that makes a tool broad-capability rather than an ordinary read. |
| `cloudflare__execute` | Executes caller-authored JavaScript with full read/create/update/delete access to the Cloudflare REST API. Same shape as the already-unassigned framer__exec: arbitrary code execution against a third-party cloud account, with no verified Noesis consumer or workflow need yet. |
| `noesis-aeon__install_pack` | readOnlyHint=false, openWorldHint=true; installs third-party community skill code into the repo via a security-scanned PR (skills land turned off by default). Despite the PR gate and off-by-default landing, this is third-party code supply-chain exposure -- the description itself says 'Confirm with the user first', which is the caller's own admission that this needs a human in the loop before use. |
| `noesis-aeon__run_skill` | Upstream itself sets destructiveHint=true. Dispatches ANY of the instance's skills (enuno/noesis-aeon currently lists dozens, including ones that spend money, publish externally, or deploy infrastructure per this repo's own skill catalog) with an arbitrary var input -- a generic 'run anything registered' dispatcher that bypasses any tool-level allowlist by construction, matching the house rule to treat broad-capability dispatchers as review-required regardless of name. |

**Operator decision required** for each: is the capability needed at all, and if so
which profile may hold it under what approval path?

---

## 5. Coverage gaps — requested categories the inventory cannot support

| Requested category | Status | Reason |
|---|---|---|
| `devops-readonly` | coverage gap | No DevOps or CI server is registered in this gateway. There is no Docker, Kubernetes, Terraform, Ansible, cloud-provider or CI tool among the 700 discovered tools. The nearest surfaces are workflow-inspection, observability and the network-* groups, and naming any of them 'devops-readonly' would misrepresent it: they report state, they do not change infrastructure. Infrastructure execution lives in the noesis-ansible repository and in the Hermes terminal toolset, not in MCPJungle. |
| `network-operations-readonly` | supported | The UniFi MCP server is registered in this gateway and contributes 212 read tools, split across seven groups by capability: network-inventory, network-security-policy, network-telemetry, network-protect, network-fleet, network-backup and network-controller, plus network-proxy which is held review-required. The deployment sets UNIFI_READ_ONLY=true, so the registered surface contains no mutating UniFi tool at all: these groups are a read-only view by construction, not by policy. Note that the separately-configured Hermes connection 'unifi-local' exposes 347 tools including mutating ones and is NOT constrained by any group here. |
| `cloud-infrastructure-readonly` | supported | The Cloudflare account is now registered (servers cloudflare, cloudflare-agents-sdk, cloudflare-blog, cloudflare-browser, cloudflare-docs). Read-only coverage is the cloudflare-docs-and-blog-read group (docs/blog/Agents-SDK/Pages-migration search) and the cloudflare-browser-render group (fetch/render a caller-chosen URL through Cloudflare's Browser Rendering service, held medium risk). This is a documentation and browser-rendering surface, not a Cloudflare zone/DNS/account-configuration read; no server here reads live zone, DNS, WAF or account settings. |
| `cloud-infrastructure-write` | coverage gap | Still a genuine gap for zone/DNS/account CONFIGURATION writes: no registered server exposes Cloudflare zone, DNS, WAF, Workers deployment or account-settings mutation. cloudflare__execute (held review-required, out of all groups, in unassigned_review_required) can reach the full Cloudflare REST API including these writes, but it is a generic code-execution dispatcher with no verified Noesis consumer, not curated write coverage -- granting it would not close this gap safely. |
| `blockchain-research` | coverage gap | No blockchain, wallet, miner or DePIN data server is registered. The noesis-ledger domain can only be served by the generic web-research, academic-research and market-research groups. |
| `financial-actions` | coverage gap | No spending, transfer, trading, payment or wallet tool exists anywhere in the 700-tool inventory. Hunter's credit-consuming lookups draw on a metered search and credit quota rather than money, and the connected account is on the free tier; on a paid plan the same calls would become billable, which is why the spending constraint is recorded on hunter-contact-records rather than treated as absent. The one payment-adjacent tool is court-listener__pray_for_document, which sits in legal-alerts under a spending control. |
| `communications-readonly (broad inbox)` | **partial** | No mail, chat or SMS server is registered in this gateway. The communications read surfaces are the Mintlify comment thread and the Notion calendar, which together are not an inbox: the Herald workflow still cannot read prior outbound correspondence, and no tool here can confirm what was already sent to anyone. |
| `database-readonly / database-write` | supported | n8n data tables, the Mintlify deployment databases and the Notion data sources provide readable and writable tabular surfaces, and the groups exist. There is still no generic SQL database server (no PostgreSQL, MySQL or SQLite tool). The two SQL surfaces present are each confined to its own store: mintlify__query_analytics is held in data-analytics, and the Notion queries in notion-data-query are read-only by construction. |
| `observability` | supported | Deployment status, workflow run history, execution records, provider credit and usage reporting, and the Hunter quota report cover the original read-only observability surface. Two BetterStack monitoring accounts are now registered: betterstack-noesis-monitoring-read (the operator's own account: uptime monitors, heartbeats, incidents, dashboards, charts, logs and metrics queries) and betterstack-ryno-monitoring-read (a separate human operator's account, read-only; write/destructive coverage of that same account sits in betterstack-ryno-monitoring-operate and betterstack-ryno-monitoring-destructive, both held with no default Noesis consumer). This closes most of the metrics/log-aggregation gap for application and uptime monitoring; there is still no infrastructure-level telemetry server (no Prometheus, Grafana or Loki) registered, and the UniFi groups still report controller state as read by the controller, not as collected telemetry. |
| `agent-infrastructure` | supported | n8n provides agent draft authoring, versioning, validation and retirement; the Beacon-managed server provides the memory and trace substrate agents read from; and Notion provides Custom Agent sessions plus the skill enablement that decides what those agents may load. All three surfaces exist, and the groups exist. |
| `security-audit` | supported but narrow | Only two genuine security surfaces exist: GitHub secret scanning and Beacon's security findings. There is no SAST, DAST, dependency-audit or container-scanning server registered, so the group cannot cover a full security review. The UniFi groups read the operator's own security posture but are not a scanning surface. |
| `source-control-readonly / source-control-write` | supported | The GitHub MCP server exposes both surfaces, split across source-control-readonly, source-control-issues-readonly and source-control-write. It is the only source-control server registered. |
| `outbound-messaging / sales-prospecting` | supported | Hunter registers 103 tools covering contact discovery, enrichment, CRM record management and outbound email sending, split across six groups. The sending surface is isolated in hunter-outbound-email, and the destructive record surface in hunter-record-destructive. This is the only registered capability that sends email to people who did not ask to be contacted, so it carries the strictest approval control in the catalog. |
| `workspace-document-management` | supported | Notion contributes 65 tools covering the operator's own workspace (pages, databases, comments, calendars and agent sessions) and GitBook contributes 12 covering the operator's own GitBook organization (sites, navigation, change requests and publication). The two are split by capability and by risk, and neither can be confused with the MISJustice/YWCA GitBook corpus, which stays in legal-research. |

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
- constrain tool arguments — `mintlify__query_analytics` accepts a SELECT,
  `notion__notion-query-data-sources` accepts a query, and
  `n8n__execute_workflow` accepts arbitrary input;
- prevent bypass through another endpoint — the main `/mcp` endpoint still
  exposes all 978 tools to any credential that can reach it, and the UniFi and
  Beacon connections are separate paths entirely.

A README that says "approval required" is documentation, not a control. For each
higher-risk group, the following must be enforced **outside** MCPJungle:

| Control | Applies to |
|---|---|
| **Per-client MCP identity** — a dedicated client token per consuming profile, with an explicit allow-list, never a shared token | every group |
| **Credential scoping at the upstream provider** — a GitHub token limited to in-scope repositories; a Mintlify token scoped to one deployment; an n8n token limited to one instance; a CourtListener token limited to read access; a Hunter token limited to one account; a GitBook token scoped to one organization | every group touching a credentialed upstream |
| **Approval gate in the runtime** — a human approval step in the agent runtime or broker *before* the tool call, enforced by the toolset the profile holds, not by prose | all `high` and `review-required` groups |
| **Argument constraints** — where a tool accepts a path, endpoint, SQL statement or credential id, constrain it in the runtime's policy layer | `data-analytics`, `legal-research`, `credential-inventory`, `web-retrieval`, `notion-data-query`, `hunter-outbound-email`, `network-proxy`, `gitbook-proxy` |
| **Profile isolation** — one MCP connection per profile, pointed at that profile's group endpoint, so a mis-scoped call cannot reach a broader surface | every group |
| **Audit** — tool calls through a group endpoint logged with the client identity, so an action can be attributed | all `high` groups |
| **Kill switch** — a per-group revoke path; `mcpjungle delete group <name>` removes the endpoint immediately | all `high` groups |
| **Separate change authority from review authority** — the profile that executes holds no reviewer group, and the reviewer profile holds no write group | `source-control-write`, `autonomous-coding`, `workflow-execution`, `docs-site-publish`, `gitbook-publish`, `hunter-outbound-email`, `notion-workspace-destructive` |

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

`sentinel`: `library-docs`, `repository-docs`, `security-audit`, `source-control-issues-readonly`, `source-control-readonly`, `workflow-inspection`

`skeptic`: `legal-citation-analysis`, `legal-regulations-research`, `legal-research`, `memory-retrieval`, `security-audit`, `source-control-issues-readonly`, `source-control-readonly`, `web-research`

Neither can write, delete, publish, spend or delegate. Reviewers do hold groups
that read sensitive data (`security-audit`, `memory-retrieval`, `legal-research`),
which a reviewer needs; reading sensitive data is not acting.

Note that `coding` is **not** proposed for either reviewer. It contains
`n8n__create_workflow_from_code`, which creates a workflow draft and is
classified `mutating`. `noesis-forge` and `noesis-architect` hold it, and they
are not reviewer-only.

Conversely, the implementation profiles (`noesis-forge`, `noesis-substrate`)
hold write groups but are not listed as consumers of any reviewer-only group.

The `network-*` groups are likewise not offered to either reviewer, although
their members only read: they are the operator's own live network estate, and
the profile that operates it (`noesis-substrate`) is the one that needs them.

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

### Deployment — completed 2026-10-26

All 86 groups were created on the live gateway and verified:

```bash
mcpjungle create group --conf config/mcpjungle/groups/<group-name>.json \
  --registry https://mcpjungle.tailf99a0.ts.net
```

**Result: 86 created, 0 failed.** Verification was two-layer:

1. Every group's live definition was compared name-by-name against its source
   file — `name`, `description` and `included_tools` are identical for all
   86.
2. Every group's MCP endpoint was probed with `initialize` + `tools/list`
   (discovery only — no tool was invoked). Each endpoint serves **exactly** its
   declared `included_tools`: 86/86 matched, 0 mismatches.

The main `/mcp` endpoint still serves all 978 tools. **Creating tool groups does
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
state: the 34 registered upstream servers, the 86 group definitions, and a
pointer to the 978-tool main-endpoint inventory. Upstream credentials are
**not** recoverable from it — every secret-bearing value in the richer
`/api/v0/server_configs` view is replaced by a non-reversible shape marker, and
the file was verified by **value** to contain none of the live secret values.
Re-apply credentials from the Bitwarden escrow if a restore is ever needed.

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
| Deployment flag changed | `UNIFI_READ_ONLY` or `UNIFI_SITE_MANAGER_ENABLED` on the UniFi deployment | The registered tool set changes with the flag. Re-discover and re-review the `network-*` groups. |

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
2026-10-26: all 86 group definitions, the 34 registered upstream servers, and a
pointer to the 978-tool inventory. **Upstream credentials are not in it** — they
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

A pattern scan across all 978 tools — bearer tokens, JWTs, provider API keys, cloud
access keys, 32-character hex secrets, credential assignments, credential-bearing
URLs and e-mail addresses — returned **zero hits**. Descriptions, schemas and
`_meta` are reproduced as returned; they contain tool contracts only, because no
live record data was retrieved during discovery.

**Not available:**

- Output schemas are absent for **345 of 978** tools because the upstream servers
  do not publish them. No output schema was inferred.
- MCP annotations carry no values for **218** tools: the server returned an empty
  annotations object for each — `CourtListener__status`, `GovInfo__describePackageOrGranule`, `GovInfo__searchGovInfo`, `deepwiki__ask_wiki_question`, `deepwiki__read_wiki_contents`, `deepwiki__read_wiki_structure`, and the 212 UniFi tools. The observed value is preserved
  verbatim. Each was classified from its description, schema and, for the UniFi
  tools, the upstream source at `/home/elvis/projects/unifi-mcp-server`.
- Server-side per-client authorisation rules could not be inspected:
  `mcpjungle list mcp-clients` is refused for a user token in enterprise mode.
- Upstream credential scopes — which organisations, repositories, sites, cases,
  workspaces or documents each configured upstream credential can reach — are not
  visible through this gateway and must be checked at the upstream provider.
- The UniFi deployment registers `UNIFI_READ_ONLY=true`, so **no mutating UniFi
  tool is registered at all**; and it leaves `UNIFI_SITE_MANAGER_ENABLED` unset, so
  the Site Manager, Carrier, Mobility, InnerSpace, ISP and integration tools raise
  *"Site Manager API is not enabled"* when called. Both are deployment facts, not
  properties of the tools, and are recorded so a later change to the flags
  triggers a re-review.
- The Hunter account's plan and quota were read from the live account (free tier,
  50 searches, 50 credits and 100 verifications per month). Moving the account to
  a paid plan changes the cost of the credit-consuming lookups and must trigger a
  re-review.

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
accepted as read-only on the strength of `readOnlyHint` alone. Tools carrying
`destructiveHint=true` that describe a configuration change rather than a literal
deletion — `manage_access_auth`, `update_workflow`, `mutate_agent` and others —
carry a corrected category and rationale in the inventory.

The 212 UniFi tools publish **no** MCP annotations at all: the upstream
returns an empty annotations object for every one of them. Their classification
was taken from the description, the input schema and the upstream source, and each
rationale says so.

| Risk level | Meaning |
|---|---|
| Risk level | Meaning |
|---|---|
| `low` | Reads state and changes nothing. |
| `medium` | Changes state, reads sensitive data, or acts on records whose blast radius is not obvious from the tool name. |
| `high` | Destructive, publishes externally, spends money, or grants persistent autonomy. |
| `review-required` | Broad-capability or unusually ambiguous. Held out of ordinary groups pending an explicit operator decision. |

Distribution across the 978 tools:

| Capability category | Risk | Tools |
|---|---|---|
| `read-only` | low | 589 |
| `sensitive-data` | medium | 93 |
| `mutating` | medium | 119 |
| `persistent-or-autonomous` | high | 31 |
| `external-communication` | high | 34 |
| `destructive` | high | 45 |
| `configuration-change` | high | 39 |
| `access-control-change` | high | 8 |
| `broad-capability` | review-required | 20 |

Totals: 608 `low`, 250 `medium`, 109 `high`, 11 `review-required`.

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

Current result: **PASS**, 86 groups, 978 tools, 974 assigned, 4 held out.
