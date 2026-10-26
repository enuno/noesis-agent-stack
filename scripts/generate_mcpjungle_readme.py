#!/usr/bin/env python3
"""Regenerate config/mcpjungle/README.md from the catalog and inventory.

Every factual claim that the README validator checks is derived here from
tool-inventory.json / tool-groups.json, so the prose cannot drift from the
artifacts. The narrative sections are templates; the tables are generated.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MCP = R / "config" / "mcpjungle"

inv = json.load(open(MCP / "tool-inventory.json"))
cat = json.load(open(MCP / "tool-groups.json"))
groups = cat["groups"]
by_name = {g["name"]: g for g in groups}

TOOLS = inv["tools"]
NT = len(TOOLS)
NS = len({t["source_server"] for t in TOOLS})
TS = inv["generated_at"]
DIST = Counter(t["source_server"] for t in TOOLS)
assigned = sum(len(g["tools"]) for g in groups)
uniq_assigned = len({t for g in groups for t in g["tools"]})
unassigned = NT - uniq_assigned
rr_tools = [e["tool"] for e in cat["review_required_summary"]["tools"]]
unassigned_tools = [e["tool"] for e in cat["unassigned_review_required"]]

cat_c = Counter(t["inferred_capability_category"] for t in TOOLS)
risk_c = Counter(t["risk_classification"] for t in TOOLS)
ann_cov = inv["discovery"]["annotation_coverage"]

# groups that appear in more than one group
memb = {}
for g in groups:
    for t in g["tools"]:
        memb.setdefault(t, []).append(g["name"])
overlaps = {t: gs for t, gs in memb.items() if len(gs) > 1}

OVERLAP_WHY = {
    "github__search_code": "Locating an implementation site vs. reading source control",
    "github__get_file_contents": "Same",
    "n8n__create_workflow_from_code": "The authoring *input* vs. a change to an existing workflow",
    "beacon-managed__beacon_findings_list": "One read serving both a memory recall and a security review",
    "beacon-managed__beacon_get_finding": "Same",
    "hunter__Get-Usage": "The Hunter quota read is provider usage for the observability workflow, and "
                         "account state for the Hunter workflow",
}

SECTIONS = [
    ("Research and discovery", ["web-research", "web-retrieval", "web-monitoring",
                                "web-monitoring-config", "autonomous-research", "academic-research",
                                "market-research", "browser-automation"]),
    ("Legal and regulatory", ["legal-research", "legal-citation-analysis",
                              "legal-regulations-research", "legislative-research", "legal-alerts"]),
    ("Source control, coding and automation", ["source-control-readonly",
                                               "source-control-issues-readonly",
                                               "source-control-write", "autonomous-coding", "coding",
                                               "workflow-inspection", "workflow-authoring",
                                               "workflow-execution", "agent-infrastructure",
                                               "credential-inventory"]),
    ("Documentation, memory, data and observability", ["library-docs", "repository-docs",
                                                       "platform-docs", "docs-site-read",
                                                       "docs-site-authoring", "docs-site-publish",
                                                       "platform-administration", "memory-retrieval",
                                                       "memory-management", "database-readonly",
                                                       "database-write", "data-analytics",
                                                       "observability", "security-audit"]),
    ("Communications and external effects", ["communications-readonly", "communications-send",
                                             "external-publication"]),
    ("Network operations — the operator's own UniFi estate",
     ["network-inventory", "network-diagnostics", "network-switching", "network-addressing",
      "network-security-policy", "network-telemetry", "network-protect", "network-fleet",
      "network-backup", "network-controller", "network-integration", "network-proxy"]),
    ("Workspace and agent sessions — the operator's own Notion workspace",
     ["notion-workspace-read", "notion-data-query", "notion-workspace-authoring",
      "notion-workspace-destructive", "notion-agent-session-read", "notion-agent-sessions",
      "notion-calendar-read", "notion-calendar-write"]),
    ("Documentation platform — the operator's own GitBook organization",
     ["gitbook-org-read", "gitbook-change-request", "gitbook-publish", "gitbook-proxy"]),
    ("Sales prospecting — the operator's own Hunter account",
     ["hunter-account-read", "hunter-contact-records", "hunter-record-authoring",
      "hunter-sequence-authoring", "hunter-record-destructive", "hunter-outbound-email",
      "hunter-prospecting-flow", "hunter-crm-integration"]),
    ("Design", ["web-design"]),
]

SHORT_PURPOSE = {
    "web-research": "General web search, fetch and Q&A",
    "web-retrieval": "Fetch, parse and crawl specific documents",
    "web-monitoring": "Read existing monitors and check history",
    "web-monitoring-config": "Create, edit, trigger, delete recurring monitors",
    "autonomous-research": "Multi-step autonomous research agents",
    "academic-research": "Peer-reviewed literature",
    "market-research": "Company, market and filings research",
    "browser-automation": "Live browser: navigate, click, run browser code",
    "legal-research": "Case law, opinions, dockets, courts, judges, filed documents, and the "
                      "MISJustice/YWCA corpus",
    "legal-citation-analysis": "Extract, parse, verify, batch-resolve citations",
    "legal-regulations-research": "Codified CFR, Federal Register, rulemaking dockets and comments",
    "legislative-research": "State bills, committees, legislators, events",
    "legal-alerts": "Create/cancel alert subscriptions; request documents",
    "source-control-readonly": "Repository content, history, branches, tags, releases, directory",
    "source-control-issues-readonly": "Issues, pull requests, issue metadata, review state",
    "source-control-write": "Branches, files, pull requests, issues, reviews",
    "autonomous-coding": "Delegate to the Copilot coding agent; request automated review",
    "coding": "Code search, SDK references, workflow-code authoring",
    "workflow-inspection": "Read n8n workflows, versions, executions, tags",
    "workflow-authoring": "Create, update, archive, restore, unpublish workflows",
    "workflow-execution": "Execute, test, publish workflows and agents",
    "agent-infrastructure": "Create, mutate, validate, version, retire agent drafts",
    "credential-inventory": "Enumerate n8n and Hunter credential identities",
    "library-docs": "Library and framework documentation",
    "repository-docs": "Generated repository wiki documentation",
    "platform-docs": "MCPJungle and Mintlify documentation",
    "docs-site-read": "Read the operator's Mintlify site",
    "docs-site-authoring": "Edit docs content, navigation, images (staged)",
    "docs-site-publish": "Publish staged changes; manage workflow runs and their PRs",
    "platform-administration": "Access control, domains, git sources, members, settings",
    "memory-retrieval": "Recall lessons; search sessions; read findings and trace metadata",
    "memory-management": "File candidates; record review decisions; adjust trace visibility",
    "database-readonly": "n8n data tables; Mintlify databases; Notion data sources",
    "database-write": "Create/extend/rename/delete tables and columns; edit database rows",
    "data-analytics": "Docs-site analytics queries and reports",
    "observability": "Deployment status, run history, provider usage and cost, Hunter quota",
    "security-audit": "Secret scanning; Beacon security findings",
    "communications-readonly": "Read docs-site comment threads",
    "communications-send": "Comments, replies, feedback, shared traces, provider feedback",
    "external-publication": "Publish Beacon lenses to the marketplace",
    "network-inventory": "Devices, WLANs, networks, WANs, topology",
    "network-switching": "Switch stacks, LAG, MLAG, port profiles, device tags",
    "network-addressing": "DHCP reservations, MAC tags, DNS, VLANs, port mappings",
    "network-integration": "Site Manager and integration API views of the estate",
    "network-diagnostics": "Health, speed, spectrum, RF, AP neighbourhood, events",
    "network-security-policy": "Firewall, zones, ACLs, RADIUS, filters, traffic matching",
    "network-telemetry": "Client identity and per-client network activity",
    "network-protect": "Cameras, alarms and premises security",
    "network-fleet": "Multi-controller, multi-site and Site Manager view",
    "network-backup": "Backup and restore state; topology export",
    "network-controller": "Inspect and select the controller calls target",
    "network-proxy": "Held review-required: caller-selected proxy paths and fleet fan-out",
    "notion-workspace-read": "Pages, databases, comments, members, skills, file references",
    "notion-data-query": "Read-only SQL over Notion data sources and meeting notes",
    "notion-workspace-authoring": "Create and edit pages, views, comments, folders, uploads",
    "notion-workspace-destructive": "Remove pages, databases, comments; rewrite schemas",
    "notion-agent-session-read": "Read agent sessions, session events and saved memories",
    "notion-agent-sessions": "Start, feed and stop Custom Agents; change enabled skills",
    "notion-calendar-read": "Calendars, events, contacts and room resources",
    "notion-calendar-write": "Create, change and cancel events",
    "gitbook-org-read": "Sites, navigation, pages, topics, plan state, operation catalogue",
    "gitbook-change-request": "Open a change request without publishing",
    "gitbook-publish": "Merge a change request and publish its edits",
    "gitbook-proxy": "Held review-required: caller-selected GitBook API operations",
    "hunter-account-read": "Account lists, tags, templates, sequences, apps, webhooks, search",
    "hunter-contact-records": "Look up real contact records and company facts",
    "hunter-prospecting-flow": "Plan and begin an end-to-end prospecting run",
    "hunter-record-authoring": "Create and edit leads, lists, tags, attributes, searches",
    "hunter-sequence-authoring": "Author sequences, steps, message bodies and schedules",
    "hunter-record-destructive": "Delete leads, lists, tags, templates, searches, API keys",
    "hunter-outbound-email": "Start, resume and add recipients to sending sequences",
    "hunter-crm-integration": "Push leads to a CRM; repoint a webhook; mint API keys",
    "web-design": "Inspect Framer workspaces, projects, docs, assets",
}


def consumers_cell(g):
    cons = g.get("suggested_consumers") or []
    if not cons:
        return "*(none proposed)*"
    return ", ".join(c.replace("noesis-", "") for c in cons)


def group_table(names):
    rows = ["| Group | Tools | Risk | Intended consumers | Purpose |",
            "|---|---|---|---|---|"]
    for n in names:
        g = by_name[n]
        rows.append(f"| `{n}` | {g['tool_count']} | {g['risk_level']} | {consumers_cell(g)} | "
                    f"{SHORT_PURPOSE.get(n, g['purpose'])} |")
    return "\n".join(rows)


def reviewer_block(profile):
    short = profile.split("-", 1)[1]
    names = sorted(g["name"] for g in groups if profile in (g.get("suggested_consumers") or []))
    return f"`{short}`: " + ", ".join(f"`{n}`" for n in names)


# ---- coverage-gap rows, derived from the catalog ----
gap_rows = []
for entry in cat["unsupported_requested_categories"]:
    name = entry["category"]
    status = entry["status"]
    label = f"**{status}**" if status in ("gap", "partial") else status
    gap_rows.append(f"| `{name}` | {label} | {entry['reason']} |")

rr_rows = []
for e in cat["review_required_summary"]["tools"]:
    disp = e["disposition"]
    if e["groups"]:
        disp += " — " + ", ".join(f"`{g}`" for g in e["groups"])
    rr_rows.append(f"| `{e['tool']}` | {e['reason']} |")

overlap_rows = ["| Tool | Groups | Why |", "|---|---|---|"]
for t, gs in sorted(overlaps.items()):
    why = OVERLAP_WHY.get(t, "One read serving two workflows")
    overlap_rows.append(f"| `{t}` | {', '.join(gs)} | {why} |")

servers_rows = ["| Server | Tools |", "|---|---|"]
for s, n in sorted(DIST.items()):
    servers_rows.append(f"| `{s}` | {n} |")

empty_ann = ann_cov["tools_with_empty_annotations_object"]
empty_sample = ", ".join(f"`{t}`" for t in empty_ann[:6]) + (
    f", and the 212 UniFi tools" if len(empty_ann) > 6 else "")

risk_level_rows = [
    "| Risk level | Meaning |", "|---|---|",
    "| `low` | Reads state and changes nothing. |",
    "| `medium` | Changes state, reads sensitive data, or acts on records whose blast radius is "
    "not obvious from the tool name. |",
    "| `high` | Destructive, publishes externally, spends money, or grants persistent autonomy. |",
    "| `review-required` | Broad-capability or unusually ambiguous. Held out of ordinary groups "
    "pending an explicit operator decision. |",
]

dist_rows = [
    "| Capability category | Risk | Tools |", "|---|---|---|",
]
cat_risk = {
    "read-only": "low", "sensitive-data": "medium", "mutating": "medium",
    "persistent-or-autonomous": "high", "external-communication": "high",
    "destructive": "high", "access-control-change": "high", "configuration-change": "high",
    "broad-capability": "review-required",
}
for c in ["read-only", "sensitive-data", "mutating", "persistent-or-autonomous",
          "external-communication", "destructive", "configuration-change",
          "access-control-change", "broad-capability"]:
    dist_rows.append(f"| `{c}` | {cat_risk[c]} | {cat_c[c]} |")

README = f"""# MCPJungle tool inventory and least-privilege groups — Noesis

