# CLAUDE.md — WhatsApp Message Notification Router

## Project Overview

Build an AI-powered WhatsApp message notification router. For every row in `dataset/messages.csv` (110 messages), produce one row in `dataset/output.csv` deciding:
- **notify**: interrupt the user now
- **digest**: useful but can wait
- **mute**: low-value, repetitive, suspicious, or unsafe

Decisions are **personalized per user** using engagement history, group membership, business relationships, and media content.

**Read `problem_statement.md` for the canonical task spec.** It is the source of truth.
**Read `AGENTS.md` for transcript logging rules.** Follow its onboarding (§3) and per-turn logging (§5.2) exactly.

---

## BEHAVIOR RULES (NON-NEGOTIABLE)

1. **Explain your approach BEFORE implementing.** State what you plan to build, which files you'll create/modify, and expected behavior. Then implement.
2. **Diagnose root causes BEFORE proposing fixes.** When something fails, inspect the actual error, trace the data flow, identify why it failed. Then fix.
3. **Never give empty continuation.** Every response must contain specific technical intent.
4. **When reviewing output rows, describe specific failures.** "Row msg_042 has action=notify but user muted this group and has 5% read rate. This should be mute."
5. **Log every turn to `%USERPROFILE%\hackerrank_orchestrate_august26\log.txt`** per AGENTS.md §5.2 format.

---

## OUTPUT SCHEMA (Pydantic — CANONICAL)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class RoutingDecision(BaseModel):
    message_id: str
    action: Literal["notify", "digest", "mute"]
    message_type: Literal[
        "personal", "urgent", "event", "payment", "business_update",
        "promotion", "greeting", "forward", "spam", "scam", "unknown"
    ]
    reason: str = Field(..., min_length=10, max_length=300)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_message_ids: str  # semicolon-separated message IDs or "none"

    @field_validator("evidence_message_ids")
    @classmethod
    def validate_evidence(cls, v: str) -> str:
        if v.strip().lower() == "none":
            return "none"
        parts = [p.strip() for p in v.split(";") if p.strip()]
        if not parts:
            return "none"
        return ";".join(parts)

    @field_validator("reason")
    @classmethod
    def validate_reason_not_generic(cls, v: str) -> str:
        generic_phrases = ["this is a message", "based on the content", "the message should be"]
        if any(g in v.lower() for g in generic_phrases):
            raise ValueError("Reason too generic. Must cite specific signals.")
        return v
```

On 3 consecutive validation failures for the same message, write a safe fallback:
```python
SAFE_FALLBACK = {
    "action": "digest",
    "message_type": "unknown",
    "reason": "Unable to determine routing with sufficient confidence. Defaulting to digest for manual review.",
    "confidence": 0.3,
    "evidence_message_ids": "none"
}
```

---

## ALLOWED VALUES (EXHAUSTIVE)

**action**: `notify`, `digest`, `mute`

**message_type**: `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, `unknown`

Any value outside these sets is a bug. Validate before writing.

---

## INPUT / OUTPUT PATHS

- Input messages: `dataset/messages.csv` (110 rows)
- Output predictions: `dataset/output.csv` (overwrite, preserve message_id order)
- Sample solved rows: `dataset/sample_messages.csv` (30 rows, separate IDs — sample_msg_*, no overlap with msg_*)
- Images: `dataset/images.csv` → 20 files under `dataset/media/images/` (.jpg, 44KB–381KB)
- Voice notes: `dataset/voice_notes.csv` → 13 files under `dataset/media/audio/` (.mp3, 87KB–190KB)

**output.csv required columns (in order):** `message_id`, `action`, `message_type`, `reason`, `confidence`, `evidence_message_ids`

One row per row in messages.csv. No missing. No extra.

---

## ACTUAL DATA SCHEMAS (USE THESE EXACT COLUMN NAMES)

### dataset/messages.csv (110 rows — what to predict)
`message_id`, `user_id`, `conversation_type` (personal/group/business), `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type` (NaN/image/voice), `media_id`, `forwarded_count`

Distribution: 63 group, 30 business, 17 personal. 15 image, 8 voice, 87 text-only. 8 messages have empty message_text (all voice-only).

### dataset/users.csv (54 rows)
`user_id`, `do_not_disturb_window` (string like "22:00-07:00"), `messages_opened_30d`, `messages_replied_30d`, `notifications_dismissed_30d`, `messages_reported_30d`

NOTE: These are raw COUNTS, not rates. Compute rates if needed by normalizing.
NOTE: DND window wraps midnight. Parse both times and handle the crossover.

