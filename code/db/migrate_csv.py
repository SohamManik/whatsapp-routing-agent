import os
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from code.db.database import engine, Base, SessionLocal
from code.db.models import (
    User, Group, GroupMember, BusinessAccount, UserBusinessHistory,
    Message, MessageEvent, DailyNotificationSummary
)

# Create tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)

DATASET_DIR = Path(__file__).parent.parent.parent / "dataset"

def load_csv_to_table(db: Session, csv_filename: str, model_class):
    csv_path = DATASET_DIR / csv_filename
    if not csv_path.exists():
        print(f"Skipping {csv_filename}, not found.")
        return
    
    print(f"Loading {csv_filename} into {model_class.__tablename__}...")
    df = pd.read_csv(csv_path)
    
    # Fill NA to prevent DB null constraint errors where empty string is expected
    df = df.where(pd.notnull(df), None)
    
    records = df.to_dict(orient="records")
    
    # Clear existing data first? (Optional, skipping for now to be safe, assuming fresh DB)
    
    # Bulk insert
    db.bulk_insert_mappings(model_class, records)
    db.commit()
    print(f"Loaded {len(records)} records into {model_class.__tablename__}.")

def main():
    db = SessionLocal()
    try:
        # Load all datasets
        load_csv_to_table(db, "users.csv", User)
        load_csv_to_table(db, "groups.csv", Group)
        load_csv_to_table(db, "group_members.csv", GroupMember)
        load_csv_to_table(db, "business_accounts.csv", BusinessAccount)
        load_csv_to_table(db, "user_business_history.csv", UserBusinessHistory)
        
        # We have messages.csv (the input messages) and message_history.csv
        # Let's combine them into the Message table, or just load message_history first.
        # Actually message_history.csv and messages.csv might have overlap or similar structures.
        load_csv_to_table(db, "message_history.csv", Message)
        load_csv_to_table(db, "messages.csv", Message)
        
        load_csv_to_table(db, "message_events.csv", MessageEvent)
        load_csv_to_table(db, "daily_notification_summary.csv", DailyNotificationSummary)
        print("Database migration complete!")
    except Exception as e:
        print(f"Error migrating data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