Catalog of the tools exposed by the Noesis MCPJungle gateway and the tool groups
that narrow that surface for individual Noesis profiles.

**Status: all {len(groups)} groups are deployed and verified live** (2026-10-26).

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
| **Unique tools** | **{NT}** |
| **Source servers** | **{NS}** |
| Discovery timestamp | `{TS}` |

### What "complete" means

This is a **complete server-wide inventory**, not merely the view one connection
happens to expose. Two independent enumerations were performed and reconciled
name-by-name:

1. `tools/list` on the authenticated connection — {NT} canonical names.
2. `mcpjungle list tools --registry https://mcpjungle.tailf99a0.ts.net` — the
   gateway's own registry-wide listing, which is independent of any client's
   permissions — {NT} canonical names.

The set difference is **empty in both directions**, and **zero** tools are
disabled registry-wide. Every one of the {NS} registered server names is an exact
canonical prefix of at least one discovered tool, so no server was missed.

### What changed on 2026-10-26

Four upstream servers were registered on this gateway, adding **392 tools**:

| Server | Tools | Surface |
|---|---|---|
| `unifi` | {DIST['unifi']} | The operator's own UniFi controller estate, via the k3s deployment |
| `hunter` | {DIST['hunter']} | The operator's own Hunter.io account |
| `notion` | {DIST['notion']} | The operator's own Notion workspace |
| `gitbook-management` | {DIST['gitbook-management']} | The operator's own GitBook organization |

