"""
Agent core: multi-turn tool-calling loop for message routing.
"""

from __future__ import annotations

import json
import logging
import os
import time
import pandas as pd
from typing import Dict, Any, List, Optional

import requests
from dotenv import load_dotenv

from code.agent.schemas import RoutingDecision, SAFE_FALLBACK, TOOLS
from code.agent.prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES, build_user_prompt
from code.tools.context import get_context
from code.tools.retrieval import retrieve_evidence
from code.tools.vision import analyze_image
from code.tools.audio import transcribe_voice
from code.safety.gates import run_all_safety_gates, GateResult
from code.data.loader import get_loader
from code.evaluation.post_llm_evaluator import evaluate_decision
from pydantic import ValidationError

load_dotenv()

logger = logging.getLogger(__name__)

def _is_empty(val) -> bool:
    """Check if a value is None, NaN, or empty string. Safe for both pandas and JSON data."""
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False

def _save_trace(message_id: str, step_order: int, step_type: str, data: dict):
    """Persist a reasoning step to the database."""
    try:
        from code.db.database import SessionLocal
        from code.db.models import ReasoningTrace
        import json
        from datetime import datetime
        db = SessionLocal()
        trace = ReasoningTrace(
            message_id=message_id,
            step_order=step_order,
            step_type=step_type,
            data=json.dumps(data),
            created_at=datetime.now().isoformat()
        )
        db.add(trace)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to save trace: {e}")

# NVIDIA NIM API for Nemotron 3 Ultra
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NEMOTRON_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
NEMOTRON_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Tool function mapping
TOOL_FUNCTIONS = {
    "get_context": get_context,
    "retrieve_evidence": retrieve_evidence,
    "analyze_image": analyze_image,
    "transcribe_voice": transcribe_voice,
}


