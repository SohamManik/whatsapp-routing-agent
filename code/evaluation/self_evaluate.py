"""
Self-evaluation script: Compare sample_output.csv predictions against sample_messages.csv ground truth.

Usage:
    python -m code.evaluation.self_evaluate
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Dict, Any


def run_self_evaluation(
    sample_output_path: Path = Path("dataset/sample_output.csv"),
    sample_messages_path: Path = Path("dataset/sample_messages.csv")
) -> Dict[str, Any]:
    """Compare predictions against ground truth and return metrics."""
    pred_df = pd.read_csv(sample_output_path)
    gt_df = pd.read_csv(sample_messages_path)

    # Merge on message_id
    merged = pred_df.merge(
        gt_df[["message_id", "action", "message_type"]],
        on="message_id",
        suffixes=("_pred", "_gt")
    )

    if len(merged) == 0:
        return {"error": "No matching message_ids"}

    # Accuracy
    action_acc = (merged["action_pred"] == merged["action_gt"]).mean()
    type_acc = (merged["message_type_pred"] == merged["message_type_gt"]).mean()

    # Confusion matrices
    action_cm = pd.crosstab(merged["action_gt"], merged["action_pred"], margins=True)
    type_cm = pd.crosstab(merged["message_type_gt"], merged["message_type_pred"], margins=True)

    # Worst mismatches (by confidence)
    mismatches = merged[
        (merged["action_pred"] != merged["action_gt"]) |
        (merged["message_type_pred"] != merged["message_type_gt"])
    ].copy()

    worst = mismatches.head(5)[[
        "message_id", "action_pred", "action_gt",
        "message_type_pred", "message_type_gt",
        "reason", "confidence"
    ]].to_dict("records")

    return {
        "total_samples": len(merged),
        "action_accuracy": float(action_acc),
        "message_type_accuracy": float(type_acc),
        "action_confusion_matrix": action_cm.to_dict(),
        "message_type_confusion_matrix": type_cm.to_dict(),
        "worst_mismatches": worst,
    }


def main():
    """Run self-evaluation and print results."""
    result = run_self_evaluation()

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print("=" * 60)
    print("SELF-EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total samples: {result['total_samples']}")
    print(f"Action accuracy: {result['action_accuracy']:.2%}")
    print(f"Message type accuracy: {result['message_type_accuracy']:.2%}")

    print("\nAction Confusion Matrix:")
    print(pd.DataFrame(result['action_confusion_matrix']).to_string())

    print("\nMessage Type Confusion Matrix:")
    print(pd.DataFrame(result['message_type_confusion_matrix']).to_string())

    print("\nWorst 5 Mismatches:")
    for i, m in enumerate(result['worst_mismatches'], 1):
        print(f"  {i}. {m['message_id']}:")
        print(f"     Pred: action={m['action_pred']}, type={m['message_type_pred']}, conf={m['confidence']:.2f}")
        print(f"     GT:   action={m['action_gt']}, type={m['message_type_gt']}")
        print(f"     Reason: {m['reason'][:80]}...")


if __name__ == "__main__":
    main()