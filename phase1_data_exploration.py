#!/usr/bin/env python
"""Phase 1: Deep Data Exploration"""

import pandas as pd
import numpy as np
from pathlib import Path

DATASET_DIR = Path("dataset")

print("=" * 70)
print("PHASE 1: DATA EXPLORATION")
print("=" * 70)

# ============================================================
# Load all datasets
# ============================================================
messages = pd.read_csv(DATASET_DIR / "messages.csv")
sample_messages = pd.read_csv(DATASET_DIR / "sample_messages.csv")
users = pd.read_csv(DATASET_DIR / "users.csv")
groups = pd.read_csv(DATASET_DIR / "groups.csv")
group_members = pd.read_csv(DATASET_DIR / "group_members.csv")
business_accounts = pd.read_csv(DATASET_DIR / "business_accounts.csv")
user_business_history = pd.read_csv(DATASET_DIR / "user_business_history.csv")
message_history = pd.read_csv(DATASET_DIR / "message_history.csv")
message_events = pd.read_csv(DATASET_DIR / "message_events.csv")
daily_notification_summary = pd.read_csv(DATASET_DIR / "daily_notification_summary.csv")
images = pd.read_csv(DATASET_DIR / "images.csv")
voice_notes = pd.read_csv(DATASET_DIR / "voice_notes.csv")

print(f"\nDataset sizes:")
print(f"  messages.csv: {len(messages)} rows")
print(f"  sample_messages.csv: {len(sample_messages)} rows")
print(f"  users.csv: {len(users)} rows")
print(f"  groups.csv: {len(groups)} rows")
print(f"  group_members.csv: {len(group_members)} rows")
print(f"  business_accounts.csv: {len(business_accounts)} rows")
print(f"  user_business_history.csv: {len(user_business_history)} rows")
print(f"  message_history.csv: {len(message_history)} rows")
print(f"  message_events.csv: {len(message_events)} rows")
print(f"  daily_notification_summary.csv: {len(daily_notification_summary)} rows")
print(f"  images.csv: {len(images)} rows")
print(f"  voice_notes.csv: {len(voice_notes)} rows")

# ============================================================
# 1. Sample messages: 2 best per action type
# ============================================================
print("\n" + "=" * 70)
print("1. SAMPLE MESSAGES: Best 2 per action type")
print("=" * 70)

for action in ["notify", "digest", "mute"]:
    subset = sample_messages[sample_messages["action"] == action]
    print(f"\n  --- {action.upper()} ({len(subset)} total) ---")
    # Pick 2 with diverse message_types
    seen_types = set()
    for _, row in subset.iterrows():
        if row["message_type"] not in seen_types and len(seen_types) < 2:
            seen_types.add(row["message_type"])
            print(f"    {row['message_id']} | type={row['message_type']}")
            print(f"      reason: {row['reason']}")
            print(f"      evidence: {row['evidence_message_ids']}")
            print(f"      confidence: {row['confidence']}")

# ============================================================
# 2. Group type distribution for 63 group messages
# ============================================================
print("\n" + "=" * 70)
print("2. GROUP TYPE DISTRIBUTION (63 group messages)")
print("=" * 70)

group_msgs = messages[messages["conversation_type"] == "group"]
print(f"  Total group messages: {len(group_msgs)}")

# Merge with groups.csv to get group_type
group_msgs_with_type = group_msgs.merge(groups[["group_id", "group_type"]], on="group_id", how="left")
dist = group_msgs_with_type["group_type"].value_counts()
for gt, count in dist.items():
    print(f"  {gt}: {count}")

# ============================================================
# 3. Business scam prevalence
# ============================================================
print("\n" + "=" * 70)
print("3. BUSINESS SCAM PREVALENCE (30 business messages)")
print("=" * 70)

business_msgs = messages[messages["conversation_type"] == "business"]
print(f"  Total business messages: {len(business_msgs)}")

# Merge with business_accounts to get verified status
business_msgs_with_ver = business_msgs.merge(
    business_accounts[["business_id", "verified", "user_reports_30d", "account_age_days", "official_domain", "domain_used_by_sender"]],
    on="business_id", how="left"
)

unverified = business_msgs_with_ver[business_msgs_with_ver["verified"] == 0]
verified = business_msgs_with_ver[business_msgs_with_ver["verified"] == 1]
print(f"  From verified businesses: {len(verified)}")
print(f"  From UNVERIFIED businesses: {len(unverified)}")

