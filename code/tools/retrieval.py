"""
Retrieval tool: retrieve_evidence(query_text, user_id, sender_user_id, group_id, business_id, top_k) -> dict

Returns relevant historical messages as evidence using BM25 ranking + Cross-Encoder reranking.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, Optional, List

import pandas as pd
import numpy as np
from rank_bm25 import BM25Okapi

from code.data.loader import get_loader

logger = logging.getLogger(__name__)

# Global CrossEncoder instance (loaded once)
_cross_encoder = None


def _get_cross_encoder():
    """Load CrossEncoder model lazily and cache it."""
    global _cross_encoder
    # Disabled for Render Free Tier to prevent OOM crash
    _cross_encoder = False
    return _cross_encoder


def tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25."""
    if not text or pd.isna(text):
        return []
    text = str(text).lower()
    # Keep alphanumeric and spaces
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def retrieve_evidence(
    query_text: str,
    user_id: str,
    sender_user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    business_id: Optional[str] = None,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Retrieve relevant historical messages as evidence using BM25 similarity search + Cross-Encoder reranking.

    Args:
        query_text: Text to search for similar historical messages
        user_id: User ID to search history for
        sender_user_id: Optional sender user ID to filter by
        group_id: Optional group ID to filter by
        business_id: Optional business ID to filter by
        top_k: Number of top results to return

    Returns:
        Dict with keys: evidence (list of dicts), pattern_summary (str)
    """
    loader = get_loader()

    # Get user's message history
    history = loader.get_message_history(user_id)
    if not history:
        return {
            "evidence": [],
            "pattern_summary": "No message history available for this user."
        }

    # Filter by context - first pass: sender/group/business
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

    # Second pass: if no results with strict filter, broaden to user_id only
    if not filtered:
        logger.info(f"No messages matched strict filter for user {user_id}, broadening to user-only search")
        filtered = [msg for msg in history if msg.get("user_id") == user_id]

    if not filtered:
        return {
            "evidence": [],
            "pattern_summary": "No historical messages match the context (even broad user-only search)."
        }

    # Prepare corpus for BM25
    corpus = []
    message_ids = []
    full_texts = []  # Store full texts for CrossEncoder
    for msg in filtered:
        text = msg.get("message_text", "")
        if pd.notna(text) and text.strip():
            corpus.append(tokenize(text))
            message_ids.append(msg["message_id"])
            full_texts.append(str(text))
        else:
            # Include messages with empty text (voice-only) with empty token list
            # They'll get score 0 from BM25 but might be relevant for other signals
            corpus.append([])
            message_ids.append(msg["message_id"])
            full_texts.append("")

    if not any(corpus):  # All empty
        return {
            "evidence": [],
            "pattern_summary": "No text content in matching historical messages."
        }

    # BM25 scoring
    bm25 = BM25Okapi(corpus)
    query_tokens = tokenize(query_text)
    scores = bm25.get_scores(query_tokens)

    # Get top candidates for reranking (take more for reranking pool)
    # Use min(20, len(scores)) to get a good pool for cross-encoder
    rerank_pool_size = min(20, len(scores))
    top_indices = np.argsort(scores)[::-1][:rerank_pool_size]

    ce_scores = None
    # Cross-Encoder reranking if available
    cross_encoder = _get_cross_encoder()
    if cross_encoder and cross_encoder is not False:
        try:
            # Prepare pairs for cross-encoder
            pairs = [[query_text, full_texts[idx]] for idx in top_indices]
            # Get cross-encoder scores
            ce_scores = cross_encoder.predict(pairs)
            # Sort by cross-encoder score
            reranked_indices = np.argsort(ce_scores)[::-1]
            # Map back to original indices
            final_indices = [top_indices[i] for i in reranked_indices]
        except Exception as e:
            logger.warning(f"CrossEncoder reranking failed, using BM25 order: {e}")
            final_indices = top_indices
    else:
        final_indices = top_indices

    # Build evidence from top reranked results (take top_k, but include all with score > 0)
    evidence = []
    for idx in final_indices:
        # Include if BM25 score > 0 OR if we have fewer than top_k results with positive score
        if scores[idx] <= 0 and len(evidence) >= top_k:
            continue
        msg_id = message_ids[idx]
        msg = next((m for m in filtered if m["message_id"] == msg_id), None)
        if not msg:
            continue

        # Get user reaction event
        event = loader.get_message_event(msg_id)
        reaction = {}
        if event:
            reaction = {
                "message_opened": int(event.get("message_opened", 0)),
                "message_replied": int(event.get("message_replied", 0)),
                "reaction_time_minutes": float(event.get("reaction_time_minutes", 0)) if pd.notna(event.get("reaction_time_minutes")) else None,
                "notification_dismissed": int(event.get("notification_dismissed", 0)),
                "muted_after_message": int(event.get("muted_after_message", 0)),
                "message_reported": int(event.get("message_reported", 0)),
            }

        # Calculate days ago
        days_ago = 0
        try:
            created = pd.to_datetime(msg.get("created_at"))
            now = pd.Timestamp.now()
            days_ago = (now - created).days
        except Exception:
            pass

        evidence.append({
            "message_id": msg_id,
            "text_preview": str(msg.get("message_text", ""))[:200],
            "similarity": float(scores[idx]),
            "cross_encoder_score": float(ce_scores[np.where(top_indices == idx)[0][0]]) if cross_encoder and cross_encoder is not False and ce_scores is not None and idx in top_indices else None,
            "reaction": reaction,
            "days_ago": days_ago,
            "conversation_type": msg.get("conversation_type", ""),
            "sender_user_id": msg.get("sender_user_id", ""),
            "group_id": msg.get("group_id", ""),
            "business_id": msg.get("business_id", ""),
        })

    # Take top 1-2 after reaction analysis
    evidence = evidence[:2]

    # Build pattern summary
    if evidence:
        opened = sum(1 for e in evidence if e["reaction"].get("message_opened", 0) == 1)
        dismissed = sum(1 for e in evidence if e["reaction"].get("notification_dismissed", 0) == 1)
        reported = sum(1 for e in evidence if e["reaction"].get("message_reported", 0) == 1)
        pattern_summary = (
            f"Found {len(evidence)} relevant historical message(s). "
            f"User opened {opened}, dismissed {dismissed}, reported {reported}."
        )
    else:
        pattern_summary = "No relevant historical messages found with positive similarity."

    return {
        "evidence": evidence,
        "pattern_summary": pattern_summary
    }