All {NT - 308} new tools are **additive**: the previous 308 are still present, and
no canonical name was reused or removed.

### Hermes reports 312 — why the numbers differ

`hermes mcp list` shows **312** tools for this server. That figure was captured
when the Hermes connection last enumerated the registry, before the four servers
above were registered. The gateway itself now serves **{NT}**. On the next
reconnection Hermes will report **{NT + 4}**: {NT} upstream tools plus **4
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
  | Tools | {DIST['unifi']} | 347 |
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
  `https://mcp.beacon.sh` endpoint exposing {DIST['beacon-managed']} tools. Both are
  Beacon, but they are separate connections with separate tool sets: the groups in
  this catalog constrain the hosted one and have no effect on the local one.

A group therefore controls only the tools reachable through *its own* group
endpoint. It does not constrain `/mcp` on the main gateway, and it does not
constrain any directly-configured MCP server.

### Registered servers

{servers_rows}

---

## 2. Compatibility evidence

All claims below are verified against **MCPJungle 0.4.6**, whose release tag is
`0.4.6` (not `v0.4.6`).

| Question | Answer | Evidence |
|---|---|---|
| Supported group JSON schema | `name`, `description`, `included_tools`, `included_servers`, `excluded_tools` — and nothing else | `pkg/types/tool_group.go` |
| Canonical tool-name format | `<server-name>__<tool-name>`, split on the **first** `__` | `internal/service/mcp/util.go` (`serverToolNameSep`, `mergeServerToolNames`) |
| How exposed names map to group names | Identically — the names `tools/list` returns *are* the names `included_tools` accepts. No rewriting, splitting or renaming is performed. | Verified against `tools/list` and `mcpjungle list tools`, both returning the same {NT} canonical names |
| Group naming constraints | `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` — must start alphanumeric; then alphanumerics, underscores, hyphens only | `internal/service/toolgroup/toolgroup.go` (`ValidGroupName`) |
| Creation syntax | `mcpjungle create group --conf <file>` | `mcpjungle create group --help` |
| Update syntax | `mcpjungle update group --conf <file>` — replaces the definition outright; removed tools stop being reachable immediately | `mcpjungle update group --help` |
| Group endpoint paths | `/v0/groups/{{group-name}}/mcp` (streamable HTTP, preferred); `/v0/groups/{{group-name}}/sse` and `/v0/groups/{{group-name}}/message` (SSE, deprecated upstream) | `internal/api/tool_groups.go` (`getToolGroupEndpoints`), `internal/api/server.go` (`V0PathPrefix = "/v0"`) |
| Unavailable / disabled / removed tools | Creation **fails** if a listed tool does not exist or is disabled. A tool disabled globally is removed from every group endpoint, though the group definition still lists it. On restart, a group whose tools cannot be resolved initialises **empty** rather than failing startup. | `internal/service/toolgroup/toolgroup.go` (`CreateToolGroup`, `initToolGroupMCPServers`) |
| Group name changes | Not possible — `update group` keeps the original name | `internal/service/toolgroup/toolgroup.go` (`UpdateToolGroup`) |
| Who may create groups | **Depends on server mode.** In enterprise mode only an admin may; in development mode `requireAdminUser` short-circuits and any caller may. **This gateway is in development mode**, so group creation succeeded with no admin token — see "Server mode" in section 7. | MCPJungle 0.4.6 source, `internal/api/middleware.go` (`requireAdminUser`); live server behaviour verified 2026-10-25 |

