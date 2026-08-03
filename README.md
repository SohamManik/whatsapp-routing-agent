# WhatsApp Message Notification Router

This project is an intelligent routing agent that processes incoming WhatsApp messages and decides whether to notify the user, digest the message for later, or mute it entirely. It is built to solve the "Signal vs. Noise" problem in modern messaging apps by acting as a strict, context-aware personal assistant.

## The Architecture (The "Seam")

The system separates **Perception** from **Decision**. It consists of three distinct layers:

1. **Pre-LLM Safety Gates (`code/safety/gates.py`)**: Fast, deterministic Python rules that instantly catch prompt injections, obvious scams, opted-out promotions, and repeated negative history. This handles ~40% of cases instantly without LLM costs.
2. **The Agentic LLM Loop (`code/agent/core.py`)**: A multi-turn reasoning engine powered by Nemotron 550B. The LLM has access to tools to fetch user context, retrieve historical evidence (via BM25 + Cross-Encoder), analyze images, and transcribe voice notes. It investigates ambiguous messages like a human assistant.
3. **Post-LLM Evaluator (`code/evaluation/post_llm_evaluator.py`)**: A deterministic Python layer that overrides the LLM if it violates hard user constraints (e.g., failing to mute an explicitly muted group).

## Project Structure

```
├── code/
│   ├── agent/
│   │   ├── core.py           # The main agentic loop and tool-calling logic
│   │   ├── prompts.py        # System prompt and few-shot examples
│   │   └── schemas.py        # Pydantic schemas for structured LLM output
│   ├── data/
│   │   └── loader.py         # Loads and filters CSV datasets
│   ├── evaluation/
│   │   └── post_llm_evaluator.py # Deterministic overrides for LLM decisions
│   ├── safety/
│   │   └── gates.py          # Pre-LLM safety checks (prompt injection, scams)
│   ├── tools/
│   │   ├── context.py        # Tool to fetch user/group/business context
│   │   ├── retrieval.py      # BM25 + Cross-Encoder hybrid search
│   │   ├── vision.py         # NVIDIA NIM API integration for image OCR
│   │   └── audio.py          # Groq Whisper API for voice transcription
│   ├── validation/
│   │   └── output.py         # CSV writing and validation
│   └── main.py               # Application entry point
├── dataset/                  # Expected directory for input CSVs
├── requirements.txt          # Python dependencies
└── .env                      # API keys
```

## Setup & Dependencies

1. **Python Version**: Python 3.9+ is recommended.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Key dependencies include `pandas`, `requests`, `pydantic`, `sentence-transformers` (for the local cross-encoder), and `rank_bm25`.*

3. **Environment Variables**:
   Create a `.env` file in the root directory with the following keys:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```

## Expected Files

The application expects the following CSV files in the `dataset/` directory:
- `messages.csv` (The input messages to route)
- `users.csv`
- `groups.csv`
- `group_members.csv`
- `businesses.csv`
- `user_business_relationships.csv`
- `message_history.csv`
- `message_events.csv`

## How to Run

To run the full pipeline and generate the routing decisions:

```bash
python -m code.main --input dataset/messages.csv --output dataset/output.csv
```

### Running the Evaluation (Sample Set)
To run the system on a smaller sample set and evaluate its accuracy against known ground truths:
```bash
python -m code.main --input dataset/sample_messages.csv --output dataset/sample_output.csv --evaluate
```

## Where the Decisions Happen

If you want to understand how the agent routes a message, follow this flow:

1. **Entry Point**: `code/main.py` reads the CSV and passes each row to `run_agent_for_message()`.
2. **Safety First**: Inside `code/agent/core.py`, it first calls `run_all_safety_gates()` (`code/safety/gates.py`). If a gate triggers, the decision is made instantly.
3. **The LLM Loop**: If no gate triggers, the message enters the `for turn in range(max_turns)` loop in `code/agent/core.py`. The LLM queries tools, analyzes the response, and eventually outputs a JSON decision.
4. **Validation & Correction**: The JSON is validated by Pydantic. If it fails, the error is fed back to the LLM to correct itself.
5. **The Final Override**: The validated decision is passed through `evaluate_decision()` (`code/evaluation/post_llm_evaluator.py`), which applies strict deterministic business rules before finalizing the output.

## Resilience & API Limits

The system is heavily engineered to survive rate limits:
- A mandatory `time.sleep(1.5)` before every Nemotron API call ensures we stay under the 40 requests/minute limit.
- A 6-tier exponential backoff handles unexpected `429 Too Many Requests` spikes.
- If the LLM completely fails, a context-aware `_smart_fallback()` ensures a safe, logical default rather than crashing the pipeline.
