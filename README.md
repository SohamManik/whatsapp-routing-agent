# 🧠 Agentic Router: WhatsApp Notification AI

Agentic Router is an intelligent, full-stack WhatsApp message routing agent that decides whether incoming multi-modal messages should be **Notify**, **Digest**, or **Mute**. It solves the "Signal vs. Noise" problem in modern messaging apps by acting as a strict, context-aware personal assistant that lives natively on the Meta WhatsApp Cloud API.

Built as a robust resume piece, this project demonstrates production-grade full-stack engineering, LLM Agent design patterns, and seamless third-party API integration.

---

## 🏗️ System Architecture

The system uses a highly resilient 3-layer architecture completely decoupled into a modern web stack, designed to mitigate LLM hallucinations and handle strict API constraints:

### 1. Database (SQLite WAL Mode / PostgreSQL)
- **SQLAlchemy ORM** stores Users, Groups, Businesses, Messages, and AI Routing Decisions.
- Implements `PRAGMA journal_mode=WAL` for high concurrency, preventing database lock errors during heavy webhook traffic.

### 2. Backend API (FastAPI)
- **Meta Webhook (`POST /webhook/whatsapp`)**: A highly optimized endpoint that parses deeply nested Meta Cloud API JSON payloads and maps them to internal schemas.
- **Verification Endpoint (`GET /webhook/whatsapp`)**: Handles Meta's secure `hub.challenge` handshake using the `META_VERIFY_TOKEN`.
- **Background Processing**: Webhooks are instantly acknowledged with `200 OK`, while the heavy LLM agent processing is handed off to FastAPI `BackgroundTasks`.
- **Reasoning Traces API**: Exposes the internal "Thought Process" of the AI for the frontend to render.

### 3. Frontend Dashboard (Next.js 15 + Tailwind v4)
- A stunning, professional dashboard inspired by Linear and Vercel design systems.
- **Live Monitor**: Watch incoming WhatsApp messages get routed in real-time.
- **Reasoning Timeline**: Visually tracks the LLM as it invokes tools, retrieves evidence, and hits safety gates.
- **Daily Digest**: An AI-summarized briefing of all low-priority "Digested" messages.

---

## 🤖 The "Seam" (Agentic AI Logic)

The AI logic is split into a robust "Seam" pattern, ensuring the LLM is tightly controlled by deterministic rules:

1. **Pre-LLM Safety Gates (`code/safety/gates.py`)**: Fast, deterministic Python rules that instantly catch prompt injections, obvious scams, and opted-out promotions before wasting LLM tokens.
2. **Agentic LLM Loop (`code/agent/core.py`)**: A multi-turn reasoning engine powered by a large language model (e.g., Nemotron / Llama 3.1). The LLM has access to tools to fetch user context, retrieve historical evidence, analyze images, and transcribe voice notes.
3. **Post-LLM Evaluator (`code/evaluation/post_llm_evaluator.py`)**: A strict deterministic Python layer that overrides the LLM if it violates hard user constraints (e.g., failing to notify the user if their name `@Vivek` is explicitly mentioned, even in a muted group).

---

## 🚀 Deployment Guide (Production)

This project is fully containerized and production-ready for deployment to Render and Vercel.

### 1. Backend to Render (API)
1. Fork or clone this repository to your GitHub.
2. Go to **Render.com** > New Web Service > Connect GitHub repository.
3. Configure the service:
   - **Environment:** Docker
   - **Dockerfile Path:** `./Dockerfile.backend`
   - **Branch:** `main`
4. Add your Environment Variables:
   - `META_VERIFY_TOKEN`: Your secret string (e.g., `my_secret_token_123`)
   - `NEMOTRON_API_KEY`: Your LLM API key
5. Deploy! Render will build the Docker container and give you a live URL (e.g., `https://agentic-api.onrender.com`).

### 2. Meta WhatsApp Webhook Integration
1. Go to the **Meta Developer Portal** > Your App > WhatsApp > Configuration.
2. Set the **Callback URL** to `https://agentic-api.onrender.com/webhook/whatsapp`.
3. Set the **Verify Token** to the exact token you put in Render (`my_secret_token_123`).
4. Click Verify. Subscribe to the `messages` webhook field.

### 3. Frontend to Vercel (Dashboard)
1. Go to **Vercel.com** > Add New Project > Connect GitHub repository.
2. Set the **Root Directory** to `frontend`.
3. Add an Environment Variable:
   - `NEXT_PUBLIC_API_URL`: Your live Render URL (`https://agentic-api.onrender.com`).
4. Click Deploy. Your dashboard is now live globally!

---

## 💻 Local Development Setup

If you want to run this locally for testing or modification:

### Prerequisites
- Python 3.10+
- Node.js 18+
- Ngrok or Localtunnel (for Meta webhook testing)

### Backend
```bash
# Install dependencies
pip install -r requirements.txt
pip install sqlalchemy fastapi uvicorn websockets

# Run the server
uvicorn code.api.main:app --reload
```

### Public Tunnel (for local Meta testing)
```bash
npx --yes localtunnel --port 8000
# Paste the resulting URL into Meta Developer Portal
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 📂 Project Structure
```text
├── code/
│   ├── api/          # FastAPI app (endpoints and background tasks)
│   ├── agent/        # Multi-turn LLM agent loop
│   ├── db/           # SQLAlchemy models and SQLite connection
│   ├── evaluation/   # Post-LLM deterministic evaluator (Overrides)
│   ├── safety/       # Pre-LLM safety gates
│   └── tools/        # Tools for LLM (vision, audio, retrieval)
├── frontend/         # Next.js App Router project
│   ├── app/          # Pages (Dashboard, Live Monitor, Digest)
│   ├── components/   # Reusable UI components
│   └── lib/          # API Client
├── dataset/          # Source CSV data
├── Dockerfile.backend
└── README.md
```
