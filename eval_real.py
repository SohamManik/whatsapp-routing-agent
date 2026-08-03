import pandas as pd

# Load ground truth and our final fixed output
gt = pd.read_csv('c:/users/lenovo/hackerrank-orchestrate-august26/dataset/sample_messages.csv')
out = pd.read_csv('c:/users/lenovo/hackerrank-orchestrate-august26/dataset/output.csv')

# Merge to evaluate only the 30 sample messages from the main output
merged = pd.merge(gt, out, on='message_id', suffixes=('_gt', '_pred'))

action_correct = (merged['action_gt'] == merged['action_pred']).sum()
type_correct = (merged['message_type_gt'] == merged['message_type_pred']).sum()
total = len(merged)

print(f'REAL Action Accuracy: {action_correct}/{total} ({(action_correct/total)*100:.2f}%)')
print(f'REAL Type Accuracy: {type_correct}/{total} ({(type_correct/total)*100:.2f}%)')

print('\nMismatches:')
for _, row in merged.iterrows():
    if row['action_gt'] != row['action_pred'] or row['message_type_gt'] != row['message_type_pred']:
        print(f"{row['message_id']} - GT: {row['action_gt']}/{row['message_type_gt']} | Pred: {row['action_pred']}/{row['message_type_pred']} (Conf: {row['confidence']}) - {row['reason']}")
