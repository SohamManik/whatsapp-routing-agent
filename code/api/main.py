import asyncio
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
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

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(payload: dict, db: Session = Depends(get_db)):
    """
    Simulated webhook. Expects a row-like dict.
    Runs the agent in a background thread to not block FastAPI.
    """
    existing_msg = db.query(models.Message).filter_by(message_id=payload.get("message_id")).first()
    if not existing_msg:
        db_msg = models.Message(
            message_id=payload.get("message_id"),
            user_id=payload.get("user_id"),
            sender_user_id=payload.get("sender_user_id"),
            group_id=payload.get("group_id"),
            business_id=payload.get("business_id"),
            message_text=payload.get("message_text"),
            media_type=payload.get("media_type"),
            media_id=payload.get("media_id"),
            conversation_type=payload.get("conversation_type", "personal"),
            forwarded_count=payload.get("forwarded_count", 0),
            is_broadcast=payload.get("is_broadcast", 0),
            created_at=payload.get("created_at")
        )
        db.add(db_msg)
        db.commit()

    loop = asyncio.get_running_loop()
    
    def emit_event(event_type: str, data: dict):
        try:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({"type": event_type, "data": data}),
                loop
            )
        except Exception:
            pass

    decision = await asyncio.to_thread(run_agent_for_message, payload, emit_event)
    
    # Save decision to db
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
        db.commit()
        
    db.add(db_decision)
    db.commit()
    
    emit_event("decision_finalized", decision.dict())
    return decision.dict()

@app.get("/api/messages")
def get_messages(db: Session = Depends(get_db)):
    msgs = db.query(models.Message).order_by(models.Message.created_at.desc()).limit(100).all()
    result = []
    for m in msgs:
        d = db.query(models.RoutingDecision).filter_by(message_id=m.message_id).first()
        m_dict = m.__dict__.copy()
        m_dict.pop('_sa_instance_state', None)
        
        d_dict = d.__dict__.copy() if d else None
        if d_dict:
            d_dict.pop('_sa_instance_state', None)
            
        result.append({
            "message": m_dict,
            "decision": d_dict
        })
    return result
