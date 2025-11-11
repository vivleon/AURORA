from __future__ import annotations
import uuid
import time
import asyncio 
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any # Any를 import

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from app.consent_collector import ConsentCollector, ConsentEvent
except ImportError:
    print("[ERROR] consent_api: Failed to import ConsentCollector. Check app/consent_collector.py")
    ConsentCollector = None
    ConsentEvent = None

consent_router = APIRouter()

_PENDING: dict[str, dict] = {}


class ConsentRequest(BaseModel):
    session_id: str = Field(..., description="UI/session identifier")
    action: str = Field(..., description="e.g., mail.send")
    purpose: str = Field(..., description="short purpose synopsis")
    scope: str = Field(..., description="mail|files|system|browser|nlp|ocr")
    risk: str = Field(..., pattern="^(low|medium|high)$")
    ttl_hours: int = Field(0, ge=0, le=168)
    rationale: Optional[Dict[str, str]] = None

class ConsentRequestResp(BaseModel):
    consent_id: str
    issued_at: str
    payload: dict

class ConsentDecision(BaseModel):
    consent_id: str
    decision: str = Field(..., pattern="^(approved|denied)$")

class ConsentDecisionResp(BaseModel):
    status: str

def _issue_pending_token(req: ConsentRequest) -> Dict[str, Any]:
    cid = str(uuid.uuid4())
    issued = datetime.utcnow().isoformat()+"Z"
    
    payload = req.dict()
    
    _PENDING[cid] = {
        "session_id": req.session_id,
        "payload": payload,
        "issued_at": issued,
        "expires_at": time.time() + 600,  # 10분 윈도우
    }
    
    return {"consent_id": cid, "issued_at": issued, "payload": payload}


@consent_router.post("/request", response_model=ConsentRequestResp)
def request_consent(req: ConsentRequest):
    token_response = _issue_pending_token(req)
    return token_response 


@consent_router.post("/decision", response_model=ConsentDecisionResp)
async def submit_decision(dec: ConsentDecision, request: Request):
    rec = _PENDING.pop(dec.consent_id, None)
    if not rec:
        raise HTTPException(status_code=404, detail="Consent not found or expired")
    if time.time() > rec["expires_at"]:
        raise HTTPException(status_code=410, detail="Consent pending window expired")

    try:
        # [FIX] List 대신 Any를 사용하여 타입 에러 해결
        consent_collector: Any = request.app.state.consent
    except Exception:
        print("[ERROR] consent_api: 'app.state.consent' (ConsentCollector) not found.")
        consent_collector = None

    if consent_collector and ConsentEvent:
        payload = rec["payload"]
        ev = ConsentEvent(
            session_id=rec["session_id"],
            action=payload.get("action", "unknown_action"),
            decision=dec.decision,
            risk=payload.get("risk", "low"),
            ttl_hours=payload.get("ttl_hours", 0),
        )
        await consent_collector.record(ev)
    else:
        print("[WARN] consent_api: ConsentCollector not available. Decision not recorded to DB.")

    return {"status": dec.decision}