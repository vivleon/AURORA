"""
Aurora Consent UI-API Bridge (FastAPI Router)
- Exposes REST endpoints to request consent and submit decisions
- Integrates with ConsentCollector and writes audit-friendly events

Mount:
    from consent_api import consent_router
    app.include_router(consent_router, prefix="/consent")

UI Flow (typical):
  1) Client calls POST /consent/request with action, purpose, scope, risk, ttl
  2) Server returns consent_id + payload → UI renders modal
  3) Client posts decision to POST /consent/decision {consent_id, decision}
  4) Router persists via ConsentCollector and returns status
"""
from __future__ import annotations
import uuid, time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    # Optional import; the app should wire actual instance on startup
    from consent_collector import ConsentCollector, ConsentEvent
except Exception:
    ConsentCollector = None
    ConsentEvent = None

consent_router = APIRouter()

# in-memory request registry (short-lived)
_PENDING: dict[str, dict] = {}


class ConsentRequest(BaseModel):
    session_id: str = Field(..., description="UI/session identifier")
    action: str = Field(..., description="e.g., mail.send")
    purpose: str = Field(..., description="short purpose synopsis")
    scope: str = Field(..., description="mail|files|system|browser|nlp|ocr")
    risk: str = Field(..., pattern="^(low|medium|high)$")
    ttl_hours: int = Field(0, ge=0, le=168)

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
    cid = str(uuid.uuid4())
    issued = datetime.utcnow().isoformat()+"Z"
    payload = {
        "action": req.action,
        "purpose": req.purpose,
        "scope": req.scope,
        "risk": req.risk,
        "ttl_hours": req.ttl_hours,
    }
    _PENDING[cid] = {
        "session_id": req.session_id,
        "payload": payload,
        "issued_at": issued,
        "expires_at": time.time() + 600,  # 10m pending window
    }
    return {"consent_id": cid, "issued_at": issued, "payload": payload}


@consent_router.post("/decision", response_model=ConsentDecisionResp)
def submit_decision(dec: ConsentDecision):
    rec = _PENDING.pop(dec.consent_id, None)
    if not rec:
        raise HTTPException(status_code=404, detail="Consent not found or expired")
    if time.time() > rec["expires_at"]:
        raise HTTPException(status_code=410, detail="Consent pending window expired")

    # wire to collector if available (app.state.consent)
    from fastapi import Request
    # Using request object via dependency would be cleaner; keeping simple here
    import inspect
    frame = inspect.currentframe()
    while frame and "request" not in frame.f_locals:
        frame = frame.f_back
    request = frame.f_locals.get("request") if frame else None

    try:
        consent: ConsentCollector = request.app.state.consent  # type: ignore
    except Exception:
        consent = None  # fallback

    if consent and ConsentEvent:
        ev = ConsentEvent(
            session_id=rec["session_id"],
            action=rec["payload"]["action"],
            decision=dec.decision,
            risk=rec["payload"]["risk"],
            ttl_hours=rec["payload"]["ttl_hours"],
        )
        # fire-and-forget is acceptable; but we block to guarantee persistence here
        import anyio
        anyio.run(consent.record, ev)  # sync call into async method for simplicity

    return {"status": dec.decision}
