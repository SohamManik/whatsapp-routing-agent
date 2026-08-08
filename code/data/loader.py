"""
Data loader module for the WhatsApp Message Notification Router.
Rewritten to use SQLAlchemy instead of in-memory pandas DataFrames.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Optional, Any, List, Tuple
from code.db.database import SessionLocal
from code.db import models

class DataLoader:
    """Fetches data directly from the SQLAlchemy SQLite database."""

    def __init__(self):
        # We'll create short-lived sessions for queries
        pass

    def get_user(self, user_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            user = db.query(models.User).filter(models.User.user_id == user_id).first()
            return user.__dict__ if user else None

    def get_group(self, group_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            group = db.query(models.Group).filter(models.Group.group_id == group_id).first()
            return group.__dict__ if group else None

    def get_group_member(self, group_id: str, user_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            member = db.query(models.GroupMember).filter(
                models.GroupMember.group_id == group_id,
                models.GroupMember.user_id == user_id
            ).first()
            return member.__dict__ if member else None

    def get_business(self, business_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            business = db.query(models.BusinessAccount).filter(models.BusinessAccount.business_id == business_id).first()
            return business.__dict__ if business else None

    def get_user_business_history(self, user_id: str, business_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            history = db.query(models.UserBusinessHistory).filter(
                models.UserBusinessHistory.user_id == user_id,
                models.UserBusinessHistory.business_id == business_id
            ).first()
            return history.__dict__ if history else None

    def get_message_history(self, user_id: str) -> List[Dict]:
        with SessionLocal() as db:
            msgs = db.query(models.Message).filter(models.Message.user_id == user_id).order_by(models.Message.created_at.desc()).all()
            return [m.__dict__ for m in msgs]

    def get_message_event(self, message_id: str) -> Optional[Dict]:
        with SessionLocal() as db:
            event = db.query(models.MessageEvent).filter(models.MessageEvent.message_id == message_id).first()
            return event.__dict__ if event else None

    def get_daily_notification(self, user_id: str, date: str) -> Optional[Dict]:
        with SessionLocal() as db:
            daily = db.query(models.DailyNotificationSummary).filter(
                models.DailyNotificationSummary.user_id == user_id,
                models.DailyNotificationSummary.date == date
            ).first()
            return daily.__dict__ if daily else None

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
        """
        user_id = message_row.get("user_id")
        group_id = message_row.get("group_id")
        business_id = message_row.get("business_id")
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
                "messages_opened_30d": int(user.get("messages_opened_30d", 0) or 0),
                "messages_replied_30d": int(user.get("messages_replied_30d", 0) or 0),
                "notifications_dismissed_30d": int(user.get("notifications_dismissed_30d", 0) or 0),
                "messages_reported_30d": int(user.get("messages_reported_30d", 0) or 0),
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
                    "member_count": int(group.get("member_count", 0) or 0),
                    "admin_count": int(group.get("admin_count", 0) or 0),
                    "messages_30d": int(group.get("messages_30d", 0) or 0),
                })
            if member:
                group_ctx.update({
                    "user_role": member.get("role", "member"),
                    "group_muted_by_user": int(member.get("group_muted_by_user", 0) or 0),
                    "user_messages_sent_30d": int(member.get("messages_sent_30d", 0) or 0),
                    "user_messages_read_30d": int(member.get("messages_read_30d", 0) or 0),
                    "user_replies_sent_30d": int(member.get("replies_sent_30d", 0) or 0),
                    "user_notifications_dismissed_30d": int(member.get("notifications_dismissed_30d", 0) or 0),
                })
            if group_ctx:
                context["group"] = group_ctx

        # --- BUSINESS ---
        if pd.notna(business_id) and business_id:
            business = self.get_business(business_id)
            if business:
                official_domain = business.get("official_domain", "") or ""
                domain_used = business.get("domain_used_by_sender", "") or ""
                domain_match = bool(official_domain and domain_used and official_domain.lower() == domain_used.lower())
                context["business"] = {
                    "business_id": business_id,
                    "display_name": business.get("display_name", ""),
                    "brand_name": business.get("brand_name", ""),
                    "category": business.get("category", ""),
                    "verified": int(business.get("verified", 0) or 0),
                    "official_domain": official_domain,
                    "domain_used_by_sender": domain_used,
                    "domain_match": domain_match,
                    "account_age_days": int(business.get("account_age_days", 0) or 0),
                    "messages_sent_30d": int(business.get("messages_sent_30d", 0) or 0),
                    "user_reports_30d": int(business.get("user_reports_30d", 0) or 0),
                }

        # --- USER-BUSINESS HISTORY ---
        if pd.notna(business_id) and business_id:
            history = self.get_user_business_history(user_id, business_id)
            if history:
                opted_out_at = history.get("promotions_opted_out_at")
                opted_out = pd.notna(opted_out_at) and str(opted_out_at).strip() != ""
                context["user_business"] = {
                    "why_user_knows_account": history.get("why_user_knows_account", ""),
                    "allows_promotions": int(history.get("allows_promotions", 0) or 0),
                    "promotions_opted_out": opted_out,
                    "promotions_opted_out_at": str(opted_out_at) if opted_out else None,
                    "activity_count_180d": int(history.get("activity_count_180d", 0) or 0),
                    "messages_opened_30d": int(history.get("messages_opened_30d", 0) or 0),
                    "messages_dismissed_30d": int(history.get("messages_dismissed_30d", 0) or 0),
                    "messages_replied_30d": int(history.get("messages_replied_30d", 0) or 0),
                    "last_activity_at": str(history.get("last_activity_at", "")),
                }

        # --- NOTIFICATION LOAD ---
        if pd.notna(created_at):
            try:
                date_str = pd.to_datetime(created_at).strftime("%Y-%m-%d")
                daily = self.get_daily_notification(user_id, date_str)
                if daily:
                    context["notification_load"] = {
                        "date": date_str,
                        "notifications_sent": int(daily.get("notifications_sent", 0) or 0),
                        "notifications_dismissed": int(daily.get("notifications_dismissed", 0) or 0),
                    }
            except:
                pass

        return context

# Global loader instance
_loader: Optional[DataLoader] = None

def get_loader() -> DataLoader:
    global _loader
    if _loader is None:
        _loader = DataLoader()
    return _loader