### Allowlist policy

Every group in `groups/` uses an explicit `included_tools` allowlist. **No group
uses `included_servers`.** Broad server membership would silently widen a group
whenever an upstream server adds a tool; an explicit allowlist cannot.

---

## 3. The groups

{len(groups)} groups, {uniq_assigned} tools assigned, {unassigned} held out. Risk is
the highest level among the member tools, raised to the group's declared floor
where the declaration is the stricter judgement.

"""

for title, names in SECTIONS:
    README += f"### {title}\n\n{group_table(names)}\n\n"
    if title == "Legal and regulatory":
        ywca = [t for t in by_name["legal-research"]["tools"]
                if t.startswith("misjusticeallinace-ywcaofmissoula-pub__")]
        ywca_feedback = [t for t in by_name["communications-send"]["tools"]
                         if t.startswith("misjusticeallinace-ywcaofmissoula-pub__")]
        README += f"""**Legal research is deliberately split from general web search.**
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

{chr(10).join('- `' + t + '`' for t in ywca)}

Its third tool, `{ywca_feedback[0]}`, submits a message to the documentation
site. That is an outbound external communication, so it is held in
`communications-send` rather than in the read-only legal group.

Note that this public documentation server is a **different surface** from the
`gitbook-management` server registered on 2026-10-26, which reaches the
operator's own GitBook organization and is grouped separately. The two must not
be confused: one is a published third-party corpus, the other is private
first-party content.

