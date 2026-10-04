#!/usr/bin/env python3
"""Tests for scripts/validate_profile_inference_assignments.py.

Run from repo root: python3 -m pytest scripts/test_validate_profile_inference_assignments.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "vpia", ROOT / "scripts" / "validate_profile_inference_assignments.py"
)
assert _spec is not None and _spec.loader is not None
vpia = importlib.util.module_from_spec(_spec)
sys.modules["vpia"] = vpia  # @dataclass resolves cls.__module__ via sys.modules
_spec.loader.exec_module(vpia)


def load_docs() -> dict:
    v = vpia.Validator()
    v.load_all()
    return v.docs


def run_full(docs: dict) -> list:
    v = vpia.Validator()
    v.docs = docs
    v.check_inventory()
    v.check_strategic_fields()
    v.check_primary_selection()
    v.check_independence()
    v.check_boundaries()
    v.check_fallback()
    v.check_eval_fixtures()
    return v.findings


def run_check(check_name: str, mutate=None) -> list:
    docs = load_docs()
    if mutate:
        mutate(docs)
    v = vpia.Validator()
    v.docs = docs
    getattr(v, check_name)()
    return v.findings


def profiles(docs) -> list:
    return docs[vpia.ASSIGNMENTS]["profiles"]


def by_id(docs, pid: str) -> dict:
    return next(p for p in profiles(docs) if p["profile_id"] == pid)


def rules(findings) -> set:
    return {f.rule for f in findings}


# ── baseline ────────────────────────────────────────────────────────────────

def test_committed_matrix_passes_full_validation():
    assert run_full(load_docs()) == []


# ── PIA001 inventory ────────────────────────────────────────────────────────

def test_unknown_profile_is_rejected():
    def mut(docs):
        rogue = copy.deepcopy(profiles(docs)[0])
        rogue["profile_id"] = "noesis-imaginary"
        profiles(docs).append(rogue)
    assert "PIA001" in rules(run_check("check_inventory", mut))


def test_missing_profile_is_rejected():
    def mut(docs):
        docs[vpia.ASSIGNMENTS]["profiles"] = [
            p for p in profiles(docs) if p["profile_id"] != "noesis-ledger"
        ]
    assert "PIA001" in rules(run_check("check_inventory", mut))


# ── PIA002 strategic fields ─────────────────────────────────────────────────

def test_missing_strategic_field_is_rejected():
    def mut(docs):
        del by_id(docs, "noesis-grid")["risk_ceiling"]
    assert "PIA002" in rules(run_check("check_strategic_fields", mut))


def test_forbidden_status_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-grid")["inference_strategy"]["status"] = "approved"
    assert "PIA002" in rules(run_check("check_strategic_fields", mut))


# ── PIA003/PIA004 primary selection ─────────────────────────────────────────

def test_noncanonical_model_ref_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-grid")["inference_strategy"]["primary"]["model_ref"] = "gpt-9-ultra"
    assert "PIA003" in rules(run_check("check_primary_selection", mut))


def test_proposed_lane_as_primary_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-signal")["inference_strategy"]["primary"]["lane"] = "PERPLEXITY_API"
    assert "PIA004" in rules(run_check("check_primary_selection", mut))


# ── PIA005/PIA006 independence ──────────────────────────────────────────────

def test_same_family_sole_critic_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-forge")["inference_strategy"]["critic"]["lane"] = "KIMI_CODE"
    assert "PIA005" in rules(run_check("check_independence", mut))


def test_qa_without_independent_review_gate_is_rejected():
    def mut(docs):
        gates = by_id(docs, "qa")["validation"]["required_gates"]
        gates.remove("independent_provider_review")
    assert "PIA006" in rules(run_check("check_independence", mut))


# ── PIA007/PIA008 boundaries ────────────────────────────────────────────────

def test_research_without_provenance_gate_is_rejected():
    def mut(docs):
        gates = by_id(docs, "noesis-signal")["validation"]["required_gates"]
        gates.remove("provenance_artifact_required")
    assert "PIA007" in rules(run_check("check_independence", mut))


def test_reflective_with_terminal_tool_is_rejected():
    def mut(docs):
        by_id(docs, "subconscious-openclaw")["tool_policy"]["allowed"].append("terminal")
    assert "PIA008" in rules(run_check("check_independence", mut))


# ── PIA009/PIA010/PIA011 fallback & privilege ───────────────────────────────

def test_privileged_profile_with_automatic_fallback_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-core")["inference_strategy"]["fallback"]["enabled"] = True
        by_id(docs, "noesis-core")["inference_strategy"]["fallback"]["ordered_candidates"] = ["KIMI_CODE"]
    assert "PIA009" in rules(run_check("check_boundaries", mut))


def test_openrouter_primary_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-grid")["inference_strategy"]["primary"]["lane"] = "OPENROUTER_FALLBACK"
    assert "PIA010" in rules(run_check("check_boundaries", mut))


def test_unbounded_fallback_is_rejected():
    def mut(docs):
        fb = by_id(docs, "noesis-grid")["inference_strategy"]["fallback"]
        fb["ordered_candidates"] = ["KIMI_CODE"]
    assert "PIA011" in rules(run_check("check_fallback", mut))


# ── PIA013/PIA014 gap discipline & data classes ─────────────────────────────

def test_null_lane_with_observe_only_status_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-signal")["inference_strategy"]["status"] = "observe_only"
    assert "PIA013" in rules(run_check("check_primary_selection", mut))


def test_confidential_data_class_is_rejected():
    def mut(docs):
        by_id(docs, "noesis-grid")["allowed_data_classes"].append("confidential")
    assert "PIA014" in rules(run_check("check_primary_selection", mut))


# ── PIA012 secret hygiene ───────────────────────────────────────────────────

def test_secret_like_material_is_rejected(tmp_path, monkeypatch):
    docs = load_docs()
    v = vpia.Validator()
    v.docs = docs
    bad = tmp_path / "platform"
    bad.mkdir(parents=True)
    leak = "sk-" + "a" * 40  # synthetic detector-probe string, not a real key
    (bad / "profile-inference-assignments.yaml").write_text(
        f"profiles: []\nleak: {leak}\n"
    )
    monkeypatch.setattr(vpia, "ROOT", tmp_path)
    v.detect_secret_like_in_file("platform/profile-inference-assignments.yaml")
    assert "PIA012" in rules(v.findings)


# ── eval fixtures ───────────────────────────────────────────────────────────

def test_missing_eval_fixture_is_rejected():
    def mut(docs):
        tests = docs["evals/profile-inference-assignment.eval.yaml"]["tests"]
        del tests[0]
    assert "PIA002" in rules(run_check("check_eval_fixtures", mut))
