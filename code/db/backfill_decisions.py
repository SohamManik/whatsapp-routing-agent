import pandas as pd
from code.db.database import SessionLocal
from code.db.models import RoutingDecision
import os

def backfill():
    db = SessionLocal()
    csv_path = "dataset/sample_output.csv"
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    count = 0
    
    for _, row in df.iterrows():
        msg_id = str(row['message_id'])
        existing = db.query(RoutingDecision).filter_by(message_id=msg_id).first()
        if not existing:
            decision = RoutingDecision(
                message_id=msg_id,
                action=str(row['action']) if pd.notna(row.get('action')) else "notify",
                message_type=str(row['message_type']) if pd.notna(row.get('message_type')) else "unknown",
                reason=str(row['reason']) if pd.notna(row.get('reason')) else "Historical decision",
                confidence=float(row['confidence']) if pd.notna(row.get('confidence')) else 1.0,
                evidence_message_ids=str(row['evidence_message_ids']) if pd.notna(row.get('evidence_message_ids')) else "none"
            )
            db.add(decision)
            count += 1
            
    db.commit()
    print(f"Backfilled {count} decisions!")
    db.close()

if __name__ == "__main__":
    backfill()
