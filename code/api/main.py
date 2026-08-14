import asyncio
import json
from typing import List, Optional
from datetime import datetime

import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, BackgroundTasks, Request, Response
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from code.agent.core import run_agent_for_message
from code.db.database import get_db
from code.db import models

app = FastAPI(title="WhatsApp Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                pass

manager = ConnectionManager()

@app.websocket("/ws/agent-stream")
async def agent_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(models.RoutingDecision.id)).scalar() or 0
    notify = db.query(func.count(models.RoutingDecision.id)).filter(models.RoutingDecision.action == "notify").scalar() or 0
    digest = db.query(func.count(models.RoutingDecision.id)).filter(models.RoutingDecision.action == "digest").scalar() or 0
    mute = db.query(func.count(models.RoutingDecision.id)).filter(models.RoutingDecision.action == "mute").scalar() or 0
    return {"total": total, "notify_count": notify, "digest_count": digest, "mute_count": mute}

class MessageFilterResponse(BaseModel):
    messages: List[dict]
    total: int
    page: int
    limit: int

@app.get("/api/messages", response_model=MessageFilterResponse)
def get_messages(
    page: int = 1,
    limit: int = 20,
    action: Optional[str] = None,
    search: Optional[str] = None,
    conversation_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Message, models.RoutingDecision).outerjoin(
        models.RoutingDecision, models.Message.message_id == models.RoutingDecision.message_id
    )
    if search:
        query = query.filter(models.Message.message_text.ilike(f"%{search}%"))
    if conversation_type:
        query = query.filter(models.Message.conversation_type == conversation_type)
    if action:
        query = query.filter(models.RoutingDecision.action == action)
        
    total = query.count()
    offset = (page - 1) * limit
    results = query.order_by(models.Message.created_at.desc()).offset(offset).limit(limit).all()
    
    messages = []
    for msg, dec in results:
        m_dict = {k: v for k, v in msg.__dict__.items() if not k.startswith('_')}
        if dec:
            m_dict["decision"] = {k: v for k, v in dec.__dict__.items() if not k.startswith('_')}
        messages.append(m_dict)
        
    return {"messages": messages, "total": total, "page": page, "limit": limit}

@app.get("/api/messages/{message_id}")
def get_message_detail(message_id: str, db: Session = Depends(get_db)):
    msg = db.query(models.Message).filter(models.Message.message_id == message_id).first()
    if not msg:
        return {"error": "Message not found"}
    dec = db.query(models.RoutingDecision).filter(models.RoutingDecision.message_id == message_id).first()
    
    m_dict = {k: v for k, v in msg.__dict__.items() if not k.startswith('_')}
    if dec:
        m_dict["decision"] = {k: v for k, v in dec.__dict__.items() if not k.startswith('_')}
        
    sender_info = None
    if msg.sender_user_id:
        user = db.query(models.User).filter(models.User.user_id == msg.sender_user_id).first()
        if user:
            sender_info = {k: v for k, v in user.__dict__.items() if not k.startswith('_')}
    elif msg.business_id:
        biz = db.query(models.BusinessAccount).filter(models.BusinessAccount.business_id == msg.business_id).first()
        if biz:
            sender_info = {k: v for k, v in biz.__dict__.items() if not k.startswith('_')}
            
    m_dict["sender_info"] = sender_info
    return m_dict

@app.get("/api/messages/{message_id}/traces")
def get_message_traces(message_id: str, db: Session = Depends(get_db)):
    traces = db.query(models.ReasoningTrace).filter(models.ReasoningTrace.message_id == message_id).order_by(models.ReasoningTrace.step_order.asc()).all()
    return [{k: v for k, v in t.__dict__.items() if not k.startswith('_')} for t in traces]

def process_message_background(payload: dict, loop: asyncio.AbstractEventLoop):
    def emit_event(event_type: str, data: dict):
        try:
            if not loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({"type": event_type, "data": data}),
                    loop
                )
        except Exception:
            pass

    try:
        try:
            decision = run_agent_for_message(payload, emit_event)
        except Exception as e:
            import logging
            logging.error(f"Agent failed entirely for {payload.get('message_id')}: {e}")
            from code.agent.schemas import RoutingDecision, SAFE_FALLBACK
            decision = RoutingDecision(
                message_id=payload.get("message_id", "unknown"),
                **SAFE_FALLBACK
            )
            decision.reason = "System timeout or unexpected error. Fallback applied."
            
        db = next(get_db())
        try:
            db_decision = models.RoutingDecision(
                message_id=decision.message_id,
                action=decision.action,
                message_type=decision.message_type,
                reason=decision.reason,
                confidence=decision.confidence,
                evidence_message_ids=decision.evidence_message_ids
            )
            existing = db.query(models.RoutingDecision).filter_by(message_id=decision.message_id).first()
            if existing:
                db.delete(existing)
            db.add(db_decision)
            db.commit()
            emit_event("decision_finalized", decision.model_dump() if hasattr(decision, "model_dump") else decision.dict())
        finally:
            db.close()
    except Exception as e:
        print(f"Error processing background message: {e}")