def call_nemotron(messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Call Nemotron 3 Ultra via NVIDIA NIM API with retry logic."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": NEMOTRON_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    # Enforce base rate limit for EVERY API call (40 RPM = 1.5s per call)
    time.sleep(1.5)

    # Retry with exponential backoff
    max_retries = 6  # Increased to 6 to handle deep 429 spikes
    base_delay = 3  # seconds
    for attempt in range(max_retries):
        try:
            response = requests.post(NEMOTRON_URL, json=payload, headers=headers, timeout=60)
            if response.status_code in [429, 503]:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Nemotron {response.status_code}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Nemotron timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Nemotron error: {e}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise

    # Should not reach here, but just in case
    raise Exception("Max retries exceeded for Nemotron API")


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call and return the result."""
    if tool_name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        func = TOOL_FUNCTIONS[tool_name]
        result = func(**arguments)
        return result
    except Exception as e:
        logger.error(f"Tool {tool_name} error: {e}")
        return {"error": str(e)}


def run_agent_for_message(message_row: dict, event_callback=None) -> RoutingDecision:
    """Run the multi-turn agent loop for a single message."""
    step_counter = [0]
    original_callback = event_callback

    def traced_callback(event_type: str, data: dict):
        step_counter[0] += 1
        _save_trace(message_row.get("message_id", ""), step_counter[0], event_type, data)
        if original_callback:
            original_callback(event_type, data)

    event_callback = traced_callback
    message_id = message_row["message_id"]
    user_id = message_row["user_id"]
    message_text = message_row.get("message_text", "") or ""
    media_type = message_row.get("media_type", "") or ""
    media_id = message_row.get("media_id", "") or ""
    sender_user_id = message_row.get("sender_user_id", "") or None
    group_id = message_row.get("group_id", "") or None
    business_id = message_row.get("business_id", "") or None

    # Check safety gates first (pre-LLM)
    gate_result = run_all_safety_gates(
        message_text=message_text if not _is_empty(message_text) else "",
        user_id=user_id,
        sender_user_id=sender_user_id if sender_user_id and not _is_empty(sender_user_id) else None,
        group_id=group_id if group_id and not _is_empty(group_id) else None,
        business_id=business_id if business_id and not _is_empty(business_id) else None,
        forwarded_count=int(message_row.get("forwarded_count", 0)) if not _is_empty(message_row.get("forwarded_count")) else 0,
        conversation_type=message_row.get("conversation_type", "") or "",
    )

    if gate_result:
        logger.info(f"Safety gate triggered for {message_id}: {gate_result.message_type}")
        if event_callback:
            event_callback("gate_triggered", {"gate": gate_result.message_type, "action": gate_result.action, "reason": gate_result.reason})
        return RoutingDecision(
            message_id=message_id,
            action=gate_result.action,
            message_type=gate_result.message_type,
            reason=gate_result.reason,
            confidence=gate_result.confidence,
            evidence_message_ids="none",
        )

    # Build initial messages with few-shot examples
    few_shot_text = ""
    for ex in FEW_SHOT_EXAMPLES:  # Use ALL examples for better pattern matching
        few_shot_text += f"\nExample:\nMessage: {ex['message'][:200]}...\nContext: {ex['context']}\nDecision: {json.dumps(ex['decision'], separators=(',', ':'))}\n"

    user_prompt = build_user_prompt(message_row)
    full_prompt = f"{user_prompt}\n\nHere are some examples:\n{few_shot_text}\n\nNow analyze this message and provide your routing decision as JSON."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": full_prompt},
    ]

    # Multi-turn tool calling loop
    max_turns = 4
    for turn in range(max_turns):
        logger.info(f"Message {message_id}: Turn {turn + 1}")

        try:
            response = call_nemotron(messages, TOOLS)
        except Exception as e:
            logger.error(f"Nemotron API error for {message_id}: {e}")
            # Return fallback on API failure
            return RoutingDecision(
                message_id=message_id,
                **SAFE_FALLBACK
            )

        choice = response["choices"][0]
        message = choice["message"]

        # Add assistant message to history
        messages.append(message)

        # Check for tool calls
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            # No tool calls - check if we have a valid decision
            content = message.get("content", "")
            try:
                decision_data = json.loads(content)
                return _validate_with_retry(decision_data, message_id, message_row, messages, max_retries=1)
            except json.JSONDecodeError:
                # Try to extract JSON from content
                try:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        decision_data = json.loads(content[start:end])
                        return _validate_with_retry(decision_data, message_id, message_row, messages, max_retries=1)
                except Exception:
                    pass
                # If we can't parse, continue the loop to let the model try again
                logger.warning(f"Could not parse decision from: {content[:200]}")
                # Add a nudge to output JSON
                messages.append({
                    "role": "user",
                    "content": "Your response was not valid JSON. Please output ONLY the final RoutingDecision JSON object with these exact fields: message_id, action (notify/digest/mute), message_type (personal/urgent/event/payment/business_update/promotion/greeting/forward/spam/scam/unknown), reason (10-300 chars citing specific signals), confidence (0.0-1.0), evidence_message_ids (semicolon-separated or 'none'). No extra text."
                })
                continue

        # Execute tool calls
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            logger.info(f"Calling tool: {func_name} with {func_args}")
            if event_callback:
                event_callback("tool_call", {"tool": func_name, "args": func_args})
            result = execute_tool_call(func_name, func_args)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": func_name,
                "content": json.dumps(result),
            })

    # Max turns reached - one final attempt without tools
    logger.warning(f"Max turns reached for {message_id}, final attempt without tools")
    try:
        final_response = call_nemotron(messages + [{"role": "user", "content": "Output ONLY the final RoutingDecision JSON now."}], tools=None)
        final_content = final_response["choices"][0]["message"]["content"]
        decision_data = json.loads(final_content)
        return _validate_with_retry(decision_data, message_id, message_row, messages, max_retries=1)
    except Exception as e:
        logger.error(f"Final attempt failed for {message_id}: {e}")
        # Use smart fallback but still apply post-LLM evaluation
        fallback = _smart_fallback(message_id, message_row)
        loader = get_loader()
        context = loader.get_message_context(message_row)
        return evaluate_decision(fallback, message_row, context)


def _validate_with_retry(
    decision_data: dict,
    message_id: str,
    message_row: dict,
    messages: list,
    max_retries: int = 1
) -> RoutingDecision:
    """Validate decision with Pydantic, retry on failure by feeding error back to LLM."""
    # Remove message_id from decision_data if present (will be passed as kwarg)
    decision_data.pop("message_id", None)
    for attempt in range(max_retries):
        try:
            decision = RoutingDecision(message_id=message_id, **decision_data)

            # Post-LLM evaluation: apply deterministic overrides
            # Build context directly from message_row to handle sample messages
            loader = get_loader()
            context = loader.get_message_context(message_row)
            evaluated_decision = evaluate_decision(decision, message_row, context)
            return evaluated_decision
        except ValidationError as e:
            error_msgs = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_msgs.append(f"{field}: {msg}")
            error_text = "; ".join(error_msgs)
            logger.warning(f"Validation failed for {message_id} (attempt {attempt + 1}/{max_retries}): {error_text}")

            if attempt < max_retries - 1:
                # Feed error back to LLM and ask to fix
                messages.append({
                    "role": "user",
                    "content": f"Your previous JSON failed validation: {error_text}. Please fix and output ONLY the corrected RoutingDecision JSON."
                })
                try:
                    retry_response = call_nemotron(messages, tools=None)
                    retry_content = retry_response["choices"][0]["message"]["content"]
                    decision_data = json.loads(retry_content)
                    decision_data.pop("message_id", None)
                    messages.append({"role": "assistant", "content": retry_content})
                except Exception as retry_e:
                    logger.error(f"Retry attempt failed: {retry_e}")
                    continue
            else:
                logger.error(f"All validation retries exhausted for {message_id}")
    # All retries failed - use smart fallback
    return _smart_fallback(message_id, message_row)


def _smart_fallback(message_id: str, message_row: dict) -> RoutingDecision:
    """Smart fallback based on context instead of generic SAFE_FALLBACK."""
    group_id = message_row.get("group_id")
    business_id = message_row.get("business_id")
    conversation_type = message_row.get("conversation_type", "")
    forwarded_count = int(message_row.get("forwarded_count", 0)) if not _is_empty(message_row.get("forwarded_count")) else 0
    message_text = str(message_row.get("message_text", "")).lower()
    sender_user_id = message_row.get("sender_user_id", "")
    user_id = message_row.get("user_id", "")

    # Get group mute status
    loader = get_loader()
    group_muted = 0
    if not _is_empty(group_id) and group_id:
        member = loader.get_group_member(group_id, message_row["user_id"])
        if member:
            group_muted = int(member.get("group_muted_by_user", 0))

    # Check business verification
    biz_unverified = False
    if not _is_empty(business_id) and business_id:
        biz = loader.get_business(business_id)
        if biz and int(biz.get("verified", 0)) == 0:
            biz_unverified = True

    # Rule 1: If user muted the group -> mute
    if group_muted == 1:
        return RoutingDecision(
            message_id=message_id,
            action="mute",
            message_type="greeting" if "good morning" in message_text or "blessing" in message_text else "forward" if forwarded_count > 3 else "spam",
            reason=f"User muted this group; fallback triggered after validation failures.",
            confidence=0.45,
            evidence_message_ids="none",
        )

    # Rule 2: Business message from unverified business -> mute/spam
    if biz_unverified and conversation_type == "business":
        return RoutingDecision(
            message_id=message_id,
            action="mute",
            message_type="spam",
            reason=f"Unverified business sender; fallback triggered after validation failures.",
            confidence=0.45,
            evidence_message_ids="none",
        )

    # Rule 3: Direct @mention -> notify
    message_text_lower = message_text.lower()
    if f"@{user_id}" in message_text_lower or f"@ {user_id}" in message_text_lower or "@vivek" in message_text_lower or "@ vivek" in message_text_lower:
        # Check if urgent keywords
        urgent_keywords = ["urgent", "now", "immediately", "asap", "emergency", "critical", "call now", "reply now"]
        if any(kw in message_text for kw in urgent_keywords):
            return RoutingDecision(
                message_id=message_id,
                action="notify",
                message_type="urgent",
                reason=f"Direct @mention with urgent language; fallback after validation failures.",
                confidence=0.65,
                evidence_message_ids="none",
            )
        else:
            return RoutingDecision(
                message_id=message_id,
                action="notify",
                message_type="personal",
                reason=f"Direct @mention requiring response; fallback after validation failures.",
                confidence=0.65,
                evidence_message_ids="none",
            )

    # Rule 4: Personal conversation with urgent keywords
    if conversation_type == "personal":
        urgent_keywords = ["urgent", "now", "immediately", "asap", "emergency", "critical", "call now", "reply now", "escalation", "retry", "threshold"]
        if any(kw in message_text for kw in urgent_keywords):
            return RoutingDecision(
                message_id=message_id,
                action="notify",
                message_type="urgent",
                reason=f"Personal message with urgent keywords; fallback after validation failures.",
                confidence=0.65,
                evidence_message_ids="none",
            )
        return RoutingDecision(
            message_id=message_id,
            action="digest",
            message_type="personal",
            reason=f"Personal message without urgency; fallback after validation failures.",
            confidence=0.55,
            evidence_message_ids="none",
        )

    # Rule 5: Group message - check for event/greeting/forward patterns
    if conversation_type == "group":
        greeting_patterns = ["good morning", "good evening", "good night", "blessing", "stay positive", "share blessings", "good vibes", "peaceful", "have a nice day"]
        if any(p in message_text for p in greeting_patterns):
            return RoutingDecision(
                message_id=message_id,
                action="digest" if not group_muted else "mute",
                message_type="greeting",
                reason=f"Group greeting; fallback after validation failures.",
                confidence=0.55,
                evidence_message_ids="none",
            )

        if forwarded_count > 3 or "forward" in message_text or "fwd" in message_text or "fwd as received" in message_text:
            return RoutingDecision(
                message_id=message_id,
                action="mute",
                message_type="forward",
                reason=f"Forwarded chain message; fallback after validation failures.",
                confidence=0.60,
                evidence_message_ids="none",
            )

        event_keywords = ["meeting", "event", "schedule", "deadline", "consent", "form", "registration", "cultural", "trip", "outing"]
        if any(kw in message_text for kw in event_keywords):
            return RoutingDecision(
                message_id=message_id,
                action="digest",
                message_type="event",
                reason=f"Group event announcement; fallback after validation failures.",
                confidence=0.55,
                evidence_message_ids="none",
            )

    # Rule 6: Default to digest/unknown as last resort
    return RoutingDecision(
        message_id=message_id,
        **SAFE_FALLBACK
    )