"""
Aurora Consent UI-API Bridge (FastAPI Router)
- Exposes REST endpoints to request consent and submit decisions
- Integrates with ConsentCollector and writes audit-friendly events

Mount:
    from consent_api import consent_router
    app.include_router(consent_router, prefix="/consent")
"""
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    # app/consent_collector.py에서 임포트
    from app.consent_collector import ConsentCollector, ConsentEvent
except ImportError:
    print("[ERROR] consent_api: Failed to import ConsentCollector. Check file location.")
    ConsentCollector = None
    ConsentEvent = None

consent_router = APIRouter()

# 임시 인메모리 요청 레지스트리 (단기)
_PENDING: dict[str, dict] = {}


class ConsentRequest(BaseModel):
    session_id: str = Field(..., description="UI/session identifier")
    action: str = Field(..., description="e.g., mail.send")
    purpose: str = Field(..., description="short purpose synopsis")
    scope: str = Field(..., description="mail|files|system|browser|nlp|ocr")
    risk: str = Field(..., pattern="^(low|medium|high)$")
    ttl_hours: int = Field(0, ge=0, le=168)
    # 'why'/'how'를 포함하는 'rationale' 추가 (UI가 필요로 함)
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


@consent_router.post("/request", response_model=ConsentRequestResp)
def request_consent(req: ConsentRequest):
    """
    (UI) -> (Server)
    UI가 동의 모달을 띄우기 직전에 호출하여, 
    안전한 'consent_id' (토큰)을 발급받습니다.
    """
    cid = str(uuid.uuid4())
    issued = datetime.utcnow().isoformat()+"Z"
    
    # 'requires_consent' 객체의 전체 내용을 페이로드로 저장
    payload = req.dict()
    
    _PENDING[cid] = {
        "session_id": req.session_id,
        "payload": payload,
        "issued_at": issued,
        "expires_at": time.time() + 600,  # 10분 윈도우
    }
    return {"consent_id": cid, "issued_at": issued, "payload": payload}


@consent_router.post("/decision", response_model=ConsentDecisionResp)
async def submit_decision(dec: ConsentDecision, request: Request):
    """
    (UI) -> (Server)
    사용자가 모달에서 [동의] 또는 [거부]를 클릭하면 호출됩니다.
    결정을 DB에 기록합니다.
    """
    rec = _PENDING.pop(dec.consent_id, None)
    if not rec:
        raise HTTPException(status_code=404, detail="Consent not found or expired")
    if time.time() > rec["expires_at"]:
        raise HTTPException(status_code=410, detail="Consent pending window expired")

    try:
        consent_collector: ConsentCollector = request.app.state.consent
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
        # Collector에 비동기 기록
        await consent_collector.record(ev)
    else:
        print("[WARN] consent_api: ConsentCollector not available. Decision not recorded to DB.")

    return {"status": dec.decision}