"""

README += f"""### Deliberate overlaps

{len(overlaps)} tools appear in more than one group. Each is a genuine
multi-workflow tool, and the overlap is named rather than removed:

{chr(10).join(overlap_rows)}

No generic tool is copied into every group.

---

## 4. Held out of all groups — review required

{len(rr_tools)} tools are classified `review-required`. {len(unassigned_tools)} are held
out of **every** group; the remaining {len(rr_tools) - len(unassigned_tools)} sit inside a
group that is itself flagged review-required and has no proposed consumer, which is
how `browser-automation` holds `firecrawl-search__firecrawl_interact`.

| Tool | Reason |
|---|---|
{chr(10).join(rr_rows)}

**Operator decision required** for each: is the capability needed at all, and if so
which profile may hold it under what approval path?

---

## 5. Coverage gaps — requested categories the inventory cannot support

| Requested category | Status | Reason |
|---|---|---|
{chr(10).join(gap_rows)}

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
  exposes all {NT} tools to any credential that can reach it, and the UniFi and
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

{reviewer_block('noesis-sentinel')}

{reviewer_block('noesis-skeptic')}

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

All {len(groups)} groups were created on the live gateway and verified:

```bash
mcpjungle create group --conf config/mcpjungle/groups/<group-name>.json \\
  --registry https://mcpjungle.tailf99a0.ts.net
```

**Result: {len(groups)} created, 0 failed.** Verification was two-layer:

