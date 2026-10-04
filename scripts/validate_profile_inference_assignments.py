#!/usr/bin/env python3
"""Offline validator for the strategic profile inference assignment matrix.

Companion to scripts/validate_inference_routing.py. Validates
platform/profile-inference-assignments.yaml against the roster, the platform
agent registry, the model catalog, provider policy, the inference-routing
policy, and the runtime reconciliation matrix.

Repository-local and deterministic: never reads ~/.hermes, never makes network
calls, never prints matched secret values.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"FATAL: PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]

ASSIGNMENTS = "platform/profile-inference-assignments.yaml"
REQUIRED_INPUTS = [
    ASSIGNMENTS,
    "profiles/noesis-roster.yaml",
    "platform/orchestrator.yaml",
    "platform/inference-routing.yaml",
    "platform/runtime-reconciliation.yaml",
    "shared/models.yaml",
    "shared/model-aliases.yaml",
    "shared/provider-policies.yaml",
]
SECRET_SCAN_TARGETS = [
    ASSIGNMENTS,
    "evals/profile-inference-assignment.eval.yaml",
    "docs/profile-inference-assignment-rationale.md",
    "scripts/validate_profile_inference_assignments.py",
]

STATUSES_NON_SELECTABLE = {"proposed", "disabled", "blocked_missing_configuration"}
ALLOWED_ASSIGNMENT_STATUS = {"observe_only", "blocked_missing_configuration", "proposed"}
ALLOWED_ROLLOUT_STAGE = {"not_routable", "observe_only", "shadow_candidate", "blocked"}
RISK_ORDER = {"r0": 0, "r1": 1, "r2": 2, "r3": 3}
EXTERNAL_RESEARCH_CLASSES = {
    "research", "intelligence", "source_discovery", "source_verification",
    "citation_backed_brief", "documentation_triage",
}
REFLECTIVE_FORBIDDEN_TOOLS = {
    "terminal", "code_execution", "artifact_publish_external",
    "treasury_read", "treasury_propose_action", "broker_submit_job", "wallet",
}
NEVER_DATA_CLASSES = {"confidential", "restricted", "secret"}

REQUIRED_EVAL_FIXTURES = {
    "profile_count_matches_roster_plus_platform_registry",
    "every_profile_has_required_strategic_fields",
    "selected_primary_model_ref_must_exist_in_shared_catalog",
    "proposed_or_disabled_lane_cannot_be_active_primary",
    "r2_r3_critic_family_must_differ_from_primary",
    "coder_qa_implementation_review_family_separation",
    "research_profiles_require_provenance_for_external_research",
    "reflective_profiles_cannot_get_write_or_external_execution",
    "privileged_profiles_no_automatic_fallback_and_require_human_approval",
    "no_openrouter_use_anywhere",
    "fallback_entries_preserve_data_risk_tool_approval_constraints",
    "no_literal_secrets_in_assignment_artifacts",
    "unresolved_gaps_block_activation_rather_than_being_guessed",
    "no_confidential_restricted_secret_data_on_any_route",
    "lane_type_permission_and_risk_ceiling_enforced",
}


@dataclass
class Finding:
    rule: str
    path: str
    field: str
    hint: str

    def render(self) -> str:
        return f"{self.rule} | {self.path} | {self.field} | {self.hint}"


class Validator:
    def __init__(self, strict: bool = False, scan_secrets: bool = True):
        self.strict = strict
        self.scan_secrets = scan_secrets
        self.findings: list[Finding] = []
        self.docs: dict[str, Any] = {}

    def add(self, rule: str, path: str, field: str, hint: str) -> None:
        self.findings.append(Finding(rule, path, field, hint))

    def load_yaml(self, rel: str) -> Any:
        path = ROOT / rel
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.add("PIA000", rel, "$", "Required file is missing.")
            return {}
        except yaml.YAMLError as exc:
            self.add("PIA000", rel, "$", f"YAML parse failed: {exc}")
            return {}

    def load_all(self) -> None:
        for rel in REQUIRED_INPUTS:
            self.docs[rel] = self.load_yaml(rel)
        eval_rel = "evals/profile-inference-assignment.eval.yaml"
        if (ROOT / eval_rel).exists():
            self.docs[eval_rel] = self.load_yaml(eval_rel)

    @property
    def matrix(self) -> dict[str, Any]:
        return self.docs.get(ASSIGNMENTS) or {}

    @property
    def lanes(self) -> dict[str, Any]:
        return (self.docs.get("platform/inference-routing.yaml") or {}).get("approved_lanes") or {}

    def known_model_refs(self) -> set[str]:
        models = self.docs.get("shared/models.yaml") or {}
        refs: set[str] = set()
        for section in ["profiles", "charter_profiles"]:
            for key, val in (models.get(section) or {}).items():
                refs.add(str(key))
                if isinstance(val, dict) and val.get("model"):
                    refs.add(str(val["model"]))
        for lane in self.lanes.values():
            for pinned in lane.get("pinned_models") or []:
                refs.add(str(pinned))
        return refs

    def validate(self) -> bool:
        self.load_all()
        self.check_inventory()
        self.check_strategic_fields()
        self.check_primary_selection()
        self.check_independence()
        self.check_boundaries()
        self.check_fallback()
        self.check_eval_fixtures()
        if self.scan_secrets:
            self.check_secret_safety()
        return not self.findings

    # ── PIA001 ────────────────────────────────────────────────────────────
    def check_inventory(self) -> None:
        roster = self.docs.get("profiles/noesis-roster.yaml") or {}
        orch = self.docs.get("platform/orchestrator.yaml") or {}
        expected = set((roster.get("profiles") or {}).keys()) | set((orch.get("agents") or {}).keys())
        records = self.matrix.get("profiles") or []
        actual = {p.get("profile_id") for p in records}
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        if missing:
            self.add("PIA001", ASSIGNMENTS, "profiles", f"Missing profiles: {', '.join(missing)}")
        if unknown:
            self.add("PIA001", ASSIGNMENTS, "profiles", f"Unknown profiles: {', '.join(unknown)}")
        reconciliation = self.docs.get("platform/runtime-reconciliation.yaml") or {}
        recon_ids = {p.get("profile_id") for p in (reconciliation.get("profiles") or [])}
        absent = sorted(actual - recon_ids)
        if absent:
            self.add("PIA001", ASSIGNMENTS, "profiles", f"Absent from runtime reconciliation: {', '.join(absent)}")

    # ── PIA002 ────────────────────────────────────────────────────────────
    def check_strategic_fields(self) -> None:
        required = [
            "profile_id", "profile_type", "purpose", "authority_level", "risk_ceiling",
            "allowed_data_classes", "prohibited_data_classes", "allowed_task_classes",
            "tool_policy", "inference_strategy", "validation", "rollout", "evidence",
        ]
        for idx, prof in enumerate(self.matrix.get("profiles") or []):
            pid = prof.get("profile_id") or f"[{idx}]"
            for field in required:
                if prof.get(field) in (None, "", []):
                    self.add("PIA002", ASSIGNMENTS, f"profiles[{idx}].{field}", f"{pid}: missing strategic field.")
            strategy = prof.get("inference_strategy") or {}
            for field in ["status", "primary", "critic", "fallback", "prohibited_lanes"]:
                if strategy.get(field) in (None, ""):
                    self.add("PIA002", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.{field}", f"{pid}: missing strategy field.")
            primary = strategy.get("primary") or {}
            for field in ["lane", "model_ref", "parameters", "selection_rationale"]:
                if field not in primary:
                    self.add("PIA002", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.{field}", f"{pid}: missing primary field.")
            status = strategy.get("status")
            if status not in ALLOWED_ASSIGNMENT_STATUS:
                self.add("PIA002", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.status", f"{pid}: status {status!r} not in {sorted(ALLOWED_ASSIGNMENT_STATUS)}.")
            stage = (prof.get("rollout") or {}).get("stage")
            if stage not in ALLOWED_ROLLOUT_STAGE:
                self.add("PIA002", ASSIGNMENTS, f"profiles[{idx}].rollout.stage", f"{pid}: stage {stage!r} invalid.")

    # ── PIA003 / PIA004 / PIA014 / PIA015 ─────────────────────────────────
    def check_primary_selection(self) -> None:
        refs = self.known_model_refs()
        for idx, prof in enumerate(self.matrix.get("profiles") or []):
            pid = prof.get("profile_id") or f"[{idx}]"
            strategy = prof.get("inference_strategy") or {}
            primary = strategy.get("primary") or {}
            lane_name = primary.get("lane")
            model_ref = primary.get("model_ref")

            if model_ref is not None and str(model_ref) not in refs:
                self.add("PIA003", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.model_ref", f"{pid}: {model_ref!r} is not a canonical catalog entry or lane pin.")

            allowed_dc = set(prof.get("allowed_data_classes") or [])
            if allowed_dc & NEVER_DATA_CLASSES:
                self.add("PIA014", ASSIGNMENTS, f"profiles[{idx}].allowed_data_classes", f"{pid}: confidential/restricted/secret data not allowed on any current route.")
            if not {"restricted", "secret"}.issubset(set(prof.get("prohibited_data_classes") or [])):
                self.add("PIA014", ASSIGNMENTS, f"profiles[{idx}].prohibited_data_classes", f"{pid}: restricted and secret must be explicitly prohibited.")

            if lane_name is None:
                if strategy.get("status") == "observe_only":
                    self.add("PIA013", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.lane", f"{pid}: null lane cannot be observe_only; use proposed/blocked_missing_configuration.")
                continue

            lane = self.lanes.get(lane_name)
            if lane is None:
                self.add("PIA004", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.lane", f"{pid}: lane {lane_name!r} absent from approved_lanes.")
                continue
            if lane.get("status") != "approved":
                self.add("PIA004", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.lane", f"{pid}: lane {lane_name} is {lane.get('status')} and cannot be primary.")
            if prof.get("profile_type") not in (lane.get("permitted_profile_types") or []):
                self.add("PIA015", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.primary.lane", f"{pid}: type {prof.get('profile_type')} not permitted on {lane_name}.")
            task_classes = set(prof.get("allowed_task_classes") or [])
            if not task_classes.issubset(set(lane.get("permitted_task_classes") or [])):
                self.add("PIA015", ASSIGNMENTS, f"profiles[{idx}].allowed_task_classes", f"{pid}: task classes exceed {lane_name} permitted set.")
            if RISK_ORDER.get(prof.get("risk_ceiling"), 99) > RISK_ORDER.get(lane.get("max_risk_tier"), -1):
                self.add("PIA015", ASSIGNMENTS, f"profiles[{idx}].risk_ceiling", f"{pid}: ceiling {prof.get('risk_ceiling')} exceeds {lane_name} max {lane.get('max_risk_tier')}.")
            if not allowed_dc.issubset(set(lane.get("permitted_data_classes") or [])):
                self.add("PIA015", ASSIGNMENTS, f"profiles[{idx}].allowed_data_classes", f"{pid}: data classes exceed {lane_name} permitted set.")
            if not set(lane.get("prohibited_data_classes") or []).issubset(set(prof.get("prohibited_data_classes") or [])):
                self.add("PIA015", ASSIGNMENTS, f"profiles[{idx}].prohibited_data_classes", f"{pid}: must preserve {lane_name} prohibited data classes.")

    # ── PIA005 / PIA006 / PIA007 / PIA008 / PIA013 ────────────────────────
    def check_independence(self) -> None:
        def family(lane_name: str | None) -> str | None:
            if not lane_name:
                return None
            return (self.lanes.get(lane_name) or {}).get("provider_family")

        records = self.matrix.get("profiles") or []
        impl_families = {
            family((p.get("inference_strategy") or {}).get("primary", {}).get("lane"))
            for p in records
            if p.get("profile_type") == "coder"
        }
        for idx, prof in enumerate(records):
            pid = prof.get("profile_id") or f"[{idx}]"
            strategy = prof.get("inference_strategy") or {}
            primary = strategy.get("primary") or {}
            critic = strategy.get("critic") or {}
            gaps = prof.get("evidence", {}).get("unresolved_gaps") or []
            activation = (prof.get("rollout") or {}).get("activation_requirements") or []

            if prof.get("risk_ceiling") in {"r2", "r3"} and critic.get("required"):
                if critic.get("lane") and family(critic.get("lane")) == family(primary.get("lane")):
                    self.add("PIA005", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.critic.lane", f"{pid}: sole critic shares primary provider family.")
                if not critic.get("lane") and not gaps and not activation:
                    self.add("PIA013", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.critic", f"{pid}: required cross-family critic is null but no gap is recorded.")

            if prof.get("profile_type") == "qa":
                qa_family = family(primary.get("lane"))
                if qa_family in impl_families:
                    gates = set((prof.get("validation") or {}).get("required_gates") or [])
                    if "independent_provider_review" not in gates:
                        self.add("PIA006", ASSIGNMENTS, f"profiles[{idx}].validation.required_gates", f"{pid}: shares family with implementation; independent_provider_review gate required.")

            if prof.get("profile_type") == "research" and set(prof.get("allowed_task_classes") or []) & EXTERNAL_RESEARCH_CLASSES:
                gates = set((prof.get("validation") or {}).get("required_gates") or [])
                if "provenance_artifact_required" not in gates:
                    self.add("PIA007", ASSIGNMENTS, f"profiles[{idx}].validation.required_gates", f"{pid}: external research classes require provenance_artifact_required gate.")

            if prof.get("profile_type") == "reflective":
                allowed_tools = set((prof.get("tool_policy") or {}).get("allowed") or [])
                if allowed_tools & REFLECTIVE_FORBIDDEN_TOOLS:
                    self.add("PIA008", ASSIGNMENTS, f"profiles[{idx}].tool_policy.allowed", f"{pid}: reflective profile granted write/external execution capability.")

    # ── PIA009 / PIA010 / PIA011 ──────────────────────────────────────────
    def check_boundaries(self) -> None:
        for idx, prof in enumerate(self.matrix.get("profiles") or []):
            pid = prof.get("profile_id") or f"[{idx}]"
            strategy = prof.get("inference_strategy") or {}
            fallback = strategy.get("fallback") or {}
            privileged = prof.get("authority_level") == "approval_gated" or prof.get("risk_ceiling") == "r3"
            if privileged:
                if fallback.get("enabled") is not False:
                    self.add("PIA009", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.fallback.enabled", f"{pid}: privileged profile must not have automatic fallback.")
                gates = " ".join((prof.get("validation") or {}).get("required_gates") or [])
                if "human_approval" not in gates:
                    self.add("PIA009", ASSIGNMENTS, f"profiles[{idx}].validation.required_gates", f"{pid}: privileged profile requires a human-approval gate.")
            lanes = [strategy.get("primary", {}).get("lane")] + list(fallback.get("ordered_candidates") or [])
            if "OPENROUTER_FALLBACK" in lanes:
                self.add("PIA010", ASSIGNMENTS, f"profiles[{idx}].inference_strategy", f"{pid}: OpenRouter must never be selected.")

    def check_fallback(self) -> None:
        for idx, prof in enumerate(self.matrix.get("profiles") or []):
            pid = prof.get("profile_id") or f"[{idx}]"
            fallback = (prof.get("inference_strategy") or {}).get("fallback") or {}
            candidates = list(fallback.get("ordered_candidates") or [])
            constraints = fallback.get("constraints") or {}
            if fallback.get("enabled") is False and candidates:
                self.add("PIA011", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.fallback.ordered_candidates", f"{pid}: disabled fallback must not list candidates.")
            if fallback.get("enabled") is True and not candidates:
                self.add("PIA011", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.fallback", f"{pid}: enabled fallback requires bounded candidate list.")
            for cand in candidates:
                lane = self.lanes.get(cand)
                if lane is None or lane.get("status") != "approved":
                    self.add("PIA011", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.fallback.ordered_candidates", f"{pid}: candidate {cand!r} is not an approved lane.")
            for key in ["preserve_data_class", "preserve_risk_tier", "preserve_tool_scope", "preserve_approval_gates"]:
                if constraints.get(key) is not True:
                    self.add("PIA011", ASSIGNMENTS, f"profiles[{idx}].inference_strategy.fallback.constraints.{key}", f"{pid}: fallback must preserve {key}.")

    # ── eval fixtures ─────────────────────────────────────────────────────
    def check_eval_fixtures(self) -> None:
        rel = "evals/profile-inference-assignment.eval.yaml"
        evals = self.docs.get(rel) or {}
        names = {t.get("name") for t in evals.get("tests") or []}
        missing = sorted(REQUIRED_EVAL_FIXTURES - names)
        if missing:
            self.add("PIA002", rel, "tests", f"Missing eval fixtures: {', '.join(missing)}")
        for idx, test in enumerate(evals.get("tests") or []):
            for field in ["setup", "expected_result", "expected_error_class_or_assertion", "linked_validator_rule", "risk_level"]:
                if not test.get(field):
                    self.add("PIA002", rel, f"tests[{idx}].{field}", "Eval fixture must map scenario to validator assertion.")

    # ── PIA012 ────────────────────────────────────────────────────────────
    def check_secret_safety(self) -> None:
        for rel in SECRET_SCAN_TARGETS:
            if (ROOT / rel).exists():
                self.detect_secret_like_in_file(rel)

    def detect_secret_like_in_file(self, rel: str) -> None:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        patterns = [
            ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
            ("seed_phrase_marker", re.compile(r"(?i)\b(seed phrase|mnemonic)\b")),
            ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}")),
            ("embedded_basic_auth_url", re.compile(r"https?://[^\s/@:]+:[^\s/@]+@")),
            ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
            ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
            ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
            ("generic_assignment_secret", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}")),
            ("cookie_value", re.compile(r"(?i)\b(cookie|sessionid|session_token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}")),
        ]
        for label, pat in patterns:
            for line in text.splitlines():
                if rel.endswith("validate_profile_inference_assignments.py") and "re.compile" in line:
                    continue
                if pat.search(line):
                    self.add("PIA012", rel, label, "Secret-like material detected; remove/redact. Matched value intentionally not printed.")
                    break

    def print_summary(self) -> None:
        if self.findings:
            print("Profile inference assignment validation FAILED")
            for finding in self.findings:
                print(finding.render())
            return
        statuses = {}
        for p in self.matrix.get("profiles") or []:
            key = (p.get("inference_strategy") or {}).get("status")
            statuses[key] = statuses.get(key, 0) + 1
        print("Profile inference assignment validation PASSED")
        print(f"profiles_assigned: {len(self.matrix.get('profiles') or [])}")
        print("assignment_status_counts:")
        for key in sorted(statuses):
            print(f"  {key}: {statuses[key]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Noesis profile inference assignment matrix.")
    parser.add_argument("--strict", action="store_true", help="Reserved for parity with the routing validator; all rules are mandatory.")
    parser.add_argument("--no-secret-scan", action="store_true", help="Skip scoped secret scan.")
    args = parser.parse_args()
    v = Validator(strict=args.strict, scan_secrets=not args.no_secret_scan)
    ok = v.validate()
    v.print_summary()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
