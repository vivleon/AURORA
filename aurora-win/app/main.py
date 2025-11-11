import os
from fastapi import FastAPI, HTTPException, Request, Body

# --- 고급 서비스 임포트 (aurora-win/aurora-win/app/main.py 기반) ---
from app.aurora_dashboard_api_stub import dash_router
from app.security.audit_middleware import AuditMiddleware
from app.event_collector_redis_patch import EventCollectorRedis # 멀티워커용 Redis 패치 버전
from app.consent_collector import ConsentCollector
from app.consent_api import consent_router
from app.event_sse_redis_router import sse_router as events_router
from app.rag_preview_router import preview_router

# --- 핵심 인지 기능 임포트 (aurora-win/app/main.py 기반) ---
from app.core import planner, verifier, executor
# 'planner_consent_gate'는 'execute' 엔드포인트에서 직접 사용됩니다.
from app.core.planner_consent_gate import evaluate_consent, Plan
from app.security.policy import Policy
from app.memory.bandit import Bandit # 업데이트된 Bandit (Thompson Sampling)
from app.memory.store import DB # DB 스텁 (필요시)

# --- [신규] Routine Builder 임포트 ---
from app.core.routine import load_routine_data
from app.core import smart_inbox # [신규]


# --- 환경 설정 ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLICY_PATH = os.getenv("POLICY_PATH", "data/policy.json")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "data/audit.log")
METRICS_DB_PATH = os.getenv("METRICS_DB_PATH", "data/metrics.db")
BANDIT_STATE_PATH = os.getenv("BANDIT_STATE_PATH", "data/bandit_state.json")

# --- FastAPI 앱 초기화 ---
app = FastAPI(title="AURORA (Complete)", version="1.0")

# --- 핵심 인지 모듈 로드 ---
try:
    policy = Policy.from_file(POLICY_PATH)
except FileNotFoundError:
    print(f"[WARN] Policy file not found at {POLICY_PATH}. Using default empty policy.")
    policy = Policy({}) # 빈 정책으로 폴백

# Bandit은 더 이상 DB를 사용하지 않고 bandit_state.json을 사용합니다.
bandit = Bandit(state_path=BANDIT_STATE_PATH) 
db = DB(METRICS_DB_PATH) # DB 스텁 (다른 모듈이 필요로 할 수 있음)

# --- 고급 서비스 및 미들웨어 로드 ---
app.add_middleware(AuditMiddleware, log_path=AUDIT_LOG_PATH)

collector = EventCollectorRedis(METRICS_DB_PATH, redis_url=REDIS_URL)
consent_collector = ConsentCollector(METRICS_DB_PATH)
app.state.collector = collector
app.state.consent = consent_collector
app.state.policy = policy # 정책 객체를 state에 추가
app.state.bandit = bandit # Bandit 객체를 state에 추가

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

# --- 핵심 인지 API 엔드포인트 (병합 및 수정) ---

@app.post("/aurora/plan")
async def plan_endpoint(req: dict):
    """
    사용자 입력(intent)을 받아 실행 계획(plan)을 생성합니다.
    """
    intent = req.get("input", "")
    ctx = req.get("context", {})
    
    # [수정] 'planner.make_plan'은 async 함수이므로 'await'가 필요합니다.
    plan_obj = await planner.make_plan(intent, ctx)
    
    return {"plan": plan_obj}

