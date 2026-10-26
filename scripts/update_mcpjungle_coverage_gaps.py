#!/usr/bin/env python3
"""Update the coverage-gap categories in the catalog for the 700-tool inventory.

The 2026-10-25 gap list described a 308-tool, 20-server world with no network
surface. Four servers changed that, so the gaps are recomputed from what is
actually registered. Run after gen.py, before gen_readme.py.
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MCP = R / "config" / "mcpjungle"

cat = json.loads((MCP / "tool-groups.json").read_text(encoding="utf-8"))
inv = json.loads((MCP / "tool-inventory.json").read_text(encoding="utf-8"))
NT = len(inv["tools"])
NS = len({t["source_server"] for t in inv["tools"]})

NEW_GAPS = [
    {
        "category": "devops-readonly",
        "status": "coverage gap",
        "reason": (
            f"No DevOps or CI server is registered in this gateway. There is no Docker, Kubernetes, "
            f"Terraform, Ansible, cloud-provider or CI tool among the {NT} discovered tools. The "
            f"nearest surfaces are workflow-inspection, observability and the network-* groups, and "
            f"naming any of them 'devops-readonly' would misrepresent it: they report state, they do "
            f"not change infrastructure. Infrastructure execution lives in the noesis-ansible "
            f"repository and in the Hermes terminal toolset, not in MCPJungle."
        ),
        "partial_analogue": ["workflow-inspection", "observability", "network-inventory"],
    },
    {
        "category": "network-operations-readonly",
        "status": "supported",
        "reason": (
            f"The UniFi MCP server is registered in this gateway and contributes {NT and 212} read "
            f"tools, split across seven groups by capability: network-inventory, "
            f"network-security-policy, network-telemetry, network-protect, network-fleet, "
            f"network-backup and network-controller, plus network-proxy which is held "
            f"review-required. The deployment sets UNIFI_READ_ONLY=true, so the registered surface "
            f"contains no mutating UniFi tool at all: these groups are a read-only view by "
            f"construction, not by policy. Note that the separately-configured Hermes connection "
            f"'unifi-local' exposes 347 tools including mutating ones and is NOT constrained by any "
            f"group here."
        ),
        "partial_analogue": [
            "network-inventory", "network-security-policy", "network-telemetry",
            "network-protect", "network-fleet", "network-backup", "network-controller",
        ],
    },
    {
        "category": "cloud-infrastructure-readonly",
        "status": "coverage gap",
        "reason": (
            "No cloud-provider server (AWS, GCP, Azure, Cloudflare) is registered in this gateway. "
            "The UniFi groups cover on-premises network hardware, which is a different estate."
        ),
    },
    {
        "category": "cloud-infrastructure-write",
        "status": "coverage gap",
        "reason": (
            "Same as cloud-infrastructure-readonly: no cloud-provider server is registered. The "
            "closest mutation surface is platform-administration, which manages one documentation "
            "site, and the UniFi deployment is read-only."
        ),
        "partial_analogue": ["platform-administration"],
    },
    {
        "category": "blockchain-research",
        "status": "coverage gap",
        "reason": (
            "No blockchain, wallet, miner or DePIN data server is registered. The noesis-ledger "
            "domain can only be served by the generic web-research, academic-research and "
            "market-research groups."
        ),
        "partial_analogue": ["market-research", "web-research", "academic-research"],
    },
    {
        "category": "financial-actions",
        "status": "coverage gap",
        "reason": (
            f"No spending, transfer, trading, payment or wallet tool exists anywhere in the {NT}-tool "
            f"inventory. Hunter's credit-consuming lookups draw on a metered search and credit "
            f"quota rather than money, and the connected account is on the free tier; on a paid plan "
            f"the same calls would become billable, which is why the spending constraint is recorded "
            f"on hunter-contact-records rather than treated as absent. The one payment-adjacent tool "
            f"is court-listener__pray_for_document, which sits in legal-alerts under a spending "
            f"control."
        ),
        "partial_analogue": ["market-research", "legal-alerts", "hunter-contact-records"],
    },
    {
        "category": "communications-readonly (broad inbox)",
        "status": "partial",
        "reason": (
            "No mail, chat or SMS server is registered in this gateway. The communications read "
            "surfaces are the Mintlify comment thread and the Notion calendar, which together are "
            "not an inbox: the Herald workflow still cannot read prior outbound correspondence, and "
            "no tool here can confirm what was already sent to anyone."
        ),
        "partial_analogue": ["communications-readonly", "notion-calendar-read"],
    },
    {
        "category": "database-readonly / database-write",
        "status": "supported",
        "reason": (
            "n8n data tables, the Mintlify deployment databases and the Notion data sources provide "
            "readable and writable tabular surfaces, and the groups exist. There is still no generic "
            "SQL database server (no PostgreSQL, MySQL or SQLite tool). The two SQL surfaces "
            "present are each confined to its own store: mintlify__query_analytics is held in "
            "data-analytics, and the Notion queries in notion-data-query are read-only by "
            "construction."
        ),
        "partial_analogue": ["database-readonly", "database-write", "data-analytics",
                             "notion-data-query"],
    },
    {
        "category": "observability",
        "status": "supported",
        "reason": (
            "Deployment status, workflow run history, execution records, provider credit and usage "
            "reporting, and the Hunter quota report cover the read-only observability surface. There "
            "is still no metrics, log-aggregation or tracing server (no Prometheus, Grafana or Loki) "
            "registered, and no infrastructure telemetry of any kind: the UniFi groups report "
            "controller state as read by the controller, not as collected telemetry."
        ),
        "partial_analogue": ["observability", "network-inventory", "network-telemetry"],
    },
    {
        "category": "agent-infrastructure",
        "status": "supported",
        "reason": (
            "n8n provides agent draft authoring, versioning, validation and retirement; the "
            "Beacon-managed server provides the memory and trace substrate agents read from; and "
            "Notion provides Custom Agent sessions plus the skill enablement that decides what those "
            "agents may load. All three surfaces exist, and the groups exist."
        ),
        "partial_analogue": ["agent-infrastructure", "notion-agent-sessions",
                             "notion-agent-session-read", "memory-management"],
    },
    {
        "category": "security-audit",
        "status": "supported but narrow",
        "reason": (
            "Only two genuine security surfaces exist: GitHub secret scanning and Beacon's security "
            "findings. There is no SAST, DAST, dependency-audit or container-scanning server "
            "registered, so the group cannot cover a full security review. The UniFi groups read "
            "the operator's own security posture but are not a scanning surface."
        ),
        "partial_analogue": ["security-audit", "network-security-policy"],
    },
    {
        "category": "source-control-readonly / source-control-write",
        "status": "supported",
        "reason": (
            "The GitHub MCP server exposes both surfaces, split across source-control-readonly, "
            "source-control-issues-readonly and source-control-write. It is the only source-control "
            "server registered."
        ),
    },
    {
        "category": "outbound-messaging / sales-prospecting",
        "status": "supported",
        "reason": (
            "Hunter registers 103 tools covering contact discovery, enrichment, CRM record "
            "management and outbound email sending, split across six groups. The sending surface is "
            "isolated in hunter-outbound-email, and the destructive record surface in "
            "hunter-record-destructive. This is the only registered capability that sends email to "
            "people who did not ask to be contacted, so it carries the strictest approval control "
            "in the catalog."
        ),
        "partial_analogue": ["hunter-outbound-email", "hunter-contact-records",
                             "hunter-record-authoring", "hunter-record-destructive"],
    },
    {
        "category": "workspace-document-management",
        "status": "supported",
        "reason": (
            "Notion contributes 65 tools covering the operator's own workspace (pages, databases, "
            "comments, calendars and agent sessions) and GitBook contributes 12 covering the "
            "operator's own GitBook organization (sites, navigation, change requests and "
            "publication). The two are split by capability and by risk, and neither can be confused "
            "with the MISJustice/YWCA GitBook corpus, which stays in legal-research."
        ),
        "partial_analogue": ["notion-workspace-read", "notion-workspace-authoring",
                             "notion-workspace-destructive", "notion-calendar-write",
                             "gitbook-org-read", "gitbook-change-request", "gitbook-publish"],
    },
]

cat["unsupported_requested_categories"] = NEW_GAPS
(MCP / "tool-groups.json").write_text(
    json.dumps(cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"updated {len(NEW_GAPS)} coverage-gap categories")
for g in NEW_GAPS:
    print(f"  {g['category']:42s} {g['status']}")