### dataset/groups.csv (23 rows)
`group_id`, `group_name`, `group_type` (family/society/etc.), `member_count`, `admin_count`, `created_at`, `messages_30d`

### dataset/group_members.csv (401 rows)
`group_id`, `user_id`, `role` (admin/member), `joined_at`, `messages_sent_30d`, `messages_read_30d`, `replies_sent_30d`, `notifications_dismissed_30d`, `group_muted_by_user` (int 0/1)

14 messages in the dataset go to users who muted that group. Key edge case.

### dataset/business_accounts.csv (110 rows)
`business_id`, `display_name`, `brand_name`, `category`, `verified` (int 0/1), `official_domain`, `domain_used_by_sender`, `account_age_days`, `messages_sent_30d`, `user_reports_30d`, `domain_used_by_sender_age_days`

84 verified, 26 unverified. All 26 unverified have domain mismatches + high reports + young accounts (scam impersonators), except business_032 (pharmacy, 0 reports, 420 days old).

### dataset/user_business_history.csv
`user_id`, `business_id`, `why_user_knows_account` (e.g. "recent_grocery_delivery", "active_sale_subscription"), `last_activity_at`, `allows_promotions` (int 0/1), `promotions_opted_out_at` (timestamp or NaN), `activity_count_180d`, `messages_opened_30d`, `messages_dismissed_30d`, `messages_replied_30d`, `last_reply_at`

### dataset/message_history.csv (412 rows — EVIDENCE SOURCE)
Same schema as messages.csv: `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`

### dataset/message_events.csv (412 rows — 1:1 with message_history)
`user_id`, `message_id`, `message_opened` (0/1), `message_replied` (0/1), `reaction_time_minutes` (float or NaN), `notification_dismissed` (0/1), `muted_after_message` (0/1), `message_reported` (0/1)

55 reported messages in history. Join key: `message_id`.

### dataset/daily_notification_summary.csv (756 rows)
`user_id`, `date`, `notifications_sent` (1–15 range), `notifications_dismissed`

### dataset/images.csv (20 rows)
`image_id`, `file_path` (e.g. "media/images/img_001.jpg")

### dataset/voice_notes.csv (13 rows)
`voice_note_id`, `file_path` (e.g. "media/audio/vn_001.mp3")

---

## ARCHITECTURE

**Single agent with 4 tools + pre-LLM safety gates + post-LLM Pydantic validation.**

### Processing Pipeline
```
1. STARTUP: Load all CSVs, build lookup indices, init empty media cache
2. PER MESSAGE (110x):
   a. Safety Gate (deterministic, pre-LLM)
      → If gated: write mute row, skip LLM
   b. Agent Core (Nemotron Ultra 550B via NIM) — MULTI-TURN TOOL CALLING LOOP:
      → Agent receives message + system prompt
      → Agent decides which tools to call (model-driven, not hardcoded)
      → Typical flow: get_context → [analyze_image if image] → [transcribe_voice if voice] → retrieve_evidence → reason → output
      → Agent may skip tools if signals are already clear (e.g., muted group greeting needs no evidence)
      → Returns RoutingDecision JSON
   c. Pydantic Validation
      → Valid: accumulate in memory
      → Invalid: retry up to 3x, then safe fallback
3. AFTER ALL MESSAGES: Write all results to dataset/output.csv at once
```

### Why Multi-Turn Tool Calling (Not Pre-Assembled Context)
The architecture score (30% of code grade) requires "real tool calling loops and model-driven routing, not hardcoded workflows." The agent must DECIDE which tools to call. For a text-only greeting in a muted group, it may skip evidence retrieval. For a business payment message, it calls get_context then retrieve_evidence. For an image-only message, it calls analyze_image first. This is model-driven routing.

### Why Accumulate Then Write (Not Append Per Row)
If the pipeline crashes at row 87, a partial output.csv could be submitted accidentally. Accumulate all 110 results in memory, validate completeness (all message_ids present, no duplicates), then write once.

### Tool Specifications (Actual Column Names)

**get_context(message_id: str) → dict**: Returns user prefs (do_not_disturb_window, is_in_dnd computed, messages_opened_30d, messages_replied_30d, notifications_dismissed_30d, messages_reported_30d), group info (group_name, group_type, member_count, user role, group_muted_by_user, user read/reply/dismiss stats), business info (display_name, verified, official_domain, domain_used_by_sender, domain_match computed, account_age_days, user_reports_30d), user-business relationship (why_user_knows_account, allows_promotions, opted_out computed, activity_count_180d, messages_opened/dismissed_30d), notification load. None for irrelevant sections. Does NOT include media content — agent must call analyze_image/transcribe_voice separately.