if len(unverified) > 0:
    print(f"\n  Unverified business details:")
    for _, row in unverified.iterrows():
        domain_match = row["official_domain"] == row["domain_used_by_sender"] if pd.notna(row["official_domain"]) and pd.notna(row["domain_used_by_sender"]) else False
        print(f"    {row['message_id']} -> {row['business_id']} (reports={row['user_reports_30d']}, age={row['account_age_days']}d, domain_match={domain_match})")

# ============================================================
# 4. User engagement spread
# ============================================================
print("\n" + "=" * 70)
print("4. USER ENGAGEMENT SPREAD (32 unique users in messages)")
print("=" * 70)

unique_users = messages["user_id"].unique()
print(f"  Unique users in messages.csv: {len(unique_users)}")

user_stats = users[users["user_id"].isin(unique_users)]
for col in ["messages_opened_30d", "messages_replied_30d", "notifications_dismissed_30d", "messages_reported_30d"]:
    print(f"  {col}: min={user_stats[col].min()}, max={user_stats[col].max()}, mean={user_stats[col].mean():.1f}")

# ============================================================
# 5. Evidence coverage
# ============================================================
print("\n" + "=" * 70)
print("5. EVIDENCE COVERAGE (messages with history from same sender/context)")
print("=" * 70)

def has_relevant_history(msg_row, history_df):
    """Check if there's history from same user AND same sender/group/business"""
    user_hist = history_df[history_df["user_id"] == msg_row["user_id"]]
    if user_hist.empty:
        return False

    mask = pd.Series(True, index=user_hist.index)
    if pd.notna(msg_row.get("sender_user_id")) and msg_row["sender_user_id"]:
        mask &= user_hist["sender_user_id"] == msg_row["sender_user_id"]
    if pd.notna(msg_row.get("group_id")) and msg_row["group_id"]:
        mask &= user_hist["group_id"] == msg_row["group_id"]
    if pd.notna(msg_row.get("business_id")) and msg_row["business_id"]:
        mask &= user_hist["business_id"] == msg_row["business_id"]

    return mask.any()

has_history = messages.apply(lambda row: has_relevant_history(row, message_history), axis=1)
print(f"  Messages with relevant history: {has_history.sum()} / {len(messages)} ({has_history.mean()*100:.1f}%)")
print(f"  Messages WITHOUT relevant history: {(~has_history).sum()} / {len(messages)} ({(~has_history).mean()*100:.1f}%)")

# ============================================================
# 6. DND overlap
# ============================================================
print("\n" + "=" * 70)
print("6. DND OVERLAP (messages created during user's DND window)")
print("=" * 70)

def parse_dnd(window_str):
    """Parse DND window string like '22:00-07:00'"""
    if pd.isna(window_str):
        return None, None
    try:
        start_str, end_str = window_str.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        return (start_h, start_m), (end_h, end_m)
    except:
        return None, None

def in_dnd(created_at, dnd_start, dnd_end):
    """Check if timestamp falls in DND window"""
    if dnd_start is None or dnd_end is None:
        return False
    try:
        dt = pd.to_datetime(created_at)
        msg_minutes = dt.hour * 60 + dt.minute
        start_minutes = dnd_start[0] * 60 + dnd_start[1]
        end_minutes = dnd_end[0] * 60 + dnd_end[1]

        if start_minutes <= end_minutes:
            return start_minutes <= msg_minutes <= end_minutes
        else:
            return msg_minutes >= start_minutes or msg_minutes <= end_minutes
    except:
        return False

# Merge messages with user DND windows
msgs_with_dnd = messages.merge(users[["user_id", "do_not_disturb_window"]], on="user_id", how="left")
msgs_with_dnd["dnd_start"], msgs_with_dnd["dnd_end"] = zip(*msgs_with_dnd["do_not_disturb_window"].apply(parse_dnd))
msgs_with_dnd["in_dnd"] = msgs_with_dnd.apply(
    lambda row: in_dnd(row["created_at"], row["dnd_start"], row["dnd_end"]), axis=1
)

dnd_count = msgs_with_dnd["in_dnd"].sum()
print(f"  Messages during DND: {dnd_count} / {len(messages)} ({dnd_count/len(messages)*100:.1f}%)")

# Show breakdown by conversation type
for ct in ["personal", "group", "business"]:
    subset = msgs_with_dnd[msgs_with_dnd["conversation_type"] == ct]
    if len(subset) > 0:
        dnd_ct = subset["in_dnd"].sum()
        print(f"    {ct}: {dnd_ct} / {len(subset)} ({dnd_ct/len(subset)*100:.1f}%)")

print("\n" + "=" * 70)
print("PHASE 1 COMPLETE")
print("=" * 70)