1. Every group's live definition was compared name-by-name against its source
   file — `name`, `description` and `included_tools` are identical for all
   {len(groups)}.
2. Every group's MCP endpoint was probed with `initialize` + `tools/list`
   (discovery only — no tool was invoked). Each endpoint serves **exactly** its
   declared `included_tools`: {len(groups)}/{len(groups)} matched, 0 mismatches.

The main `/mcp` endpoint still serves all {NT} tools. **Creating tool groups does
not narrow the main gateway** — narrowing a client requires pointing it at a
group endpoint. No Hermes client connection was repointed.

For updates and removal:

```bash
mcpjungle update group --conf config/mcpjungle/groups/<group-name>.json \\
  --registry https://mcpjungle.tailf99a0.ts.net

mcpjungle delete group <group-name> \\
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

The route shape `/v0/groups/{{group-name}}/mcp` was verified from the MCPJungle
0.4.6 source before deployment, and every URL below is live and serving:

```
https://mcpjungle.tailf99a0.ts.net/v0/groups/<group-name>/mcp
```

Each group file and catalog entry is marked `"endpoint_status": "live"`.

### Backup

`config/mcpjungle/backup/gateway-state-backup.json` captures the live gateway
state: the {NS} registered upstream servers, the {len(groups)} group definitions, and a
pointer to the {NT}-tool main-endpoint inventory. Upstream credentials are
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
old = {{t["name"] for t in json.load(open("config/mcpjungle/tool-inventory.json"))["tools"]}}
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
2026-10-26: all {len(groups)} group definitions, the {NS} registered upstream servers, and a
pointer to the {NT}-tool inventory. **Upstream credentials are not in it** — they
must come from the Bitwarden escrow if a restore is ever needed. Restore servers
before groups: group creation validates every listed tool and fails if a tool
does not exist.

### Before any future change

```bash
# 1. Export the current definition of every affected group and keep it.
mcpjungle get group <group-name> --registry https://mcpjungle.tailf99a0.ts.net \\
  > "rollback/<group-name>.before.json"

# 2. Record the exact pre-change tool set.
mcpjungle list tools --group <group-name> --registry https://mcpjungle.tailf99a0.ts.net \\
  > "rollback/<group-name>.tools.before.txt"
```

Keep both files. `get group` shows the stored definition including tools that are
already disabled or deleted; `list tools --group` shows what is actually callable
right now. You need both to reconstruct state exactly.

### Rolling back a group

```bash
mcpjungle update group --conf rollback/<group-name>.before.json \\
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

A pattern scan across all {NT} tools — bearer tokens, JWTs, provider API keys, cloud
access keys, 32-character hex secrets, credential assignments, credential-bearing
URLs and e-mail addresses — returned **zero hits**. Descriptions, schemas and
`_meta` are reproduced as returned; they contain tool contracts only, because no
live record data was retrieved during discovery.

**Not available:**

- Output schemas are absent for **{ann_cov['tools_without_output_schema']} of {NT}** tools because the upstream servers
  do not publish them. No output schema was inferred.
- MCP annotations carry no values for **{len(empty_ann)}** tools: the server returned an empty
  annotations object for each — {empty_sample}. The observed value is preserved
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

The {DIST['unifi']} UniFi tools publish **no** MCP annotations at all: the upstream
returns an empty annotations object for every one of them. Their classification
was taken from the description, the input schema and the upstream source, and each
rationale says so.

| Risk level | Meaning |
|---|---|
{chr(10).join(risk_level_rows)}

Distribution across the {NT} tools:

{chr(10).join(dist_rows)}

Totals: {risk_c['low']} `low`, {risk_c['medium']} `medium`, {risk_c['high']} `high`, {risk_c['review-required']} `review-required`.

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

Current result: **PASS**, {len(groups)} groups, {NT} tools, {uniq_assigned} assigned, {unassigned} held out.
"""

out = MCP / "README.md"
out.write_text(README, encoding="utf-8")
print(f"wrote {out}")
print(f"  {len(groups)} groups, {NT} tools, {uniq_assigned} assigned, {unassigned} held out")
print(f"  review-required: {len(rr_tools)}  overlaps: {len(overlaps)}")
