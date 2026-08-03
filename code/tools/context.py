"""
Context tool: get_context(message_id) -> dict

Returns contextual information for a message including:
- User preferences and DND status
- Group info and user's role/mute status
- Business account info and verification
- User-business relationship history
- Recent notification load
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from code.data.loader import get_loader


def get_context(message_id: str) -> Dict[str, Any]:
    """
    Get full context for a message by message_id.

    Args:
        message_id: The message ID to get context for

    Returns:
        Dict with keys: user, group, business, user_business, notification_load
        Each value is a dict or None if not applicable
    """
    loader = get_loader()

    # Find the message in messages.csv
    message_row = loader.messages[loader.messages["message_id"] == message_id]
    if message_row.empty:
        return {"error": f"Message {message_id} not found"}

    # Convert to dict
    msg = message_row.iloc[0].to_dict()

    # Use the loader's context assembly method
    return loader.get_message_context(msg)