@app.post("/aurora/execute")
async def execute_endpoint(req: dict, fast_req: Request):
    """
    Plan을 실행합니다. 
    고위험 작업 시, 동의 게이트를 통과시켜 'requires_consent' 객체를 반환합니다.
    """
    plan_obj = req.get("plan")
    session_id = req.get("session_id", "default-session")
    
    if not plan_obj or not plan_obj.get("steps"):
        raise HTTPException(400, "Valid 'plan' with 'steps' is missing")

    # 1. 위험도 평가 (Verifier 사용)
    risk = verifier.assess_risk(plan_obj, policy)

    # 2. 동의 게이트 평가 (planner_consent_gate 사용)
    #
    # 참고: 이 로직은 단일 단계(step)를 가정합니다.
    # 멀티-스텝 계획의 경우, 첫 번째 고위험 단계를 기준으로 평가해야 합니다.
    # 여기서는 단순화를 위해 첫 번째 스텝을 Plan 객체로 변환합니다.
    
    first_step = plan_obj["steps"][0]
    gate_plan = Plan(
        intent=req.get("intent", first_step.get("tool")),
        tool=f"{first_step.get('tool')}.{first_step.get('op')}",
        args=first_step.get("args", {}),
        risk=risk
    )
    
    # planner_consent_gate.py의 evaluate_consent 호출
    gate_decision = evaluate_consent(session_id, gate_plan)

    if "requires_consent" in gate_decision:
        # 동의 필요: UI가 처리할 수 있도록 동의 요청 객체를 반환합니다.
        return gate_decision

    # 3. 실행 (Executor 사용)
    # 동의가 필요 없으므로 즉시 실행합니다.
    #
    # 중요: executor.run의 시그니처를 수정하여 'audit' 대신 'collector'를 전달합니다.
    result = await executor.run(
        plan_obj, 
        policy=policy, 
        collector=fast_req.app.state.collector, # 'audit' 대신 'collector' 전달
        db=db, 
        bandit=bandit,
        session_id=session_id
    )
    return {"status": "ok", "result": result}

# --- [신규] Smart Inbox API (자동화 워크플로우) ---
@app.post("/aurora/run-smart-inbox")
async def run_smart_inbox_endpoint(
    req: Request,
    limit: int = 3
):
    """
    Smart Inbox 자동화 워크플로우를 실행합니다.
    (Routine이 아닌 복잡한 워크플로우 예시)
    """
    # app state에서 의존성 가져오기
    policy = req.app.state.policy
    db = DB(METRICS_DB_PATH) # (store.py가 상태를 갖지 않으므로 새로 생성)
    
    # app/core/smart_inbox.py의 함수 호출
    results = await smart_inbox.process_inbox(
        policy=policy,
        db=db,
        limit=limit
    )
    
    return {"status": "ok", "processed": results}


# --- [신규] Routine Builder API (Week 2 목표) ---
@app.post("/routine/run")
async def run_routine_endpoint(
    req: dict = Body(...), 
    fast_req: Request = None
):
    """
    data/routines/에 정의된 YAML 루틴을 이름으로 실행합니다.
    (30일 계획 섹션 4 API)
    """
    routine_name = req.get("name")
    if not routine_name:
        raise HTTPException(400, "Routine 'name' is missing")

    try:
        # app/core/routine.py에서 YAML 로드
        routine_data = load_routine_data(routine_name)
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load routine: {e}")

    # 실행을 위해 Plan 객체 형식으로 변환
    plan_obj = {
        "intent": f"Routine: {routine_name}",
        "steps": routine_data.get("steps", [])
    }
    
    session_id = req.get("session_id", f"routine-{routine_name}")

    # [중요] 루틴도 동의 게이트를 통과해야 합니다.
    risk = verifier.assess_risk(plan_obj, policy)
    if risk == "high":
        # 고위험 루틴은 자동 실행을 차단하고,
        # 향후 루틴용 동의 UI가 구현되어야 함을 알림.
        raise HTTPException(403, 
            detail=f"Routine '{routine_name}' contains high-risk steps and cannot be run automatically.")

    # app state에서 의존성 가져오기
    collector = fast_req.app.state.collector
    
    # 기존 Executor 재사용
    result = await executor.run(
        plan_obj, 
        policy=policy, 
        collector=collector,
        db=db, 
        bandit=bandit,
        session_id=session_id
    )
    return {"status": "ok", "routine": routine_name, "result": result}