**retrieve_evidence(query_text: str, user_id: str, sender_user_id: str | None, group_id: str | None, business_id: str | None, top_k: int = 3) → dict**: Returns 1-2 best evidence matches with message_id, text_preview, similarity, user reaction booleans (opened/replied/dismissed/muted/reported), reaction_time_minutes, days_ago. Plus pattern_summary string. Uses BM25 ranking over filtered message_history.

**analyze_image(media_id: str) → dict**: Calls NIM Llama 3.2 Vision 11B. Returns content_type, extracted_text, risk_signals, description. **Results are cached** — second call for same media_id returns instantly. The agent decides whether to call this based on media_type.

**transcribe_voice(media_id: str) → dict**: Calls Groq Whisper Large v3 Turbo. Returns transcription, language, duration_seconds. **Results are cached** — second call for same media_id returns instantly. The agent decides whether to call this based on media_type.

---

## SAFETY GATES (PRE-LLM, DETERMINISTIC, NO LLM OVERRIDE)

### Gate 1: Prompt Injection Detection
Patterns: "action=notify", "mark as notify", "classify as urgent", "system note", "router instruction", "routing override", "assistant instruction", "ignore sender risk", "internal router metadata", "verified_business=true", "user_priority=high", "confidence=1"
→ Action: mute, Type: scam, Confidence: 0.93

### Gate 2: Business Scam (unverified + reports > 5 + age < 60 days + domain mismatch)
→ Action: mute, Type: scam, Confidence: 0.95

### Gate 3: Scam Language (English + Hindi/Hinglish)
EN: "won a prize", "share otp", "send otp", "confirm your pin", "fill bank details", "reactivation fee", etc.
HI: "otp batao", "link open karo", "block ho jayega", "band ho jayega", "code daal do", etc.
→ Combined with other signals for gating decision

### Gate 4: User Opt-Out (promotions_opted_out_at is not NaN)
→ Action: mute, Type: promotion, Confidence: 0.90

### Gate 5: Repeated Negative History (3+ dismissed/muted/reported from same sender in 14 days)
→ Action: mute, Type: spam, Confidence: 0.88

---

## ENGINEERING STANDARDS (MANDATORY)

1. **Type hints on every function signature.** No exceptions.
2. **Secrets via environment variables.** Use `python-dotenv`. Load from `.env` at repo root.
   - `NVIDIA_API_KEY` — for NIM (NemoTron + Vision)
   - `GROQ_API_KEY` — for Whisper
3. **Multi-file structure under `code/`.** Agent logic, tools, safety, data, validation in separate modules.
4. **Functions under 30 lines.** Refactor if exceeded.
5. **No unused imports.**
6. **No comments describing unimplemented behavior.**
7. **Logging, not print.** Use Python `logging` module.
8. **Error handling.** Every API call: try/except, retry up to 3x with exponential backoff. Never crash.
9. **All code under `code/` directory.** Entry point: `code/main.py`.
10. **main.py accepts `--input` flag.** Default: `dataset/messages.csv`. Can also accept `dataset/sample_messages.csv` for self-evaluation.
11. **Accumulate all results in memory, write once.** Validate completeness before writing.

---

## PROJECT STRUCTURE

```
.                                  # Repo root (AGENTS.md, README.md, problem_statement.md exist)
├── CLAUDE.md                      # This file
├── .env                           # Already exists: NVIDIA_API_KEY, GROQ_API_KEY
├── code/
│   ├── main.py                    # Entry point: --input flag, logging, orchestration
│   ├── requirements.txt
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py                # Multi-turn tool-calling agent loop
│   │   ├── prompts.py             # System prompt, few-shot examples
│   │   └── schemas.py             # Pydantic models
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── context.py             # get_context (local, no API)
│   │   ├── retrieval.py           # retrieve_evidence (BM25, local)
│   │   ├── vision.py              # analyze_image (NIM Vision, cached)
│   │   └── audio.py               # transcribe_voice (Groq Whisper, cached)
│   ├── safety/
│   │   ├── __init__.py
│   │   └── gates.py               # All 5 deterministic safety gates
│   ├── data/
│   │   ├── __init__.py
│   │   └── loader.py              # CSV loading, in-memory indexing
│   ├── validation/
│   │   ├── __init__.py
│   │   └── output.py              # Pydantic validation, CSV writing, fallback
│   └── evaluation/
│       ├── __init__.py
│       └── self_evaluate.py       # Compare output vs sample_messages.csv ground truth
├── dataset/                       # Provided (DO NOT MODIFY except output.csv)
│   ├── messages.csv
│   ├── output.csv                 # WRITE PREDICTIONS HERE
│   └── ...
```

