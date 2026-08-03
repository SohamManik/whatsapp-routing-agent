"""
Deterministic safety gates that run before the LLM.

These gates catch prompt injections, scams, opt-outs, and repeated negative history.
"""

from __future__ import annotations

import re
from typing import Optional
from dataclasses import dataclass

import pandas as pd

from code.data.loader import get_loader


@dataclass
class GateResult:
    """Result of a safety gate check."""
    triggered: bool
    action: str
    message_type: str
    reason: str
    confidence: float


# Gate 1: Prompt Injection Patterns
PROMPT_INJECTION_PATTERNS = [
    r"action\s*=\s*notify",
    r"mark\s+as\s+notify",
    r"classify\s+as\s+urgent",
    r"system\s+note",
    r"router\s+instruction",
    r"routing\s+override",
    r"assistant\s+instruction",
    r"ignore\s+sender\s+risk",
    r"internal\s+router\s+metadata",
    r"verified_business\s*=\s*true",
    r"user_priority\s*=\s*high",
    r"confidence\s*=\s*1",
]


# Gate 3: Scam Language Patterns
SCAM_PATTERNS_EN = [
    r"won\s+a\s+prize",
    r"share\s+otp",
    r"send\s+otp",
    r"confirm\s+your\s+pin",
    r"fill\s+bank\s+details",
    r"reactivation\s+fee",
    r"otp\s+verification\s+failed",
    r"verify\s+now",
    r"account\s+block",
    r"profile\s+block",
    r"login\s+code",
    r"wallet\s+verification",
    r"payment\s+verification",
    r"click\s+the\s+link",
    r"open\s+the\s+link",
    r"scan\s+qr",
    r"scan\s+and\s+pay",
    r"urgent.*verify",
    r"immediate.*action",
    r"expires\s+today",
    r"expires\s+tonight",
    r"today\s+only",
    r"limited\s+time",
    r"claim\s+now",
    r"congratulations.*reward",
    r"selected\s+for\s+voucher",
]

SCAM_PATTERNS_HI = [
    r"otp\s+batao",
    r"link\s+open\s+karo",
    r"block\s+ho\s+jayega",
    r"band\s+ho\s+jayega",
    r"code\s+daal\s+do",
    r"verification\s+code\s+abhi",
    r"account\s+bachane",
    r"profile\s+band",
    r"wallet\s+payments",
    r"kyc\s+incomplete",
    r"password\s+otp",
    r"verify\s+abhi",
    r"jaldi\s+karo",
    r"time\s+kam\s+hai",
]


def check_gate_1_prompt_injection(message_text: str) -> Optional[GateResult]:
    """Gate 1: Detect prompt injection attempts in message text."""
    if not message_text or pd.isna(message_text):
        return None
    text_lower = str(message_text).lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return GateResult(
                triggered=True,
                action="mute",
                message_type="scam",
                reason="Prompt injection detected: message attempts to override router behavior with system-level instructions.",
                confidence=0.93,
            )
    return None


def check_gate_2_business_scam(
    business_id: Optional[str],
    user_id: str,
    sender_user_id: Optional[str] = None
) -> Optional[GateResult]:
    """Gate 2: Detect business scams (unverified + high reports + young account + domain mismatch)."""
    if not business_id:
        return None

    loader = get_loader()
    business = loader.get_business(business_id)
    if not business:
        return None

    verified = int(business.get("verified", 0))
    user_reports = int(business.get("user_reports_30d", 0))
    account_age = int(business.get("account_age_days", 0))
    official_domain = str(business.get("official_domain", "")).strip()
    domain_used = str(business.get("domain_used_by_sender", "")).strip()

    # Handle NaN values
    if official_domain.lower() == "nan":
        official_domain = ""
    if domain_used.lower() == "nan":
        domain_used = ""

    domain_match = bool(official_domain and domain_used and official_domain.lower() == domain_used.lower())

    # Scam criteria: unverified + reports > 5 + age < 60 days + domain mismatch
    if verified == 0 and user_reports > 5 and account_age < 60 and not domain_match:
        return GateResult(
            triggered=True,
            action="mute",
            message_type="scam",
            reason=f"Unverified business ({business_id}) with {user_reports} reports, {account_age}-day-old account, and domain mismatch. Likely impersonator.",
            confidence=0.95,
        )
    return None


def check_gate_3_scam_language(message_text: str) -> Optional[GateResult]:
    """Gate 3: Detect scam language patterns in English and Hindi/Hinglish."""
    if not message_text or pd.isna(message_text):
        return None
    text_lower = str(message_text).lower()

    en_matches = sum(1 for p in SCAM_PATTERNS_EN if re.search(p, text_lower, re.IGNORECASE))
    hi_matches = sum(1 for p in SCAM_PATTERNS_HI if re.search(p, text_lower, re.IGNORECASE))

    # Trigger if 2+ EN patterns OR 2+ HI patterns OR 1+ each
    if en_matches >= 2 or hi_matches >= 2 or (en_matches >= 1 and hi_matches >= 1):
        return GateResult(
            triggered=True,
            action="mute",
            message_type="scam",
            reason=f"Scam language detected ({en_matches} EN patterns, {hi_matches} HI patterns). Message uses urgency, OTP requests, or account blocking pressure.",
            confidence=0.88,
        )
    return None


