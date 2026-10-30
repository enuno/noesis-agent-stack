#!/usr/bin/env python3
"""Tests for scripts/validate_kimi_canonical_mapping.py.

Run from repo root: python3 -m pytest scripts/test_validate_kimi_canonical_mapping.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "vkcm", ROOT / "scripts" / "validate_kimi_canonical_mapping.py"
)
assert _spec is not None and _spec.loader is not None
vkcm = importlib.util.module_from_spec(_spec)
sys.modules["vkcm"] = vkcm  # @dataclass resolves cls.__module__ via sys.modules
_spec.loader.exec_module(vkcm)


def load_docs() -> dict:
    v = vkcm.Validator()
    v.load_all()
    return v.docs


def run_all(docs: dict) -> list:
    v = vkcm.Validator()
    v.docs = docs
    v.check_shape()
    for idx, rec in enumerate(v.records):
        v.check_candidate(idx, rec)
    v.check_eval_fixtures()
    return v.findings


def rules(findings) -> set:
    return {f.rule for f in findings}


def candidate(docs) -> dict:
    return docs[vkcm.CANDIDATE]["models"][0]


# ── baseline ────────────────────────────────────────────────────────────────

def test_committed_candidate_passes_full_validation():
    assert run_all(load_docs()) == []


# ── KCM001 shape ────────────────────────────────────────────────────────────

def test_extra_candidate_record_is_rejected():
    docs = load_docs()
    docs[vkcm.CANDIDATE]["models"].append(copy.deepcopy(candidate(docs)))
    assert "KCM001" in rules(run_all(docs))


def test_wrong_policy_mode_is_rejected():
    docs = load_docs()
    docs[vkcm.CANDIDATE]["policy_mode"] = "live"
    assert "KCM001" in rules(run_all(docs))


# ── KCM002/003 pin discipline ───────────────────────────────────────────────

def test_canonical_model_id_must_stay_null():
    docs = load_docs()
    candidate(docs)["canonical_model_id"] = "kimi-k2.7-code"
    assert "KCM002" in rules(run_all(docs))


def test_approved_pin_status_is_rejected():
    docs = load_docs()
    candidate(docs)["pin_status"] = "approved"
    assert "KCM003" in rules(run_all(docs))


# ── KCM004/005 boundaries ───────────────────────────────────────────────────

def test_r2_risk_tier_is_rejected():
    docs = load_docs()
    candidate(docs)["max_risk_tier"] = "r2"
    assert "KCM004" in rules(run_all(docs))


def test_r3_risk_tier_is_rejected():
    docs = load_docs()
    candidate(docs)["max_risk_tier"] = "r3"
    assert "KCM004" in rules(run_all(docs))


def test_confidential_data_class_is_rejected():
    docs = load_docs()
    candidate(docs)["allowed_data_classes"].append("confidential")
    assert "KCM005" in rules(run_all(docs))


def test_missing_prohibited_data_class_is_rejected():
    docs = load_docs()
    candidate(docs)["prohibited_data_classes"] = ["confidential"]
    assert "KCM005" in rules(run_all(docs))


# ── KCM006 approval language ────────────────────────────────────────────────

def test_record_claiming_active_route_is_rejected():
    docs = load_docs()
    candidate(docs)["notes"] = "this route is active for production dispatch"
    assert "KCM006" in rules(run_all(docs))


# ── KCM007/008/009 usage restrictions ───────────────────────────────────────

def test_eligible_profiles_must_stay_empty():
    docs = load_docs()
    candidate(docs)["eligible_profiles"] = ["noesis-grid"]
    assert "KCM007" in rules(run_all(docs))


def test_automatic_fallback_is_rejected():
    docs = load_docs()
    candidate(docs)["fallback_eligible"] = True
    assert "KCM008" in rules(run_all(docs))


def test_default_route_is_rejected():
    docs = load_docs()
    candidate(docs)["default_route"] = True
    assert "KCM009" in rules(run_all(docs))


# ── KCM010/011 gates and evidence ───────────────────────────────────────────

def test_missing_activation_gate_is_rejected():
    docs = load_docs()
    candidate(docs)["activation_requirements"].remove("verify_upstream_immutable_model_identifier")
    assert "KCM010" in rules(run_all(docs))


def test_human_approval_gate_cannot_be_removed():
    docs = load_docs()
    candidate(docs)["activation_requirements"].remove("explicit_human_approval")
    assert "KCM010" in rules(run_all(docs))


def test_fabricated_observed_reference_is_rejected():
    docs = load_docs()
    candidate(docs)["observed_model_reference"] = "kimi-k9-imaginary"
    assert "KCM011" in rules(run_all(docs))


# ── eval fixtures ───────────────────────────────────────────────────────────

def test_missing_eval_fixture_is_rejected():
    docs = load_docs()
    del docs[vkcm.EVAL_FIXTURES]["tests"][0]
    assert "KCM001" in rules(run_all(docs))


# ── KCM012 secret hygiene ───────────────────────────────────────────────────

def test_secret_like_material_is_rejected(tmp_path, monkeypatch):
    docs = load_docs()
    v = vkcm.Validator()
    v.docs = docs
    bad = tmp_path / "shared"
    bad.mkdir(parents=True)
    leak = "sk-" + "b" * 40  # synthetic detector-probe string, not a real key
    (bad / "models.kimi-proposed.yaml").write_text(f"models: []\nleak: {leak}\n")
    monkeypatch.setattr(vkcm, "ROOT", tmp_path)
    v.check_secret_safety()
    assert "KCM012" in rules(v.findings)