### Self-Evaluation Workflow
```bash
# Run pipeline on the 30 solved examples
python code/main.py --input dataset/sample_messages.csv --output dataset/sample_output.csv

# Compare against ground truth
python code/evaluation/self_evaluate.py
```
`self_evaluate.py` compares `sample_output.csv` predictions against the action/message_type columns already in `sample_messages.csv`. Reports: accuracy per field, confusion matrix, and prints the 5 worst mismatches with predicted vs expected values.

---

## MODEL CONFIGURATION

| Task | Model | Provider | Env Var | Base URL |
|------|-------|----------|---------|----------|
| Agent reasoning | `nemotron-3-ultra-550b-a55b` | NVIDIA NIM | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` |
| Image analysis | Llama 3.2 Vision 11B (or best available) | NVIDIA NIM | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` |
| Evidence reranking | `nvidia/nv-rerankqa-mistral-4b-v3` (or best available) | NVIDIA NIM | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` |
| Voice transcription | Whisper Large v3 Turbo | Groq | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |

Fallback for vision: Phi-3.5 Vision or any available NIM vision model.
Fallback for reranker: skip reranking, use BM25 ranking only.

---

## CONFIDENCE CALIBRATION

| Signal Strength | Confidence Range |
|----------------|-----------------|
| Safety gate triggered (scam/injection) | 0.90 – 0.95 |
| 3+ consistent user reactions from history | 0.85 – 0.90 |
| Strong context match (payment + active order) | 0.80 – 0.90 |
| Moderate signals, some history | 0.60 – 0.80 |
| Weak signals, little history | 0.40 – 0.60 |
| Conflicting signals | 0.30 – 0.50 |

---

## RETRIEVAL STRATEGY

**BM25 candidate generation + NIM cross-encoder reranking.** This is the pipeline that separates top-10 from top-100 submissions.

1. Filter `message_history` by `user_id` + optionally `sender_user_id` / `group_id` / `business_id`
2. BM25 rank filtered messages by text similarity to incoming message → take top 5 candidates
3. Rerank top 5 using NIM reranking API (`nvidia/nv-rerankqa-mistral-4b-v3` or best available)
4. Join top reranked matches with `message_events` to get user reactions
5. Return top 1-2 with reaction data and pattern summary

If NIM reranking API is unavailable (tested in Phase 0), fall back to BM25 ranking only — still functional, just lower evidence quality.

---

## EVIDENCE GUIDELINES

- Target **1-2 evidence message IDs**, not 5. Sample data shows most rows have exactly 1.
- Evidence must be **real message_ids from message_history.csv**. Never hallucinate IDs.
- Pick evidence that shows a **pattern** (user dismissed similar) or **context** (previous scam from same sender).
- Write `none` if no relevant historical message exists. Don't force evidence.

---

## MUTED GROUP RULES

If `group_muted_by_user == 1`:
- Default action: **mute** (user explicitly chose to mute this group)
- Exception: message directly @mentions user by their user_id AND content is urgent/actionable
- NOT an exception: chain messages, greetings, forwards that happen to @mention the user
- Scam messages in muted groups: still **mute** with type **scam** (not just forward/greeting)

---

## SUBMISSION CHECKLIST

```bash
python -c "import pandas as pd; m=pd.read_csv('dataset/messages.csv'); o=pd.read_csv('dataset/output.csv'); print(f'Input: {len(m)}, Output: {len(o)}, Match: {len(m)==len(o)}')"
python -c "import pandas as pd; m=set(pd.read_csv('dataset/messages.csv')['message_id']); o=set(pd.read_csv('dataset/output.csv')['message_id']); print(f'Missing: {m-o}'); print(f'Extra: {o-m}')"
python -c "import pandas as pd; print(list(pd.read_csv('dataset/output.csv').columns))"
python -c "import pandas as pd; o=pd.read_csv('dataset/output.csv'); print('Invalid actions:', o[~o['action'].isin(['notify','digest','mute'])].shape[0]); print('Invalid types:', o[~o['message_type'].isin(['personal','urgent','event','payment','business_update','promotion','greeting','forward','spam','scam','unknown'])].shape[0]); print('Empty reasons:', o['reason'].isna().sum()); print('Confidence range:', o['confidence'].min(), '-', o['confidence'].max())"
```
## After every significant interaction, append a timestamped summary to:
%USERPROFILE%\hackerrank_orchestrate_august26\log.txt