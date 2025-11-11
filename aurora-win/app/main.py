import os
import asyncio 
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# --- 고급 서비스 임포트 ---
from app.aurora_dashboard_api_stub import dash_router
from app.security.audit_middleware import AuditMiddleware
from app.event_collector_redis_patch import EventCollectorRedis
from app.consent_collector import ConsentCollector
from app.consent_api import consent_router, _issue_pending_token, ConsentRequest as ConsentRequestModel
from app.event_sse_redis_router import sse_router as events_router
from app.rag_preview_router import preview_router

# --- 핵심 인지 기능 임포트 ---
from app.core import planner, verifier, executor
from app.core.planner_consent_gate import evaluate_consent, Plan
from app.security.policy import Policy
from app.memory.bandit import Bandit
from app.memory.store import DB

# --- [신규] Routine Builder 임포트 ---
from app.core.routine import load_routine_data
from app.core import smart_inbox


# --- 환경 설정 ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLICY_PATH = os.getenv("POLICY_PATH", "data/policy.json")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "data/audit.log")
METRICS_DB_PATH = os.getenv("METRICS_DB_PATH", "data/metrics.db")
BANDIT_STATE_PATH = os.getenv("BANDIT_STATE_PATH", "data/bandit_state.json")

# --- FastAPI 앱 초기화 ---
app = FastAPI(title="AURORA (Complete)", version="1.0")


# --- CORS 미들웨어 추가 (UI 접속 허용) ---
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 핵심 인지 모듈 로드 ---
try:
    policy = Policy.from_file(POLICY_PATH)
except FileNotFoundError:
    print(f"[WARN] Policy file not found at {POLICY_PATH}. Using default empty policy.")
    policy = Policy({})

bandit = Bandit(state_path=BANDIT_STATE_PATH) 
db = DB(METRICS_DB_PATH)

# --- 고급 서비스 및 미들웨어 로드 ---
app.add_middleware(AuditMiddleware, log_path=AUDIT_LOG_PATH)

collector = EventCollectorRedis(METRICS_DB_PATH, redis_url=REDIS_URL)
consent_collector = ConsentCollector(METRICS_DB_PATH)
app.state.collector = collector
app.state.consent = consent_collector
app.state.policy = policy
app.state.bandit = bandit

# --- 라우터 마운트 ---
app.include_router(dash_router, prefix="/dash")
app.include_router(consent_router, prefix="/consent")
app.include_router(events_router,  prefix="/events")
app.include_router(preview_router)

# --- FastAPI 라이프사이클 이벤트 ---
@app.on_event("startup")
async def _boot():
    await collector.start()
    await consent_collector.start()

@app.on_event("shutdown")
async def _stop():
    await consent_collector.stop()
    await collector.stop()

# --- 핵심 인지 API 엔드포인트 ---

@app.post("/aurora/plan")
async def plan_endpoint(req: dict):
    intent = req.get("input", "")
    ctx = req.get("context", {})
    plan_obj = await planner.make_plan(intent, ctx)
    return {"plan": plan_obj}

@app.post("/aurora/execute")
async def execute_endpoint(req: dict, fast_req: Request):
    plan_obj = req.get("plan")
    session_id = req.get("session_id", "default-session")
    
    if not plan_obj or not plan_obj.get("steps"):
        raise HTTPException(400, "Valid 'plan' with 'steps' is missing")

    risk = verifier.assess_risk(plan_obj, policy)
    
    first_step = plan_obj["steps"][0]
    gate_plan = Plan(
        intent=req.get("intent", first_step.get("tool")),
        tool=f"{first_step.get('tool')}.{first_step.get('op')}",
        args=first_step.get("args", {}),
        risk=risk
    )
    
    gate_decision = evaluate_consent(session_id, gate_plan)

    if "requires_consent" in gate_decision:
        # 동의 필요: 토큰을 발급하고 UI로 반환합니다.
        consent_payload = gate_decision["requires_consent"]
        
        try:
            consent_model = ConsentRequestModel(**consent_payload)
        except Exception as e:
            raise HTTPException(500, detail=f"Internal Error: Invalid Consent Payload Structure: {e}")
        
        # 토큰 발급 (동기 함수이므로 asyncio.to_thread 사용)
        token_response = await asyncio.to_thread(_issue_pending_token, consent_model) 
        
        # 발급된 토큰을 UI가 기대하는 'token' 필드에 추가합니다.
        consent_payload['token'] = token_response['consent_id'] 
        
        return {"requires_consent": consent_payload}


    # 동의가 필요 없으므로 즉시 실행합니다.
    result = await executor.run(
        plan_obj, 
        policy=policy, 
        collector=fast_req.app.state.collector,
        db=db, 
        bandit=bandit,
        session_id=session_id
    )
    return {"status": "ok", "result": result}

# --- Smart Inbox API ---
@app.post("/aurora/run-smart-inbox")
async def run_smart_inbox_endpoint(
    req: Request,
    limit: int = 3
):
    policy = req.app.state.policy
    db = DB(METRICS_DB_PATH) 
    
    results = await smart_inbox.process_inbox(
        policy=policy,
        db=db,
        limit=limit
    )
    
    return {"status": "ok", "processed": results}


# --- Routine Builder API ---
@app.post("/routine/run")
async def run_routine_endpoint(
    req: dict = Body(...), 
    fast_req: Request = None
):
    routine_name = req.get("name")
    if not routine_name:
        raise HTTPException(400, "Routine 'name' is missing")

    try:
        routine_data = load_routine_data(routine_name)
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load routine: {e}")

    plan_obj = {
        "intent": f"Routine: {routine_name}",
        "steps": routine_data.get("steps", [])
    }
    
    session_id = req.get("session_id", f"routine-{routine_name}")

    risk = verifier.assess_risk(plan_obj, policy)
    if risk == "high":
        raise HTTPException(403, 
            detail=f"Routine '{routine_name}' contains high-risk steps and cannot be run automatically.")

    collector = fast_req.app.state.collector
    
    result = await executor.run(
        plan_obj, 
        policy=policy, 
        collector=collector,
        db=db, 
        bandit=bandit,
        session_id=session_id
    )
    return {"status": "ok", "routine": routine_name, "result": result}