def check_gate_4_user_opt_out(user_id: str, business_id: Optional[str]) -> Optional[GateResult]:
    """Gate 4: Check if user has opted out of promotions from this business."""
    if not business_id:
        return None

    loader = get_loader()
    history = loader.get_user_business_history(user_id, business_id)
    if not history:
        return None

    opted_out_at = history.get("promotions_opted_out_at")
    if pd.notna(opted_out_at) and str(opted_out_at).strip() != "":
        return GateResult(
            triggered=True,
            action="mute",
            message_type="promotion",
            reason=f"User opted out of promotions from {business_id} on {opted_out_at}.",
            confidence=0.90,
        )
    return None


def check_gate_5_repeated_negative_history(
    user_id: str,
    sender_user_id: Optional[str],
    group_id: Optional[str],
    business_id: Optional[str],
    message_text: str = "",
    forwarded_count: int = 0,
    conversation_type: str = ""
) -> Optional[GateResult]:
    """Gate 5: Check for weighted negative reactions from same sender/context in 14 days.

    Weighted scoring: reported=3, muted_after_message=3, dismissed=1. Trigger at score >= 5.
    """
    loader = get_loader()

    history = loader.get_message_history(user_id)
    if not history:
        return None

    # Filter by context
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
        return None

    # Check events for negative reactions with weighted scoring
    weighted_score = 0
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
            if muted:
                msg_score += 3
            if dismissed:
                msg_score += 1

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

    if weighted_score >= 5:
        # Determine message_type based on CURRENT message content and context (not history)
        message_type = "spam"  # default
        reason_parts = [f"Weighted negative reaction score {weighted_score} (threshold 5) from recent messages"]

        # Check if scam patterns detected in CURRENT message (Gate 3 would have caught, but double-check)
        text_lower = str(message_text).lower() if message_text else ""
        en_scam = sum(1 for p in SCAM_PATTERNS_EN if re.search(p, text_lower, re.IGNORECASE))
        hi_scam = sum(1 for p in SCAM_PATTERNS_HI if re.search(p, text_lower, re.IGNORECASE))
        if en_scam >= 1 or hi_scam >= 1:
            message_type = "scam"
            reason_parts.append("; scam language in current message")

        # If business is unverified with high reports/young account (Gate 2), use "scam"
        elif business_id:
            biz = loader.get_business(business_id)
            if biz:
                verified = int(biz.get("verified", 0))
                reports = int(biz.get("user_reports_30d", 0))
                age = int(biz.get("account_age_days", 0))
                official = str(biz.get("official_domain", "")).strip()
                used = str(biz.get("domain_used_by_sender", "")).strip()
                # Handle NaN values
                if official.lower() == "nan":
                    official = ""
                if used.lower() == "nan":
                    used = ""
                domain_match = bool(official and used and official.lower() == used.lower())
                if verified == 0 and reports > 5 and age < 60 and not domain_match:
                    message_type = "scam"
                    reason_parts.append("; unverified business with scam signals")

        # If user opted out of promotions (Gate 4), use "promotion"
        elif business_id:
            hist = loader.get_user_business_history(user_id, business_id)
            if hist:
                opted_out = hist.get("promotions_opted_out_at")
                if pd.notna(opted_out) and str(opted_out).strip() != "":
                    message_type = "promotion"
                    reason_parts.append("; user opted out of promotions")

        # If no specific gate signal, infer from CURRENT message content and forwarded_count
        if message_type == "spam":
            # Check for greeting patterns in current message
            greeting_patterns = ["good morning", "good evening", "good night", "blessing", "stay positive", "share blessings", "good vibes", "peaceful"]
            if any(p in text_lower for p in greeting_patterns):
                message_type = "greeting"
                reason_parts.append("; greeting content in message")
            # Check for forward patterns
            elif forwarded_count > 3 or "forward" in text_lower or "fwd" in text_lower or "fwd as received" in text_lower:
                message_type = "forward"
                reason_parts.append("; forwarded message pattern")
            # Check conversation type
            elif conversation_type == "business":
                message_type = "promotion"
                reason_parts.append("; business conversation")
            elif conversation_type == "personal":
                message_type = "spam"
                reason_parts.append("; personal conversation")
            elif conversation_type == "group":
                # Default to greeting for groups if not clearly forward
                message_type = "greeting"
                reason_parts.append("; group message default")

        return GateResult(
            triggered=True,
            action="mute",
            message_type=message_type,
            reason=" ".join(reason_parts) + ". Details: " + "; ".join(negative_details[:3]),
            confidence=0.88,
        )
    return None


def run_all_safety_gates(
    message_text: str,
    user_id: str,
    sender_user_id: Optional[str],
    group_id: Optional[str],
    business_id: Optional[str],
    forwarded_count: int = 0,
    conversation_type: str = ""
) -> Optional[GateResult]:
    """Run all safety gates in order. Returns first triggered gate result or None."""
    # Handle NaN values
    if pd.isna(message_text):
        message_text = ""
    if sender_user_id and pd.isna(sender_user_id):
        sender_user_id = None
    if group_id and pd.isna(group_id):
        group_id = None
    if business_id and pd.isna(business_id):
        business_id = None
    # Also ensure strings
    message_text = str(message_text) if message_text else ""
    sender_user_id = str(sender_user_id) if sender_user_id else None
    group_id = str(group_id) if group_id else None
    business_id = str(business_id) if business_id else None
    conversation_type = str(conversation_type) if conversation_type else ""

    gates = [
        check_gate_1_prompt_injection(message_text),
        check_gate_2_business_scam(business_id, user_id, sender_user_id),
        check_gate_3_scam_language(message_text),
        check_gate_4_user_opt_out(user_id, business_id),
        check_gate_5_repeated_negative_history(user_id, sender_user_id, group_id, business_id, message_text, forwarded_count, conversation_type),
    ]

    for gate_result in gates:
        if gate_result and gate_result.triggered:
            return gate_result
    return None