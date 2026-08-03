"""
Output validation and CSV writing module.
"""

from __future__ import annotations

import csv
import logging
from typing import List, Dict, Any, Set
from pathlib import Path

import pandas as pd

from code.agent.schemas import (
    RoutingDecision,
    OUTPUT_COLUMNS,
    ALLOWED_ACTIONS,
    ALLOWED_MESSAGE_TYPES,
    SAFE_FALLBACK,
)

logger = logging.getLogger(__name__)


def validate_decision(decision: RoutingDecision) -> List[str]:
    """Validate a routing decision. Returns list of error messages (empty if valid)."""
    errors = []

    # Check action
    if decision.action not in ALLOWED_ACTIONS:
        errors.append(f"Invalid action: {decision.action}")

    # Check message_type
    if decision.message_type not in ALLOWED_MESSAGE_TYPES:
        errors.append(f"Invalid message_type: {decision.message_type}")

    # Check reason length
    if len(decision.reason) < 10:
        errors.append("Reason too short (min 10 chars)")
    if len(decision.reason) > 300:
        errors.append(f"Reason too long: {len(decision.reason)} chars (max 300)")

    # Check confidence range
    if not (0.0 <= decision.confidence <= 1.0):
        errors.append(f"Confidence out of range: {decision.confidence}")

    # Check evidence format
    evidence = decision.evidence_message_ids
    if evidence.lower() != "none":
        parts = [p.strip() for p in evidence.split(";") if p.strip()]
        for part in parts:
            if not (part.startswith("message_") or part.startswith("sample_msg_")):
                errors.append(f"Evidence ID format suspicious: {part}")

    return errors


def validate_all_decisions(decisions: List[RoutingDecision], expected_message_ids: List[str]) -> Dict[str, Any]:
    """Validate all decisions for completeness and correctness."""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "message_id_set": set(),
        "duplicate_ids": [],
        "missing_ids": [],
        "extra_ids": [],
    }

    # Check for duplicates
    seen: Set[str] = set()
    for d in decisions:
        if d.message_id in seen:
            results["duplicate_ids"].append(d.message_id)
        seen.add(d.message_id)

    results["message_id_set"] = seen

    # Check against expected
    expected_set = set(expected_message_ids)
    results["missing_ids"] = list(expected_set - seen)
    results["extra_ids"] = list(seen - expected_set)

    if results["missing_ids"]:
        results["valid"] = False
        results["errors"].append(f"Missing message_ids: {results['missing_ids']}")

    if results["extra_ids"]:
        results["valid"] = False
        results["errors"].append(f"Extra message_ids: {results['extra_ids']}")

    if results["duplicate_ids"]:
        results["valid"] = False
        results["errors"].append(f"Duplicate message_ids: {results['duplicate_ids']}")

    # Validate each decision
    for d in decisions:
        errors = validate_decision(d)
        if errors:
            results["valid"] = False
            results["errors"].append(f"{d.message_id}: {'; '.join(errors)}")

    return results


def write_output_csv(decisions: List[RoutingDecision], output_path: Path) -> None:
    """Write decisions to output CSV in the required format."""
    # Sort by original message order
    loader = __import__("code.data.loader", fromlist=["get_loader"]).get_loader()
    message_order = {mid: i for i, mid in enumerate(loader.messages["message_id"].tolist())}

    sorted_decisions = sorted(decisions, key=lambda d: message_order.get(d.message_id, 999999))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for d in sorted_decisions:
            writer.writerow(d.model_dump())

    logger.info(f"Wrote {len(decisions)} decisions to {output_path}")