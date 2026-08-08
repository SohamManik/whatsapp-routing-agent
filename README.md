# Agentic Router: WhatsApp Notification AI

Agentic Router is an intelligent, full-stack WhatsApp message routing agent that decides if incoming multi-modal messages should be `notify`, `digest`, or `mute`. It solves the "Signal vs. Noise" problem in modern messaging apps by acting as a strict, context-aware personal assistant.

## The Architecture

The system uses a robust 3-layer architecture to handle strict API limits and LLM hallucinations, completely decoupled into a modern web stack:

### 1. Database (PostgreSQL / SQLite)
- Uses **SQLAlchemy** to store Users, Groups, Businesses, and Routing Decisions.
- Fast and reliable data layer, built to scale.

### 2. Backend (FastAPI)
- Exposes a REST API (`POST /webhook/whatsapp`) to receive messages from a WhatsApp bridge.
- Provides a **WebSocket stream** (`/ws/agent-stream`) to broadcast the AI's real-time "Thought Process".

### 3. Frontend (Next.js + Tailwind + Framer Motion)
- A stunning, glassmorphic UI to view incoming messages in real-time.
- **Agent Inspector**: Visually tracks the Nemotron LLM as it invokes tools (retrieving evidence, transcribing audio) and hits safety gates.

## The "Seam" (AI Logic)
1. **Pre-LLM Safety Gates (`code/safety/gates.py`)**: Fast, deterministic Python rules that instantly catch prompt injections, obvious scams, and opted-out promotions.
2. **Agentic LLM Loop (`code/agent/core.py`)**: A multi-turn reasoning engine powered by Nemotron 550B. The LLM has access to tools to fetch user context, retrieve historical evidence, analyze images, and transcribe voice notes.
3. **Post-LLM Evaluator (`code/evaluation/post_llm_evaluator.py`)**: A deterministic Python layer that overrides the LLM if it violates hard user constraints (e.g., failing to mute an explicitly muted group).

## How to Run Locally

You can spin up the entire Full-Stack application (Database, FastAPI, Next.js) using Docker Compose.

1. Create a `.env` file in the root directory:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```
2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
3. Open `http://localhost:3000` in your browser to view the Live Feed and Agent Inspector.

## Project Structure
```
├── code/
│   ├── api/          # FastAPI app (webhooks and websockets)
│   ├── agent/        # Nemotron multi-turn agent loop
│   ├── db/           # SQLAlchemy models and SQLite migration scripts
│   ├── evaluation/   # Post-LLM deterministic evaluator
│   ├── safety/       # Pre-LLM safety gates
│   └── tools/        # Tools for LLM (vision, audio, retrieval, context)
├── frontend/         # Next.js App Router project (Dashboard)
├── dataset/          # Source CSV data and SQLite DB
├── docker-compose.yml
├── Dockerfile.backend
└── Dockerfile.frontend
```
