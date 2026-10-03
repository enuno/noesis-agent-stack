#!/usr/bin/env python3
"""Offline semantic validator for proposed Noesis inference routing policy.

This validator is intentionally repository-local and deterministic. It never reads
~/.hermes, never makes network calls, and never prints matched secret values.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"FATAL: PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_INPUTS = [
    "platform/inference-routing.yaml",
    "platform/runtime-reconciliation.yaml",
    "shared/models.yaml",
    "shared/model-aliases.yaml",
    "shared/provider-policies.yaml",
    "profiles/noesis-roster.yaml",
    "profiles/model-profiles.yaml",
    "platform/risk-tiers.yaml",
]

SECRET_SCAN_TARGETS = [
    "platform/inference-routing.yaml",
    "platform/runtime-reconciliation.yaml",
    "docs/inference-lanes-design.md",
    "evals/inference-routing.eval.yaml",
    "scripts/validate_inference_routing.py",
    ".github/workflows/inference-routing-policy.yml",
]

STATUSES_NON_SELECTABLE = {"proposed", "disabled", "blocked_missing_configuration"}
RISK_ORDER = {"r0": 0, "r1": 1, "r2": 2, "r3": 3}

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
            self.add("R000", rel, "$", "Required file is missing.")
            return {}
        except yaml.YAMLError as exc:
            self.add("R000", rel, "$", f"YAML parse failed: {exc}")
            return {}

    def load_all(self) -> None:
        for rel in REQUIRED_INPUTS:
            self.docs[rel] = self.load_yaml(rel)
        # Optional files used by checks.
        for rel in ["evals/inference-routing.eval.yaml"]:
            if (ROOT / rel).exists():
                self.docs[rel] = self.load_yaml(rel)

    @property
    def policy(self) -> dict[str, Any]:
        return self.docs.get("platform/inference-routing.yaml") or {}

    @property
    def reconciliation(self) -> dict[str, Any]:
        return self.docs.get("platform/runtime-reconciliation.yaml") or {}

    @property
    def lanes(self) -> dict[str, Any]:
        return self.policy.get("approved_lanes") or {}

    def validate(self) -> bool:
        self.load_all()
        self.check_global_policy()
        self.check_model_and_aliases()
        self.check_openrouter()
        self.check_risk_and_independence()
        self.check_reconciliation()
        self.check_eval_fixtures()
        if self.scan_secrets:
            self.check_secret_safety()
        return not self.findings

    def check_global_policy(self) -> None:
        rel = "platform/inference-routing.yaml"
        iom = self.policy.get("interim_operating_mode") or {}
        required_iom = {
            "mode": "reconciliation_freeze",
            "status": "proposed_not_live",
            "effective_until": "canonical_lane_review_approved",
        }
        for key, expected in required_iom.items():
            if iom.get(key) != expected:
                self.add("R001", rel, f"interim_operating_mode.{key}", f"Expected {expected!r}.")
        for item in [
            "new_provider_activation",
            "new_model_activation",
            "new_model_alias_activation",
            "openrouter_primary_routing",
            "openrouter_automatic_fallback",
            "automatic_execution_fallback",
            "r2_or_r3_route_promotion",
            "unapproved_profile_reconciliation",
            "secret_or_restricted_data_external_egress",
            "live_runtime_mutation",
        ]:
            if item not in (iom.get("prohibited") or []):
                self.add("R001", rel, "interim_operating_mode.prohibited", f"Freeze mode must prohibit {item}.")

        if not self.lanes:
            self.add("R003", rel, "approved_lanes", "approved_lanes must be present.")
            return

        for lane_name, lane in self.lanes.items():
            status = lane.get("status")
            if not status:
                self.add("R003", rel, f"approved_lanes.{lane_name}.status", "Lane needs explicit status.")
            for field in ["permitted_data_classes", "prohibited_data_classes", "max_risk_tier", "execution_mode_max"]:
                if lane.get(field) in (None, [], ""):
                    self.add("R004", rel, f"approved_lanes.{lane_name}.{field}", "Lane requires this policy field.")
            if status != "approved" and not lane.get("activation_requirements"):
                self.add("R004", rel, f"approved_lanes.{lane_name}.activation_requirements", "Non-approved lanes require activation requirements.")
            unsafe = {"secret", "restricted", "confidential"}.intersection(set(lane.get("permitted_data_classes") or []))
            if unsafe:
                provider_policy = self.docs.get("shared/provider-policies.yaml") or {}
                # No current approved lane should permit these exact data classes without explicit provider policy.
                self.add("R005", rel, f"approved_lanes.{lane_name}.permitted_data_classes", "Do not permit secret/restricted/confidential data without explicit approved provider policy.")

        # Proposed/disabled/blocked lanes cannot be eligible active primary lanes.
        classes = self.policy.get("profile_routing_classes") or {}
        for cls_name, cls in classes.items():
            for lane in cls.get("eligible_primary_lanes") or []:
                status = (self.lanes.get(lane) or {}).get("status")
                if status in STATUSES_NON_SELECTABLE:
                    self.add("R002", rel, f"profile_routing_classes.{cls_name}.eligible_primary_lanes", f"{lane} is {status} and cannot be active primary.")
                if lane not in self.lanes:
                    self.add("R003", rel, f"profile_routing_classes.{cls_name}.eligible_primary_lanes", f"{lane} is absent from approved_lanes.")

        # Fallback must preserve classification/tooling and log substitution.
        fallback = self.policy.get("fallback_policy") or {}
        required_preserve = {"task_id", "profile_id", "data_classification", "risk_tier", "tool_scope", "execution_mode", "output_schema"}
        if not required_preserve.issubset(set(fallback.get("preserve_fields") or [])):
            self.add("R006", rel, "fallback_policy.preserve_fields", "Fallback must preserve task identity, classification, risk, tool scope, mode, and schema.")
        invariants = self.policy.get("global_invariants") or {}
        if invariants.get("provider_substitution_must_be_logged") is not True:
            self.add("R006", rel, "global_invariants.provider_substitution_must_be_logged", "Provider substitution logging invariant is required.")

    def check_model_and_aliases(self) -> None:
        rel = "platform/inference-routing.yaml"
        models = self.docs.get("shared/models.yaml") or {}
        model_aliases = self.docs.get("shared/model-aliases.yaml") or {}
        # Build known catalog identifiers from the repository, not from runtime.
        known_models: set[str] = set()
        for section in ["profiles", "charter_profiles"]:
            for key, val in (models.get(section) or {}).items():
                known_models.add(str(key))
                if isinstance(val, dict) and val.get("model"):
                    known_models.add(str(val["model"]))
        known_aliases = set((model_aliases.get("capability_aliases") or {}).keys()) | known_models

        for lane_name, lane in self.lanes.items():
            if lane.get("status") == "approved" and not lane.get("pinned_models"):
                self.add("R007", rel, f"approved_lanes.{lane_name}.pinned_models", "Approved lane needs a pinned model or approved immutable alias mapping.")
        perplexity = self.lanes.get("PERPLEXITY_API") or {}
        if perplexity.get("pinned_models"):
            self.add("R008", rel, "approved_lanes.PERPLEXITY_API.pinned_models", "Keep empty until canonical Perplexity model IDs are verified in shared catalog.")
        observed = set(perplexity.get("observed_aliases_not_canonical_pins") or [])
        if {"sonar", "sonar-pro"}.difference(observed):
            self.add("R009", rel, "approved_lanes.PERPLEXITY_API.observed_aliases_not_canonical_pins", "sonar and sonar-pro must be recorded as observed aliases, not canonical pins.")

        # Reconciliation repo declarations must use known or explicitly blocked/missing evidence states.
        for idx, prof in enumerate(self.reconciliation.get("profiles") or []):
            repo_model = str((prof.get("repo_declared") or {}).get("model_alias_or_id") or "unknown")
            state = (prof.get("resolution") or {}).get("state")
            alignment = prof.get("alignment")
            if repo_model in {"unknown", "None", ""}:
                continue
            if repo_model not in known_aliases and state not in {"blocked", "needs_evidence"} and alignment != "missing_repo_declaration":
                self.add("R006", "platform/runtime-reconciliation.yaml", f"profiles[{idx}].repo_declared.model_alias_or_id", "Unknown model/alias must be blocked, needs_evidence, or explicitly non-verifiable.")

    def check_openrouter(self) -> None:
        rel = "platform/inference-routing.yaml"
        lane = self.lanes.get("OPENROUTER_FALLBACK") or {}
        if lane.get("primary_eligible") is not False:
            self.add("R012", rel, "approved_lanes.OPENROUTER_FALLBACK.primary_eligible", "OpenRouter fallback must not be primary eligible.")
        if lane.get("automatic_execution_fallback") is not False:
            self.add("R013", rel, "approved_lanes.OPENROUTER_FALLBACK.automatic_execution_fallback", "OpenRouter must not be automatic execution fallback.")
        if lane.get("fallback_eligible") is not False:
            self.add("R013", rel, "approved_lanes.OPENROUTER_FALLBACK.fallback_eligible", "OpenRouter fallback eligibility must remain false during freeze.")
        if RISK_ORDER.get(lane.get("max_risk_tier", "r3"), 99) > 0:
            self.add("R014", rel, "approved_lanes.OPENROUTER_FALLBACK.max_risk_tier", "OpenRouter cannot be selectable for r1-r3 while disabled/frozen.")

        # Detect repo live OpenRouter primaries; require reconciliation to mark them blocked.
        blocked_ids = {p.get("profile_id") for p in (self.reconciliation.get("profiles") or []) if (p.get("resolution") or {}).get("state") == "blocked"}
        for path in glob.glob(str(ROOT / "profiles/live/*/config.yaml")):
            data = self.safe_load_path(Path(path))
            provider = (((data or {}).get("model") or {}).get("provider") or "").lower()
            if provider == "openrouter":
                pid = Path(path).parent.name
                if pid not in blocked_ids:
                    self.add("R011", str(Path(path).relative_to(ROOT)), "model.provider", "OpenRouter primary declarations must be represented as blocked in runtime reconciliation while OpenRouter is disabled.")

    def check_risk_and_independence(self) -> None:
        rel = "platform/inference-routing.yaml"
        r2 = ((self.policy.get("risk_tier_requirements") or {}).get("r2") or {})
        if "independent" not in str(r2.get("review", "")):
            self.add("R015", rel, "risk_tier_requirements.r2.review", "r2 requires independent provider-family review.")
        r3 = ((self.policy.get("risk_tier_requirements") or {}).get("r3") or {})
        if "no_automatic_execution_fallback" not in str(r3.get("fallback", "")):
            self.add("R016", rel, "risk_tier_requirements.r3.fallback", "r3 must disable automatic execution fallback.")
        if "mandatory" not in str(r3.get("human_approval", "")):
            self.add("R016", rel, "risk_tier_requirements.r3.human_approval", "r3 must require explicit human approval.")
        if r3.get("rollback_required") is not True:
            self.add("R016", rel, "risk_tier_requirements.r3.rollback_required", "r3 must require rollback/recovery.")

        classes = self.policy.get("profile_routing_classes") or {}
        impl = classes.get("implementation_coder") or {}
        gates = set(impl.get("required_gates") or [])
        if not {"independent_provider_review", "qa_validation"}.issubset(gates):
            self.add("R017", rel, "profile_routing_classes.implementation_coder.required_gates", "Implementation profiles require independent review and QA.")
        research = classes.get("research_evidence") or {}
        research_checks = set(research.get("required_gates") or []) | set((self.lanes.get("PERPLEXITY_API") or {}).get("required_policy_checks") or [])
        if "provenance_artifact_required" not in research_checks:
            self.add("R018", rel, "profile_routing_classes.research_evidence", "External evidence routes require provenance artifacts.")
        for cls_name, cls in classes.items():
            if cls_name in {"structured_worker", "research_evidence", "supervisor_control_plane"} and cls.get("structured_output_required") is not True and "schema_validation" not in (cls.get("required_gates") or []):
                self.add("R019", rel, f"profile_routing_classes.{cls_name}", "Worker/research/control-plane contracts need structured-output or schema enforcement.")

    def check_reconciliation(self) -> None:
        rel = "platform/runtime-reconciliation.yaml"
        roster = self.docs.get("profiles/noesis-roster.yaml") or {}
        orch = self.docs.get("platform/orchestrator.yaml") or {}
        expected = set((roster.get("profiles") or {}).keys()) | set((orch.get("agents") or {}).keys())
        profiles = self.reconciliation.get("profiles") or []
        actual = {p.get("profile_id") for p in profiles}
        missing = sorted(expected - actual)
        if missing:
            self.add("R020", rel, "profiles", f"Missing reconciliation entries: {', '.join(missing)}")
        for idx, p in enumerate(profiles):
            alignment = p.get("alignment")
            resolution = p.get("resolution") or {}
            state = resolution.get("state")
            rationale = resolution.get("rationale")
            if alignment in {"drift", "blocked"} or state == "blocked":
                if not state or not rationale:
                    self.add("R021", rel, f"profiles[{idx}].resolution", "Drift/blocked entries require explicit resolution state and rationale.")
            repo_lane = (p.get("repo_declared") or {}).get("provider_lane")
            if repo_lane == "OPENROUTER_FALLBACK" and state != "blocked":
                self.add("R022", rel, f"profiles[{idx}].resolution.state", "Repo OpenRouter primary declarations must remain blocked.")
            if state == "adopt_runtime":
                gates = set(resolution.get("required_gates") or [])
                if "explicit_human_approval" not in gates:
                    self.add("R023", rel, f"profiles[{idx}].resolution.required_gates", "adopt_runtime requires explicit human approval metadata.")
        self.detect_secret_like_in_file(rel, rule="R024")

    def check_eval_fixtures(self) -> None:
        rel = "evals/inference-routing.eval.yaml"
        evals = self.docs.get(rel) or {}
        names = {t.get("name") for t in evals.get("tests") or []}
        required = {
            "freeze_blocks_new_lane_activation",
            "kimi_observed_runtime_is_not_automatic_policy",
            "perplexity_requires_canonical_model_pin_before_approval",
            "perplexity_restricts_data_to_public_or_internal_redacted",
            "perplexity_requires_provenance_artifact",
            "claude_code_requires_bridge_independent_review_and_qa",
            "proposed_lane_cannot_be_selected",
            "openrouter_disabled_cannot_be_primary",
            "openrouter_cannot_be_automatic_execution_fallback",
            "provider_outage_preserves_task_class_and_logs_substitution",
            "r2_requires_independent_provider_family_review",
            "r3_disables_automatic_execution_fallback_and_requires_human_gate",
            "secrets_denied_before_external_dispatch",
            "runtime_repo_drift_requires_explicit_reconciliation_state",
            "alias_change_requires_routing_review",
        }
        missing = sorted(required - names)
        if missing:
            self.add("R010", rel, "tests", f"Missing eval fixtures: {', '.join(missing)}")
        for idx, test in enumerate(evals.get("tests") or []):
            for field in ["setup", "expected_result", "expected_error_class_or_assertion", "linked_validator_rule", "risk_level"]:
                if not test.get(field):
                    self.add("R010", rel, f"tests[{idx}].{field}", "Eval fixture must map scenario to validator assertion.")

    def check_secret_safety(self) -> None:
        for rel in SECRET_SCAN_TARGETS:
            if (ROOT / rel).exists():
                self.detect_secret_like_in_file(rel, rule="R025")

    def detect_secret_like_in_file(self, rel: str, rule: str) -> None:
        path = ROOT / rel
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
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
                # Do not flag this validator's own regex definitions as leaked material.
                if rel.endswith("validate_inference_routing.py") and "re.compile" in line:
                    continue
                if pat.search(line):
                    self.add(rule, rel, label, "Secret-like material detected; remove/redact. Matched value intentionally not printed.")
                    break

    def safe_load_path(self, path: Path) -> Any:
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def print_summary(self) -> None:
        if self.findings:
            print("Inference routing validation FAILED")
            for finding in self.findings:
                print(finding.render())
            return
        lane_status = {name: lane.get("status") for name, lane in self.lanes.items()}
        recon_counts = Counter(p.get("alignment") for p in self.reconciliation.get("profiles") or [])
        resolution_counts = Counter((p.get("resolution") or {}).get("state") for p in self.reconciliation.get("profiles") or [])
        print("Inference routing validation PASSED")
        print("lane_statuses:")
        for name in sorted(lane_status):
            print(f"  {name}: {lane_status[name]}")
        print("reconciliation_alignment_counts:")
        for key, value in sorted(recon_counts.items()):
            print(f"  {key}: {value}")
        print("reconciliation_resolution_counts:")
        for key, value in sorted(resolution_counts.items()):
            print(f"  {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Noesis inference routing policy artifacts.")
    parser.add_argument("--strict", action="store_true", help="Treat unresolved required fields as failures.")
    parser.add_argument("--no-secret-scan", action="store_true", help="Skip scoped secret scan.")
    args = parser.parse_args()
    v = Validator(strict=args.strict, scan_secrets=not args.no_secret_scan)
    ok = v.validate()
    v.print_summary()
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
