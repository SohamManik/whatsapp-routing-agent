#!/usr/bin/env python
"""
Main entry point for the WhatsApp Message Notification Router.

Usage:
    python -m code.main --input dataset/messages.csv --output dataset/output.csv
    python -m code.main --input dataset/sample_messages.csv --output dataset/sample_output.csv --evaluate
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Add code directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from code.data.loader import DataLoader, get_loader
from code.agent.core import run_agent_for_message
from code.agent.schemas import RoutingDecision, SAFE_FALLBACK
from code.validation.output import validate_all_decisions, write_output_csv
from code.evaluation.self_evaluate import run_self_evaluation


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Message Notification Router")
    parser.add_argument(
        "--input",
        default="dataset/messages.csv",
        help="Input messages CSV file (default: dataset/messages.csv)"
    )
    parser.add_argument(
        "--output",
        default="dataset/output.csv",
        help="Output predictions CSV file (default: dataset/output.csv)"
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run self-evaluation against sample_messages.csv"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading data from {input_path}")
    loader = DataLoader(input_path.parent)
    messages_df = pd.read_csv(input_path)

    logger.info(f"Processing {len(messages_df)} messages")

    decisions = []
    for idx, row in messages_df.iterrows():
        message_id = row["message_id"]
        logger.info(f"Processing {idx + 1}/{len(messages_df)}: {message_id}")
        time.sleep(2)  # Throttle to stay under 40 requests/minute API limit

        try:
            decision = run_agent_for_message(row.to_dict())
            decisions.append(decision)
            logger.info(f"  -> {decision.action} / {decision.message_type} (conf={decision.confidence:.2f})")
        except Exception as e:
            logger.error(f"Error processing {message_id}: {e}")
            # Use fallback
            decisions.append(RoutingDecision(message_id=message_id, **SAFE_FALLBACK))

    # Validate all decisions
    expected_ids = messages_df["message_id"].tolist()
    validation = validate_all_decisions(decisions, expected_ids)

    if not validation["valid"]:
        logger.error("Validation failed:")
        for err in validation["errors"]:
            logger.error(f"  - {err}")
        sys.exit(1)

    if validation["warnings"]:
        for warn in validation["warnings"]:
            logger.warning(f"  - {warn}")

    logger.info("All validations passed")

    # Write output
    write_output_csv(decisions, output_path)
    logger.info(f"Output written to {output_path}")

    # Self-evaluation if requested
    if args.evaluate:
        sample_output = Path("dataset/sample_output.csv")
        sample_messages = Path("dataset/sample_messages.csv")
        if sample_output.exists() and sample_messages.exists():
            logger.info("Running self-evaluation...")
            eval_results = run_self_evaluation(sample_output, sample_messages)
            logger.info(f"Action Accuracy: {eval_results['action_accuracy']:.2%}")
            logger.info(f"Message Type Accuracy: {eval_results['message_type_accuracy']:.2%}")
            logger.info(f"Worst mismatches: {eval_results['worst_mismatches']}")


if __name__ == "__main__":
    main()