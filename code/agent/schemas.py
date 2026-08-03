"""
Pydantic schemas for the WhatsApp Message Notification Router.

This module defines the canonical output schema as specified in CLAUDE.md.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class RoutingDecision(BaseModel):
    """
    Final routing decision for a WhatsApp message.

    Fields match the required output.csv columns in exact order:
    message_id, action, message_type, reason, confidence, evidence_message_ids
    """
    message_id: str
    action: Literal["notify", "digest", "mute"]
    message_type: Literal[
        "personal", "urgent", "event", "payment", "business_update",
        "promotion", "greeting", "forward", "spam", "scam", "unknown"
    ]
    reason: str = Field(..., min_length=10, max_length=300)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_message_ids: str  # semicolon-separated message IDs or "none"

    @field_validator("evidence_message_ids")
    @classmethod
    def validate_evidence(cls, v: str) -> str:
        """Normalize evidence message IDs: lowercase 'none' -> 'none', trim semicolons."""
        v = v.strip()
        if v.lower() == "none":
            return "none"
        parts = [p.strip() for p in v.split(";") if p.strip()]
        if not parts:
            return "none"
        return ";".join(parts)

    @field_validator("reason")
    @classmethod
    def validate_reason_not_generic(cls, v: str) -> str:
        """Reject generic reasons that don't cite specific signals."""
        generic_phrases = [
            "this is a message",
            "based on the content",
            "the message should be",
            "based on the message",
            "this message is",
            "the content indicates",
        ]
        v_lower = v.lower()
        if any(g in v_lower for g in generic_phrases):
            raise ValueError("Reason too generic. Must cite specific signals.")
        return v


# Safe fallback for validation failures (from CLAUDE.md)
SAFE_FALLBACK = {
    "action": "digest",
    "message_type": "unknown",
    "reason": "Unable to determine routing with sufficient confidence. Defaulting to digest for manual review.",
    "confidence": 0.3,
    "evidence_message_ids": "none"
}


# Output column order (must match exactly)
OUTPUT_COLUMNS = [
    "message_id",
    "action",
    "message_type",
    "reason",
    "confidence",
    "evidence_message_ids",
]

# Allowed values for validation
ALLOWED_ACTIONS = {"notify", "digest", "mute"}
ALLOWED_MESSAGE_TYPES = {
    "personal", "urgent", "event", "payment", "business_update",
    "promotion", "greeting", "forward", "spam", "scam", "unknown"
}


# Tool function schemas for the agent
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_context",
            "description": "Get contextual information for a message including user preferences, group info, business info, and user-business history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The message ID to get context for"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_evidence",
            "description": "Retrieve relevant historical messages as evidence using BM25 similarity search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "Text to search for similar historical messages"},
                    "user_id": {"type": "string", "description": "User ID to search history for"},
                    "sender_user_id": {"type": "string", "description": "Optional sender user ID to filter by"},
                    "group_id": {"type": "string", "description": "Optional group ID to filter by"},
                    "business_id": {"type": "string", "description": "Optional business ID to filter by"},
                    "top_k": {"type": "integer", "description": "Number of top results to return", "default": 3}
                },
                "required": ["query_text", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze image content using NVIDIA NIM Vision model. Returns content type, extracted text, risk signals, and description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_id": {"type": "string", "description": "Image media ID to analyze"}
                },
                "required": ["media_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_voice",
            "description": "Transcribe voice note using Groq Whisper Large v3 Turbo. Returns transcription, language, and duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_id": {"type": "string", "description": "Voice note media ID to transcribe"}
                },
                "required": ["media_id"]
            }
        }
    }
]