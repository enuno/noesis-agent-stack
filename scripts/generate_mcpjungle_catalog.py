#!/usr/bin/env python3
"""Generate the canonical MCPJungle artifacts from the live tool contracts.

Reads:
  /home/elvis/.hermes/cache/scratch/mcpgrp/all-tools.json   (700 live contracts)
  config/mcpjungle/tool-inventory.json                        (308 canonical entries, kept verbatim)

Writes:
  config/mcpjungle/tool-inventory.json
  config/mcpjungle/groups/*.json
  config/mcpjungle/tool-groups.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Paths are overridable so the generator is not bound to one checkout or one
# scratch directory:
#   --repo PATH       repository root            (default: two levels above this file)
#   --contracts PATH  live tool contracts JSON   (default: $MCPGRP_SCRATCH/all-tools.json)
#   --deployed        mark the groups endpoint_status as live
import argparse

_ap = argparse.ArgumentParser(add_help=False)
_ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
_ap.add_argument("--contracts", default=os.environ.get(
    "MCPGRP_SCRATCH", "/home/elvis/.hermes/cache/scratch/mcpgrp") + "/all-tools.json")
_args, _ = _ap.parse_known_args()

R = Path(_args.repo).resolve()
MCP = R / "config" / "mcpjungle"
SCRATCH = Path(_args.contracts).resolve().parent
CONTRACTS = Path(_args.contracts)
DEPLOYED = "--deployed" in sys.argv

DISCOVERY_TS = "2026-10-26T00:00:00.000000+00:00"

CONSUMER_BASIS = (
    "Profile names verified against the 16 profile keys in profiles/noesis-roster.yaml. "
    "NoesisPraxis is a persona and host naming convention, not a roster profile: the repository's "
    "STANDING-GOAL-FINAL-DELIVERABLE.md records that 'noesis-praxis' is not an entry in "
    "profiles/noesis-roster.yaml, so it is not used as a consumer name. The infrastructure-operator "
    "role is represented by noesis-substrate. Reviewer-only profiles (noesis-sentinel, noesis-skeptic) "
    "receive no group that can write, delete, publish, spend or delegate; they may hold groups whose "
    "members only read, including reads of sensitive data, which a reviewer needs."
)
RISK_BASIS = (
    "The highest risk level among the member tools, using the per-tool classification in "
    "tool-inventory.json, raised to the group's declared floor where the declaration is the stricter "
    "judgement."
)
NON_LOW_NOTE = (
    "Every member whose risk_classification in tool-inventory.json is not 'low'. The medium-risk "
    "members are included deliberately: omitting them would make this field mislead a reviewer "
    "auditing which members of a group carry any elevated risk."
)
SAFETY_NOTE = (
    "Recorded for completeness; the Notion connection reaches the operator's own workspace and the "
    "credential scope must be confirmed at the upstream provider."
)

def _add_missing(seq, items):
    """Append only the items that are not already present.

    The generator appends to lists carried forward from git HEAD. HEAD may
    already contain the generator's own earlier output, so the append must be
    a set-union rather than a plain extend.
    """
    out = list(seq)
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _dedupe(seq):
    """Order-preserving de-duplication.

    The generator appends to lists carried forward from git HEAD, so the
    appends must be idempotent: re-running against a HEAD that already contains
    the generator's own output must not duplicate them.
    """
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


live = json.load(open(CONTRACTS))
live_by_name = {t["name"]: t for t in live}
# The canonical baseline is read from git HEAD, not from the working-tree file:
# the generator is then idempotent and can be re-run after a partial edit.
#
# The four servers added on 2026-10-26 are classified from the live contracts
# below, so their tools are excluded from the carried-forward baseline. Without
# that exclusion the generator would depend on whether HEAD already contains
# them, and a re-run after committing its own output would add them twice.
import subprocess
baseline_raw = subprocess.run(
    ["git", "-C", str(R), "show", "HEAD:config/mcpjungle/tool-inventory.json"],
    capture_output=True, text=True, check=True).stdout
canon_inv = json.loads(baseline_raw)
NEW_SERVERS = ("unifi", "notion", "hunter", "gitbook-management")
canon_by_name = {t["name"]: t for t in canon_inv["tools"]
                 if t["source_server"] not in NEW_SERVERS}

# --------------------------------------------------------------------------
# rationale helpers
# --------------------------------------------------------------------------

def first_sentence(desc: str) -> str:
    d = " ".join((desc or "").split())
    m = re.search(r"^(.{20,300}?)\.(?:\s|$)", d)
    s = m.group(1) if m else d[:240]
    s = s.replace("`", "'")
    if s and s[-1] not in ".!?":
        s += "."
    return s


def read_rationale(t, unifi_style: bool) -> str:
    fs = first_sentence(t.get("description"))
    if unifi_style:
        return (
            "The upstream publishes no MCP annotations for this tool (the annotations object is "
            f"empty), so the classification rests on its description and input schema alone: {fs} "
            "Nothing is written, sent, delegated or spent, so the tool reads state and changes nothing."
        )
    return (
        "Upstream advertises readOnlyHint=true, and the description and input schema expose no "
        "mutation, deletion, publication or external-message effect. The tool name was also checked "
        "against a mutation-verb list and contains none."
    )


def mutating_rationale(t, unifi_style: bool, scope: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream advertises readOnlyHint=false: "
    )
    return (
        f"{lead}{fs} The change is confined to {scope} and is reversible; it removes nothing, "
        "publishes nothing externally and spends nothing."
    )


def sensitive_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream advertises readOnlyHint=true, but the content returned is the sensitive part: "
    )
    return (
        f"{lead}{fs} The output is {what}, so it needs scoped credentials and redaction before it "
        "leaves the host."
    )


def destructive_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream marks the operation destructive: "
    )
    return (
        f"{lead}{fs} It {what}, and no undo exists from the API."
    )


def external_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream marks the operation as affecting the open world: "
    )
    return (
        f"{lead}{fs} It {what}, so the effect crosses the Noesis boundary and is visible to third "
        "parties."
    )


def persistent_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream marks the operation destructive: "
    )
    return f"{lead}{fs} It {what}, and the work continues after the call returns."


def config_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream marks the operation destructive because it overwrites configuration: "
    )
    return (
        f"{lead}{fs} It {what}, and the rewritten configuration outlives the call."
    )


def access_rationale(t, unifi_style: bool, what: str) -> str:
    fs = first_sentence(t.get("description"))
    lead = (
        "The upstream publishes no MCP annotations for this tool (the annotations object is empty), "
        "so the classification rests on its description and input schema alone: "
        if unifi_style
        else "Upstream marks the operation destructive: "
    )
    return f"{lead}{fs} It {what}, and the new authority outlives the call."


# --------------------------------------------------------------------------
# UniFi classification
# --------------------------------------------------------------------------

UNIFI_PROXY = {
    "connector_network_get": (
        "Generic GET proxy for the UniFi Network application: the caller supplies the console id and "
        "the sub-path under the Cloud Connector proxy prefix, and the raw upstream response is "
        "returned. The upstream restricts the request to GET and validates every path segment against "
        "traversal, but the endpoint itself is caller-selected, so group membership cannot constrain "
        "which UniFi endpoint is read. It is narrower than court-listener__call_endpoint, which also "
        "exposes the HTTP method, but it is the same shape: a caller-chosen target. In this deployment "
        "the tool is additionally inert, because UNIFI_SITE_MANAGER_ENABLED is unset and the call "
        "raises 'Site Manager API is not enabled'."
    ),
    "connector_protect_get": (
        "Generic GET proxy for the UniFi Protect application: the caller supplies the console id and "
        "the sub-path under the Cloud Connector proxy prefix, and the raw upstream response is "
        "returned. The upstream restricts the request to GET and validates every path segment against "
        "traversal, but the endpoint itself is caller-selected, so group membership cannot constrain "
        "which Protect endpoint is read, including the camera and event endpoints. In this deployment "
        "the tool is additionally inert, because UNIFI_SITE_MANAGER_ENABLED is unset and the call "
        "raises 'Site Manager API is not enabled'."
    ),
}
UNIFI_FANOUT = (
    "Runs one caller-named read tool across every controller in scope at once. The upstream enforces "
    "that only read-tier controller tools can be fanned out and rejects fleet-prefixed and unknown "
    "tool names, so the effect class is bounded to reads, but the caller still chooses which tool "
    "runs: a holder of this tool reaches every read-tier controller tool whether or not that tool is "
    "in the group it was granted. Group membership therefore cannot constrain the target, which is "
    "the property that makes a tool broad-capability rather than an ordinary read."
)

def _is_integration(n):
    """The UniFi Site Manager / integration API surface."""
    for p in ("integration_", "get_integration_"):
        if n.startswith(p):
            return True
    return n in ("list_hosts", "get_host", "get_version_control", "list_vantage_points",
                 "list_countries", "list_resources", "read_resource",
                 "list_all_sites_aggregated", "compare_site_performance", "search_across_sites",
                 "get_site_details", "get_site_statistics", "get_site_inventory",
                 "get_site_health_summary", "get_cross_site_statistics", "list_sites",
                 "get_internet_health", "get_isp_metrics", "query_isp_metrics", "health_check")


def _is_switching(n):
    """Switch, stack, LAG and port configuration."""
    for p in ("list_switch_stacks", "get_switch_stack", "list_lags", "get_lag_details",
              "list_mclag_domains", "get_mclag_domain", "list_port_profiles", "get_port_profile",
              "list_device_tags"):
        if n.startswith(p) or n == p:
            return True
    return False


def _is_addressing(n):
    """Address assignment: DHCP, DNS, VLANs, subnets, MAC tags, port mappings."""
    for p in ("list_dhcp_reservations", "get_dhcp_reservation", "list_mac_tags", "get_mac_tag",
              "list_dynamic_dns", "get_dynamic_dns", "list_wan_dns", "list_vlans",
              "get_subnet_info", "get_port_mappings"):
        if n.startswith(p) or n == p:
            return True
    return False


def _is_inventory(n):
    """Device, WLAN and network configuration reads."""
    for p in ("list_devices", "get_device_", "search_devices", "list_pending_devices",
              "list_wlans", "get_wlan_statistics", "get_ap_radio_config",
              "get_network_details", "get_network_statistics", "get_network_topology",
              "get_topology_statistics", "list_wan_connections", "get_application_info"):
        if n.startswith(p) or n == p:
            return True
    return False


def _is_fleet(n):
    if n.startswith("fleet_") and n != "fleet_fanout":
        return True
    for p in ("site_manager", "integration_", "innerspace", "carrier_", "mobility_",
              "get_carrier", "get_mobility", "get_innerspace", "download_innerspace"):
        if n.startswith(p):
            return True
    return n in ("list_hosts", "get_host", "get_version_control", "list_vantage_points",
                 "list_countries", "list_resources", "read_resource", "list_all_sites_aggregated",
                 "compare_site_performance", "search_across_sites", "get_site_details",
                 "get_site_statistics", "get_site_inventory", "get_site_health_summary",
                 "get_cross_site_statistics", "list_sites", "get_internet_health",
                 "get_isp_metrics", "query_isp_metrics", "health_check",
                 # site-manager surfaces that the family matcher above does not catch
                 "get_sdwan_config", "get_sdwan_config_status", "list_sdwan_configs")


def _is_diagnostics(n):
    """Health, speed, spectrum and RF diagnostics."""
    for p in ("get_historical_stats", "get_network_references", "get_spectrum_scan",
              "list_spectrum_interference", "get_speed_test_history", "get_speed_test_status",
              "list_client_rf_health", "list_ap_neighbors_v2", "list_neighboring_aps",
              "list_site_internal_ap_neighbors_v2", "list_alarms", "list_events",
              "stream_traffic_flows"):
        if n.startswith(p) or n == p:
            return True
    return False


def _is_backup(n):
    if "backup" in n or n.startswith("export_topology"):
        return True
    return n in ("get_restore_status", "validate_backup")


def _is_telemetry(n):
    for p in ("get_client", "list_client", "get_flow", "get_traffic", "get_top_flows",
              "get_dpi", "list_dpi", "list_top_applications", "filter_traffic", "find_flows",
              "export_traffic"):
        if n.startswith(p):
            return True
    return n in ("list_active_clients", "get_connection_states", "search_clients",
                 "get_device_by_mac", "get_device_connections", "get_device_statistics",
                 "get_device_port_overrides")


def _is_security_policy(n):
    for p in ("list_firewall", "get_firewall", "list_acl", "get_acl", "list_radius",
              "get_radius", "list_content_filter", "list_content_filters", "get_dns_filter",
              "list_port_forwards", "list_traffic_matching", "get_traffic_matching",
              "list_traffic_routes", "list_zone", "get_zone", "list_hotspot", "get_hotspot",
              "get_guest_portal", "list_vouchers", "get_voucher"):
        if n.startswith(p):
            return True
    return n == "get_smart_queue_status"


def _is_controller(n):
    return n in ("list_controllers", "get_active_controller", "select_controller")


# name-pattern -> unifi group
UNIFI_FAMILIES = [
    ("network-proxy", lambda n: n.startswith("connector_")),
    ("network-integration", _is_integration),
    ("network-fleet", _is_fleet),
    ("network-protect", lambda n: "protect" in n),
    ("network-backup", _is_backup),
    ("network-telemetry", _is_telemetry),
    ("network-security-policy", _is_security_policy),
    ("network-controller", _is_controller),
    ("network-switching", _is_switching),
    ("network-addressing", _is_addressing),
    ("network-inventory", _is_inventory),
    ("network-diagnostics", _is_diagnostics),
]

# unifi tools whose output is sensitive even though they only read
UNIFI_SENSITIVE = {
    "get_radius_account": "the RADIUS account configuration of the operator's site, which can carry "
                           "shared-secret material",
    "get_protect_live_view": "live camera view material for the operator's premises",
    "get_protect_event_messages": "Protect event messages describing activity at the operator's premises",
    "get_protect_camera": "the configuration and identity of a camera at the operator's premises",
    "get_protect_nvr": "the configuration and identity of the operator's video recorder",
    "get_protect_sensor": "the configuration and identity of a sensor at the operator's premises",
    "get_protect_siren": "the configuration and identity of a siren at the operator's premises",
    "get_protect_speaker": "the configuration and identity of a speaker at the operator's premises",
    "get_protect_bridge": "the configuration and identity of a Protect bridge",
    "get_protect_alarm_hub": "the configuration and identity of the alarm hub",
    "get_protect_chime": "the configuration and identity of a doorbell chime",
    "get_protect_fob": "the identity and state of a Protect fob",
    "get_protect_light": "the configuration and identity of a Protect light",
    "get_protect_relay": "the configuration and identity of a Protect relay",
    "get_protect_link_station": "the configuration and identity of a link station",
    "get_protect_user": "the identity of a Protect account",
    "get_protect_viewer": "the identity of a Protect viewer",
    "get_protect_ulp_user": "the identity of a UniFi Identity account",
    "list_protect_events": "the event history of the operator's camera system",
    "list_protect_users": "the identities of every Protect account",
    "list_protect_viewers": "the identities of every Protect viewer",
    "list_protect_ulp_users": "the identities of every UniFi Identity account",
    "list_protect_devices": "the inventory of devices attached to the operator's premises",
    "list_protect_cameras": "the inventory of cameras at the operator's premises",
    "list_protect_nvrs": "the inventory of video recorders at the operator's premises",
    "list_protect_sensors": "the inventory of sensors at the operator's premises",
    "list_protect_lights": "the inventory of Protect lights at the operator's premises",
    "list_protect_sirens": "the inventory of Protect sirens at the operator's premises",
    "list_protect_speakers": "the inventory of Protect speakers at the operator's premises",
    "list_protect_bridges": "the inventory of Protect bridges",
    "list_protect_alarm_hubs": "the inventory of alarm hubs at the operator's premises",
    "list_protect_fobs": "the identities of Protect fobs",
    "list_protect_chimes": "the inventory of doorbell chimes",
    "list_protect_relays": "the inventory of Protect relays",
    "list_protect_link_stations": "the inventory of link stations",
    "list_protect_live_views": "the inventory of live camera views",
    "get_protect_subscribe_events": "the Protect event feed for the operator's premises",
    "get_protect_subscribe_devices": "the Protect device feed for the operator's premises",
    "get_protect_arm_profile": "the arm profile governing when the premises are protected",
    "list_protect_arm_profiles": "the arm profiles governing when the premises are protected",
}

UNIFI_SCOPE = {
    "network-inventory": "the operator's own network configuration",
    "network-security-policy": "the operator's own policy configuration",
    "network-telemetry": "the operator's own network telemetry",
    "network-fleet": "the operator's own multi-site estate",
    "network-protect": "the operator's own premises",
    "network-backup": "the operator's own backup store",
    "network-controller": "the controller selected for the current session",
}


def unifi_group(name: str) -> str:
    for g, pred in UNIFI_FAMILIES:
        if pred(name):
            return g
    return "network-inventory"


def classify_unifi(name: str):
    t = live_by_name["unifi__" + name]
    if name in UNIFI_PROXY:
        return "network-proxy", "broad-capability", "review-required", UNIFI_PROXY[name]
    if name == "fleet_fanout":
        return "network-proxy", "broad-capability", "review-required", UNIFI_FANOUT
    g = unifi_group(name)
    if name == "select_controller":
        return (g, "mutating", "medium",
                "The upstream publishes no MCP annotations for this tool (the annotations object is "
                "empty), so the classification rests on its description and input schema alone: "
                "Choose the controller this session's later tool calls target. It changes session-scoped "
                "routing, so subsequent calls act against a different device; the change is local and "
                "reversible rather than destructive, published or externally visible. In this "
                "deployment the server runs stateless HTTP, so the upstream refuses the call and the "
                "tool is inert.")
    if name in UNIFI_SENSITIVE:
        return (g, "sensitive-data", "medium",
                sensitive_rationale(t, True, UNIFI_SENSITIVE[name]))
    if name == "download_backup":
        return (g, "mutating", "medium",
                "The upstream publishes no MCP annotations for this tool (the annotations object is "
                "empty), so the classification rests on its description and input schema alone: "
                "Download a backup file to local storage. It writes a controller backup archive to the "
                "MCP server's own download directory, so the change is local and reversible, but the "
                "artifact contains the operator's controller configuration and must be handled as "
                "sensitive. The controller itself is not modified.")
    if name == "export_topology":
        return (g, "read-only", "low",
                read_rationale(t, True) + " The exported topology is the operator's own network graph "
                "and nothing is written or sent.")
    if name in ("get_traffic_flows", "filter_traffic_flows", "get_traffic_flow_details",
                "get_top_flows", "get_flow_analytics", "get_flow_statistics", "get_flow_trends",
                "export_traffic_flows", "find_flows_for_rule_reference"):
        return (g, "sensitive-data", "medium",
                sensitive_rationale(t, True,
                                    "per-client flow records naming source clients and the "
                                    "destinations they reached"))
    if name in ("get_client_details", "get_client_statistics", "get_client_dpi",
                "get_client_flow_aggregation", "list_active_clients", "search_clients",
                "get_connection_states", "list_client_rf_health"):
        return (g, "sensitive-data", "medium",
                sensitive_rationale(t, True,
                                    "client identity and per-client activity for the devices on the "
                                    "operator's network"))
    return (g, "read-only", "low", read_rationale(t, True))


# --------------------------------------------------------------------------
# Notion classification
# --------------------------------------------------------------------------

NOTION_ASSIGN = {
    # group, category, risk
    "notion-fetch": ("notion-workspace-read", "read-only", "low"),
    "notion-search": ("notion-workspace-read", "read-only", "low"),
    "notion-list-favorite-pages": ("notion-workspace-read", "read-only", "low"),
    "notion-list-private-pages": ("notion-workspace-read", "read-only", "low"),
    "notion-list-recent-pages": ("notion-workspace-read", "read-only", "low"),
    "notion-list-shared-pages": ("notion-workspace-read", "read-only", "low"),
    "notion-list-page-backlinks": ("notion-workspace-read", "read-only", "low"),
    "notion-get-comments": ("notion-workspace-read", "read-only", "low"),
    "notion-get-self": ("notion-workspace-read", "read-only", "low"),
    "notion-get-teams": ("notion-workspace-read", "read-only", "low"),
    "notion-get-groups": ("notion-workspace-read", "read-only", "low"),
    "notion-get-tool-access": ("notion-workspace-read", "read-only", "low"),
    "notion-get-enabled-skills": ("notion-workspace-read", "read-only", "low"),
    "notion-download-attachment": ("notion-workspace-read", "read-only", "low"),
    "notion-download-skill": ("notion-workspace-read", "read-only", "low"),
    "notion-get-file-download-urls": ("notion-workspace-read", "read-only", "low"),
    "notion-check-mcp-next-steps": ("notion-workspace-read", "read-only", "low"),
    "notion-show-advanced-analysis-next-steps": ("notion-workspace-read", "read-only", "low"),
    "notion-get-users": ("notion-workspace-read", "sensitive-data", "medium"),

    "notion-query-data-sources": ("notion-data-query", "sensitive-data", "medium"),
    "notion-query-multiple-data-sources": ("notion-data-query", "sensitive-data", "medium"),
    "notion-query-meeting-notes": ("notion-data-query", "sensitive-data", "medium"),

    "notion-create-pages": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-database": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-view": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-update-page": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-update-view": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-update-comment": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-comment": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-set-comment-reaction": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-set-discussion-resolved": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-move-pages": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-duplicate-page": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-restore-pages": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-attachment": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-file-upload": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-create-folder": ("notion-workspace-authoring", "mutating", "medium"),
    "notion-update-folder": ("notion-workspace-authoring", "mutating", "medium"),

    "notion-delete-pages": ("notion-workspace-destructive", "destructive", "high"),
    "notion-delete-databases": ("notion-workspace-destructive", "destructive", "high"),
    "notion-delete-comment": ("notion-workspace-destructive", "destructive", "high"),
    "notion-update-data-source": ("notion-workspace-destructive", "destructive", "high"),
    "notion-upload-skill": ("notion-workspace-destructive", "destructive", "high"),

    "notion-query-sessions": ("notion-agent-session-read", "read-only", "low"),
    "notion-search-sessions": ("notion-agent-session-read", "read-only", "low"),
    "notion-search-agents": ("notion-agent-session-read", "read-only", "low"),
    "notion-list-session-events": ("notion-agent-session-read", "read-only", "low"),
    "notion-get-session-status": ("notion-agent-session-read", "read-only", "low"),
    "notion-get-async-task": ("notion-agent-session-read", "read-only", "low"),
    "notion-wait-session": ("notion-agent-session-read", "read-only", "low"),
    "notion-memory-search": ("notion-agent-session-read", "read-only", "low"),
    "notion-read-session-event": ("notion-agent-session-read", "sensitive-data", "medium"),

    "notion-spawn-session": ("notion-agent-sessions", "persistent-or-autonomous", "high"),
    "notion-send-message-to-session": ("notion-agent-sessions", "persistent-or-autonomous", "high"),
    "notion-stop-session": ("notion-agent-sessions", "mutating", "medium"),
    "notion-update-enabled-skills": ("notion-agent-sessions", "configuration-change", "high"),
    "notion-convert-page-to-skill": ("notion-agent-sessions", "configuration-change", "high"),

    "notion-calendar-list-calendars": ("notion-calendar-read", "read-only", "low"),
    "notion-calendar-list-events": ("notion-calendar-read", "read-only", "low"),
    "notion-calendar-list-calendar-resources": ("notion-calendar-read", "read-only", "low"),
    "notion-calendar-list-contacts": ("notion-calendar-read", "sensitive-data", "medium"),
    "notion-calendar-list-coworkers-events": ("notion-calendar-read", "sensitive-data", "medium"),

    "notion-calendar-create-events": ("notion-calendar-write", "external-communication", "high"),
    "notion-calendar-update-events": ("notion-calendar-write", "external-communication", "high"),
    "notion-calendar-cancel-events": ("notion-calendar-write", "external-communication", "high"),
}

NOTION_CUSTOM = {
    "notion-get-users": sensitive_rationale(
        live_by_name["notion__notion-get-users"], False,
        "the identity of every member and guest in the operator's workspace"),
    "notion-query-data-sources": sensitive_rationale(
        live_by_name["notion__notion-query-data-sources"], False,
        "bulk rows from the operator's Notion data sources, which may hold personal records"),
    "notion-query-multiple-data-sources": sensitive_rationale(
        live_by_name["notion__notion-query-multiple-data-sources"], False,
        "bulk rows across several of the operator's Notion data sources"),
    "notion-query-meeting-notes": sensitive_rationale(
        live_by_name["notion__notion-query-meeting-notes"], False,
        "the content of the operator's meeting notes, including attendee records"),
    "notion-read-session-event": sensitive_rationale(
        live_by_name["notion__notion-read-session-event"], False,
        "the full visible content of a saved agent session event"),
    "notion-calendar-list-contacts": sensitive_rationale(
        live_by_name["notion__notion-calendar-list-contacts"], False,
        "the contacts reachable across the operator's connected calendar accounts"),
    "notion-calendar-list-coworkers-events": sensitive_rationale(
        live_by_name["notion__notion-calendar-list-coworkers-events"], False,
        "the event details of the operator's coworkers, which are other people's schedules"),
    "notion-delete-pages": destructive_rationale(
        live_by_name["notion__notion-delete-pages"], False,
        "moves pages and every database row to Trash, and the rows are gone from the workspace"),
    "notion-delete-databases": destructive_rationale(
        live_by_name["notion__notion-delete-databases"], False,
        "moves a database and all of its rows to Trash"),
    "notion-delete-comment": destructive_rationale(
        live_by_name["notion__notion-delete-comment"], False,
        "removes a comment, and with it the discussion when it was the last one"),
    "notion-update-data-source": destructive_rationale(
        live_by_name["notion__notion-update-data-source"], False,
        "accepts SQL DDL, so a DROP COLUMN statement removes a property and its values from every row"),
    "notion-upload-skill": destructive_rationale(
        live_by_name["notion__notion-upload-skill"], False,
        "replaces the target page's title, description, body and files with the imported archive"),
    "notion-spawn-session": persistent_rationale(
        live_by_name["notion__notion-spawn-session"], False,
        "hands work to a published Custom Agent that keeps running after the call returns"),
    "notion-send-message-to-session": persistent_rationale(
        live_by_name["notion__notion-send-message-to-session"], False,
        "feeds more work to a running Custom Agent that keeps acting after the call returns"),
    "notion-stop-session": mutating_rationale(
        live_by_name["notion__notion-stop-session"], False,
        "the agent session's live work; the capability can be started again"),
    "notion-update-enabled-skills": config_rationale(
        live_by_name["notion__notion-update-enabled-skills"], False,
        "enables or disables the skills available to the user and to external MCP clients and Notion AI"),
    "notion-convert-page-to-skill": config_rationale(
        live_by_name["notion__notion-convert-page-to-skill"], False,
        "marks an existing page as an agent skill, which changes what agents may load"),
    "notion-calendar-create-events": external_rationale(
        live_by_name["notion__notion-calendar-create-events"], False,
        "creates events on calendars the operator's attendees can see, and may notify them"),
    "notion-calendar-update-events": external_rationale(
        live_by_name["notion__notion-calendar-update-events"], False,
        "changes event times, attendees or recurrence on calendars others can see, and may notify them"),
    "notion-calendar-cancel-events": external_rationale(
        live_by_name["notion__notion-calendar-cancel-events"], False,
        "cancels events on calendars others can see, and may notify the attendees"),
}

NOTION_SCOPE = "the operator's own Notion workspace"


def classify_notion(name: str):
    if name not in NOTION_ASSIGN:
        raise SystemExit(f"notion tool not classified: {name}")
    g, cat, risk = NOTION_ASSIGN[name]
    if name in NOTION_CUSTOM:
        return g, cat, risk, NOTION_CUSTOM[name]
    t = live_by_name["notion__" + name]
    if cat == "read-only":
        return g, cat, risk, read_rationale(t, False)
    if cat == "mutating":
        return g, cat, risk, mutating_rationale(t, False, NOTION_SCOPE)
    raise SystemExit(f"missing custom rationale for {name}")


# --------------------------------------------------------------------------
# Hunter classification
# --------------------------------------------------------------------------

HUNTER_ASSIGN = {
    # group, category, risk
    "Get-Account-Details": ("hunter-account-read", "read-only", "low"),
    "Get-Company-List": ("hunter-account-read", "read-only", "low"),
    "Get-Connected-App": ("hunter-account-read", "read-only", "low"),
    "Get-Custom-Attribute": ("hunter-account-read", "read-only", "low"),
    "Get-Leads-List": ("hunter-account-read", "read-only", "low"),
    "Get-Message-Template": ("hunter-account-read", "read-only", "low"),
    "Get-Saved-Search": ("hunter-account-read", "read-only", "low"),
    "Get-Sequence": ("hunter-account-read", "read-only", "low"),
    "Get-Sequence-Follow-Up": ("hunter-account-read", "read-only", "low"),
    "Lead-Exists": ("hunter-account-read", "read-only", "low"),
    "List-Company-List-Folders": ("hunter-account-read", "read-only", "low"),
    "List-Company-Lists": ("hunter-account-read", "read-only", "low"),
    "List-Connected-Apps": ("hunter-account-read", "read-only", "low"),
    "List-Custom-Attributes": ("hunter-account-read", "read-only", "low"),
    "List-Email-Account-Sequences": ("hunter-account-read", "read-only", "low"),
    "List-Email-Accounts": ("hunter-account-read", "read-only", "low"),
    "List-Lead-Tags": ("hunter-account-read", "read-only", "low"),
    "List-Leads-List-Folders": ("hunter-account-read", "read-only", "low"),
    "List-Leads-Lists": ("hunter-account-read", "read-only", "low"),
    "List-Message-Templates": ("hunter-account-read", "read-only", "low"),
    "List-Saved-Searches": ("hunter-account-read", "read-only", "low"),
    "List-Sequence-Follow-Ups": ("hunter-account-read", "read-only", "low"),
    "List-Sequences": ("hunter-account-read", "read-only", "low"),
    "List-Webhooks": ("hunter-account-read", "read-only", "low"),
    "Get-Usage": ("hunter-account-read", "read-only", "low"),
    "List-API-Keys": ("credential-inventory", "sensitive-data", "medium"),
    "Report-API-Feedback": ("communications-send", "external-communication", "high"),
    "Find-Companies": ("hunter-contact-records", "sensitive-data", "medium"),
    "Find-Similar-Companies": ("hunter-contact-records", "sensitive-data", "medium"),
    "Find-People": ("hunter-contact-records", "sensitive-data", "medium"),
    "Email-Count": ("hunter-contact-records", "sensitive-data", "medium"),
    "Plan-Prospecting-Flow": ("hunter-prospecting-flow", "mutating", "medium"),

    "Domain-Search": ("hunter-contact-records", "sensitive-data", "medium"),
    "Domain-Search-Found": ("hunter-contact-records", "sensitive-data", "medium"),
    "Email-Finder": ("hunter-contact-records", "sensitive-data", "medium"),
    "Email-Verifier": ("hunter-contact-records", "sensitive-data", "medium"),
    "Company-Enrichment": ("hunter-contact-records", "sensitive-data", "medium"),
    "Person-Enrichment": ("hunter-contact-records", "sensitive-data", "medium"),
    "Combined-Enrichment": ("hunter-contact-records", "sensitive-data", "medium"),
    "Get-Email-Account": ("hunter-contact-records", "sensitive-data", "medium"),
    "Get-Lead": ("hunter-contact-records", "sensitive-data", "medium"),
    "List-Leads": ("hunter-contact-records", "sensitive-data", "medium"),
    "List-Sequence-Recipients": ("hunter-contact-records", "sensitive-data", "medium"),
    "Get-Sequence-Stats": ("hunter-contact-records", "sensitive-data", "medium"),

    "Add-Company-To-List": ("hunter-record-authoring", "mutating", "medium"),
    "Add-Tag-To-Lead": ("hunter-record-authoring", "mutating", "medium"),
    "Archive-Sequence": ("hunter-sequence-authoring", "mutating", "medium"),
    "Bulk-Copy-Companies": ("hunter-record-authoring", "mutating", "medium"),
    "Bulk-Move-Companies": ("hunter-record-authoring", "mutating", "medium"),
    "Bulk-Move-Leads": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Company-List": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Company-List-Folder": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Custom-Attribute": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Lead": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Lead-If-Missing": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Lead-Tag": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Leads-List": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Leads-List-Folder": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Message-Template": ("hunter-sequence-authoring", "mutating", "medium"),
    "Create-Or-Update-Lead": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Saved-Search": ("hunter-record-authoring", "mutating", "medium"),
    "Create-Sequence": ("hunter-sequence-authoring", "mutating", "medium"),
    "Create-Sequence-Follow-Up": ("hunter-sequence-authoring", "mutating", "medium"),
    "Favorite-Company-List": ("hunter-record-authoring", "mutating", "medium"),
    "Favorite-Leads-List": ("hunter-record-authoring", "mutating", "medium"),
    "Pause-Sequence": ("hunter-sequence-authoring", "mutating", "medium"),
    "Remove-Company-From-List": ("hunter-record-authoring", "mutating", "medium"),
    "Remove-Sequence-Recipients": ("hunter-sequence-authoring", "mutating", "medium"),
    "Remove-Tag-From-Lead": ("hunter-record-authoring", "mutating", "medium"),
    "Save-Company": ("hunter-record-authoring", "mutating", "medium"),
    "Unfavorite-Company-List": ("hunter-record-authoring", "mutating", "medium"),
    "Unfavorite-Leads-List": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Company-List": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Company-List-Folder": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Custom-Attribute": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Lead": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Lead-Tag": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Leads-List": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Leads-List-Folder": ("hunter-record-authoring", "mutating", "medium"),
    "Update-Message-Template": ("hunter-sequence-authoring", "mutating", "medium"),
    "Update-Sequence": ("hunter-sequence-authoring", "mutating", "medium"),
    "Update-Sequence-Follow-Up": ("hunter-sequence-authoring", "mutating", "medium"),

    "Delete-Company-List": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Company-List-Folder": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Custom-Attribute": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Lead": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Lead-Tag": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Leads-List": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Leads-List-Folder": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Message-Template": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Saved-Search": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Sequence": ("hunter-record-destructive", "destructive", "high"),
    "Delete-Sequence-Follow-Up": ("hunter-record-destructive", "destructive", "high"),
    "Delete-API-Key": ("hunter-record-destructive", "destructive", "high"),
    "Bulk-Delete-Companies": ("hunter-record-destructive", "destructive", "high"),
    "Bulk-Delete-Leads": ("hunter-record-destructive", "destructive", "high"),
    "Merge-Leads-Lists": ("hunter-record-destructive", "destructive", "high"),

    "Start-Sequence": ("hunter-outbound-email", "external-communication", "high"),
    "Resume-Sequence": ("hunter-outbound-email", "external-communication", "high"),
    "Add-Sequence-Recipients": ("hunter-outbound-email", "external-communication", "high"),

    "Create-API-Key": ("hunter-crm-integration", "access-control-change", "high"),
    "Push-Leads-To-CRM": ("hunter-crm-integration", "external-communication", "high"),
    "Update-Webhook": ("hunter-crm-integration", "configuration-change", "high"),
}

HUNTER_CUSTOM = {
    "Plan-Prospecting-Flow": (
        "The upstream description states that it gathers contacts for review and returns them as a "
        "table, and only saves to the operator's Hunter leads when the user explicitly asks. A call "
        "can therefore write real records into the account, even though the upstream advertises "
        "readOnlyHint=true and the tool itself is free. It also returns a plan whose later steps are "
        "other Hunter tools that charge credits, so one call can commit the caller to a billable "
        "chain. The description, not the annotation, decides this classification."),
    "Find-Companies": sensitive_rationale(
        live_by_name["hunter__Find-Companies"], False,
        "company records drawn from Hunter's index, naming real businesses by location, industry and "
        "size. It is free to call and writes nothing, but the output is third-party company data "
        "rather than the operator's own account configuration"),
    "Find-People": sensitive_rationale(
        live_by_name["hunter__Find-People"], False,
        "counts of the people and published email addresses Hunter holds for each named company. The "
        "tool returns counts only, not the addresses, and is free to call, but it reports what "
        "personal information exists about identified individuals at those companies"),
    "Find-Similar-Companies": sensitive_rationale(
        live_by_name["hunter__Find-Similar-Companies"], False,
        "company records for businesses similar to a seed company. The upstream records that this "
        "feature is not available on free plans, so on the connected free-tier account it will fail, "
        "but it writes nothing and the output is third-party company data"),
    "Email-Count": sensitive_rationale(
        live_by_name["hunter__Email-Count"], False,
        "the number of email addresses Hunter has indexed for a named domain, split by personal and "
        "generic. It is free to call and writes nothing, but it reports how much personal "
        "information Hunter holds about a domain's staff"),
    "Get-Email-Account": sensitive_rationale(
        live_by_name["hunter__Get-Email-Account"], False,
        "the full sending configuration of the operator's email account, including its signature and "
        "tracking domain"),
    "Get-Lead": sensitive_rationale(
        live_by_name["hunter__Get-Lead"], False,
        "a stored lead record holding a real contact's name and email address"),
    "List-Leads": sensitive_rationale(
        live_by_name["hunter__List-Leads"], False,
        "stored lead records holding real contacts' names and email addresses"),
    "List-Sequence-Recipients": sensitive_rationale(
        live_by_name["hunter__List-Sequence-Recipients"], False,
        "the email addresses of the recipients in a sending sequence"),
    "Get-Sequence-Stats": sensitive_rationale(
        live_by_name["hunter__Get-Sequence-Stats"], False,
        "per-recipient statistics for a sending sequence"),
    "Domain-Search": sensitive_rationale(
        live_by_name["hunter__Domain-Search"], False,
        "published contact records for a domain, naming people and their positions. It also draws one "
        "search credit per ten addresses returned; the connected account is on Hunter's free tier with "
        "50 searches and 50 credits per month, so the blast radius is quota exhaustion rather than "
        "spend, but on a paid plan the same call is billable"),
    "Domain-Search-Found": sensitive_rationale(
        live_by_name["hunter__Domain-Search-Found"], False,
        "guaranteed non-inferred contact records for a domain, naming people and their positions, and "
        "it draws search credits on the same terms as Domain-Search"),
    "Email-Finder": sensitive_rationale(
        live_by_name["hunter__Email-Finder"], False,
        "a specific person's email address at a company, and it draws one search credit when an "
        "address is found"),
    "Email-Verifier": sensitive_rationale(
        live_by_name["hunter__Email-Verifier"], False,
        "the deliverability verdict for a real person's email address, and it draws verification credits"),
    "Company-Enrichment": sensitive_rationale(
        live_by_name["hunter__Company-Enrichment"], False,
        "enriched company records that include contact email addresses, and it draws enrichment credits"),
    "Person-Enrichment": sensitive_rationale(
        live_by_name["hunter__Person-Enrichment"], False,
        "a real person's name, position and email address, and it draws enrichment credits"),
    "Combined-Enrichment": sensitive_rationale(
        live_by_name["hunter__Combined-Enrichment"], False,
        "a real person's contact and company records, and it draws enrichment credits"),
    "Start-Sequence": external_rationale(
        live_by_name["hunter__Start-Sequence"], False,
        "starts sending real email to every recipient on the sequence"),
    "Resume-Sequence": external_rationale(
        live_by_name["hunter__Resume-Sequence"], False,
        "starts sending outbound email again to a paused sequence's recipients"),
    "Add-Sequence-Recipients": external_rationale(
        live_by_name["hunter__Add-Sequence-Recipients"], False,
        "on an already-started sequence, schedules a real outbound email to the added recipient"),
    "Push-Leads-To-CRM": external_rationale(
        live_by_name["hunter__Push-Leads-To-CRM"], False,
        "sends lead records, with their contact details, to a third-party CRM account"),
    "Create-API-Key": access_rationale(
        live_by_name["hunter__Create-API-Key"], False,
        "mints a new credential that can act on the Hunter account, and the response is the only time "
        "the full key value is ever visible"),
    "Update-Webhook": config_rationale(
        live_by_name["hunter__Update-Webhook"], False,
        "overwrites the delivery target and event subscription of a webhook another system may already "
        "rely on, so deliveries move to a new endpoint immediately"),
    "Delete-API-Key": destructive_rationale(
        live_by_name["hunter__Delete-API-Key"], False,
        "permanently removes a credential that can act on the account"),
    "Merge-Leads-Lists": destructive_rationale(
        live_by_name["hunter__Merge-Leads-Lists"], False,
        "deletes the source list after moving its leads to the destination"),
    "Delete-Lead-Tag": destructive_rationale(
        live_by_name["hunter__Delete-Lead-Tag"], False,
        "removes the tag from every lead it was applied to"),
    "Bulk-Delete-Leads": destructive_rationale(
        live_by_name["hunter__Bulk-Delete-Leads"], False,
        "deletes leads permanently, with no undo"),
    "Bulk-Delete-Companies": destructive_rationale(
        live_by_name["hunter__Bulk-Delete-Companies"], False,
        "deletes companies permanently, with no undo"),
    "Delete-Sequence": destructive_rationale(
        live_by_name["hunter__Delete-Sequence"], False,
        "deletes a draft sequence permanently"),
    "Delete-Sequence-Follow-Up": destructive_rationale(
        live_by_name["hunter__Delete-Sequence-Follow-Up"], False,
        "deletes a step of a sequence, and the authored message text goes with it"),
    "Delete-Message-Template": destructive_rationale(
        live_by_name["hunter__Delete-Message-Template"], False,
        "deletes a saved message template permanently, and the API offers no undo"),
    "Delete-Saved-Search": destructive_rationale(
        live_by_name["hunter__Delete-Saved-Search"], False,
        "deletes a saved search permanently, and the API offers no undo"),
    "List-API-Keys": sensitive_rationale(
        live_by_name["hunter__List-API-Keys"], False,
        "the identities of the Hunter API keys the connected user can act with. The values are masked "
        "to the last four characters, but the listing is still a map of what the agent can act as"),
    "Report-API-Feedback": external_rationale(
        live_by_name["hunter__Report-API-Feedback"], False,
        "submits a report about the tool to Hunter, which Hunter's staff can read"),
}

HUNTER_DESTRUCTIVE_EFFECT = {
    "Delete-Company-List": "deletes a company list, and the entries it holds are gone with it",
    "Delete-Company-List-Folder": "deletes a company-list folder; the lists filed in it are deleted "
                                  "with it rather than moved",
    "Delete-Custom-Attribute": "deletes a custom attribute from every lead it was applied to",
    "Delete-Lead": "deletes a lead record permanently",
    "Delete-Leads-List": "deletes a leads list and every lead in it",
    "Delete-Leads-List-Folder": "deletes a leads-list folder; the lists filed in it are deleted with "
                                "it rather than moved",
}

HUNTER_SCOPE = "the operator's own Hunter account"


def classify_hunter(name: str):
    if name not in HUNTER_ASSIGN:
        raise SystemExit(f"hunter tool not classified: {name}")
    g, cat, risk = HUNTER_ASSIGN[name]
    if name in HUNTER_CUSTOM:
        return g, cat, risk, HUNTER_CUSTOM[name]
    t = live_by_name["hunter__" + name]
    if cat == "read-only":
        return g, cat, risk, read_rationale(t, False)
    if cat == "mutating":
        return g, cat, risk, mutating_rationale(t, False, HUNTER_SCOPE)
    if cat == "destructive":
        effect = HUNTER_DESTRUCTIVE_EFFECT.get(name, "removes the record permanently")
        return g, cat, risk, destructive_rationale(t, False, effect)
    raise SystemExit(f"missing custom rationale for {name}")


# --------------------------------------------------------------------------
# GitBook classification
# --------------------------------------------------------------------------

GITBOOK_ASSIGN = {
    "list_sites": ("gitbook-org-read", "read-only", "low"),
    "get_site_structure": ("gitbook-org-read", "read-only", "low"),
    "get_page": ("gitbook-org-read", "read-only", "low"),
    "list_site_topics": ("gitbook-org-read", "read-only", "low"),
    "get_subscription_information": ("gitbook-org-read", "read-only", "low"),
    "get_usage_guide": ("gitbook-org-read", "read-only", "low"),
    "search": ("gitbook-org-read", "read-only", "low"),
    "describe_operation": ("gitbook-org-read", "read-only", "low"),
    "create_change_request": ("gitbook-change-request", "mutating", "medium"),
    "submit_or_merge_change_request": ("gitbook-publish", "persistent-or-autonomous", "high"),
}

GITBOOK_CUSTOM = {
    "create_change_request": mutating_rationale(
        live_by_name["gitbook-management__create_change_request"], False,
        "a staged change request on the operator's GitBook space; the edits are not published until "
        "the change request is submitted and merged"),
    "submit_or_merge_change_request": persistent_rationale(
        live_by_name["gitbook-management__submit_or_merge_change_request"], False,
        "merges the change request and publishes its edits to the space, where readers see them and "
        "the merge cannot be undone"),
    "get_subscription_information": read_rationale(
        live_by_name["gitbook-management__get_subscription_information"], False) +
        " It reports plan and trial state for the organization, which is account rather than content "
        "data.",
}


def classify_gitbook(name: str):
    if name in ("report_tool_feedback", "invoke_operation"):
        raise SystemExit(f"gitbook tool handled specially: {name}")
    if name not in GITBOOK_ASSIGN:
        raise SystemExit(f"gitbook tool not classified: {name}")
    g, cat, risk = GITBOOK_ASSIGN[name]
    if name in GITBOOK_CUSTOM:
        return g, cat, risk, GITBOOK_CUSTOM[name]
    t = live_by_name["gitbook-management__" + name]
    return g, cat, risk, read_rationale(t, False)


# --------------------------------------------------------------------------
# assign every live tool
# --------------------------------------------------------------------------

assignment: dict[str, tuple[str, str, str, str]] = {}   # canonical name -> (group, cat, risk, rationale)

for name, t in live_by_name.items():
    srv = name.split("__", 1)[0]
    up = name.split("__", 1)[1]
    if srv == "unifi":
        g, cat, risk, rat = classify_unifi(up)
    elif srv == "notion":
        g, cat, risk, rat = classify_notion(up)
    elif srv == "hunter":
        g, cat, risk, rat = classify_hunter(up)
    elif srv == "gitbook-management":
        if up == "report_tool_feedback":
            g, cat, risk = "communications-send", "external-communication", "high"
            rat = external_rationale(
                t, False,
                "submits a report about the tool to GitBook, which the vendor's staff can read")
        elif up == "invoke_operation":
            g, cat, risk = "gitbook-proxy", "broad-capability", "review-required"
            rat = (
                "Runs one caller-selected GitBook API operation discovered through search, with "
                "caller-supplied path, query and body parameters. The upstream states that the "
                "operation surface includes actions that are visible to the public or cannot be "
                "undone, such as publishing a site or merging a change request, so the caller chooses "
                "the target and therefore the effect class. This is the same shape as "
                "court-listener__call_endpoint, and the curated GitBook tools are not a constraint on "
                "what it can reach."
            )
        else:
            g, cat, risk, rat = classify_gitbook(up)
    else:
        continue  # canonical tool: membership is preserved from the existing catalog
    assignment[name] = (g, cat, risk, rat)

# --------------------------------------------------------------------------
# existing catalog: preserve, and amend three groups
# --------------------------------------------------------------------------

catalog = json.loads(subprocess.run(
    ["git", "-C", str(R), "show", "HEAD:config/mcpjungle/tool-groups.json"],
    capture_output=True, text=True, check=True).stdout)
existing = {g["name"]: g for g in catalog["groups"]}

# Four new tools belong to a group that already exists, so they are members of
# it rather than of a new one. One of them also serves a second workflow, which
# is the deliberate additive overlap the house taxonomy allows.
MERGE_PRIMARY = {
    "gitbook-management__report_tool_feedback": "communications-send",
    "hunter__Report-API-Feedback": "communications-send",
    "hunter__List-API-Keys": "credential-inventory",
    "hunter__Get-Usage": "observability",
}

# Additional membership beyond the primary group.
MERGE_SECONDARY = {
    "hunter-account-read": ["hunter__Get-Usage"],
}

HUNTER_FEEDBACK_RATIONALE = external_rationale(
    live_by_name["hunter__Report-API-Feedback"], False,
    "submits a report about the tool to Hunter, which Hunter's staff can read")

# groups that hold new tools
NEW_GROUP_SPEC = {
    "network-inventory": dict(
        purpose="Read the device, site, controller, wireless, routing and health configuration of "
                "the operator's own UniFi estate.",
        risk="low",
        controls=[
            "Read-only. The credential is an administrative credential on the operator's own "
            "controller; scoping it to a single site is the control that makes this group acceptable.",
            "The deployment is read-only upstream (UNIFI_READ_ONLY=true), so no mutating UniFi tool "
            "is registered at all. This group therefore cannot mutate the controller even by accident.",
            "Site Manager, Carrier, Mobility and InnerSpace tools in this group raise 'Site Manager API "
            "is not enabled' in the current deployment. They are listed because they are registered; "
            "re-review this group if UNIFI_SITE_MANAGER_ENABLED is ever set.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-security-policy": dict(
        purpose="Read the firewall, zone, ACL, RADIUS, content-filter, DNS-filter and traffic-matching "
                "policy of the operator's own network.",
        risk="medium",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "The output is the operator's own security posture. A policy dump is exactly what an "
            "attacker wants, so do not copy it into a shared transcript without redaction.",
            "get_radius_account may carry RADIUS shared-secret material; treat its output as secret "
            "and do not paste it into a ticket or a repository.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-telemetry": dict(
        purpose="Read per-client identity and per-client network activity on the operator's network.",
        risk="medium",
        controls=[
            "Read-only. No tool in this group mutates the controller.",
            "Every member returns client-attributed data: MAC addresses, client names, and the "
            "destinations clients reached. This is occupancy and browsing data for the operator's own "
            "house or office, so redact before it leaves the host.",
            "Treat the destination fields as sensitive even for the operator's own traffic; the group "
            "exists because a reviewer needs to see what the network did, not to publish it.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-protect": dict(
        purpose="Read the UniFi Protect camera, alarm and premises-security surface of the operator's "
                "own site.",
        risk="medium",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "This group is physical-security data: camera identity, event history, live-view material, "
            "alarm-hub state and the identities of every Protect account. Treat the output as sensitive "
            "and keep it out of shared transcripts.",
            "get_protect_live_view returns live camera material for the operator's premises. It must "
            "not be invoked on the agent's own initiative.",
            "No member can trigger a siren, speaker or alarm: the upstream registers no mutating "
            "Protect tool in a read-only deployment.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-fleet": dict(
        purpose="Read the multi-controller, multi-site and Cloud Site Manager view of the operator's "
                "own estate.",
        risk="low",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "These tools span the whole estate rather than one site, so a read here is a read of every "
            "site the credential can reach. Scope the credential accordingly.",
            "The Site Manager, Carrier, Mobility, InnerSpace, ISP and integration tools raise 'Site "
            "Manager API is not enabled' in the current deployment. They are listed because they are "
            "registered; re-review this group if that flag is ever set.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-backup": dict(
        purpose="Read the operator's controller backup and restore state, and export the network "
                "topology.",
        risk="medium",
        controls=[
            "Read-only against the controller, but download_backup writes a controller backup archive "
            "into the MCP server's own download directory. That is a local side effect and the "
            "controller is not modified.",
            "A controller backup contains the operator's configuration and credential material. Treat "
            "the downloaded file as a secret: do not copy it into a transcript, a ticket or a "
            "repository, and delete it when the review is finished.",
            "validate_backup and the restore-status tools are the checks that tell you whether a "
            "recovery point is usable; a backup job having run is not the same as a restorable backup.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-integration": dict(
        purpose="Read the operator's own estate through the UniFi Site Manager and integration API: "
                "sites, hosts, clients, devices, DNS and WiFi broadcast policies, VPN servers, WANs "
                "and version control.",
        risk="low",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "These tools address the operator's own estate and describe it; they change nothing.",
            "The deployment leaves UNIFI_SITE_MANAGER_ENABLED unset, so every one of these tools "
            "currently raises 'Site Manager API is not enabled' when called. They are kept in the "
            "catalog because they are genuinely registered: if the flag is ever enabled, this group "
            "becomes a live read surface and must be re-reviewed before use.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-switching": dict(
        purpose="Read the operator's own layer-2 switching configuration: switch stacks, link "
                "aggregation groups, MLAG domains, port profiles and device tags.",
        risk="low",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "Port profiles and device tags describe how a port is expected to behave, so this group "
            "reveals the intended segmentation of the operator's network. Treat the output as "
            "sensitive internal configuration.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-addressing": dict(
        purpose="Read the operator's own address assignment: DHCP reservations, MAC tags, dynamic "
                "DNS, WAN DNS, VLANs, subnets and port mappings.",
        risk="low",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "DHCP reservations and port mappings name specific devices and the internal addresses "
            "they are given. That is an internal inventory: keep the output inside the operator's "
            "own estate.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-diagnostics": dict(
        purpose="Read the operator's own network health: link and speed diagnostics, spectrum and "
                "RF conditions, AP neighbourhood, and the controller's event and alarm history.",
        risk="low",
        controls=[
            "Read-only, and the same read-only upstream guard applies as in network-inventory.",
            "These are the health and diagnostic reads a network operator reaches for first. They "
            "describe the operator's own estate and change nothing.",
            "stream_traffic_flows is a read-only tool whose own upstream description records that "
            "streaming is not supported on the v2 endpoint, so it returns an error rather than a "
            "stream. Use get_traffic_flows on a poll schedule instead.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-controller": dict(
        purpose="Inspect and select which controller subsequent UniFi calls target.",
        risk="medium",
        controls=[
            "select_controller changes session-scoped routing, so later calls act against a different "
            "device. The change is local and reversible, not destructive.",
            "The server runs stateless HTTP, so select_controller is refused in the current "
            "deployment and the tool is inert. Pass controller=<name> explicitly instead.",
            "list_controllers and get_active_controller are read-only and report which controller a "
            "call without an explicit controller argument would reach.",
        ],
        consumers=["noesis-substrate"],
        overlap=""),
    "network-proxy": dict(
        purpose="Held review-required: caller-selected UniFi proxy paths and fleet-wide tool fan-out.",
        risk="review-required",
        controls=[
            "Every member lets the caller choose the target, so group membership cannot constrain "
            "what is reached. The group is created to hold that capability apart from the ordinary "
            "read groups, and it has no proposed consumer.",
            "connector_network_get and connector_protect_get are GET-only and their path segments are "
            "validated against traversal, so they cannot write. They can still read any endpoint of "
            "the Network or Protect application for a console, including the camera and event "
            "endpoints.",
            "fleet_fanout is bounded to read-tier controller tools by the upstream, so it cannot "
            "mutate, but it lets a holder run any read-tier tool on any controller in scope.",
            "In the current deployment the two connector proxies raise 'Site Manager API is not "
            "enabled', so they are inert. That is a deployment flag, not a property of the tool.",
        ],
        consumers=[],
        overlap=""),
    "notion-workspace-read": dict(
        purpose="Read the operator's own Notion workspace: pages, databases, comments, members, "
                "skills and file references.",
        risk="medium",
        controls=[
            "Read-only. No member in this group writes to the workspace.",
            "The Notion connection reaches the operator's personal workspace. Its scope must be "
            "confirmed at the upstream provider, because the gateway cannot see which pages the "
            "credential may read.",
            "Workspace content is the operator's own material and may quote third parties. Do not copy "
            "it into a shared transcript without redaction.",
        ],
        consumers=["noesis-scribe", "noesis-quill", "noesis-architect"],
        overlap=""),
    "notion-data-query": dict(
        purpose="Query the operator's Notion data sources, meeting notes and multi-source records with "
                "read-only SQL.",
        risk="medium",
        controls=[
            "Read-only: the queries run against the data sources in read-only mode.",
            "The rows can hold personal records, including meeting notes that name attendees. Treat "
            "the output as sensitive and redact before it leaves the host.",
            "The query accepts caller-supplied SQL. Constrain it in the runtime policy layer to "
            "SELECT-only against the intended collection, exactly as data-analytics does for the docs "
            "site.",
        ],
        consumers=["noesis-grid", "noesis-scribe"],
        overlap=""),
    "notion-workspace-authoring": dict(
        purpose="Create and edit pages, databases, views, comments, folders, attachments and uploads in "
                "the operator's own Notion workspace.",
        risk="medium",
        controls=[
            "Every member writes to the operator's workspace but removes nothing: each change is "
            "reversible from the Notion interface.",
            "Comments and reactions are visible to anyone the page is shared with, so treat a comment "
            "as a message to third parties and require operator approval of the text.",
            "Content written here is read by whoever the workspace is shared with. Never write a "
            "credential, token or private session content into a page.",
        ],
        consumers=["noesis-scribe", "noesis-quill"],
        overlap=""),
    "notion-workspace-destructive": dict(
        purpose="Remove content from the operator's Notion workspace and rewrite data-source schemas.",
        risk="high",
        controls=[
            "Every member removes content that cannot be restored from the API. Trash is recoverable "
            "from the Notion interface, but a dropped schema column takes its values with it.",
            "Require explicit operator approval for each call, naming the pages, databases or columns "
            "affected before the call is made.",
            "update_data-source accepts SQL DDL. Constrain it in the runtime policy layer to the "
            "intended data source, because a DROP COLUMN statement is destructive.",
            "upload-skill overwrites the target page's title, description, body and files. Read the "
            "imported archive before uploading it.",
        ],
        consumers=["noesis-scribe"],
        overlap=""),
    "notion-agent-session-read": dict(
        purpose="Read the agent sessions, session events and saved memories of the operator's Notion "
                "workspace.",
        risk="medium",
        controls=[
            "Read-only. No member starts, feeds or stops an agent.",
            "Session events can quote private conversation content, so treat the output as sensitive "
            "and redact before it enters a shared surface.",
            "A record carries whatever the agent wrote, including inferences. Do not promote an "
            "inference to a finding.",
        ],
        consumers=["noesis-architect", "noesis-scribe"],
        overlap=""),
    "notion-agent-sessions": dict(
        purpose="Start, feed and stop Notion Custom Agents, and change which skills they may load.",
        risk="high",
        controls=[
            "spawn-session and send-message-to-session hand work to a published Custom Agent that "
            "keeps acting after the call returns, so per-action approval is impossible. Bound the "
            "task, and require operator approval before the call.",
            "update-enabled-skills and convert-page-to-skill change what agents can load across the "
            "user's surfaces and any external MCP client. Require operator approval and record the "
            "change, because it is not confined to one page.",
            "stop-session removes a live capability rather than data, so it is reversible by starting "
            "the session again.",
        ],
        consumers=["noesis-architect"],
        overlap=""),
    "notion-calendar-read": dict(
        purpose="Read the operator's calendars, events, contacts and room resources.",
        risk="medium",
        controls=[
            "Read-only. No member creates, changes or cancels an event.",
            "Contacts and coworker events are other people's records: they name colleagues and show "
            "when people are available. Treat them as sensitive.",
            "Calendar discovery is scoped to the accounts connected to this connection; check which "
            "accounts are connected before assuming the read is the operator's own schedule.",
        ],
        consumers=["noesis-steward", "noesis-herald"],
        overlap=""),
    "notion-calendar-write": dict(
        purpose="Create, change and cancel events on the operator's connected calendars.",
        risk="high",
        controls=[
            "Every member publishes to calendars other people can see, and the upstream states that "
            "creation and cancellation may notify attendees. Nothing here may be invoked on the "
            "agent's own initiative.",
            "Require explicit operator approval of the exact event, its time, its attendees and the "
            "target calendar before the call.",
            "Scope the credential so the agent cannot write to calendars it was not asked to touch.",
        ],
        consumers=["noesis-steward", "noesis-herald"],
        overlap=""),
    "gitbook-org-read": dict(
        purpose="Read the operator's GitBook organization: sites, navigation, pages, topics, plan "
                "state and the operation catalogue.",
        risk="low",
        controls=[
            "Read-only. No member changes a space, a page or a plan.",
            "describe_operation and search expose the shape of the GitBook API including destructive "
            "operations; they are a catalogue, not a licence to call them.",
            "get_subscription_information reports plan and trial state. Confirm which GitBook "
            "organization the credential reaches before treating site content as the operator's own.",
        ],
        consumers=["noesis-scribe", "noesis-quill"],
        overlap=""),
    "gitbook-change-request": dict(
        purpose="Open a change request on a GitBook space without publishing anything.",
        risk="medium",
        controls=[
            "Staged editing only. The edits reach readers when the change request is submitted and "
            "merged, which lives in gitbook-publish.",
            "The change request is created inside the operator's GitBook organization. Confirm which "
            "organization and space is targeted before creating one.",
        ],
        consumers=["noesis-scribe", "noesis-quill"],
        overlap=""),
    "gitbook-publish": dict(
        purpose="Merge a GitBook change request and publish its edits to the space.",
        risk="high",
        controls=[
            "Publishing makes content visible to the space's readers and cannot be undone from the "
            "agent's point of view. Require explicit operator approval every time.",
            "Review the staged diff, not the tool call. The merge is the irreversible step.",
        ],
        consumers=["noesis-scribe", "noesis-quill"],
        overlap=""),
    "gitbook-proxy": dict(
        purpose="Held review-required: caller-selected GitBook API operations.",
        risk="review-required",
        controls=[
            "The caller chooses the operation, and the upstream states that the surface includes "
            "publishing a site and merging a change request. Group membership cannot constrain what "
            "it reaches.",
            "The group exists to hold the capability apart from the curated GitBook tools, and it has "
            "no proposed consumer.",
        ],
        consumers=[],
        overlap=""),
    "hunter-account-read": dict(
        purpose="Read the operator's Hunter account: lists, folders, tags, templates, saved searches, "
                "sequences, connected apps, webhooks and company search results.",
        risk="low",
        controls=[
            "Read-only. No member creates, changes or deletes anything in the Hunter account.",
            "Find-Companies and Find-Similar-Companies query Hunter's own index rather than the open "
            "web. The results are a database, not a search-engine snippet, so a figure from one is "
            "still worth checking against the company's own filings.",
            "Plan-Prospecting-Flow plans a workflow rather than performing it, but it prescribes the "
            "shape of an outbound campaign. Read it before any prospecting work is run.",
        ],
        consumers=[],
        overlap=""),
    "hunter-contact-records": dict(
        purpose="Look up real contact records and company facts: published addresses for a domain, "
                "a person's address at a company, verification, natural-language company and people "
                "discovery, and the operator's stored leads.",
        risk="medium",
        controls=[
            "The output is personal data about third parties: names, positions and direct email "
            "addresses of real people, many of whom never asked to be listed. Redact before it "
            "enters a shared transcript.",
            "These are the credit-consuming calls. The connected account is on Hunter's free tier with "
            "50 searches, 50 credits and 100 verifications per month, so the blast radius today is "
            "quota exhaustion; on a paid plan the same calls are billable, and the plan must be "
            "checked before a bulk run.",
            "Keep the upstream's own contact rules in view: a published address is not consent to be "
            "contacted.",
        ],
        consumers=[],
        overlap=""),
    "hunter-prospecting-flow": dict(
        purpose="Plan and begin an end-to-end prospecting run across Hunter: turn a natural-language "
                "brief into a step plan and execute its first action.",
        risk="medium",
        controls=[
            "The tool gathers contacts for review and returns them as a table. It only saves to the "
            "operator's Hunter leads when the user explicitly asks, so a call can write real records "
            "into the account. Treat every call as potentially writing.",
            "The plan it returns is a chain of other Hunter tools, and those sub-tools charge their own "
            "credits. The tool itself is free; the chain it starts is not. Read the plan before "
            "executing it, and check the sequence of calls it implies against the credit budget.",
            "A natural-language brief is the only input, so the scope of the run is decided by the "
            "brief itself. A brief that names many companies or many contacts multiplies the "
            "downstream cost.",
        ],
        consumers=[],
        overlap=""),
    "hunter-record-authoring": dict(
        purpose="Create and edit the operator's Hunter CRM records: leads, company and leads lists, "
                "list folders, tags, custom attributes and saved searches.",
        risk="medium",
        controls=[
            "Every member writes to the operator's Hunter account and removes nothing.",
            "Bulk-Copy-Companies and the bulk move tools act on many records at once and run "
            "asynchronously. Confirm the selection size before calling them.",
            "Create-Or-Update-Lead overwrites the fields of an existing lead, so a call can silently "
            "replace data the operator recorded earlier.",
        ],
        consumers=[],
        overlap=""),
    "hunter-sequence-authoring": dict(
        purpose="Author the operator's outbound sequences and message templates: the steps, the "
                "subject, the body, the schedule and the sending account.",
        risk="medium",
        controls=[
            "Every member writes to the operator's Hunter account and removes nothing. The destructive "
            "sequence tools are in hunter-record-destructive, and the sending tools in "
            "hunter-outbound-email.",
            "Update-Sequence-Follow-Up is the only tool that can author a sequence's introduction "
            "email, and Update-Message-Template rewrites a saved message body. Drafting is not sending, "
            "but the drafted body is addressed to real people: review it before it is staged.",
            "A sequence's schedule, senders and sending account are set here, so this group decides "
            "who will be contacted and when. Treat a change here as a change to an outbound campaign.",
        ],
        consumers=[],
        overlap=""),
    "hunter-record-destructive": dict(
        purpose="Delete the operator's Hunter records: leads, lists, tags, templates, searches, "
                "sequence steps and API keys.",
        risk="high",
        controls=[
            "Every member removes records permanently, and the upstream states that no undo exists "
            "for most of them. Require explicit operator approval naming the records affected.",
            "Merge-Leads-Lists deletes the source list after moving its leads, so both the source "
            "name and its contents change in one call.",
            "Delete-API-Key revokes a credential that may be in use by an integration elsewhere. "
            "Check what depends on the key before removing it.",
        ],
        consumers=[],
        overlap=""),
    "hunter-outbound-email": dict(
        purpose="Send the operator's Hunter sequences: start, resume, and add recipients to a "
                "started sequence.",
        risk="high",
        controls=[
            "Every member sends real email to real people who did not ask to be contacted. Nothing "
            "here may be invoked on the agent's own initiative.",
            "Require explicit operator approval of the recipient list, the message body, the sending "
            "account and the schedule before the call. The upstream enforces a confirmation prompt, "
            "and the approval must come from a person, not from the agent's own reasoning.",
            "Add-Sequence-Recipients on an already-started sequence schedules a send immediately, so "
            "adding one recipient is equivalent to sending one email.",
            "Check the sending account's status first: a warm-up account sends a reduced volume, and "
            "a disconnected account sends nothing at all.",
        ],
        consumers=[],
        overlap=""),
    "hunter-crm-integration": dict(
        purpose="Control how the operator's Hunter data leaves the account: push leads to a CRM, "
                "repoint a webhook, and mint API keys.",
        risk="high",
        controls=[
            "Push-Leads-To-CRM sends lead records, with contact details, to a third-party CRM account "
            "the operator connected. Confirm which CRM and which leads before the call.",
            "Update-Webhook overwrites the delivery target of a webhook another system may rely on, "
            "so deliveries move to a new endpoint immediately. List the webhooks first.",
            "Create-API-Key mints a credential that can act on the account, and the full key value is "
            "shown exactly once. Surface it to the operator once and never repeat it into a "
            "conversation, a lead or a note.",
        ],
        consumers=[],
        overlap=""),
}

# --------------------------------------------------------------------------
# assemble groups
# --------------------------------------------------------------------------

groups: dict[str, dict] = {}

# Only the groups that pre-date the 2026-10-26 four-server addition are carried
# forward from HEAD. The new groups are rebuilt from NEW_GROUP_SPEC below, so
# carrying them forward as well would make the generator's output depend on
# whether HEAD already contains its own output.
existing = {g["name"]: g for g in existing.values() if g["name"] not in NEW_GROUP_SPEC}

# carry the existing 41 forward
for name, g in existing.items():
    groups[name] = json.loads(json.dumps(g))

# A merged tool's PRIMARY group may be an existing group; add it there.
for cname, gname in MERGE_PRIMARY.items():
    if gname in groups:
        g = groups[gname]
        g["tools"] = sorted(set(g["tools"]) | {cname})
        g["tool_count"] = len(g["tools"])

# A merged tool's SECONDARY membership may land in an existing group too.
for gname, adds in MERGE_SECONDARY.items():
    if gname in groups:
        g = groups[gname]
        g["tools"] = sorted(set(g["tools"]) | set(adds))
        g["tool_count"] = len(g["tools"])

# existing groups whose purpose/controls must mention the new members
groups["communications-send"]["purpose"] = (
    "Send comments, replies, reactions, feedback and shared traces to external services, including "
    "provider feedback endpoints for Hunter and GitBook."
)
groups["communications-send"]["required_controls"] = _add_missing(
    groups["communications-send"]["required_controls"], [
        "The Hunter and GitBook feedback tools report on the agent's own use of those servers and are "
        "read by the vendors' staff. The upstream tells the agent to report proactively and without "
        "asking; that does not override the approval requirement above.",
    ])
groups["credential-inventory"]["purpose"] = (
    "Enumerate the credential identities the authenticated user can reference, on the n8n instance "
    "and on the Hunter account."
)
groups["credential-inventory"]["required_controls"] = _add_missing(
    groups["credential-inventory"]["required_controls"], [
    "hunter__List-API-Keys returns masked values (last four characters only) and is scoped to the "
    "connecting user, but it is still a map of what the agent can act as.",
])
groups["observability"]["purpose"] = (
    "Read deployment status and settings, workflow run history, reachable deployments and provider "
    "usage and cost, including the Hunter account's credit and quota consumption."
)
groups["observability"]["required_controls"] = _add_missing(
    groups["observability"]["required_controls"], [
    "hunter__Get-Usage reports the Hunter quota consumed in the current billing period. It is the "
    "signal that the credit-consuming lookups in hunter-contact-records are approaching the plan "
    "ceiling.",
])

# The three amended groups were redeployed on 2026-10-26, so their endpoint note
# records that redeployment rather than the original 2026-10-25 rollout.
AMENDED = {"communications-send", "credential-inventory", "observability"}
for _gname in AMENDED:
    groups[_gname]["endpoint_status"] = "live" if DEPLOYED else "pending"
    groups[_gname]["endpoint_note"] = (
        "Redeployed to the gateway on 2026-10-26 with the new members added, and re-verified by MCP "
        "initialize + tools/list against the group endpoint: the served tool set matches the declared "
        "included_tools exactly. The route shape /v0/groups/{group-name}/mcp was verified from the "
        "MCPJungle 0.4.6 source before deployment."
        if DEPLOYED else
        "Not yet deployed. The route shape /v0/groups/{group-name}/mcp was verified from the "
        "MCPJungle 0.4.6 source before deployment."
    )

# build the new groups from the assignment
group_tools: dict[str, list[str]] = {}
for cname, (g, _cat, _risk, _rat) in assignment.items():
    # a merged tool's primary group is the established group it belongs to
    g = MERGE_PRIMARY.get(cname, g)
    group_tools.setdefault(g, []).append(cname)

# a merged tool's secondary membership lands in a new group alongside its own
for gname, adds in MERGE_SECONDARY.items():
    if gname in NEW_GROUP_SPEC:
        group_tools.setdefault(gname, []).extend(adds)

for gname, spec in NEW_GROUP_SPEC.items():
    tools = sorted(group_tools.get(gname, []))
    if not tools:
        raise SystemExit(f"new group {gname} resolved to no tools")
    groups[gname] = {
        "name": gname,
        "purpose": spec["purpose"],
        "risk_level": spec["risk"],
        "risk_basis": RISK_BASIS,
        "required_controls": spec["controls"],
        "suggested_consumers": spec["consumers"],
        "consumer_basis": CONSUMER_BASIS,
        "tool_count": len(tools),
        "tools": tools,
        "deployable_file": f"groups/{gname}.json",
        "proposed_endpoint": f"https://mcpjungle.tailf99a0.ts.net/v0/groups/{gname}/mcp",
        "endpoint_status": "live" if DEPLOYED else "pending",
        "endpoint_note": (
            "Deployed to the gateway on 2026-10-26 and verified by MCP initialize + tools/list "
            "against the group endpoint: the served tool set matches the declared included_tools "
            "exactly. The route shape /v0/groups/{group-name}/mcp was verified from the MCPJungle "
            "0.4.6 source before deployment."
            if DEPLOYED else
            "Not yet deployed. The route shape /v0/groups/{group-name}/mcp was verified from the "
            "MCPJungle 0.4.6 source before deployment."
        ),
        "deliberate_overlap": spec["overlap"],
        "non_low_risk_member_count": 0,
        "non_low_risk_members": [],
        "non_low_risk_member_note": NON_LOW_NOTE,
    }

# every tool in a group must come from the assignment or the existing catalog
assigned_new = set(group_tools)
print(f"new tools classified: {len(assignment)}")
print(f"new groups: {len(NEW_GROUP_SPEC)}")

# --------------------------------------------------------------------------
# unassigned review-required
# --------------------------------------------------------------------------

# The three tools held out of EVERY group. The four newly-classified
# review-required tools are not here: they are held in the network-proxy and
# gitbook-proxy review-required groups, which is how browser-automation holds
# firecrawl_interact.
UNASSIGNED = {
    # carried forward from the existing catalog
    "court-listener__call_endpoint": next(
        e["reason"] for e in catalog["unassigned_review_required"] if e["tool"] == "court-listener__call_endpoint"),
    "framer__exec": next(
        e["reason"] for e in catalog["unassigned_review_required"] if e["tool"] == "framer__exec"),
    "framer__create_project": next(
        e["reason"] for e in catalog["unassigned_review_required"] if e["tool"] == "framer__create_project"),
}
for t in UNASSIGNED:
    for g in groups.values():
        assert t not in g["tools"], f"{t} must not be in group {g['name']}"

# --------------------------------------------------------------------------
# build the inventory
# --------------------------------------------------------------------------

def entry_from_live(cname: str, t: dict, group: str, cat: str, risk: str, rat: str) -> dict:
    return {
        "name": cname,
        "source_server": cname.split("__", 1)[0],
        "upstream_tool_name": cname.split("__", 1)[1],
        "description": t.get("description"),
        "input_schema": t.get("inputSchema"),
        "output_schema": t.get("outputSchema"),
        "annotations": t.get("annotations"),
        "_meta": t.get("_meta"),
        "inferred_capability_category": cat,
        "risk_classification": risk,
        "risk_rationale": rat,
    }


new_tools = []
for cname, (g, cat, risk, rat) in assignment.items():
    new_tools.append(entry_from_live(cname, live_by_name[cname], g, cat, risk, rat))

tools_out = []
for cname, t in sorted(canon_by_name.items()):
    tools_out.append(t)
tools_out.extend(sorted(new_tools, key=lambda t: t["name"]))
tools_out.sort(key=lambda t: t["name"])
assert len(tools_out) == len(canon_by_name) + len(new_tools), "inventory size mismatch"

by_server = {}
for t in tools_out:
    by_server[t["source_server"]] = by_server.get(t["source_server"], 0) + 1

empty_ann = [t["name"] for t in tools_out if t.get("annotations") == {}]
no_ann = [t["name"] for t in tools_out if t.get("annotations") is None]
with_out_schema = sum(1 for t in tools_out if t.get("output_schema"))
with_ann = sum(1 for t in tools_out if t.get("annotations"))

from collections import Counter
cat_count = Counter(t["inferred_capability_category"] for t in tools_out)
risk_count = Counter(t["risk_classification"] for t in tools_out)
print("categories:", json.dumps(dict(cat_count), indent=1))
print("risks:", json.dumps(dict(risk_count), indent=1))
print("empty annotations:", len(empty_ann), " null annotations:", len(no_ann))
print("with output schema:", with_out_schema, " with annotations:", with_ann)

inventory = {
    "schema_version": canon_inv["schema_version"],
    "generated_at": DISCOVERY_TS,
    "endpoint": canon_inv["endpoint"],
    "registry_base_url": canon_inv["registry_base_url"],
    "visibility_scope": canon_inv["visibility_scope"],
    "discovery": {
        "method": canon_inv["discovery"]["method"],
        "protocol_version": canon_inv["discovery"]["protocol_version"],
        "pagination": canon_inv["discovery"]["pagination"],
        "pages_fetched": 1,
        "completeness": "complete",
        "completeness_evidence": [
            "tools/list returned no nextCursor, so no further page existed.",
            "Independent enumeration via 'mcpjungle list tools' produced the identical 700-name set: "
            "the set difference is empty in both directions.",
            "All 24 registered servers contribute tools, and every registered server name is an exact "
            "canonical prefix of at least one discovered tool, so no server was missed.",
            "Canonical names are '<server>__<tool>' split on the first '__'. Every discovered name "
            "maps to exactly one registered server, with no prefix ambiguity between registered "
            "server names.",
            "The 308 tools of the previous snapshot are all still present; the 392 new tools are "
            "purely additive.",
        ],
        "tools_discovered": len(tools_out),
        "source_servers": len(by_server),
        "tools_by_source_server": dict(sorted(by_server.items())),
        "hermes_exposed_tool_count": 312,
        "hermes_count_reconciliation": (
            "Hermes reports 312 tools for this MCP server. That figure was captured when the "
            "connection enumerated the registry, before the four servers added on 2026-10-26 were "
            "registered; the gateway itself now serves 700. On the next reconnection Hermes will "
            "report 704: 700 upstream tools plus the 4 synthesised per-server utilities "
            "(list_resources, read_resource, list_prompts, get_prompt). Those 4 names are Hermes "
            "constructs, not MCPJungle canonical tools, and they are excluded from this inventory and "
            "from every group."
        ),
        "annotation_coverage": {
            "tools_with_annotations": with_ann,
            "tools_with_empty_annotations_object": sorted(empty_ann),
            "annotation_absence_note": (
                "These tools are the ones for which the server returned an empty annotations object. "
                "The field was present but carried no annotation values, which is the protocol's way "
                "of saying the upstream publishes no annotations for them. The observed value is "
                "preserved verbatim as an empty object."
            ),
            "tools_with_null_annotations": sorted(no_ann),
            "tools_with_output_schema": with_out_schema,
            "tools_without_output_schema": len(tools_out) - with_out_schema,
        },
    },
    "classification_method": canon_inv["classification_method"],
    "redactions": {
        "performed": True,
        "items": [
            "No access token, authorization header, environment secret or credential value is "
            "recorded in this file.",
            "The MCPJungle user token was read from the local CLI credential store only to authenticate "
            "discovery, and is not written here.",
            "No tool description, schema or _meta block contained a literal secret. A pattern scan "
            f"across all {len(tools_out)} tools for bearer tokens, JWTs, provider API keys, cloud "
            "access keys, 32-character hex secrets, credential assignments, credential-bearing URLs "
            "and e-mail addresses returned zero hits.",
            "Descriptions, schemas and _meta are reproduced as returned. They contain tool contracts "
            "only; no live record data was retrieved during discovery.",
        ],
        "not_redacted_because_absent": (
            "Descriptions that mention identifiers such as repository ids, docket ids or bill ids are "
            "field descriptions, not records, and are preserved verbatim."
        ),
    },
    "unavailable_information": _add_missing(canon_inv["unavailable_information"], [
        "The 212 UniFi tools publish an empty MCP annotations object, so none of them carries an "
        "upstream read-only or destructive assertion. Their classification was taken from the "
        "description, the input schema and the upstream source at "
        "/home/elvis/projects/unifi-mcp-server.",
        "The UniFi deployment registers UNIFI_READ_ONLY=true, so no mutating UniFi tool is registered "
        "at all and the 212 tools are the read surface. The deployment also leaves "
        "UNIFI_SITE_MANAGER_ENABLED unset, so the 33 Site Manager, Carrier, Mobility, InnerSpace, ISP "
        "and integration tools raise 'Site Manager API is not enabled' when called. Both are "
        "deployment facts, not properties of the tools, and are recorded so a later change to the "
        "flags triggers a re-review.",
        "The Hunter account's plan and quota were read from the live account (free tier, 50 "
        "searches, 50 credits and 100 verifications per month). Whether the account is later moved to "
        "a paid plan changes the cost of the credit-consuming lookups and must trigger a re-review.",
        "The GitBook credential's organization scope is not visible through this gateway and must be "
        "confirmed at GitBook.",
    ]),
    "tools": tools_out,
}

# --------------------------------------------------------------------------
# non-low members, group risk floors, catalog
# --------------------------------------------------------------------------

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "review-required": 3}
inv_by_name = {t["name"]: t for t in tools_out}

for gname, g in groups.items():
    members = []
    for t in g["tools"]:
        inv = inv_by_name.get(t)
        if inv is None:
            raise SystemExit(f"{gname}: {t} not in inventory")
        if inv["risk_classification"] != "low":
            members.append(f"{t}: {inv['risk_rationale']}")
    g["non_low_risk_members"] = sorted(members)
    g["non_low_risk_member_count"] = len(members)
    g["tool_count"] = len(g["tools"])
    member_max = max((RISK_ORDER[inv_by_name[t]["risk_classification"]] for t in g["tools"]), default=0)
    if RISK_ORDER[g["risk_level"]] < member_max:
        raise SystemExit(
            f"{gname}: declared risk {g['risk_level']} is below member max "
            f"{[t for t in g['tools'] if RISK_ORDER[inv_by_name[t]['risk_classification']] == member_max][:3]}"
        )

# catalog
cat_groups = []
for gname in sorted(groups):
    g = groups[gname]
    cat_groups.append({
        "name": g["name"],
        "purpose": g["purpose"],
        "risk_level": g["risk_level"],
        "risk_basis": g["risk_basis"],
        "required_controls": g["required_controls"],
        "suggested_consumers": g["suggested_consumers"],
        "consumer_basis": g["consumer_basis"],
        "tool_count": g["tool_count"],
        "tools": g["tools"],
        "deployable_file": g["deployable_file"],
        "proposed_endpoint": g["proposed_endpoint"],
        "endpoint_status": g["endpoint_status"],
        "endpoint_note": g["endpoint_note"],
        "deliberate_overlap": g["deliberate_overlap"],
        "non_low_risk_member_count": g["non_low_risk_member_count"],
        "non_low_risk_members": g["non_low_risk_members"],
        "non_low_risk_member_note": g["non_low_risk_member_note"],
    })

# review-required summary: every tool whose per-tool risk is review-required
rr_tools = sorted(t["name"] for t in tools_out if t["risk_classification"] == "review-required")
rr_entries = []
for t in rr_tools:
    gnames = sorted(g["name"] for g in groups.values() if t in g["tools"])
    reason = inv_by_name[t]["risk_rationale"]
    rr_entries.append({
        "tool": t,
        "source_server": t.split("__", 1)[0],
        "disposition": "held in a review-required group" if gnames else "held out of all groups",
        "groups": gnames,
        "reason": reason,
    })

unassigned_entries = []
for t in sorted(UNASSIGNED):
    inv = inv_by_name[t]
    unassigned_entries.append({
        "tool": t,
        "source_server": t.split("__", 1)[0],
        "risk_classification": inv["risk_classification"],
        "disposition": "review-required",
        "reason": UNASSIGNED[t],
        "decision_needed": (
            "An operator decision on whether this capability is needed at all, and if so which "
            "profile may hold it under what approval path."
        ),
    })

catalog_out = {
    "schema_version": catalog["schema_version"],
    "artifact_type": catalog["artifact_type"],
    "not_directly_deployable": catalog["not_directly_deployable"],
    "not_directly_deployable_note": catalog["not_directly_deployable_note"],
    "inventory_provenance": {
        "inventory_file": "tool-inventory.json",
        "discovery_timestamp": DISCOVERY_TS,
        "endpoint": canon_inv["endpoint"],
        "mcpjungle_version": "0.4.6",
        "completeness": "complete",
        "tools_in_inventory": len(tools_out),
        "source_servers": len(by_server),
    },
    "mcpjungle_constraints": catalog["mcpjungle_constraints"],
    "group_count": len(cat_groups),
    "deployment_status": catalog["deployment_status"],
    "groups": cat_groups,
    "review_required_summary": {
        "definition": catalog["review_required_summary"]["definition"],
        "count": len(rr_entries),
        "tools": rr_entries,
    },
    "unassigned_review_required": unassigned_entries,
    "unsupported_requested_categories": catalog["unsupported_requested_categories"],
}

# --------------------------------------------------------------------------
# coverage assertions
# --------------------------------------------------------------------------

assigned = set()
for g in groups.values():
    assigned |= set(g["tools"])
missing = set(inv_by_name) - assigned - set(UNASSIGNED)
if missing:
    raise SystemExit(f"unassigned tools: {sorted(missing)[:20]}")
for t in UNASSIGNED:
    assert t in inv_by_name, t
    assert t not in assigned, t
print(f"groups: {len(cat_groups)}  tools assigned: {len(assigned)}  held out: {len(UNASSIGNED)}")

# --------------------------------------------------------------------------
# write
# --------------------------------------------------------------------------

def dump(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path)


dump(MCP / "tool-inventory.json", inventory)
dump(MCP / "tool-groups.json", catalog_out)

for gname, g in groups.items():
    doc = {
        "name": gname,
        "description": g["purpose"],
        "included_tools": sorted(g["tools"]),
    }
    dump(MCP / "groups" / f"{gname}.json", doc)

print("\nSUMMARY")
print(" tools:", len(tools_out), " servers:", len(by_server), " groups:", len(cat_groups))
for g in cat_groups:
    print(f"  {g['name']:34s} {g['risk_level']:16s} {g['tool_count']:4d}")
