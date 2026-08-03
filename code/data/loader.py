"""
Data loader module for the WhatsApp Message Notification Router.

Loads all CSV datasets and builds in-memory indices for fast lookups.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

# Dataset directory relative to repo root (parent of code/)
DATASET_DIR = Path(__file__).parent.parent.parent / "dataset"


class DataLoader:
    """Loads and indexes all dataset CSV files for fast lookup."""

    def __init__(self, dataset_dir: Optional[str | Path] = None):
        self.dataset_dir = Path(dataset_dir) if dataset_dir else DATASET_DIR
        self._load_all()

    def _load_all(self) -> None:
        """Load all CSV files and build lookup indices."""
        # Core datasets
        self.messages = pd.read_csv(self.dataset_dir / "messages.csv")
        self.users = pd.read_csv(self.dataset_dir / "users.csv")
        self.groups = pd.read_csv(self.dataset_dir / "groups.csv")
        self.group_members = pd.read_csv(self.dataset_dir / "group_members.csv")
        self.business_accounts = pd.read_csv(self.dataset_dir / "business_accounts.csv")
        self.user_business_history = pd.read_csv(self.dataset_dir / "user_business_history.csv")
        self.message_history = pd.read_csv(self.dataset_dir / "message_history.csv")
        self.message_events = pd.read_csv(self.dataset_dir / "message_events.csv")
        self.daily_notification_summary = pd.read_csv(self.dataset_dir / "daily_notification_summary.csv")
        self.images = pd.read_csv(self.dataset_dir / "images.csv")
        self.voice_notes = pd.read_csv(self.dataset_dir / "voice_notes.csv")

        # Log record counts
        print(f"[DataLoader] Loaded:")
        print(f"  messages: {len(self.messages)}")
        print(f"  users: {len(self.users)}")
        print(f"  groups: {len(self.groups)}")
        print(f"  group_members: {len(self.group_members)}")
        print(f"  business_accounts: {len(self.business_accounts)}")
        print(f"  user_business_history: {len(self.user_business_history)}")
        print(f"  message_history: {len(self.message_history)}")
        print(f"  message_events: {len(self.message_events)}")
        print(f"  daily_notification_summary: {len(self.daily_notification_summary)}")
        print(f"  images: {len(self.images)}")
        print(f"  voice_notes: {len(self.voice_notes)}")

        # Build indices for fast lookup
        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup dictionaries for O(1) access."""
        # User index by user_id
        self.users_by_id: Dict[str, Dict] = {
            row.user_id: row.to_dict() for _, row in self.users.iterrows()
        }

        # Group index by group_id
        self.groups_by_id: Dict[str, Dict] = {
            row.group_id: row.to_dict() for _, row in self.groups.iterrows()
        }

        # Group member index by (group_id, user_id)
        self.group_members_by_user_group: Dict[Tuple[str, str], Dict] = {
            (row.group_id, row.user_id): row.to_dict() for _, row in self.group_members.iterrows()
        }

        # Business account index by business_id
        self.businesses_by_id: Dict[str, Dict] = {
            row.business_id: row.to_dict() for _, row in self.business_accounts.iterrows()
        }

        # User-business history index by (user_id, business_id)
        self.user_business_by_user_business: Dict[Tuple[str, str], Dict] = {
            (row.user_id, row.business_id): row.to_dict() for _, row in self.user_business_history.iterrows()
        }

        # Message history grouped by user (sorted by created_at desc)
        self.history_by_user: Dict[str, List[Dict]] = {}
        for user_id, df in self.message_history.groupby("user_id"):
            df_sorted = df.sort_values("created_at", ascending=False)
            self.history_by_user[user_id] = df_sorted.to_dict("records")

        # Message events index by message_id (1:1)
        self.events_by_message: Dict[str, Dict] = {
            row.message_id: row.to_dict() for _, row in self.message_events.iterrows()
        }

        # Images index by image_id
        self.images_by_id: Dict[str, Dict] = {
            row.image_id: row.to_dict() for _, row in self.images.iterrows()
        }

        # Voice notes index by voice_note_id
        self.voice_notes_by_id: Dict[str, Dict] = {
            row.voice_note_id: row.to_dict() for _, row in self.voice_notes.iterrows()
        }

        # Daily notification summary index by (user_id, date)
        self.daily_summary_by_user_date: Dict[Tuple[str, str], Dict] = {
            (row.user_id, row.date): row.to_dict() for _, row in self.daily_notification_summary.iterrows()
        }

    # ========================================================
    # Lookup methods
    # ========================================================

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self.users_by_id.get(user_id)

    def get_group(self, group_id: str) -> Optional[Dict]:
        return self.groups_by_id.get(group_id)

    def get_group_member(self, group_id: str, user_id: str) -> Optional[Dict]:
        return self.group_members_by_user_group.get((group_id, user_id))

    def get_business(self, business_id: str) -> Optional[Dict]:
        return self.businesses_by_id.get(business_id)

    def get_user_business_history(self, user_id: str, business_id: str) -> Optional[Dict]:
        return self.user_business_by_user_business.get((user_id, business_id))

    def get_message_history(self, user_id: str) -> List[Dict]:
        return self.history_by_user.get(user_id, [])

    def get_message_event(self, message_id: str) -> Optional[Dict]:
        return self.events_by_message.get(message_id)

    def get_image_path(self, image_id: str) -> Optional[str]:
        row = self.images_by_id.get(image_id)
        if row:
            return str(self.dataset_dir / row.get("file_path", ""))
        return None

    def get_voice_note_path(self, voice_note_id: str) -> Optional[str]:
        row = self.voice_notes_by_id.get(voice_note_id)
        if row:
            return str(self.dataset_dir / row.get("file_path", ""))
        return None

    def get_daily_notification(self, user_id: str, date: str) -> Optional[Dict]:
        return self.daily_summary_by_user_date.get((user_id, date))

    # ========================================================
    # Context assembly
    # ========================================================

    def is_in_dnd(self, window: str, check_time) -> bool:
        """Check if a given time falls within the user's DND window. Handles midnight crossover."""
        if not window or pd.isna(window):
            return False
        try:
            start_str, end_str = window.split("-")
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))

            check_minutes = check_time.hour * 60 + check_time.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            if start_minutes <= end_minutes:
                return start_minutes <= check_minutes <= end_minutes
            else:
                return check_minutes >= start_minutes or check_minutes <= end_minutes
        except Exception:
            return False

    def get_message_context(self, message_row: Dict) -> Dict[str, Any]:
        """
        Assemble full context for a message as specified in CLAUDE.md.

        Returns dict with keys: user, group, business, user_business, notification_load
        Each value is a dict or None if not applicable.
        Does NOT include media content (agent calls tools for that).
        """
        user_id = message_row.get("user_id")
        group_id = message_row.get("group_id")
        business_id = message_row.get("business_id")
        sender_user_id = message_row.get("sender_user_id")
        created_at = message_row.get("created_at")

        context = {}

        # --- USER ---
        user = self.get_user(user_id)
        if user:
            dnd_window = user.get("do_not_disturb_window", "")
            check_time = pd.to_datetime(created_at) if pd.notna(created_at) else pd.Timestamp.now()
            context["user"] = {
                "user_id": user_id,
                "do_not_disturb_window": dnd_window,
                "is_in_dnd": self.is_in_dnd(dnd_window, check_time),
                "messages_opened_30d": int(user.get("messages_opened_30d", 0)),
                "messages_replied_30d": int(user.get("messages_replied_30d", 0)),
                "notifications_dismissed_30d": int(user.get("notifications_dismissed_30d", 0)),
                "messages_reported_30d": int(user.get("messages_reported_30d", 0)),
            }

        # --- GROUP ---
        if pd.notna(group_id) and group_id:
            group = self.get_group(group_id)
            member = self.get_group_member(group_id, user_id)
            group_ctx = {}
            if group:
                group_ctx.update({
                    "group_id": group_id,
                    "group_name": group.get("group_name", ""),
                    "group_type": group.get("group_type", ""),
                    "member_count": int(group.get("member_count", 0)),
                    "admin_count": int(group.get("admin_count", 0)),
                    "messages_30d": int(group.get("messages_30d", 0)),
                })
            if member:
                group_ctx.update({
                    "user_role": member.get("role", "member"),
                    "group_muted_by_user": int(member.get("group_muted_by_user", 0)),
                    "user_messages_sent_30d": int(member.get("messages_sent_30d", 0)),
                    "user_messages_read_30d": int(member.get("messages_read_30d", 0)),
                    "user_replies_sent_30d": int(member.get("replies_sent_30d", 0)),
                    "user_notifications_dismissed_30d": int(member.get("notifications_dismissed_30d", 0)),
                })
            if group_ctx:
                context["group"] = group_ctx

        # --- BUSINESS ---
        if pd.notna(business_id) and business_id:
            business = self.get_business(business_id)
            if business:
                official_domain = business.get("official_domain", "")
                domain_used = business.get("domain_used_by_sender", "")
                # Handle NaN values
                if isinstance(official_domain, float) and pd.isna(official_domain):
                    official_domain = ""
                if isinstance(domain_used, float) and pd.isna(domain_used):
                    domain_used = ""
                domain_match = bool(official_domain and domain_used and official_domain.lower() == domain_used.lower())
                context["business"] = {
                    "business_id": business_id,
                    "display_name": business.get("display_name", ""),
                    "brand_name": business.get("brand_name", ""),
                    "category": business.get("category", ""),
                    "verified": int(business.get("verified", 0)),
                    "official_domain": official_domain,
                    "domain_used_by_sender": domain_used,
                    "domain_match": domain_match,
                    "account_age_days": int(business.get("account_age_days", 0)),
                    "messages_sent_30d": int(business.get("messages_sent_30d", 0)),
                    "user_reports_30d": int(business.get("user_reports_30d", 0)),
                }

        # --- USER-BUSINESS HISTORY ---
        if pd.notna(business_id) and business_id:
            history = self.get_user_business_history(user_id, business_id)
            if history:
                opted_out_at = history.get("promotions_opted_out_at")
                opted_out = pd.notna(opted_out_at) and str(opted_out_at).strip() != ""
                context["user_business"] = {
                    "why_user_knows_account": history.get("why_user_knows_account", ""),
                    "allows_promotions": int(history.get("allows_promotions", 0)),
                    "promotions_opted_out": opted_out,
                    "promotions_opted_out_at": str(opted_out_at) if opted_out else None,
                    "activity_count_180d": int(history.get("activity_count_180d", 0)),
                    "messages_opened_30d": int(history.get("messages_opened_30d", 0)),
                    "messages_dismissed_30d": int(history.get("messages_dismissed_30d", 0)),
                    "messages_replied_30d": int(history.get("messages_replied_30d", 0)),
                    "last_activity_at": str(history.get("last_activity_at", "")),
                }

        # --- NOTIFICATION LOAD ---
        if pd.notna(created_at):
            date_str = pd.to_datetime(created_at).strftime("%Y-%m-%d")
            daily = self.get_daily_notification(user_id, date_str)
            if daily:
                context["notification_load"] = {
                    "date": date_str,
                    "notifications_sent": int(daily.get("notifications_sent", 0)),
                    "notifications_dismissed": int(daily.get("notifications_dismissed", 0)),
                }

        return context


# Global loader instance
_loader: Optional[DataLoader] = None


def get_loader() -> DataLoader:
    """Get or create the global DataLoader instance."""
    global _loader
    if _loader is None:
        _loader = DataLoader()
    return _loader


if __name__ == "__main__":
    # Quick test
    loader = DataLoader()
    print("\n[Test] Loading context for first 3 messages...")
    for _, row in loader.messages.head(3).iterrows():
        ctx = loader.get_message_context(row.to_dict())
        print(f"\n{row['message_id']}:")
        for k, v in ctx.items():
            print(f"  {k}: {v}")