@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Verification Endpoint"""
    verify_token = os.getenv("META_VERIFY_TOKEN", "my_secret_token_123")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print("Webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    return Response(status_code=403)

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Determine if this is a Meta payload or our internal test payload
    is_meta_payload = payload.get("object") == "whatsapp_business_account"
    
    if is_meta_payload:
        # Parse Meta's deeply nested payload
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]["value"]
            
            # Sometimes Meta sends status updates (read/delivered) instead of messages
            if "messages" not in changes:
                return {"status": "ignored"}
                
            msg_data = changes["messages"][0]
            contact_data = changes.get("contacts", [{}])[0]
            
            message_id = msg_data.get("id")
            sender_phone = msg_data.get("from")
            
            # Extract text if available
            message_text = ""
            if msg_data.get("type") == "text":
                message_text = msg_data["text"]["body"]
                
            # If the user has a profile name, we can prepend it or store it, 
            # but for our LLM, we just pass the text.
            
            # Convert timestamp
            timestamp_int = int(msg_data.get("timestamp", 0))
            created_at = datetime.utcfromtimestamp(timestamp_int).isoformat() + "Z" if timestamp_int else datetime.utcnow().isoformat()
            
            # Build mapped payload for our agent
            internal_payload = {
                "message_id": message_id,
                "user_id": "u_001",  # Hardcoded to our demo user
                "sender_user_id": sender_phone,
                "group_id": None,
                "business_id": None,
                "message_text": message_text,
                "media_type": None,
                "media_id": None,
                "conversation_type": "personal",
                "forwarded_count": 0,
                "is_broadcast": 0,
                "created_at": created_at
            }
        except (KeyError, IndexError) as e:
            print(f"Failed to parse Meta payload: {e}")
            return Response(status_code=400)
    else:
        # Fallback to our internal test schema (for the Live Monitor "Send Test Message" feature)
        internal_payload = payload

    existing_msg = db.query(models.Message).filter_by(message_id=internal_payload.get("message_id")).first()
    if not existing_msg:
        db_msg = models.Message(
            message_id=internal_payload.get("message_id"),
            user_id=internal_payload.get("user_id"),
            sender_user_id=internal_payload.get("sender_user_id"),
            group_id=internal_payload.get("group_id"),
            business_id=internal_payload.get("business_id"),
            message_text=internal_payload.get("message_text"),
            media_type=internal_payload.get("media_type"),
            media_id=internal_payload.get("media_id"),
            conversation_type=internal_payload.get("conversation_type", "personal"),
            forwarded_count=internal_payload.get("forwarded_count", 0),
            is_broadcast=internal_payload.get("is_broadcast", 0),
            created_at=internal_payload.get("created_at") or datetime.utcnow().isoformat()
        )
        db.add(db_msg)
        db.commit()

    loop = asyncio.get_running_loop()
    background_tasks.add_task(process_message_background, internal_payload, loop)
    
    return {"status": "processing", "message_id": internal_payload.get("message_id")}

@app.get("/api/digest/summary")
def get_digest_summary(db: Session = Depends(get_db)):
    from code.agent.core import call_nemotron
    
    decisions = db.query(models.RoutingDecision).filter(models.RoutingDecision.action == "digest").order_by(models.RoutingDecision.id.desc()).limit(15).all()
    if not decisions:
        return {"summary": "No digested messages found recently."}
        
    msg_ids = [d.message_id for d in decisions]
    messages = db.query(models.Message).filter(models.Message.message_id.in_(msg_ids)).all()
    texts = [f"From {m.sender_user_id or m.group_id or m.business_id}: {m.message_text}" for m in messages if m.message_text]
    
    if not texts:
        return {"summary": "No text messages found in recent digests."}
        
    prompt = "You are a helpful assistant. Summarize these low-priority WhatsApp messages into a short, cohesive summary (max 3 bullet points) for the user to read at the end of the day:\n\n" + "\n".join(texts)
    
    try:
        res = call_nemotron([{"role": "user", "content": prompt}])
        content = res["choices"][0]["message"]["content"]
        return {"summary": content}
    except Exception as e:
        return {"summary": f"Could not generate summary at this time (Error: {e})"}
