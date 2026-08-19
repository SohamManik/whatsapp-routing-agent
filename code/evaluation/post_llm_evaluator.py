"""
Post-LLM Evaluation Layer: Deterministic overrides after LLM proposes a decision.

This module implements the evaluation rules specified in the task:
1. MUTED GROUP ENFORCEMENT
2. SCAM ESCALATION
3. SCAM FROM HISTORY
4. HEALTHCARE EVENT CORRECTION
5. OPTED-OUT PROMOTION ENFORCEMENT
6. CONFIDENCE CALIBRATION
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

import pandas as pd

from code.agent.schemas import RoutingDecision
from code.data.loader import get_loader

logger = logging.getLogger(__name__)


def _has_direct_mention(message_text: str, user_id: str) -> bool:
    """Check if message contains a direct @mention of the user_id."""
    if not message_text or pd.isna(message_text):
        return False
    text = str(message_text).lower()
    # Look for @user_id pattern or @Soham (since we hardcoded Soham for the demo)
    user_id_lower = str(user_id).lower() if user_id else ""
    return f"@{user_id_lower}" in text or f"@ {user_id_lower}" in text or "@soham" in text or "@ soham" in text


def _check_gate_5_weighted_score(user_id: str, sender_user_id: Optional[str],
                                  group_id: Optional[str], business_id: Optional[str]) -> Dict[str, Any]:
    """
    Compute Gate 5 weighted score and details.
    Returns dict with: weighted_score, majority_reported (bool), details
    """
    loader = get_loader()
    history = loader.get_message_history(user_id)
    if not history:
        return {"weighted_score": 0, "majority_reported": False, "details": []}

    filtered = []
    for msg in history:
        match = True
        if sender_user_id and msg.get("sender_user_id") != sender_user_id:
            match = False
        if group_id and msg.get("group_id") != group_id:
            match = False
        if business_id and msg.get("business_id") != business_id:
            match = False
        if match:
            filtered.append(msg)

    if not filtered:
        return {"weighted_score": 0, "majority_reported": False, "details": []}

    weighted_score = 0
    reported_count = 0
    dismissed_count = 0
    muted_count = 0
    negative_details = []

    for msg in filtered:
        event = loader.get_message_event(msg.get("message_id", ""))
        if event:
            dismissed = int(event.get("notification_dismissed", 0))
            muted = int(event.get("muted_after_message", 0))
            reported = int(event.get("message_reported", 0))

            msg_score = 0
            if reported:
                msg_score += 3
                reported_count += 1
            if muted:
                msg_score += 3
                muted_count += 1
            if dismissed:
                msg_score += 1
                dismissed_count += 1

            if msg_score > 0:
                weighted_score += msg_score
                parts = []
                if reported:
                    parts.append(f"reported({reported})")
                if muted:
                    parts.append(f"muted({muted})")
                if dismissed:
                    parts.append(f"dismissed({dismissed})")
                negative_details.append(f"msg {msg.get('message_id')}: {', '.join(parts)}")

    total_negative = reported_count + muted_count + dismissed_count
    # Majority reported means reported signals are the dominant or co-dominant negative signal
    # (reported >= dismissed and reported >= muted) - reported is at least tied for most frequent
    majority_reported = reported_count >= dismissed_count and reported_count >= muted_count if total_negative > 0 else False

    return {
        "weighted_score": weighted_score,
        "majority_reported": majority_reported,
        "details": negative_details,
    }


def evaluate_decision(
    decision: RoutingDecision,
    message_row: Dict[str, Any],
    context: Dict[str, Any]
) -> RoutingDecision:
    """
    Post-LLM deterministic override layer. Only overrides when confident.

    Rules applied in priority order:
    1. MUTED GROUP ENFORCEMENT
    2. SCAM ESCALATION
    3. SCAM FROM HISTORY
    4. HEALTHCARE EVENT CORRECTION
    5. OPTED-OUT PROMOTION ENFORCEMENT
    6. CONFIDENCE CALIBRATION
    """
    original_action = decision.action
    original_type = decision.message_type
    original_reason = decision.reason
    original_confidence = decision.confidence
    original_evidence = decision.evidence_message_ids

    # Create mutable copies
    action = decision.action
    message_type = decision.message_type
    reason = decision.reason
    confidence = decision.confidence
    evidence = decision.evidence_message_ids

    user_id = message_row.get("user_id", "")
    message_text = message_row.get("message_text", "") or ""
    group_id = message_row.get("group_id", "") or None
    business_id = message_row.get("business_id", "") or None
    sender_user_id = message_row.get("sender_user_id", "") or None
    forwarded_count = int(message_row.get("forwarded_count", 0)) if pd.notna(message_row.get("forwarded_count")) else 0

    # Extract context components
    group_ctx = context.get("group") if context else None
    business_ctx = context.get("business") if context else None
    user_business_ctx = context.get("user_business") if context else None

    # ============================================================
    # Rule 1: MUTED GROUP ENFORCEMENT
    # ============================================================
    if group_ctx and group_ctx.get("group_muted_by_user", 0) == 1:
        has_mention = _has_direct_mention(message_text, user_id)
        if not has_mention and action != "mute":
            action = "mute"
            if len(reason) + 30 <= 300:
                reason = f"{reason} Override: user muted this group."
            logger.info(f"Post-LLM evaluator override for {decision.message_id}: Muted group enforcement -> action=mute")

    # ============================================================
    # Rule 2: SCAM ESCALATION
    # ============================================================
    if business_ctx:
        verified = business_ctx.get("verified", 0)
        user_reports = business_ctx.get("user_reports_30d", 0)
        account_age = business_ctx.get("account_age_days", 0)
        official_domain = business_ctx.get("official_domain", "")
        domain_used = business_ctx.get("domain_used_by_sender", "")

        # Handle NaN values
        if isinstance(official_domain, float) and pd.isna(official_domain):
            official_domain = ""
        if isinstance(domain_used, float) and pd.isna(domain_used):
            domain_used = ""
        official_domain = str(official_domain).strip()
        domain_used = str(domain_used).strip()

        domain_match = bool(official_domain and domain_used and official_domain.lower() == domain_used.lower())

        # Scam criteria: unverified + reports > 5 + age < 60 days + domain mismatch
        if verified == 0 and user_reports > 5 and account_age < 60 and not domain_match:
            if message_type == "spam":
                message_type = "scam"
                if len(reason) + 45 <= 300:
                    reason = f"{reason} Override: unverified business with scam signals."
                logger.info(f"Post-LLM evaluator override for {decision.message_id}: Scam escalation -> type=scam")

    # ============================================================
    # Rule 3: SCAM FROM HISTORY
    # ============================================================
    if sender_user_id or group_id or business_id:
        gate5_result = _check_gate_5_weighted_score(
            user_id, sender_user_id, group_id, business_id
        )
        weighted_score = gate5_result["weighted_score"]
        majority_reported = gate5_result["majority_reported"]

        if weighted_score >= 10 and majority_reported and message_type != "scam":
            message_type = "scam"
            if len(reason) + 45 <= 300:
                reason = f"{reason} Override: history shows repeated reported messages."
            logger.info(f"Post-LLM evaluator override for {decision.message_id}: Scam from history -> type=scam")

    # ============================================================
    # Rule 4: HEALTHCARE EVENT CORRECTION
    # ============================================================
    if business_ctx and business_ctx.get("category"):
        category = str(business_ctx.get("category", "")).lower()
        healthcare_keywords = ["health", "medical", "clinic", "hospital", "care"]
        is_healthcare = any(kw in category for kw in healthcare_keywords)

        if is_healthcare:
            event_keywords = ["camp", "screening", "vaccination", "checkup", "drive", "appointment"]
            text_lower = str(message_text).lower()
            mentions_event = any(kw in text_lower for kw in event_keywords)

            if mentions_event and message_type == "business_update":
                message_type = "event"
                if len(reason) + 35 <= 300:
                    reason = f"{reason} Override: healthcare event."
                logger.info(f"Post-LLM evaluator override for {decision.message_id}: Healthcare event correction -> type=event")

    # ============================================================
    # Rule 5: OPTED-OUT PROMOTION ENFORCEMENT
    # ============================================================
    if user_business_ctx and user_business_ctx.get("promotions_opted_out", False):
        if action != "mute":
            action = "mute"
            message_type = "promotion"
            if len(reason) + 40 <= 300:
                reason = f"{reason} Override: user opted out of promotions."
            logger.info(f"Post-LLM evaluator override for {decision.message_id}: Opted-out promotion enforcement -> mute/promotion")

    # ============================================================
    # Rule 6: CONFIDENCE CALIBRATION
    # ============================================================
    if confidence > 0.90 and (not evidence or evidence.lower() == "none"):
        confidence = min(confidence, 0.80)
        if len(reason) + 35 <= 300:
            reason = f"{reason} Override: confidence capped (no evidence)."
        logger.info(f"Post-LLM evaluator override for {decision.message_id}: Confidence calibration -> {confidence:.2f}")

    # Check if any override occurred
    if (action != original_action or
        message_type != original_type or
        reason != original_reason or
        confidence != original_confidence):
        logger.info(
            f"Post-LLM evaluator override for {decision.message_id}: "
            f"action={original_action}->{action}, type={original_type}->{message_type}, "
            f"conf={original_confidence:.2f}->{confidence:.2f}"
        )

    # Ensure reason length is within bounds
    if len(reason) > 300:
        reason = reason[:297] + "..."

    return RoutingDecision(
        message_id=decision.message_id,
        action=action,
        message_type=message_type,
        reason=reason,
        confidence=confidence,
        evidence_message_ids=evidence,
    )