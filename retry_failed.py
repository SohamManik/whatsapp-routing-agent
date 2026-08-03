import sys
from pathlib import Path
import pandas as pd
import logging

# Add code to path
sys.path.insert(0, str(Path("c:/users/lenovo/hackerrank-orchestrate-august26")))

from code.agent.core import run_agent_for_message
from code.validation.output import write_output_csv
from code.agent.schemas import RoutingDecision

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    messages_path = Path("c:/users/lenovo/hackerrank-orchestrate-august26/dataset/messages.csv")
    output_path = Path("c:/users/lenovo/hackerrank-orchestrate-august26/dataset/output.csv")
    
    messages_df = pd.read_csv(messages_path)
    output_df = pd.read_csv(output_path)
    
    # Identify failed rows
    failed_mask = (output_df['message_type'] == 'unknown') & (output_df['confidence'] == 0.3)
    failed_ids = output_df[failed_mask]['message_id'].tolist()
    
    logger.info(f"Found {len(failed_ids)} failed messages to retry.")
    
    if not failed_ids:
        logger.info("No failed messages found. Exiting.")
        return
        
    # Reconstruct decisions list from output_df
    decisions = []
    for _, row in output_df.iterrows():
        decisions.append(RoutingDecision(
            message_id=row['message_id'],
            action=row['action'],
            message_type=row['message_type'],
            reason=row['reason'],
            confidence=row['confidence'],
            evidence_message_ids=row['evidence_message_ids']
        ))
        
    # Retry failed ones
    for idx, msg_id in enumerate(failed_ids):
        logger.info(f"Retrying {idx + 1}/{len(failed_ids)}: {msg_id}")
        
        # Get original message row
        msg_row = messages_df[messages_df['message_id'] == msg_id].iloc[0].to_dict()
        
        try:
            new_decision = run_agent_for_message(msg_row)
            
            # Replace in decisions list
            for i, d in enumerate(decisions):
                if d.message_id == msg_id:
                    decisions[i] = new_decision
                    break
                    
            logger.info(f"  -> {new_decision.action} / {new_decision.message_type} (conf={new_decision.confidence:.2f})")
            
            # Save incrementally just in case it crashes again
            write_output_csv(decisions, output_path)
            
        except Exception as e:
            logger.error(f"Failed to process {msg_id} again: {e}")

    logger.info("Finished retrying failed messages.")

if __name__ == "__main__":
    main()
