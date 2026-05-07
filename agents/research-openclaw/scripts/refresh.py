#!/usr/bin/env python3
"""Main evidence collection run for research-openclaw.

Executes the full research protocol: fetch sources, extract claims,
normalize, promote to findings, evaluate signals, and write all artifacts.

Supports four modes: bootstrap, refresh, targeted-query, build-intent-research.

Usage:
    python refresh.py --mode refresh \
                      --config-dir agents/research-openclaw/config \
                      --vault-dir workspace/research-vault
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from lib.claims import ClaimProcessor
from lib.fetcher import Fetcher
from lib.ledger import Ledger
from lib.schemas import SchemaManager, ValidationError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research evidence collection run")
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "refresh", "targeted-query", "build-intent-research"],
        required=True,
        help="Execution mode",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("agents/research-openclaw/config"),
        help="Path to config directory",
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    parser.add_argument(
        "--objective",
        type=str,
        default="",
        help="Research objective (for targeted-query and build-intent-research)",
    )
    parser.add_argument(
        "--collectors-config",
        type=Path,
        default=None,
        help="Override path to collectors.yaml",
    )
    return parser.parse_args(argv)


def load_thresholds(config_dir: Path) -> dict[str, Any]:
    """Load threshold configuration."""
    import yaml
    path = config_dir / "thresholds.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_constraints(config_dir: Path, mode: str) -> dict[str, Any]:
    """Load default job constraints for a mode."""
    import yaml
    path = config_dir / "jobs.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        jobs = yaml.safe_load(f) or {}
    job_types = jobs.get("job_types", {})
    for jt in job_types:
        if jt.get("mode") == mode:
            return jt.get("default_constraints", {})
    return {}


def write_receipt(
    vault_dir: Path,
    run_id: str,
    mode: str,
    status: str,
    metrics: dict[str, Any],
    artifacts: list[str],
    breaches: list[dict[str, Any]],
    step: str,
) -> None:
    """Write the run receipt to state/runs/receipts.jsonl."""
    receipt = {
        "run_id": run_id,
        "job_id": run_id,  # In standalone mode, run_id doubles as job_id
        "mode": mode,
        "status": status,
        "artifacts_written": artifacts,
        "metrics": metrics,
        "guardrail_breaches": breaches,
        "interrupted_at_step": step if status == "partial" else None,
        "started_at": metrics.get("started_at"),
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    ledger = Ledger(vault_dir / "state" / "runs" / "receipts.jsonl")
    ledger.append([receipt])


def run_bootstrap(
    vault_dir: Path, config_dir: Path, schemas: SchemaManager, collectors_path: Path
) -> tuple[str, dict[str, Any], list[str], list[dict]]:
    """Execute bootstrap mode. Returns (status, metrics, artifacts, breaches)."""
    run_id = str(__import__("uuid").uuid4())
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metrics = {"started_at": started_at, "source_count": 0, "claim_count": 0, "finding_count": 0, "signal_count": 0, "build_intent_count": 0}
    artifacts: list[str] = []
    breaches: list[dict] = []

    thresholds = load_thresholds(config_dir)
    fetcher = Fetcher(collectors_path)
    processor = ClaimProcessor(schemas, thresholds)

    sources_ledger = Ledger(vault_dir / "knowledge" / "sources.jsonl")
    claims_ledger = Ledger(vault_dir / "knowledge" / "claims.jsonl")

    try:
        sources = fetcher.fetch_all()
        metrics["source_count"] = len(sources)

        # Enrich sources with ledger-required fields before validation
        for s in sources:
            s.setdefault("schema_version", "1.0")
            s.setdefault("run_id", run_id)
            s.setdefault("created_at", started_at)
            s.setdefault("source_agent", "research-openclaw")
            s.setdefault("collector", s.pop("collector_key", None))

        # Validate and write sources
        valid_sources, invalid = schemas.validate_batch(sources, "sources")
        if invalid:
            print(f"Warning: {len(invalid)} sources failed validation")

        sources_ledger.append(valid_sources)
        artifacts.append(str(sources_ledger.path))

        # Extract claims (no promotion in bootstrap)
        all_claims: list[dict] = []
        for source in valid_sources:
            claims = processor.extract(source)
            all_claims.extend(claims)

        metrics["claim_count"] = len(all_claims)

        # Enrich claims with ledger-required fields before validation
        for c in all_claims:
            c.setdefault("schema_version", "1.0")
            c.setdefault("run_id", run_id)
            c.setdefault("created_at", started_at)
            c.setdefault("source_agent", "research-openclaw")
            c.setdefault("extracted_from", c.get("source_id"))
            c.setdefault("extraction_method", "rule_based")

        valid_claims, invalid_claims = schemas.validate_batch(all_claims, "claims")
        if invalid_claims:
            print(f"Warning: {len(invalid_claims)} claims failed validation")
        claims_ledger.append(valid_claims)
        artifacts.append(str(claims_ledger.path))

        return "completed", metrics, artifacts, breaches
    except Exception as exc:
        metrics["error"] = str(exc)
        return "partial", metrics, artifacts, breaches


def run_refresh(
    vault_dir: Path, config_dir: Path, schemas: SchemaManager, collectors_path: Path
) -> tuple[str, dict[str, Any], list[str], list[dict]]:
    """Execute refresh mode."""
    run_id = str(__import__("uuid").uuid4())
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metrics = {"started_at": started_at, "source_count": 0, "claim_count": 0, "finding_count": 0, "signal_count": 0, "build_intent_count": 0}
    artifacts: list[str] = []
    breaches: list[dict] = []

    thresholds = load_thresholds(config_dir)
    fetcher = Fetcher(collectors_path)
    processor = ClaimProcessor(schemas, thresholds)

    sources_ledger = Ledger(vault_dir / "knowledge" / "sources.jsonl")
    claims_ledger = Ledger(vault_dir / "knowledge" / "claims.jsonl")
    findings_ledger = Ledger(vault_dir / "knowledge" / "findings.jsonl")

    existing_sources = sources_ledger.read_all()
    existing_claims = claims_ledger.read_all()
    existing_hashes = {s.get("content_hash") for s in existing_sources}

    try:
        sources = fetcher.fetch_all()
        new_sources = [s for s in sources if s.get("content_hash") not in existing_hashes]
        metrics["source_count"] = len(new_sources)

        # Enrich sources with ledger-required fields before validation
        for s in new_sources:
            s.setdefault("schema_version", "1.0")
            s.setdefault("run_id", run_id)
            s.setdefault("created_at", started_at)
            s.setdefault("source_agent", "research-openclaw")
            s.setdefault("collector", s.pop("collector_key", None))

        valid_sources, _ = schemas.validate_batch(new_sources, "sources")
        sources_ledger.append(valid_sources)
        artifacts.append(str(sources_ledger.path))

        all_new_claims: list[dict] = []
        for source in valid_sources:
            claims = processor.extract(source)
            all_new_claims.extend(claims)

        normalized = processor.normalize(all_new_claims, existing_claims)
        metrics["claim_count"] = len(normalized)

        # Enrich claims with ledger-required fields before validation
        for c in normalized:
            c.setdefault("schema_version", "1.0")
            c.setdefault("run_id", run_id)
            c.setdefault("created_at", started_at)
            c.setdefault("source_agent", "research-openclaw")
            c.setdefault("extracted_from", c.get("source_id"))
            c.setdefault("extraction_method", "rule_based")

        valid_claims, invalid_claims = schemas.validate_batch(normalized, "claims")
        if invalid_claims:
            print(f"Warning: {len(invalid_claims)} claims failed validation")
        claims_ledger.append(valid_claims)
        artifacts.append(str(claims_ledger.path))

        # Promote findings
        all_claims = existing_claims + valid_claims
        findings = processor.promote(all_claims, sources_ledger.read_all())
        metrics["finding_count"] = len(findings)

        valid_findings, _ = schemas.validate_batch(findings, "findings")
        findings_ledger.append(valid_findings)
        artifacts.append(str(findings_ledger.path))

        # Signals
        signals = [f for f in valid_findings if f.get("signal_value") in ("high", "medium")]
        metrics["signal_count"] = len(signals)
        if signals:
            signals_dir = vault_dir / "signals"
            signals_dir.mkdir(parents=True, exist_ok=True)
            signal_path = signals_dir / f"signals-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
            with open(signal_path, "w", encoding="utf-8") as f:
                json.dump(signals, f, indent=2)
            artifacts.append(str(signal_path))

        return "completed", metrics, artifacts, breaches
    except Exception as exc:
        metrics["error"] = str(exc)
        return "partial", metrics, artifacts, breaches


def run_targeted_query(
    vault_dir: Path, config_dir: Path, schemas: SchemaManager, collectors_path: Path, objective: str
) -> tuple[str, dict[str, Any], list[str], list[dict]]:
    """Execute targeted-query mode."""
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metrics = {"started_at": started_at, "source_count": 0, "claim_count": 0, "finding_count": 0, "signal_count": 0, "build_intent_count": 0}
    artifacts: list[str] = []
    breaches: list[dict] = []

    # In standalone mode, targeted-query is a simplified refresh on a topic
    # Full implementation would fetch specific URLs/questions
    return run_refresh(vault_dir, config_dir, schemas, collectors_path)


def run_build_intent_research(
    vault_dir: Path, config_dir: Path, schemas: SchemaManager, collectors_path: Path, objective: str
) -> tuple[str, dict[str, Any], list[str], list[dict]]:
    """Execute build-intent-research mode."""
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metrics = {"started_at": started_at, "source_count": 0, "claim_count": 0, "finding_count": 0, "signal_count": 0, "build_intent_count": 0}
    artifacts: list[str] = []
    breaches: list[dict] = []

    # First run refresh to collect evidence
    status, metrics, artifacts, breaches = run_refresh(vault_dir, config_dir, schemas, collectors_path)

    # Then evaluate if evidence supports a build intent
    findings_ledger = Ledger(vault_dir / "knowledge" / "findings.jsonl")
    findings = findings_ledger.read_all()

    high_confidence = [f for f in findings if f.get("confidence") in ("high", "medium")]
    if len(high_confidence) >= 2:
        build_intent = {
            "intent_id": str(__import__("uuid").uuid4()),
            "objective": objective or "Auto-generated from research findings",
            "evidence_findings": [f["finding_id"] for f in high_confidence[:5]],
            "confidence": "medium" if any(f["confidence"] == "high" for f in high_confidence) else "low",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        handoff_dir = vault_dir / "output" / "handoff-candidates"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_path = handoff_dir / f"build-intent-{build_intent['intent_id'][:8]}.json"
        with open(handoff_path, "w", encoding="utf-8") as f:
            json.dump(build_intent, f, indent=2)
        artifacts.append(str(handoff_path))
        metrics["build_intent_count"] = 1

    return status, metrics, artifacts, breaches


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    config_dir = args.config_dir.resolve()

    print(f"Running research-openclaw in mode: {args.mode}")

    schemas = SchemaManager()
    collectors_path = args.collectors_config if args.collectors_config else config_dir / "collectors.yaml"

    if args.mode == "bootstrap":
        status, metrics, artifacts, breaches = run_bootstrap(vault_dir, config_dir, schemas, collectors_path)
    elif args.mode == "refresh":
        status, metrics, artifacts, breaches = run_refresh(vault_dir, config_dir, schemas, collectors_path)
    elif args.mode == "targeted-query":
        status, metrics, artifacts, breaches = run_targeted_query(
            vault_dir, config_dir, schemas, collectors_path, args.objective
        )
    elif args.mode == "build-intent-research":
        status, metrics, artifacts, breaches = run_build_intent_research(
            vault_dir, config_dir, schemas, collectors_path, args.objective
        )
    else:
        print(f"Unknown mode: {args.mode}")
        return 1

    run_id = str(__import__("uuid").uuid4())
    write_receipt(
        vault_dir, run_id, args.mode, status, metrics, artifacts, breaches,
        step="" if status == "completed" else "unknown"
    )

    print(f"Run {run_id}: {status}")
    print(f"  Sources: {metrics['source_count']}")
    print(f"  Claims: {metrics['claim_count']}")
    print(f"  Findings: {metrics['finding_count']}")
    print(f"  Signals: {metrics['signal_count']}")
    print(f"  Build intents: {metrics['build_intent_count']}")

    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
