from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    do_not_disturb_window = Column(String, nullable=True)
    messages_opened_30d = Column(Integer, default=0)
    messages_replied_30d = Column(Integer, default=0)
    notifications_dismissed_30d = Column(Integer, default=0)
    messages_reported_30d = Column(Integer, default=0)

class Group(Base):
    __tablename__ = "groups"
    group_id = Column(String, primary_key=True, index=True)
    group_name = Column(String)
    group_type = Column(String)
    member_count = Column(Integer, default=0)
    admin_count = Column(Integer, default=0)
    messages_30d = Column(Integer, default=0)

class GroupMember(Base):
    __tablename__ = "group_members"
    # Using composite primary key conceptually, but sqlite doesn't strictly need it if we don't query it as PK
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String, index=True)
    user_id = Column(String, index=True)
    role = Column(String, default="member")
    group_muted_by_user = Column(Integer, default=0)
    messages_sent_30d = Column(Integer, default=0)
    messages_read_30d = Column(Integer, default=0)
    replies_sent_30d = Column(Integer, default=0)
    notifications_dismissed_30d = Column(Integer, default=0)

class BusinessAccount(Base):
    __tablename__ = "business_accounts"
    business_id = Column(String, primary_key=True, index=True)
    display_name = Column(String)
    brand_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    verified = Column(Integer, default=0)
    official_domain = Column(String, nullable=True)
    domain_used_by_sender = Column(String, nullable=True)
    account_age_days = Column(Integer, default=0)
    messages_sent_30d = Column(Integer, default=0)
    user_reports_30d = Column(Integer, default=0)

class UserBusinessHistory(Base):
    __tablename__ = "user_business_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    business_id = Column(String, index=True)
    why_user_knows_account = Column(String, nullable=True)
    allows_promotions = Column(Integer, default=0)
    promotions_opted_out_at = Column(String, nullable=True)
    activity_count_180d = Column(Integer, default=0)
    messages_opened_30d = Column(Integer, default=0)
    messages_dismissed_30d = Column(Integer, default=0)
    messages_replied_30d = Column(Integer, default=0)
    last_activity_at = Column(String, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    message_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    sender_user_id = Column(String, nullable=True, index=True)
    group_id = Column(String, nullable=True, index=True)
    business_id = Column(String, nullable=True, index=True)
    message_text = Column(Text, nullable=True)
    media_type = Column(String, nullable=True)
    media_id = Column(String, nullable=True)
    conversation_type = Column(String)
    forwarded_count = Column(Integer, default=0)
    is_broadcast = Column(Integer, default=0)
    created_at = Column(String, nullable=True)

class MessageEvent(Base):
    __tablename__ = "message_events"
    message_id = Column(String, primary_key=True, index=True)
    notification_dismissed = Column(Integer, default=0)
    muted_after_message = Column(Integer, default=0)
    message_reported = Column(Integer, default=0)

class DailyNotificationSummary(Base):
    __tablename__ = "daily_notification_summary"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    date = Column(String, index=True)
    notifications_sent = Column(Integer, default=0)
    notifications_dismissed = Column(Integer, default=0)

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True, index=True)
    action = Column(String)  # notify, digest, mute
    message_type = Column(String)
    reason = Column(String)
    confidence = Column(Float)
    evidence_message_ids = Column(String, nullable=True)

class ReasoningTrace(Base):
    __tablename__ = "reasoning_traces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, index=True)
    step_order = Column(Integer)
    step_type = Column(String)  # "gate_check", "tool_call", "tool_result", "llm_response", "decision"
    data = Column(Text)  # JSON string of the step data
    created_at = Column(String, nullable=True)
