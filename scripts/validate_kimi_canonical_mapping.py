#!/usr/bin/env python3
"""Offline validator for the KIMI canonicalization candidate package.

Guards shared/models.kimi-proposed.yaml so the unverified observed model
reference `kimi-k2.7-code` can never be laundered into a pin, an approved
route, an r2/r3 path, a confidential route, an automatic fallback, or a
provider-selection default.

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

CANDIDATE = "shared/models.kimi-proposed.yaml"
RECONCILIATION = "platform/runtime-reconciliation.yaml"
EVAL_FIXTURES = "evals/kimi-canonical-mapping.eval.yaml"
SCAN_TARGETS = [
    CANDIDATE,
    "docs/kimi-canonicalization-plan.md",
    EVAL_FIXTURES,
    "scripts/validate_kimi_canonical_mapping.py",
    "scripts/test_validate_kimi_canonical_mapping.py",
]

FORBIDDEN_STATUS_WORDS = {"approved", "active", "enforced", "production", "selectable"}
NEVER_DATA_CLASSES = {"confidential", "restricted", "secret"}
ALLOWED_PIN_STATUS = {"observed_not_verified", "unverified", "needs_evidence"}
REQUIRED_ACTIVATION_REQUIREMENTS = {
    "verify_upstream_immutable_model_identifier",
    "resolve_dual_transport_naming_kimi_vs_kimi_coding",
    "add_canonical_catalog_entry_in_shared_models",
    "verify_provider_policy_and_data_handling",
    "define_cost_rate_latency_budget",
    "define_structured_output_contract",
    "add_offline_and_shadow_evals",
    "resolve_drifted_profile_reconciliation_entries",
    "independent_security_review",
    "explicit_human_approval",
}
REQUIRED_EVAL_IDS = {f"KCM-{i:03d}" for i in range(1, 13)}
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
    def __init__(self, scan_secrets: bool = True):
        self.scan_secrets = scan_secrets
        self.findings: list[Finding] = []
        self.docs: dict[str, Any] = {}

    def add(self, rule: str, path: str, field: str, hint: str) -> None:
        self.findings.append(Finding(rule, path, field, hint))

    def load_yaml(self, rel: str) -> Any:
        try:
            with (ROOT / rel).open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.add("KCM000", rel, "$", "Required file is missing.")
            return {}
        except yaml.YAMLError as exc:
            self.add("KCM000", rel, "$", f"YAML parse failed: {exc}")
            return {}

    def load_all(self) -> None:
        for rel in [CANDIDATE, RECONCILIATION, EVAL_FIXTURES]:
            self.docs[rel] = self.load_yaml(rel)

    @property
    def candidate_doc(self) -> dict[str, Any]:
        return self.docs.get(CANDIDATE) or {}

    @property
    def records(self) -> list[dict[str, Any]]:
        return list((self.candidate_doc.get("models") or []))

    def validate(self) -> bool:
        self.load_all()
        self.check_shape()
        records = self.records
        for idx, rec in enumerate(records):
            self.check_candidate(idx, rec)
        self.check_eval_fixtures()
        if self.scan_secrets:
            self.check_secret_safety()
        return not self.findings

    # ── KCM001 ────────────────────────────────────────────────────────────
    def check_shape(self) -> None:
        doc = self.candidate_doc
        if not doc:
            self.add("KCM001", CANDIDATE, "$", "Candidate file is empty or missing.")
            return
        if doc.get("policy_mode") != "proposed_not_live":
            self.add("KCM001", CANDIDATE, "policy_mode", "Must be proposed_not_live.")
        if doc.get("candidate_status") not in {"observed_not_verified", "unverified", "needs_evidence"}:
            self.add("KCM001", CANDIDATE, "candidate_status", "Must be an unverified-status value.")
        models = doc.get("models")
        if not isinstance(models, list) or len(models) != 1:
            self.add("KCM001", CANDIDATE, "models", "Exactly one candidate record is allowed.")
            return
        rec = models[0]
        for field in ["catalog_id", "provider_lane", "observed_model_reference", "pin_status",
                      "identification", "eligible_profiles", "eligible_task_classes",
                      "allowed_data_classes", "prohibited_data_classes", "max_risk_tier",
                      "execution_mode_max", "fallback_eligible", "default_route",
                      "parameter_profiles", "usage_restrictions", "activation_requirements"]:
            if field not in rec:
                self.add("KCM001", CANDIDATE, f"models[0].{field}", "Missing required candidate field.")

    def check_candidate(self, idx: int, rec: dict[str, Any]) -> None:
        path = f"{CANDIDATE}#models[{idx}]"
        # KCM002: no unverified pin
        if rec.get("canonical_model_id") is not None:
            self.add("KCM002", path, "canonical_model_id", "canonical_model_id must stay null until upstream immutability is verified.")
        # KCM003: pin status must not claim approval
        if rec.get("pin_status") not in ALLOWED_PIN_STATUS:
            self.add("KCM003", path, "pin_status", f"{rec.get('pin_status')!r} is not an unverified pin status.")
        # KCM004: no r2/r3 route
        if RISK_ORDER.get(str(rec.get("max_risk_tier")), 99) > RISK_ORDER["r1"]:
            self.add("KCM004", path, "max_risk_tier", "Unverified candidate cannot carry r2 or r3 work.")
        # KCM005: data classes
        allowed = set(rec.get("allowed_data_classes") or [])
        if allowed & NEVER_DATA_CLASSES:
            self.add("KCM005", path, "allowed_data_classes", "confidential/restricted/secret must never be allowed.")
        if not NEVER_DATA_CLASSES.issubset(set(rec.get("prohibited_data_classes") or [])):
            self.add("KCM005", path, "prohibited_data_classes", "confidential, restricted, and secret must be explicitly prohibited.")
        # KCM006: no approval claims anywhere in the record
        text = str(rec)
        negation = re.compile(r"\b(not|never|cannot|blocked|no)\b", flags=re.IGNORECASE)
        for word in FORBIDDEN_STATUS_WORDS:
            for m in re.finditer(rf"\b{word}\b", text, flags=re.IGNORECASE):
                ctx = text[max(0, m.start() - 40):m.end() + 40]
                if "may_not_be_used_as" in text[:m.start()][-200:] and word in {"approved", "active"}:
                    continue  # prohibition listing is fine
                if negation.search(ctx):
                    continue
                self.add("KCM006", path, "record_text", f"Record text asserts {word!r} without a negation.")
                break
        if rec.get("provider_lane") != "KIMI_CODE":
            self.add("KCM006", path, "provider_lane", "Candidate must reference the KIMI_CODE lane design only.")
        # KCM007: no eligible profiles yet
        if rec.get("eligible_profiles"):
            self.add("KCM007", path, "eligible_profiles", "No profile may be assigned the unverified candidate.")
        # KCM008 / KCM009: fallback and default
        if rec.get("fallback_eligible") is not False:
            self.add("KCM008", path, "fallback_eligible", "Unverified candidate must never be an automatic fallback.")
        if rec.get("default_route") is not False:
            self.add("KCM009", path, "default_route", "Unverified candidate must never be a provider-selection default.")
        # KCM010: activation gates
        declared = set(rec.get("activation_requirements") or [])
        missing = sorted(REQUIRED_ACTIVATION_REQUIREMENTS - declared)
        if missing:
            self.add("KCM010", path, "activation_requirements", f"Missing gates: {', '.join(missing)}.")
        # KCM011: observed reference must match reconciliation evidence
        observed = rec.get("observed_model_reference")
        recon = self.docs.get(RECONCILIATION) or {}
        refs = {
            (p.get("observed_runtime") or {}).get("model_alias_or_id")
            for p in (recon.get("profiles") or [])
        }
        if observed is not None and str(observed) not in {str(r) for r in refs}:
            self.add("KCM011", path, "observed_model_reference", f"{observed!r} does not match any reconciliation observed_runtime reference.")

    # ── eval fixtures ─────────────────────────────────────────────────────
    def check_eval_fixtures(self) -> None:
        evals = self.docs.get(EVAL_FIXTURES) or {}
        ids = {t.get("id") for t in evals.get("tests") or []}
        missing = sorted(REQUIRED_EVAL_IDS - ids)
        if missing:
            self.add("KCM001", EVAL_FIXTURES, "tests", f"Missing eval fixtures: {', '.join(missing)}.")
        for idx, test in enumerate(evals.get("tests") or []):
            for field in ["setup", "expected_result", "expected_error_class_or_assertion", "linked_validator_rule", "risk_level"]:
                if not test.get(field):
                    self.add("KCM001", EVAL_FIXTURES, f"tests[{idx}].{field}", "Fixture must map to a validator assertion.")

    # ── KCM012 ────────────────────────────────────────────────────────────
    def check_secret_safety(self) -> None:
        patterns = [
            ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
            ("seed_phrase_marker", re.compile(r"(?i)\b(seed phrase|mnemonic)\b")),
            ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}")),
            ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
            ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
            ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
            ("embedded_basic_auth_url", re.compile(r"https?://[^\s/@:]+:[^\s/@]+@")),
            ("generic_assignment_secret", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}")),
        ]
        for rel in SCAN_TARGETS:
            p = ROOT / rel
            if not p.exists():
                continue
            for label, pat in patterns:
                for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if rel.endswith("validate_kimi_canonical_mapping.py") and "re.compile" in line:
                        continue
                    if pat.search(line):
                        self.add("KCM012", rel, label, "Secret-like material detected; matched value intentionally not printed.")
                        break

    def print_summary(self) -> None:
        if self.findings:
            print("KIMI canonical mapping validation FAILED")
            for f in self.findings:
                print(f.render())
            return
        print("KIMI canonical mapping validation PASSED")
        rec = self.records[0] if self.records else {}
        print(f"candidate: {rec.get('catalog_id')}")
        print(f"pin_status: {rec.get('pin_status')}")
        print(f"canonical_model_id: {rec.get('canonical_model_id')}")
        print(f"max_risk_tier: {rec.get('max_risk_tier')}")
        print("posture: design-only; not a pin, not a route, not a fallback, not a default")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate KIMI canonicalization candidate package.")
    parser.add_argument("--strict", action="store_true", help="All rules are mandatory.")
    parser.add_argument("--no-secret-scan", action="store_true", help="Skip scoped secret scan.")
    args = parser.parse_args()
    v = Validator(scan_secrets=not args.no_secret_scan)
    ok = v.validate()
    v.print_summary()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
